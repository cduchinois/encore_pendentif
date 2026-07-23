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
