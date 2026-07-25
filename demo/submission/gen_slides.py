#!/usr/bin/env python3
"""Generate demo/submission/slides.html — 3 fixed-canvas 1920x1080 slides for the
hackathon submission media. Each slide recreates one app screenshot inside an
iPhone mockup (Pendant / Phone / Demo tabs) over a club-style background.

Render to PNG with demo/submission/render.mjs (headless Chromium).
Optionally embeds Inter as base64 if a woff2 path is passed: gen_slides.py <inter.woff2>
"""
import base64
import math
import sys
from pathlib import Path

OUT = Path(__file__).parent / "slides.html"

# ---------------------------------------------------------------- helpers

def frac(i, salt=0.0):
    """Deterministic pseudo-random in [0,1)."""
    x = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return x - math.floor(x)


def waveform(n=44, mode="uniform", w=317, h=54, salt=1.0):
    bar_w = 4.0
    gap = (w - n * bar_w) / (n - 1)
    rects = []
    for i in range(n):
        if mode == "uniform":
            bh = h * 0.44 + frac(i, salt) * 7
        else:  # two-hump envelope like the SESSION LIVE card
            env = 0.22 + 0.78 * abs(math.sin(i / n * math.pi * 2.0 - 0.4))
            bh = h * (0.10 + 0.78 * env * (0.8 + 0.2 * frac(i, salt)))
        x = i * (bar_w + gap)
        y = (h - bh) / 2
        rects.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bh:.1f}" rx="2"/>')
    return (f'<svg class="wf" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="rgba(255,255,255,0.92)">{"".join(rects)}</svg>')


# ---------------------------------------------------------------- icons (inline SVG)

def _svg(inner, size=22, stroke=True):
    s = ('fill="none" stroke="currentColor" stroke-width="1.9" '
         'stroke-linecap="round" stroke-linejoin="round"') if stroke else 'fill="currentColor"'
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {s}>{inner}</svg>'


def ic_wave(size=22):
    bars = []
    for i, (x, h) in enumerate([(4, 8), (8, 14), (12, 20), (16, 14), (20, 8)]):
        bars.append(f'<rect x="{x - 1.2}" y="{12 - h / 2}" width="2.4" height="{h}" rx="1.2"/>')
    return _svg("".join(bars), size, stroke=False)


def ic_broadcast(size=18):
    return _svg(
        '<circle cx="12" cy="12" r="1.7" fill="currentColor" stroke="none"/>'
        '<path d="M8.6 15.4a4.8 4.8 0 0 1 0-6.8"/><path d="M15.4 8.6a4.8 4.8 0 0 1 0 6.8"/>'
        '<path d="M5.8 18.2a8.8 8.8 0 0 1 0-12.4"/><path d="M18.2 5.8a8.8 8.8 0 0 1 0 12.4"/>',
        size)


def ic_mic(size=18):
    return _svg(
        '<rect x="9.2" y="2.8" width="5.6" height="11" rx="2.8" fill="currentColor" stroke="none"/>'
        '<path d="M6 11.5a6 6 0 0 0 12 0"/><path d="M12 17.5V21"/><path d="M8.5 21h7"/>',
        size)


def ic_play(size=13):
    return _svg('<path d="M7 4.5 19 12 7 19.5Z"/>', size, stroke=False)


def ic_phone(size=22):
    return _svg('<rect x="7" y="2.5" width="10" height="19" rx="3"/><path d="M10.5 18.5h3"/>', size)


def ic_music(size=22):
    return _svg(
        '<path d="M4 6.5h9"/><path d="M4 12h9"/><path d="M4 17.5h5"/>'
        '<circle cx="16.5" cy="17" r="2.4" fill="currentColor" stroke="none"/>'
        '<path d="M18.9 17V7.2l2.6 1"/>',
        size)


def ic_gear(size=22):
    teeth = "".join(
        f'<rect x="11" y="1.6" width="2" height="4.4" rx="1" transform="rotate({a} 12 12)" '
        'fill="currentColor" stroke="none"/>' for a in range(0, 360, 45))
    return _svg(teeth + '<circle cx="12" cy="12" r="4.6"/><circle cx="12" cy="12" r="1.6" '
                'fill="currentColor" stroke="none"/>', size)


