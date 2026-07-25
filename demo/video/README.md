# Encore — 60 s short video

Video built with [hyperframes](https://github.com/heygen-com/hyperframes) (HTML in,
deterministic MP4 out).

- `storyboard.md` — the 8 scenes / 60 s, compressed from `demo/demo_script.md`.
- `frame.md` — design spec (tokens, type, motion) derived from the real app screenshots.
- `index.html` — the hyperframes composition (1080×1920, 30 fps). Self-contained: app
  screens are rebuilt as HTML components, the brand logo is inline SVG.
- `make_bed.py` — synthesizes the music bed (hyperframes muxes audio but does not compose
  it). `assets/bed.wav`: 60 s house, 124 BPM, drop at 38 s, deterministic.

## Workflow

```bash
python3 make_bed.py       # regenerate assets/bed.wav if missing (needs numpy)
npx hyperframes preview   # live reload in the browser, scrub the timeline
npx hyperframes render    # headless Chrome + FFmpeg -> encore_short.mp4
```

Rules: assets land in `assets/` first, then scenes; keep all animation CSS-keyframe based
(seekable — no randomness, no wall-clock JS) or the render won't be deterministic.
