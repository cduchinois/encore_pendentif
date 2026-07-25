#!/usr/bin/env python3
"""Synthesize the 60s music bed for the Encore short (assets/bed.wav).

House, 124 BPM, arranged to the storyboard grid:
  0-6s   intro (filtered, muffled — scene 1 "phone kills the moment")
  6-31s  groove (kick + bass + hats + pad)
  31-38s riser (energy climbs, kick drops out at the end)
  38s    THE DROP (lands on scene 6's LED flash)
  52-60s outro (elements fall away, fade)

Deterministic by construction (fixed seed) — re-running gives the same file.
Only needs numpy: python3 make_bed.py
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 124
BEAT = 60.0 / BPM          # 0.4839 s
BAR = 4 * BEAT
DUR = 60.0
N = int(DUR * SR)
DROP = 38.0

rng = np.random.default_rng(2026_07_25)
t = np.arange(N) / SR


def seg(start, end):
    """Boolean mask for a time window."""
    return (t >= start) & (t < end)


def env(x, attack, decay):
    """Exponential attack/decay envelope over a local time axis x (seconds)."""
    return np.clip(x / max(attack, 1e-4), 0, 1) * np.exp(-np.maximum(x, 0) / decay)


def lowpass(x, cutoff):
    """One-pole lowpass, cheap and stable."""
    alpha = 1.0 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


mix = np.zeros(N)

# --- Kick: every beat, out during the last riser bar (36-38s) and after 56s.
kick = np.zeros(N)
beat_times = np.arange(0, DUR, BEAT)
for bt in beat_times:
    if 36.06 <= bt < DROP or bt >= 56.0:
        continue
    i0 = int(bt * SR)
    n = int(0.35 * SR)
    x = np.arange(min(n, N - i0)) / SR
    f = 140 * np.exp(-x / 0.035) + 48
    phase = 2 * np.pi * np.cumsum(f) / SR
    kick[i0:i0 + len(x)] += np.sin(phase) * np.exp(-x / 0.12)
    kick[i0:i0 + len(x)] += rng.standard_normal(len(x)) * np.exp(-x / 0.004) * 0.4  # click
mix += kick * 0.9

# --- Sidechain envelope driven by the kick grid (ducks bass/pad after each kick).
duck = np.ones(N)
for bt in beat_times:
    i0 = int(bt * SR)
    n = int(BEAT * SR)
    x = np.arange(min(n, N - i0)) / BEAT
    duck[i0:i0 + len(x)] = np.minimum(duck[i0:i0 + len(x)], 0.25 + 0.75 * x ** 1.5)

# --- Bass: Am / F / C / G loop, one root per bar, saw -> lowpass, sidechained.
ROOTS = [55.0, 43.65, 65.41, 49.0]  # A1 F1 C2 G1
bass = np.zeros(N)
for b, bar_t in enumerate(np.arange(0, DUR, BAR)):
    f0 = ROOTS[b % 4]
    i0 = int(bar_t * SR)
    n = int(min(BAR * SR, N - i0))
    x = np.arange(n) / SR
    saw = 2 * ((x * f0) % 1.0) - 1.0
    bass[i0:i0 + n] += saw
bass = lowpass(bass, 220) * duck
mix += bass * 0.55

# --- Hats: offbeat closed hats (8ths), out before 6s.
hat = np.zeros(N)
for ht in np.arange(BEAT / 2, DUR, BEAT):
    if ht < 6.0 or ht >= 56.0:
        continue
    i0 = int(ht * SR)
    n = int(0.06 * SR)
    x = np.arange(min(n, N - i0)) / SR
    noise = rng.standard_normal(len(x))
    hat[i0:i0 + len(x)] += (noise - np.concatenate(([0], noise[:-1]))) * np.exp(-x / 0.02)
mix += hat * 0.16

# --- Pad: Am7-ish stack, slow, sidechained, enters at 13s (timeline scene).
pad = np.zeros(N)
for f0 in (220.0, 261.63, 329.63, 392.0):  # A3 C4 E4 G4
    detune = 1 + rng.uniform(-0.002, 0.002)
    pad += np.sin(2 * np.pi * f0 * detune * t) + 0.5 * np.sin(2 * np.pi * f0 * detune * 2 * t)
pad = lowpass(pad, 900) * duck
fade_in = np.clip((t - 13.0) / 4.0, 0, 1)
mix += pad * 0.10 * fade_in

# --- Riser into the drop: noise sweep + rising tone, 31 -> 38s.
m = seg(31.0, DROP)
x = (t[m] - 31.0) / (DROP - 31.0)
sweep = rng.standard_normal(m.sum()) * (0.05 + 0.30 * x ** 2)
tone = np.sin(2 * np.pi * (220 + 660 * x ** 2) * t[m]) * 0.12 * x
mix[m] += sweep + tone

# --- Drop impact: sub boom + crash at exactly 38s.
i0 = int(DROP * SR)
n = int(1.6 * SR)
x = np.arange(min(n, N - i0)) / SR
mix[i0:i0 + len(x)] += np.sin(2 * np.pi * 42 * x) * np.exp(-x / 0.5) * 0.9
crash = rng.standard_normal(len(x)) * np.exp(-x / 0.9)
mix[i0:i0 + len(x)] += lowpass(crash, 9000) * 0.25

# --- Section shaping: muffled intro, full after the drop, fade-out at the end.
brightness = np.where(t < 6.0, 0.5, 1.0)
mix *= brightness
muffled = lowpass(mix.copy(), 600)
blend = np.clip((t - 5.0) / 2.0, 0, 1)          # open the filter across 5-7s
mix = muffled * (1 - blend) + mix * blend
mix[t >= DROP] *= 1.12                            # post-drop lift
mix *= np.clip((DUR - t) / 4.0, 0, 1) ** 0.8 * np.clip(t / 0.05, 0, 1)  # out/in fades

# --- Normalize with soft clip, write 16-bit mono WAV.
mix = np.tanh(mix / (np.percentile(np.abs(mix), 99.5) + 1e-9) * 1.2) * 0.92
out = Path(__file__).parent / "assets" / "bed.wav"
with wave.open(str(out), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {DUR:.0f}s @ {BPM} BPM, drop at {DROP}s)")
