# frame.md — Encore short video (60 s, vertical)

Design spec for the [hyperframes](https://github.com/heygen-com/hyperframes) composition in this
folder. This file inverts the app's design system for the camera: every scene of the video must
look like it came out of the Encore iOS app.

## Canvas

- **Format**: 1080 × 1920 (9:16 vertical — Reels / TikTok / Shorts).
- **Frame rate**: 30 fps. **Duration**: 60 s.
- **Safe areas**: keep text inside the central 1080 × 1550; top 180 px and bottom 190 px are
  covered by platform UI (username, caption, tab bar).

## Reference: app screens (rebuilt in HTML)

The visual truth is the real app UI, as seen on Jade's iPhone (25 Jul 2026). Since the
composition is HTML anyway, the two screens are **recreated as HTML components** in
`index.html` (class `.phone`) instead of compositing PNGs — pixel-crisp at any size, no
asset files needed:

| Component | Mirrors | What it shows |
|---|---|---|
| Timeline (scene 3) | **Phone** tab | Live setlist: left rail of timestamps with green dot markers, one glass card per matched track (*Blue Velvet — Bobby Vinton*…), "La setlist · live" label. |
| Capture Vibe (scene 6) | **Pendant** tab | "CAPTURE VIBE" glass card: waveform bars, `TRACKS / FPS / BATTERY` stats row, orange privacy hand. |

If real screenshots land in `assets/` later, they can replace the replicas 1:1 — but keep
the replicas as the default (they animate, screenshots don't).

## Brand layer ("Feel the beat")

The logo redesign (heart outline + heartbeat line, pink-peach gradient on dark plum) is used
for the bookends only — scene 2 (reveal) and scene 8 (end card). The logo is inline SVG in
`index.html`. In-app scenes keep the green palette below; never mix the two in one scene.

| Token | Value | Use |
|---|---|---|
| `--brand-bg` | `#1C1626` | Brand-scene background (dark plum) |
| `--brand-1` | `#F9A8D4` | Gradient start (pink) |
| `--brand-2` | `#E0699B` | Gradient mid (rose) — tagline text |
| `--brand-3` | `#FBCFA4` | Gradient end (peach) |

## Color tokens

Taken from the screenshots — the whole video lives in this palette:

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0A0F08` | Global background (near-black green) |
| `--room-green` | `#5A7A1E` | Party-light wash, gradients, glows |
| `--lime` | `#B6E354` | Highlight light beams, waveform peaks |
| `--accent` | `#30D158` | Encore green: logo loop, live dots, active tab, LED pin flash |
| `--glass` | `rgba(120, 150, 80, 0.28)` | Card fills (always with `backdrop-filter: blur(24px)`) |
| `--glass-stroke` | `rgba(255, 255, 255, 0.18)` | 1 px card borders |
| `--text` | `#FFFFFF` | Primary text |
| `--text-dim` | `rgba(255, 255, 255, 0.55)` | Secondary text (artist names, timestamps, labels) |
| `--privacy` | `#FF6B3D` | Privacy hand glyph, "listening cut" states |
| `--fail-red` | `#FF453A` | Only for the Shazam-fails beat (scene 4) |

## Type

System stack, mirroring iOS: `-apple-system, "SF Pro Display", "Helvetica Neue", sans-serif`.

- **Punchlines** (one per scene): 72–96 px, weight 700, tight leading (1.05), white.
- **Labels** ("CAPTURE VIBE" style): 28 px, weight 600, UPPERCASE, `letter-spacing: 0.18em`,
  `--text-dim`.
- **Track cards**: title 40 px / 600 / white; artist 32 px / 400 / `--text-dim`.
- **Stats** (0 / 50 / 100%): 64 px, weight 700, tabular numerals.

## Components

- **Glass card**: `--glass` fill, `--glass-stroke` border, radius 28 px, blur 24 px. Same
  proportions as the app cards.
- **Timeline entry**: timestamp (`--text-dim`) + dot (`--accent`) + glass card. New entries
  animate in: fade + 24 px slide-up, 400 ms ease-out — one at a time, ~1 s apart, like live
  matches landing.
- **Waveform**: row of thin vertical bars (like the CAPTURE VIBE card), animating heights;
  `--text` at 80 % opacity, peaks tinted `--lime`.
- **LED pin flash**: full-frame white flash 80 ms → decay to `--accent` glow 400 ms. Used once,
  at the drop (scene 5).
- **Logo**: the green loop glyph (Dynamic Island in the screenshots) + wordmark
  `E N C O R E` in label style.

## Motion rules

- Cuts on the beat: scene changes every 6–10 s, aligned to the music grid (assume 124 BPM,
  bar ≈ 1.94 s).
- Animations are CSS/WAAPI only, deterministic (hyperframes seeks frame-by-frame — no
  `Math.random()` at render time, no video-element autoplay assumptions).
- Camera feel: slow scale 1.0 → 1.06 on full-bleed backgrounds (Ken Burns), never on UI
  screenshots (UI stays pixel-crisp, subtle parallax ≤ 12 px allowed).
- Dark, warm, party-lit. No pure white backgrounds anywhere.

## Audio

- The music bed is **generated, not sourced**: `python3 make_bed.py` writes
  `assets/bed.wav` (60 s house, 124 BPM, riser 31–38 s, drop at exactly 38 s = the LED
  flash). Deterministic (fixed seed) — same file every run. hyperframes only muxes audio,
  it does not compose it.
- To swap in a real track later, just replace `assets/bed.wav` (keep the drop at ~38 s or
  retime scene 6).
- Optional French VO; on-screen punchlines carry the message without sound.
