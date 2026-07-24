# pipeline/ — catalog prep + context engineering (Python, Mathieu's Mac)

[← Main README](../README.md) · Contracts: [contracts/](../contracts/README.md) · Owner: pipeline-dev agent

Everything that runs on the Mac: the night-before catalog build, the deferred SerpAPI resolution, the two-stage context compiler (Alien Intelligence track), and its benchmark. **Rule: pip-only, no heavyweight deps** (no dejavu/MySQL) — it must run on Mathieu's Mac as-is.

```bash
cd pipeline && pip install -r requirements.txt
pytest                       # contract tests
```

## Layout & how each part works

### `ingest/` — the catalog (run the night before) — WORKING
- **`fingerprint_catalog.py`**: walks a music folder, reads tags (mutagen), builds `data/catalog/catalog.sqlite` (one row per track + enrichment columns), and calls the Swift helper per track to emit `signatures/<id>.shazamsignature` for the ShazamKit custom catalog. Optional `--bpm` (librosa, slow — demo subset only). Resumable, batch-committed.
  `python ingest/fingerprint_catalog.py --music-dir ~/Music/crate`
- **`make_signature.swift`**: macOS-only helper (ShazamKit `SHSignatureGenerator`), audio file → `.shazamsignature` at 44.1 kHz mono.
- **`enrich_catalog.py`**: fills `apple_url`, `artwork_url`, `preview_url` (iTunes Search API, free, throttled 3.1 s/req) and optionally `spotify_url` (client-credentials flow, keys in `.env`). `--priority data/demo_set/demo_tracks.txt` does the ~50 demo tracks first.

### `context/` — the Alien Intelligence layer — STUB
`compiler.py`, two deterministic, unit-tested entry points:
- `compile_party_state(journal, budget_tokens)` — journal ([schema](../contracts/journal.schema.json)) → ultra-compact structured party state (setlist tail, BPM curve, crowd level, pins). Feeds every Gemma call.
- `compile_serp_evidence(serp_json, id_card, budget_tokens)` — ~50 KB raw SERP → <1000 tokens of structured evidence for Gemma arbitration.
Shared shape with the Swift `ContextCompiler` — same output, two languages, contracts keep them honest.

### `resolve/` — deferred resolution — STUB
`serp_resolver.py`: id_card + saved clip → SerpAPI quoted-lyrics search → description search → YouTube check → `compile_serp_evidence` → Gemma arbitration (candidate + confidence). **Cache every SerpAPI response** in `data/serp_cache/<hash>.json` (credits!). Keep each step a pure function with fixture tests.

### `bench/` — the jury artifact — STUB
`context_bench.py`: N resolution cases with ground truth; arm A = small model + compiled evidence, arm B = big model + raw SERP JSON; metric = correct resolutions per context token. One table + one chart.

### `tests/` — WORKING (minimal)
`test_contracts.py` validates both JSON schemas and an example ID card.

## Tasks to be accomplished

**Before the 25th (critical path — Mathieu)**
- [ ] **Fix the resume bug in `fingerprint_catalog.py`**: already-inserted tracks are skipped before the signature step, so the promised "rerun on the Mac re-signs where signature_ok=0" never happens — a Linux-then-Mac run would end with zero signatures. Skip only when `signature_ok=1`.
- [ ] **Pin librosa `<0.11`** (or switch to `librosa.feature.rhythm.tempo`): `librosa.beat.tempo` is removed in 0.11 and `requirements.txt` says `>=0.10`.
- [ ] Run the fingerprint on the 3000 tracks (overnight); enrich the demo subset (`--priority`).
- [ ] Eyeball the enrichment of the ~50 demo tracks — `itunes_lookup` takes the first hit without an artist check; bootlegs can match the wrong release.

**Day-of**
- [ ] Implement `context/compiler.py` (core, gate 3/4 depend on party state) with unit tests — deterministic, `len(text)//4` token approximation is fine.
- [ ] Golden-clip tests once `data/samples/` exists (see [demo/TESTPLAN.md](../demo/TESTPLAN.md)).

**Bonus (after 15:00 freeze, on branches)**
- [ ] `resolve/serp_resolver.py` live during the demo (beat 6).
- [ ] `bench/context_bench.py` with 10–20 cases from the demo set + chart.

## Catalog build — done this session (branch `feat/pipe-catalog-build-speedup`)

Built ~16.8k-track catalog (Compilations + Ultimate from SSDMusic): **16814/16815 signed**, verified consistent. New in `ingest/`:
- **`fingerprint_catalog.py`**: resume bug fixed (skip only `signature_ok=1`); swift helper precompiled once (`swiftc` → cached binary, ~6.5× faster); afconvert transcode fallback for AVFoundation-unreadable MP3s (recovered the ~3% "nilError" failures).
- **`verify_catalog.py`** (new): read-only DB↔signatures consistency + failure list; non-zero exit for a gate check.
- **`extract_artwork.py`** (new): embedded covers de-duplicated by content hash (16.8k tracks → **1274 unique**, 802 MB full-res / ~45 MB as 300px thumbs), written to `data/catalog/artwork/<sha1>.jpg` + `index.json` (`track_id → file`). **Contract-neutral: does NOT touch `catalog.sqlite`.**

## ⚠️ Open design decisions — decide with Jade before wiring

1. **How the app gets artwork.** Covers are extracted locally (offline, instant) as a deduped set + `artwork/index.json` sidecar. To wire into the DB, pick one — this touches `contracts/`:
   - (a) **Reuse `artwork_url`** as a bundle-relative path (e.g. `artwork/<sha1>.jpg`). Zero schema change, but overloads a field named `_url`; iOS must load bundle-local, not fetch remote.
   - (b) **Add a dedicated field** `artwork_local` (schema change → contracts first, both consumers same branch).
   The slow work (scanning 16.8k files) is done; wiring is a 1-line update from `index.json` either way.
2. **Shipped artwork size.** Full-res unique set is 802 MB (too big to bundle). Recommend regenerating thumbnails: `extract_artwork.py --max-px 300` (~45 MB, native `sips`, no dep). Pick the px.
3. **`artwork_url` semantics** already imply remote/online — but Encore is offline-first. Confirm the app never needs network to render a match card (favors local artwork).
4. **iTunes links enrichment** (`apple_url`, `spotify_url`, `preview_url`) is online + throttled (3.1 s/req → ~14 h for all). Run `enrich_catalog.py --priority data/demo_set/demo_tracks.txt` on the ~18 demo tracks only (~1 min) — deferred, not blocking.
