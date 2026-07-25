# Submission media — 3 slides (16:9)

Three 1920×1080 slides for the hackathon submission, each mocking one app
screenshot (Pendant / Phone / Demo tabs) inside an iPhone frame over a club
background. Two variants per slide: with explanation copy (`slideN.png`) and
screenshot-only (`slideN_notext.png`).

The screens are HTML recreations of the real app screenshots (the originals
weren't in the repo), generated deterministically.

## Regenerate

```bash
# 1. build slides.html (optionally embedding Inter as base64 for offline render)
python3 gen_slides.py [path/to/inter.woff2]

# 2. render PNGs (needs playwright-core + a Chromium binary)
npm i playwright-core
CHROMIUM_PATH=/path/to/chrome node render.mjs slides.html out/
```