def ic_wand(size=18):
    return _svg(
        '<path d="M12 2.5 13.6 8 19 9.6 13.6 11.2 12 16.7 10.4 11.2 5 9.6 10.4 8Z" '
        'fill="currentColor" stroke="none"/>'
        '<path d="M18.5 15.5 19.3 18 21.8 18.8 19.3 19.6 18.5 22.1 17.7 19.6 15.2 18.8 17.7 18Z" '
        'fill="currentColor" stroke="none"/>',
        size)


def ic_signal():
    bars, out = [(3, 5), (8, 8), (13, 11), (18, 14)], []
    for i, (x, h) in enumerate(bars):
        op = "1" if i < 2 else "0.35"
        out.append(f'<rect x="{x}" y="{17 - h}" width="3.4" height="{h}" rx="1.2" opacity="{op}"/>')
    return f'<svg width="19" height="13" viewBox="0 0 23 17" fill="currentColor">{"".join(out)}</svg>'


def ic_wifi():
    return ('<svg width="18" height="13" viewBox="0 0 24 18" fill="none" stroke="currentColor" '
            'stroke-width="2.2" stroke-linecap="round">'
            '<path d="M2 6a15 15 0 0 1 20 0"/><path d="M5.5 10a10 10 0 0 1 13 0"/>'
            '<path d="M9 13.6a5 5 0 0 1 6 0"/><circle cx="12" cy="16.4" r="1.4" '
            'fill="currentColor" stroke="none"/></svg>')


def ic_battery(level=1.0, charging=False, label=""):
    fill_w = 18 * level
    fill_col = "#9be15d" if charging else "rgba(255,255,255,0.95)"
    bolt = ('<path d="M13.2 3.5 9.8 9h2.6l-1.6 4.5L14.6 8h-2.7l1.3-4.5Z" fill="#fff" '
            'stroke="#3a4a1e" stroke-width="0.8"/>') if charging else ""
    txt = (f'<text x="10.8" y="9.4" text-anchor="middle" font-size="9" font-weight="700" '
           f'fill="#1a1a1a">{label}</text>') if label else ""
    txt_fill = "rgba(255,255,255,0.9)" if label else fill_col
    return (f'<svg width="27" height="13" viewBox="0 0 27 13">'
            f'<rect x="0.5" y="0.5" width="21" height="12" rx="3.5" fill="none" '
            f'stroke="rgba(255,255,255,0.5)"/>'
            f'<rect x="2" y="2" width="{fill_w:.0f}" height="9" rx="2" fill="{txt_fill}"/>'
            f'<rect x="23" y="4" width="2.5" height="5" rx="1.2" fill="rgba(255,255,255,0.5)"/>'
            f'{bolt}{txt}</svg>')


# ---------------------------------------------------------------- phone chrome

def statusbar(time, kind):
    if kind == "5g-charging":
        right = f'{ic_signal()}<span class="net">5G</span>{ic_battery(0.9, charging=True)}'
    else:  # wifi-58
        right = f'{ic_signal()}{ic_wifi()}{ic_battery(0.58, label="58")}'
    return (f'<div class="status"><span class="time">{time}</span>'
            f'<span class="sicons">{right}</span></div>')


def tabbar(active):
    items = [("Pendant", ic_wave(22)), ("Phone", ic_phone(22)),
             ("Demo", ic_music(22)), ("Settings", ic_gear(22))]
    tabs = "".join(
        f'<div class="tab{" active" if name == active else ""}">{icon}<span>{name}</span></div>'
        for name, icon in items)
    return f'<div class="tabbar">{tabs}</div>'


def card_head(icon, label):
    return (f'<div class="chead"><span class="chico">{icon}</span>'
            f'<span class="clabel">{label}</span><span class="bcast">{ic_broadcast()}</span></div>')


def stats(cols):
    cells = "".join(f'<div class="stat"><b>{v}</b><i>{k}</i></div>' for v, k in cols)
    return f'<div class="stats">{cells}</div>'


