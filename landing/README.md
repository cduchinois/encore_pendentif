# Encore preorder landing page

Self-contained static page (`index.html`, Inter embedded, no build step, no JS).
Preorder at **42€**, delivery **1 October 2026**.

## Wire up Stripe (required before going live)

The two CTA buttons point to the placeholder
`https://buy.stripe.com/REPLACE_WITH_PAYMENT_LINK`.

1. Stripe Dashboard → **Payment Links** → **+ New**.
2. Product: "Encore pendant — preorder", one-time, **42.00 EUR**
   (mention "delivery 1 October 2026" in the product description; enable the
   address collection you need for shipping).
3. Copy the `https://buy.stripe.com/...` URL, then either:
   - regenerate: `python3 gen_landing.py [assets_dir] <your-stripe-url>`, or
   - search-replace the placeholder in `index.html`.

## Deploy

Any static host works (the file is standalone). Quickest: GitHub Pages —
repo Settings → Pages → deploy from branch, folder `/landing` (or copy
`index.html` to the Pages root).

## Regenerate

`gen_landing.py` imports the phone-mockup components from
`demo/submission/gen_slides.py`. The hero phone shows the real "One More Time"
session screen recreated over the app's actual background asset
(`ios/.../BackgroundImage.png`, downscaled).

Pass an assets dir as the first argument to embed (all optional):
`inter-400.woff2` (UI font), `fraunces-600.woff2` (logo font),
`bg_screen.jpg` (the downscaled app background). Without it, fonts fall back
to Google Fonts imports and the screen background to a gradient.

## Logo

The "Encore" wordmark is a gradient-text recreation of the brand logo
(Fraunces 600 + the logo's green gradient). To use the exact logo image
instead, commit the PNG (transparent background) as `landing/assets/logo.png`
and replace the nav/footer `<span class="logo-word">Encore</span>` with
`<img src="assets/logo.png" alt="Encore" style="height:44px">`.
