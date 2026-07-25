# Catalog pack audit — "Ultimate" (Mathieu, 2026-07-24)

Verified 2026-07-25 morning before bundling into the iOS app.

- **388 tracks, 388 signatures (100%)** — sqlite `id` ↔ `signatures/<id>.shazamsignature` join is perfect: 0 missing, 0 orphans.
- `catalog.sqlite`: no empty titles, no empty artists, all `path` values relative (no machine-specific paths), all `signature_ok=1`.
- Signatures: uniform binary header (`80258025 0200…`) across all 388 files — single consistent `SHSignatureGenerator` build (whole file, 44.1 kHz mono, macOS). Sizes 9 KB–623 KB, ~64 KB avg, 25 MB total.
- Final proof (an actual `SHSession` match) can only run on Apple hardware — covered by the gate-2 test.

Where things live:

- `ios/Encore/Catalog/signatures/*.shazamsignature` + `catalog.json` — **committed**, bundled into the app. `catalog.json` is generated from `catalog.sqlite` (id, title, artist, album, duration, bpm) and is what Swift reads; regenerate it if the sqlite is enriched.
- `catalog.sqlite` + original audio (`Ultimate/`) — **not in git** (data/ payloads are gitignored; audio stays on the Macs). The sqlite remains the source of truth for enrichment columns.