def sect(title, right):
    return f'<div class="sect"><h3>{title}</h3><span>{right}</span></div>'


def track_card(title, artist, meta=None, desc=None, quote=None, listen=False, cls=""):
    h = [f'<div class="tcard{" " + cls if cls else ""}">',
         f'<div class="tt">{title}</div>', f'<div class="ta">{artist}</div>']
    if meta:
        h.append(f'<div class="tm">{meta}</div>')
    if desc:
        h.append(f'<div class="td">{desc}</div>')
    if quote:
        h.append(f'<div class="tq">&laquo;&nbsp;{quote}&nbsp;&raquo;</div>')
    if listen:
        h.append(f'<div class="lpill">{ic_play()}<span>&Eacute;couter l\'extrait</span></div>')
    h.append("</div>")
    return "".join(h)


def trow(time, card, ring=False):
    dot = '<span class="ring"></span>' if ring else "<span></span>"
    return (f'<div class="trow"><div class="ttime">{time}</div>'
            f'<div class="tdot">{dot}</div><div class="tbody">{card}</div></div>')


# ---------------------------------------------------------------- screen backgrounds

def bg_green(salt=0):
    beams = "".join(
        f'<i class="beam" style="left:{l}%;top:{t}%;height:{h}%;width:{w}px;opacity:{o}"></i>'
        for l, t, h, w, o in [(52, 4, 55, 9, .95), (60, 2, 62, 13, .8),
                              (74, 6, 48, 7, .65), (38, 8, 34, 6, .4)])
    crowd = "".join(
        f'<b style="left:{l}%;bottom:{b}px;width:{w}px;height:{h}px"></b>'
        for l, b, w, h in [(-12, -55, 260, 190), (25, -70, 300, 200),
                           (58, -50, 280, 180), (85, -60, 220, 170)])
    return (f'<div class="scr-bg green"><div class="ceil"></div><div class="glow"></div>'
            f'{beams}<div class="crowd">{crowd}</div><div class="tint g"></div></div>')


def bg_warm():
    beams = "".join(
        f'<i class="beam warmb" style="left:{l}%;top:{t}%;height:{h}%;width:{w}px;opacity:{o}"></i>'
        for l, t, h, w, o in [(30, 2, 40, 8, .55), (48, 0, 50, 11, .7), (68, 4, 36, 7, .45)])
    crowd = "".join(
        f'<b style="left:{l}%;bottom:{b}px;width:{w}px;height:{h}px"></b>'
        for l, b, w, h in [(-15, 120, 240, 260), (20, 90, 300, 300),
                           (55, 110, 280, 280), (82, 130, 230, 240)])
    return (f'<div class="scr-bg warm"><div class="glow warmg"></div>{beams}'
            f'<div class="crowd warmc">{crowd}</div><div class="tint w"></div></div>')


# ---------------------------------------------------------------- the three screens

def screen_pendant():
    return f'''<div class="screen">{bg_green()}<div class="sc">
{statusbar("16:46", "5g-charging")}
<div class="eyeb">ENCORE</div>
<div class="h1">Pendant</div>
<div class="sub">25 Jul 2026 at 16:40 &middot; en direct</div>
<div class="gcard">{card_head(ic_wave(17), "CAPTURE VIBE")}{waveform(46, "uniform", salt=3)}
{stats([("1", "TRACKS"), ("49", "FPS"), ("100%", "BATTERY")])}</div>
{sect("La setlist", "live &middot; 1 tracks")}
<div class="botfade g"></div>
<div class="timeline">
{trow("16:45", track_card("Titre inconnu", "Afrobeats", meta="188 BPM",
      desc="A club recording capturing background crowd chatter in French alongside an "
           "energetic Afrobeats track playing with prom&hellip;",
      quote="I don't know why they did it again look at the score", listen=True), ring=True)}
</div>
{tabbar("Pendant")}</div></div>'''


