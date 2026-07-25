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
   - regenerate: `python3 gen_landing.py [inter.woff2] <your-stripe-url>`, or
   - search-replace the placeholder in `index.html`.

## Deploy

Any static host works (the file is standalone). Quickest: GitHub Pages —
repo Settings → Pages → deploy from branch, folder `/landing` (or copy
`index.html` to the Pages root).

## Regenerate

`gen_landing.py` imports the phone mockup from
`demo/submission/gen_slides.py`, so the hero visual stays in sync with the
submission media. Pass the Inter woff2 as the first argument to embed the font
(see `demo/submission/README.md`), otherwise it falls back to a Google Fonts
import.
