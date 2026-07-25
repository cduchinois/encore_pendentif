#!/usr/bin/env python3
"""Generate landing/index.html — the Encore preorder landing page.

Reuses the phone-mockup CSS/components from demo/submission/gen_slides.py.
The hero phone shows the real "One More Time" session screen, recreated over
the app's actual background asset (ios/.../BackgroundImage.png, downscaled).

Usage:
    python3 gen_landing.py [assets_dir] [stripe_payment_link_url]

assets_dir may contain (all optional, page degrades gracefully):
    inter-400.woff2      UI font, embedded base64
    fraunces-600.woff2   logo font, embedded base64
    bg_screen.jpg        downscaled app background for the phone screen

The Stripe URL defaults to a placeholder; create the real one in the Stripe
Dashboard (Payment Links -> new -> one-time, 42.00 EUR) and re-run, or
search-replace the placeholder directly in index.html.
"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "demo" / "submission"))
from gen_slides import (  # noqa: E402
    CSS as MOCK_CSS, card_head, ic_wand, ic_wave, ic_wifi, sect, stats,
    track_card, trow, waveform,
)

OUT = Path(__file__).parent / "index.html"
ASSETS = Path(sys.argv[1]) if len(sys.argv) > 1 else None

STRIPE_LINK = sys.argv[2] if len(sys.argv) > 2 else "https://buy.stripe.com/REPLACE_WITH_PAYMENT_LINK"
PRICE = "42€"
DELIVERY = "1 October 2026"


def _asset(name):
    if ASSETS and (ASSETS / name).exists():
        return (ASSETS / name).read_bytes()
    return None


def font_css():
    css = []
    inter = _asset("inter-400.woff2")
    if inter:
        css.append("@font-face{font-family:'Inter';font-style:normal;font-weight:100 900;"
                   f"src:url(data:font/woff2;base64,{base64.b64encode(inter).decode()}) format('woff2');}}")
    else:
        css.append("@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');")
    fraunces = _asset("fraunces-600.woff2")
    if fraunces:
        css.append("@font-face{font-family:'Fraunces';font-style:normal;font-weight:600;"
                   f"src:url(data:font/woff2;base64,{base64.b64encode(fraunces).decode()}) format('woff2');}}")
    else:
        css.append("@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600&display=swap');")
    return "\n".join(css)


def bg_img_tag():
    jpg = _asset("bg_screen.jpg")
    if jpg:
        return f'<img class="bgimg" alt="" src="data:image/jpeg;base64,{base64.b64encode(jpg).decode()}"/>'
    return '<div class="bgimg" style="background:linear-gradient(180deg,#b9cfa0,#8fae78 60%,#5d7a4c)"></div>'


def status_light(time):
    dots = "".join('<circle cx="{}" cy="8" r="1.7"/>'.format(4 + i * 5) for i in range(4))
    signal = f'<svg width="20" height="12" viewBox="0 0 24 12" fill="currentColor" opacity="0.45">{dots}</svg>'
    battery = ('<svg width="27" height="13" viewBox="0 0 27 13">'
               '<rect x="0.5" y="0.5" width="21" height="12" rx="3.5" fill="none" '
               'stroke="currentColor" stroke-opacity="0.6"/>'
               '<rect x="2" y="2" width="18" height="9" rx="2" fill="currentColor"/>'
               '<rect x="23" y="4" width="2.5" height="5" rx="1.2" fill="currentColor" '
               'fill-opacity="0.6"/></svg>')
    return (f'<div class="status statdark"><span class="time">{time}</span>'
            f'<span class="sicons">{signal}{ic_wifi()}{battery}</span></div>')


def screen_session():
    """The real app screenshot: One More Time recap over the botanical background."""
    rows = [
        trow("00:00", track_card("One More Time", "Daft Punk", meta="123 BPM &middot; 5:20")),
        trow("04:12", track_card("Music Sounds Better With You", "Stardust",
                                 meta="122 BPM &middot; 7:03", cls="rainbow")),
        trow("08:47", track_card("Lady (Hear Me Tonight)", "Modjo", meta="126 BPM &middot; 5:00")),
        trow("13:26", track_card("Finally", "Kings of Tomorrow", meta="121 BPM &middot; 8:22")),
        trow("23:10", track_card("Sing It Back", "Moloko")),
    ]
    return f'''<div class="screen light">{bg_img_tag()}<div class="scrhaze"></div><div class="sc">
{status_light("20:32")}
<div class="eyeb">ENCORE</div>
<div class="h1">One More Time</div>
<div class="sub">DJ Set &middot; 1 h 24 min &middot; Paris &middot; 24 Jul 2026</div>
<div class="gcard session-green">{card_head(ic_wave(17), "SESSION LIVE")}{waveform(46, "humps", salt=5)}
{stats([("12", "TRACKS"), ("1h24", "DUR&Eacute;E"), ("125", "AVG BPM")])}</div>
{sect("La setlist", "extrait &middot; 00:00 &rarr; 58:37")}
<div class="timeline">{"".join(rows)}</div>
<div class="playlist-btn lightbtn">{ic_wand()}<span>G&eacute;n&eacute;rer une playlist</span></div>
</div></div>'''


LANDING_CSS = f"""
/* ---- landing overrides (after mockup CSS so they win) ---- */
html{{scroll-behavior:smooth}}
body{{color:#fff;font-family:'Inter',-apple-system,'Helvetica Neue',sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.5;background-color:#060803;
  background-image:
    radial-gradient(1100px 700px at 78% 0px, rgba(125,195,70,0.16), transparent 65%),
    radial-gradient(900px 700px at 8% 100%, rgba(60,90,25,0.14), transparent 70%),
    linear-gradient(160deg,#141a0b 0%,#0c1106 55%,#060803 100%);
  background-repeat:no-repeat;background-size:auto,auto,100% 100%}}
.wrap{{max-width:1140px;margin:0 auto;padding:0 24px}}

.logo-word{{font-family:'Fraunces',Georgia,serif;font-weight:600;letter-spacing:0;
  background:linear-gradient(93deg,#1b6b4a 0%,#37945a 20%,#7cbb55 38%,#b8dd75 52%,
    #d9eeb0 64%,#a5e0c6 82%,#62c9b2 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent}}

.lp-nav{{display:flex;align-items:center;justify-content:space-between;padding:26px 0}}
.lp-brand{{text-decoration:none;font-size:34px;line-height:1}}
.btn{{display:inline-flex;align-items:center;justify-content:center;gap:10px;
  background:#9be15d;color:#0c1106;font-weight:700;text-decoration:none;
  border-radius:999px;padding:15px 30px;font-size:17px;letter-spacing:0.2px;
  transition:transform .15s ease,box-shadow .15s ease;
  box-shadow:0 8px 30px rgba(155,225,93,0.25)}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 12px 40px rgba(155,225,93,0.35)}}
.btn.small{{padding:11px 22px;font-size:15px}}
.btn.ghost{{background:transparent;color:#d9f5bd;border:1px solid rgba(255,255,255,0.25);
  box-shadow:none}}

.hero{{display:flex;align-items:center;gap:40px;padding:40px 0 30px}}
.hero-copy{{flex:1;min-width:0}}
.pill{{display:inline-block;padding:9px 18px;border-radius:999px;font-size:12.5px;
  letter-spacing:2.5px;font-weight:700;color:#9be15d;border:1px solid rgba(155,225,93,0.4);
  background:rgba(155,225,93,0.08)}}
.hero h1{{font-size:64px;font-weight:800;line-height:1.05;letter-spacing:-2px;margin-top:26px}}
.hero .lead{{margin-top:24px;font-size:21px;line-height:1.55;color:rgba(255,255,255,0.75);
  max-width:560px}}
.price-row{{display:flex;align-items:baseline;gap:16px;margin-top:34px}}
.price{{font-size:44px;font-weight:800;color:#9be15d;letter-spacing:-1px}}
.price-note{{font-size:16px;color:rgba(255,255,255,0.65)}}
.cta-row{{display:flex;align-items:center;gap:18px;margin-top:22px;flex-wrap:wrap}}
.micro{{margin-top:16px;font-size:13.5px;color:rgba(255,255,255,0.5)}}

.hero-mock{{flex:0 0 auto;width:400px;height:790px;position:relative}}
.mock-scale{{position:absolute;top:0;left:50%;transform:translateX(-50%) scale(0.9);
  transform-origin:top center}}

/* ---- light (real-screenshot) phone screen ---- */
.bgimg{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.scrhaze{{position:absolute;inset:0;background:linear-gradient(180deg,
  rgba(235,242,225,0.22),rgba(210,225,195,0.10) 45%,rgba(120,140,100,0.18))}}
.statdark{{color:#1c2413}}
.screen.light .h1{{font-size:36px}}
.screen.light .sub{{font-size:15px}}
.screen.light .gcard{{padding:12px 14px}}
.screen.light .stat b{{font-size:26px}}
.screen.light .sect{{margin:14px 2px 8px}}
.screen.light .tcard{{padding:11px 14px}}
.screen.light .tbody{{padding-bottom:9px}}
.screen.light .tt{{font-size:17px}}
.screen.light .tt,.screen.light .ta,.screen.light .tm,.screen.light .stat,
.screen.light .clabel{{text-shadow:0 1px 7px rgba(40,60,30,0.3)}}
.screen.light .stat i{{color:rgba(255,255,255,0.85)}}
.screen.light .eyeb,.screen.light .h1,.screen.light .sub{{
  text-shadow:0 1px 14px rgba(40,60,30,0.35)}}
.screen.light .eyeb{{color:rgba(255,255,255,0.95)}}
.screen.light .gcard{{background:rgba(255,255,255,0.30);border-color:rgba(255,255,255,0.55)}}
.screen.light .session-green{{background:rgba(150,205,110,0.42)}}
.screen.light .tcard{{background:rgba(255,255,255,0.28);border-color:rgba(255,255,255,0.5)}}
.screen.light .tcard.rainbow{{background:rgba(255,255,255,0.34)}}
.screen.light .sect h3{{text-shadow:0 1px 10px rgba(40,60,30,0.3)}}
.screen.light .sect span,.screen.light .ttime{{color:rgba(255,255,255,0.95);
  text-shadow:0 1px 8px rgba(40,60,30,0.4)}}
.screen.light .ta{{color:rgba(255,255,255,0.9)}}
.screen.light .tm{{color:rgba(255,255,255,0.8)}}
.screen.light .timeline::before{{background:rgba(255,255,255,0.65)}}
.playlist-btn.lightbtn{{bottom:26px;background:rgba(255,255,255,0.30);
  border-color:rgba(255,255,255,0.6);color:#fff;
  text-shadow:0 1px 8px rgba(40,60,30,0.4)}}

.steps{{display:flex;gap:24px;padding:60px 0}}
.step{{flex:1;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.12);
  border-radius:24px;padding:28px}}
.step .num{{font-size:13px;letter-spacing:3px;font-weight:700;color:#9be15d}}
.step h3{{font-size:23px;font-weight:800;margin-top:12px;letter-spacing:-0.3px}}
.step p{{margin-top:10px;font-size:15.5px;line-height:1.55;color:rgba(255,255,255,0.7)}}

.specs{{padding:10px 0 40px}}
.specs h2,.preorder h2{{font-size:38px;font-weight:800;letter-spacing:-1px}}
.spec-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:30px}}
.spec{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
  border-radius:18px;padding:20px 22px}}
.spec b{{display:block;font-size:16px;font-weight:700}}
.spec span{{display:block;margin-top:6px;font-size:14px;color:rgba(255,255,255,0.62);
  line-height:1.5}}

.preorder{{margin:50px 0 70px;text-align:center;background:rgba(155,225,93,0.07);
  border:1px solid rgba(155,225,93,0.3);border-radius:32px;padding:60px 40px}}
.preorder p{{margin:18px auto 0;font-size:18px;color:rgba(255,255,255,0.75);max-width:620px}}
.preorder .price-row{{justify-content:center}}
.preorder .btn{{margin-top:26px}}

.lp-footer{{border-top:1px solid rgba(255,255,255,0.1);padding:34px 0 44px;
  display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
  font-size:14px;color:rgba(255,255,255,0.5)}}
.lp-footer a{{color:rgba(255,255,255,0.7)}}
.lp-footer .logo-word{{font-size:22px}}

@media (max-width: 960px){{
  .hero{{flex-direction:column-reverse;text-align:center;padding-top:10px}}
  .hero .lead{{margin-left:auto;margin-right:auto}}
  .price-row,.cta-row{{justify-content:center}}
  .hero h1{{font-size:44px}}
  .hero-mock{{width:340px;height:660px}}
  .mock-scale{{transform:translateX(-50%) scale(0.75)}}
  .steps{{flex-direction:column}}
  .spec-grid{{grid-template-columns:1fr}}
  .lp-nav .btn{{display:none}}
}}
"""


def build_html():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Encore &mdash; the pendant that remembers your party</title>
<meta name="description" content="Encore captures a party's setlist in real time, fully on-device. Preorder for {PRICE}, delivery {DELIVERY}."/>
<style>
{font_css()}
{MOCK_CSS}
{LANDING_CSS}
</style>
</head>
<body>

<nav class="lp-nav wrap">
  <a class="lp-brand" href="#"><span class="logo-word">Encore</span></a>
  <a class="btn small" href="{STRIPE_LINK}">Preorder &middot; {PRICE}</a>
</nav>

<header class="hero wrap">
  <div class="hero-copy">
    <span class="pill">FINALIST &middot; GEMMA 4 HACKATHON PARIS</span>
    <h1>The pendant that remembers your party.</h1>
    <p class="lead">Encore listens to the night for you &mdash; and gives it back:
    a timestamped setlist, the transitions, the highlight moments and a ready-to-play
    playlist. Everything runs locally on your iPhone.</p>
    <div class="price-row">
      <span class="price">{PRICE}</span>
      <span class="price-note">preorder &middot; delivery {DELIVERY}</span>
    </div>
    <div class="cta-row">
      <a class="btn" href="{STRIPE_LINK}">Preorder now</a>
      <a class="btn ghost" href="#how">How it works</a>
    </div>
    <p class="micro">Secure checkout via Stripe &middot; limited first batch</p>
  </div>
  <div class="hero-mock"><div class="mock-scale">
    <div class="phone"><div class="island"></div>{screen_session()}</div>
  </div></div>
</header>

<section id="how" class="steps wrap">
  <div class="step"><div class="num">01 &middot; CAPTURE</div>
    <h3>Wear the night</h3>
    <p>The pendant streams the party to your iPhone. Gemma&nbsp;4 runs fully
    on-device and gives every unknown track an ID card &mdash; genre, BPM, vibe
    and a line caught from the crowd.</p></div>
  <div class="step"><div class="num">02 &middot; IDENTIFY</div>
    <h3>Every track, named</h3>
    <p>ShazamKit matches the tracks the world knows; embeddings and Gemma&nbsp;4
    cover everything the catalogs don't &mdash; unreleased edits, live mashups,
    B2B surprises.</p></div>
  <div class="step"><div class="num">03 &middot; RELIVE</div>
    <h3>Get your night back</h3>
    <p>Wake up to a timestamped setlist with transitions, highlights and audio
    extracts &mdash; then turn the whole night into a playlist in one tap.</p></div>
</section>

<section class="specs wrap">
  <h2>Small pendant, long memory.</h2>
  <div class="spec-grid">
    <div class="spec"><b>100% on-device</b><span>Matching and Gemma&nbsp;4 run on
      your iPhone. The audio never has to leave your pocket.</span></div>
    <div class="spec"><b>Privacy, one press away</b><span>Long-press the pendant
      and it stops listening instantly. Double-tap to pin a moment.</span></div>
    <div class="spec"><b>Ambiance LED</b><span>A soft LED glows with the room
      and flashes when you pin a highlight.</span></div>
    <div class="spec"><b>Works without the pendant</b><span>Phone-mic mode builds
      the same live setlist straight from your pocket.</span></div>
    <div class="spec"><b>Playlist export</b><span>One tap turns the night into an
      Apple&nbsp;Music playlist of everything that played.</span></div>
    <div class="spec"><b>Open hardware</b><span>Built on the XIAO ESP32-S3 Sense,
      streaming over Wi&#8209;Fi with BLE fallback.</span></div>
  </div>
</section>

<section class="preorder wrap">
  <h2>Be first in line.</h2>
  <p>The first batch ships for <b>{DELIVERY}</b>. Preorder now for {PRICE} and
  get your setlist back from every party this season.</p>
  <div class="price-row"><span class="price">{PRICE}</span>
    <span class="price-note">one-time &middot; delivery {DELIVERY}</span></div>
  <a class="btn" href="{STRIPE_LINK}">Preorder for {PRICE}</a>
</section>

<footer class="lp-footer wrap">
  <span class="logo-word">Encore</span>
  <span>Built at the Gemma 4 Hackathon, Paris &middot; July 2026 &middot;
    Team: Jade &amp; Mathieu &middot;
    <a href="https://github.com/cduchinois/encore_pendentif">GitHub</a></span>
</footer>

</body>
</html>"""


def main():
    html = build_html()
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({len(html)} bytes), stripe link: {STRIPE_LINK}")


if __name__ == "__main__":
    main()