def screen_phone():
    rows = [
        trow("16:52", track_card("Titre inconnu", "Techno", meta="83 BPM",
             desc="An energetic electronic club track featuring a driving kick drum beat, "
                  "rhythmic synth bass, and subtle percussion.", listen=True)),
        trow("16:52", track_card("Fools Gold", "The Stone Roses")),
        trow("16:53", track_card("Titre inconnu", "Synthwave", meta="61 BPM",
             desc="A bright, retro 80s-style synthesizer melody plays over a rhythmic "
                  "tapping beat.", listen=True)),
        trow("16:53", track_card("LFO", "LFO")),
    ]
    return f'''<div class="screen">{bg_warm()}<div class="sc">
{statusbar("17:02", "wifi-58")}
<div class="h1" style="margin-top:10px">Phone</div>
<div class="sub">micro iphone &middot; sans pendentif</div>
<div class="gcard mic-card">{card_head(ic_mic(17), "MICRO IPHONE")}{waveform(46, "uniform", salt=7)}
<div class="listen-big">{ic_mic(19)}<span>&Eacute;couter</span></div></div>
{sect("La setlist", "live &middot; 10 tracks")}
<div class="timeline">{"".join(rows)}</div>
<div class="botfade w"></div>
{tabbar("Phone")}</div></div>'''


def screen_demo():
    rows = [
        trow("00:00", track_card("One More Time", "Daft Punk", meta="123 BPM &middot; 5:20")),
        trow("04:12", track_card("Music Sounds Better With You", "Stardust",
                                 meta="122 BPM &middot; 7:03", cls="rainbow")),
        trow("08:47", track_card("Lady (Hear Me Tonight)", "Modjo", meta="126 BPM &middot; 5:00")),
        trow("13:26", track_card("Finally", "Kings of Tomorrow")),
        trow("18:05", track_card("You Don't Know Me", "Armand Van Helden")),
    ]
    return f'''<div class="screen">{bg_green(salt=9)}<div class="sc">
{statusbar("16:50", "5g-charging")}
<div class="eyeb">ENCORE</div>
<div class="h1">One More Time</div>
<div class="sub">DJ Set &middot; 1 h 24 min &middot; Paris &middot; 24 Jul 2026</div>
<div class="gcard">{card_head(ic_wave(17), "SESSION LIVE")}{waveform(46, "humps", salt=5)}
{stats([("12", "TRACKS"), ("1h24", "DUR&Eacute;E"), ("125", "AVG BPM")])}</div>
{sect("La setlist", "extrait &middot; 00:00 &rarr; 58:37")}
<div class="timeline">{"".join(rows)}</div>
<div class="botfade g"></div>
<div class="playlist-btn">{ic_wand()}<span>G&eacute;n&eacute;rer une playlist</span></div>
{tabbar("Demo")}</div></div>'''


# ---------------------------------------------------------------- slides

SLIDES = [
    dict(num="01", step="01 &middot; CAPTURE", title="Wear the<br>night.",
         para="A pendant with a mic streams the party to your iPhone over Wi&#8209;Fi. "
              "Gemma&nbsp;4 runs fully on-device and gives every unknown track an ID card "
              "&mdash; genre, BPM, vibe and a line caught from the crowd.",
         chips=["XIAO ESP32-S3", "WI-FI / UDP STREAM", "100% ON-DEVICE"],
         screen=screen_pendant, accent="rgba(125,195,70,0.22)"),
    dict(num="02", step="02 &middot; IDENTIFY", title="No pendant?<br>No problem.",
         para="Phone-mic mode builds the same live setlist straight from your pocket "
              "&mdash; ShazamKit for known tracks, embeddings and Gemma&nbsp;4 for "
              "everything the catalogs don't know.",
         chips=["SHAZAMKIT", "EMBEDDINGS MATCH", "GEMMA 4 E2B"],
         screen=screen_phone, accent="rgba(215,175,90,0.20)"),
    dict(num="03", step="03 &middot; RELIVE", title="Get your<br>night back.",
         para="Wake up to a timestamped setlist with transitions, highlights and audio "
              "extracts &mdash; then turn the whole night into a playlist in one tap.",
         chips=["TIMESTAMPED SETLIST", "HIGHLIGHTS", "MUSICKIT PLAYLIST"],
         screen=screen_demo, accent="rgba(125,195,70,0.22)"),
]

