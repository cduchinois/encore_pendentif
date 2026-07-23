# data/ — catalog, demo set, golden clips

[← Main README](../README.md) · Built by: [pipeline/](../pipeline/README.md) · Owner: Mathieu

Heavy payloads live here but are **gitignored** (audio files, `catalog/*`, `samples/*`); only manifests and audit notes are committed. Never commit audio or the sqlite/catalog artifacts.

## Layout

- **`catalog/`** (gitignored, built by `pipeline/ingest/fingerprint_catalog.py`): `catalog.sqlite` (one row per track: tags, duration, BPM, enrichment links) + `signatures/<id>.shazamsignature` (the ShazamKit custom catalog references). The iOS app ships these in its bundle — the whole offline recognition rests on this build.
- **`demo_set/demo_tracks.txt`** (committed): `Artist - Title` lines, the ~50 tracks of the demo set. `enrich_catalog.py --priority` enriches these first; lines must match the file tags exactly (lowercased).
- **`demo_set/rare_tracks_audit.md`** (committed): the anti-Shazam audit table — each rarity tested against Shazam online, keep only confirmed failures for the duel.
- **`samples/`** (gitignored): the 6 golden clips from [demo/TESTPLAN.md](../demo/TESTPLAN.md) (clean match, pitched +4%, overlap, crowd noise, unreleased beat, silence/speech) used by automated tests on machines that have them.
- **`serp_cache/`** (to create, gitignored): cached SerpAPI responses `<hash>.json` — never spend a credit twice.

## Tasks to be accomplished (before the 25th — critical path)

- [ ] Export the library cleanly: reliable title/artist tags at the source (the whole product displays what's in the DB).
- [ ] Run the overnight fingerprint on the 3000 tracks on the Mac (after the resume-bug fix in [pipeline/README.md](../pipeline/README.md)).
- [ ] Fill `demo_tracks.txt` (~50 tracks) and run priority enrichment.
- [ ] Anti-Shazam audit: fill `rare_tracks_audit.md`, keep only confirmed Shazam failures.
- [ ] Record the 6 golden clips into `samples/`.
- [ ] Produce the fake unreleased beat (30 s is enough) — demo beat 6.