BRAND_MARK = ('<svg width="26" height="26" viewBox="0 0 26 26" fill="none">'
              '<circle cx="13" cy="13" r="10" stroke="#9be15d" stroke-width="3.2"/>'
              '<circle cx="20.5" cy="19.5" r="3.4" fill="#0b0e06" stroke="#9be15d" '
              'stroke-width="2.4"/></svg>')


def slide(s):
    chips = "".join(f'<span class="chip">{c}</span>' for c in s["chips"])
    return f'''<div class="slide" data-canvas-width="1920" data-canvas-height="1080">
<div class="sbg" style="--accent:{s["accent"]}"></div>
<div class="brand">{BRAND_MARK}<span>ENCORE</span></div>
<div class="copy">
  <div class="eyebrow">{s["step"]}</div>
  <h2>{s["title"]}</h2>
  <p>{s["para"]}</p>
  <div class="chips">{chips}</div>
</div>
<div class="phone-wrap"><div class="phone-glow" style="background:radial-gradient(closest-side,{s["accent"]},transparent 70%)"></div>
<div class="phone"><div class="island"></div>{s["screen"]()}</div></div>
<div class="footnote">Encore &mdash; the pendant that remembers your party &middot; Gemma 4 Hackathon, Paris &middot; July 2026</div>
<div class="pagenum">{s["num"]} / 03</div>
</div>'''


# ---------------------------------------------------------------- css

def font_css():
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        b64 = base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
        return ("@font-face{font-family:'Inter';font-style:normal;font-weight:100 900;"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');"


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#222;font-family:'Inter',-apple-system,'Helvetica Neue',sans-serif;
     -webkit-font-smoothing:antialiased}

/* ---- slide canvas ---- */
.slide{position:relative;width:1920px;height:1080px;overflow:hidden;color:#fff;margin:0 auto}
.sbg{position:absolute;inset:0;background:
  radial-gradient(1000px 760px at 71% 45%, var(--accent), transparent 68%),
  radial-gradient(1400px 1000px at 15% 110%, rgba(60,90,25,0.18), transparent 70%),
  linear-gradient(160deg,#161c0c 0%,#0d1207 45%,#060803 100%)}
.sbg::after{content:'';position:absolute;inset:0;
  background:radial-gradient(1600px 1100px at 50% 50%, transparent 60%, rgba(0,0,0,0.55))}
.brand{position:absolute;left:64px;top:56px;display:flex;align-items:center;gap:14px;
  font-weight:800;font-size:19px;letter-spacing:7px;color:#b5e878}
.copy{position:absolute;left:120px;top:50%;transform:translateY(-50%);width:660px}
.eyebrow{font-size:15px;letter-spacing:5px;font-weight:700;color:#9be15d}
.copy h2{font-size:74px;font-weight:800;line-height:1.04;letter-spacing:-2px;margin-top:20px}
.copy p{margin-top:28px;font-size:23px;line-height:1.55;color:rgba(255,255,255,0.72)}
.chips{display:flex;gap:12px;margin-top:38px;flex-wrap:wrap}
.chip{padding:10px 17px;border:1px solid rgba(255,255,255,0.22);border-radius:999px;
  font-size:12.5px;letter-spacing:2px;font-weight:600;color:rgba(255,255,255,0.85);
  background:rgba(255,255,255,0.05)}
.footnote{position:absolute;left:64px;bottom:46px;font-size:15px;color:rgba(255,255,255,0.4)}
.pagenum{position:absolute;right:64px;bottom:46px;font-size:15px;letter-spacing:3px;
  color:rgba(255,255,255,0.4)}

/* ---- phone mockup ---- */
.phone-wrap{position:absolute;top:50%;right:190px;transform:translateY(-50%)}
.phone-glow{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  width:860px;height:860px;pointer-events:none}
.phone{position:relative;width:417px;height:876px;background:#101408;border-radius:64px;
  padding:12px;box-shadow:0 0 0 2px rgba(255,255,255,0.16),0 12px 30px rgba(0,0,0,0.5),
  0 45px 100px rgba(0,0,0,0.65)}
.island{position:absolute;top:25px;left:50%;transform:translateX(-50%);width:112px;
  height:32px;background:#000;border-radius:18px;z-index:6}
.screen{position:relative;width:393px;height:852px;border-radius:52px;overflow:hidden}

/* ---- in-screen backgrounds ---- */
.scr-bg{position:absolute;inset:0}
.scr-bg.green{background:linear-gradient(180deg,#4c5e27 0%,#39481d 28%,#243014 62%,#0f1607 100%)}
.scr-bg.warm{background:linear-gradient(180deg,#8f7f52 0%,#7d6a45 38%,#57452c 72%,#2c2214 100%)}
.ceil{position:absolute;inset:0 0 52% 0;opacity:.55;background:
  repeating-linear-gradient(180deg,rgba(255,255,255,0.07) 0 2px,transparent 2px 36px),
  repeating-linear-gradient(90deg,rgba(0,0,0,0.12) 0 3px,transparent 3px 92px)}
.beam{position:absolute;border-radius:6px;filter:blur(5px);
  background:linear-gradient(180deg,rgba(255,255,235,0.95),rgba(220,255,150,0.25) 65%,transparent)}
.beam.warmb{background:linear-gradient(180deg,rgba(255,250,230,0.9),rgba(255,230,170,0.2) 65%,transparent)}
.glow{position:absolute;width:430px;height:330px;left:34%;top:26%;filter:blur(12px);
  background:radial-gradient(closest-side,rgba(230,255,170,0.45),transparent)}
.glow.warmg{background:radial-gradient(closest-side,rgba(255,235,180,0.4),transparent);top:14%}
.crowd b{position:absolute;background:#0b1105;border-radius:50%;filter:blur(18px)}
.crowd.warmc b{background:#241a0e}
.tint{position:absolute;inset:0}
.tint.g{background:linear-gradient(180deg,rgba(140,190,60,0.16),rgba(18,26,8,0.5) 88%)}
.tint.w{background:linear-gradient(180deg,rgba(150,170,80,0.18),rgba(35,26,14,0.5) 88%)}

/* ---- screen content ---- */
.sc{position:absolute;inset:0;padding:0 20px;font-size:15px}
.status{display:flex;justify-content:space-between;align-items:center;height:54px;
  padding:8px 10px 0}
.status .time{font-size:16.5px;font-weight:600}
.sicons{display:flex;align-items:center;gap:7px}
.net{font-size:13.5px;font-weight:600}
.eyeb{margin-top:10px;font-size:12px;letter-spacing:3.5px;font-weight:700;
  color:rgba(235,255,215,0.9)}
.h1{font-size:38px;font-weight:800;letter-spacing:-0.5px;margin-top:3px}
.sub{font-size:15.5px;color:rgba(255,255,255,0.82);margin-top:5px}

.gcard{margin-top:14px;background:rgba(255,255,255,0.13);border:1px solid rgba(255,255,255,0.28);
  border-radius:26px;padding:14px 16px;backdrop-filter:blur(18px);
  box-shadow:0 8px 30px rgba(0,0,0,0.18)}
.gcard .wf{display:block;margin:9px auto 1px}
.mic-card{border:1.5px solid rgba(150,220,90,0.65)}
.chead{display:flex;align-items:center;gap:9px}
.chico{display:flex;color:rgba(255,255,255,0.95)}
.clabel{font-size:12.5px;letter-spacing:2.5px;font-weight:700}
.bcast{margin-left:auto;display:flex;color:#c9f29a}
.stats{display:flex;margin-top:8px}
.stat{flex:1;text-align:center;padding:5px 0}
.stat + .stat{border-left:1px solid rgba(255,255,255,0.22)}
.stat b{display:block;font-size:28px;font-weight:800;letter-spacing:-0.5px}
.stat i{display:block;font-style:normal;font-size:10.5px;letter-spacing:2px;font-weight:600;
  color:rgba(255,255,255,0.7);margin-top:3px}
.listen-big{margin:14px 4px 4px;height:54px;border-radius:999px;background:rgba(10,14,6,0.72);
  display:flex;align-items:center;justify-content:center;gap:10px;font-size:16.5px;
  font-weight:600}

.sect{display:flex;justify-content:space-between;align-items:baseline;margin:18px 2px 10px}
.sect h3{font-size:24px;font-weight:800}
.sect span{font-size:13.5px;color:rgba(255,255,255,0.68)}

.timeline{position:relative}
.timeline::before{content:'';position:absolute;left:61px;top:10px;bottom:4px;width:1.5px;
  background:rgba(255,255,255,0.28)}
.trow{display:flex;margin-bottom:2px}
.ttime{width:48px;text-align:right;font-size:13.5px;font-weight:600;padding-top:5px;
  color:rgba(255,255,255,0.92)}
.tdot{width:29px;display:flex;justify-content:center;padding-top:8px;position:relative}
.tdot span{width:9px;height:9px;border-radius:50%;background:#fff}
.tdot .ring{background:transparent;border:2.5px solid #fff;width:11px;height:11px}
.tbody{flex:1;padding-bottom:10px}
.tcard{background:rgba(255,255,255,0.13);border:1px solid rgba(255,255,255,0.26);
  border-radius:22px;padding:12px 15px;backdrop-filter:blur(16px)}
.tcard.rainbow{position:relative;border-color:transparent;
  background:rgba(255,255,255,0.17)}
.tcard.rainbow::before{content:'';position:absolute;inset:-1px;border-radius:22px;
  padding:2.5px;background:linear-gradient(100deg,#ffb3ba,#e6c5ff,#bdb2ff,#9bf6ff,#caffbf,#ffc6ff);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
.tt{font-size:18px;font-weight:700;letter-spacing:-0.2px}
.ta{font-size:14.5px;color:rgba(255,255,255,0.78);margin-top:1px}
.tm{font-size:13px;color:rgba(255,255,255,0.62);margin-top:5px}
.td{font-size:13.5px;line-height:1.42;color:rgba(255,255,255,0.82);margin-top:8px}
.tq{font-size:13.5px;line-height:1.4;color:rgba(255,255,255,0.68);margin-top:7px}
.lpill{display:inline-flex;align-items:center;gap:8px;margin-top:11px;padding:8px 14px;
  border-radius:999px;background:rgba(8,12,4,0.4);font-size:13.5px;font-weight:600}

.botfade{position:absolute;left:0;right:0;bottom:0;height:215px;z-index:3;pointer-events:none}
.botfade.g{background:linear-gradient(180deg,transparent,rgba(14,20,7,0.72) 55%,rgba(12,17,6,0.94))}
.botfade.w{background:linear-gradient(180deg,transparent,rgba(40,31,18,0.72) 55%,rgba(30,23,12,0.94))}
.playlist-btn{position:absolute;left:16px;right:16px;bottom:108px;height:56px;z-index:4;
  border-radius:999px;background:rgba(28,36,14,0.78);backdrop-filter:blur(20px);
  border:1px solid rgba(255,255,255,0.2);display:flex;align-items:center;
  justify-content:center;gap:11px;font-size:17.5px;font-weight:600;
  box-shadow:0 10px 30px rgba(0,0,0,0.35)}
.tabbar{position:absolute;left:14px;right:14px;bottom:14px;height:78px;z-index:5;
  border-radius:999px;background:rgba(16,20,8,0.74);backdrop-filter:blur(22px);
  border:1px solid rgba(255,255,255,0.12);display:flex;align-items:center;padding:6px}
.tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:4px;font-size:12px;font-weight:600;color:rgba(255,255,255,0.88);height:66px;
  border-radius:999px}
.tab.active{color:#9be15d;background:rgba(255,255,255,0.1)}
"""


def main():
    slides = "\n".join(slide(s) for s in SLIDES)
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Encore &mdash; submission slides</title>
<meta name="hz:slide-selector" content=".slide"/>
<meta name="hz:canvas-width" content="1920"/>
<meta name="hz:canvas-height" content="1080"/>
<style>
{font_css()}
{CSS}
</style>
</head>
<body>
{slides}
</body>
</html>'''
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
