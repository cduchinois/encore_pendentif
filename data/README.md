# data/ — catalog, demo set, golden clips

[← Main README](../README.md) · Built by: [pipeline/](../pipeline/README.md) · Owner: Mathieu

Heavy payloads live here but are **gitignored** (audio files, `catalog/*`, `samples/*`); only manifests and audit notes are committed. Never commit audio or the sqlite/catalog artifacts.

## Layout

- **`catalog/`** (gitignored, built by `pipeline/ingest/fingerprint_catalog.py`): `catalog.sqlite` (one row per track: tags, duration, BPM, enrichment links) + `signatures/<id>.shazamsignature` (the ShazamKit custom catalog references). The iOS app ships these in its bundle — the whole offline recognition rests on this build.
- **`demo_set/demo_tracks.txt`** (committed): `Artist - Title` lines, the ~50 tracks of the demo set. `enrich_catalog.py --priority` enriches these first; lines must match the file tags exactly (lowercased).
- **`demo_set/rare_tracks_audit.md`** (committed): the anti-Shazam audit table — each rarity tested against Shazam online, keep only confirmed failures for the duel.
- **`samples/`** (gitignored): the 6 golden clips from [demo/TESTPLAN.md](../demo/TESTPLAN.md) (clean match, pitched +4%, overlap, crowd noise, unreleased beat, silence/speech) used by automated tests on machines that have them.
- **`serp_cache/`** (to create, gitignored): cached SerpAPI responses `<hash>.json` — never spend a credit twice.

## Mathieu: what to index, and how

"Indexing" a track means producing **two artifacts**, and both are needed:

1. **A metadata row** in `catalog/catalog.sqlite` — title, artist, album, duration, later BPM and Spotify/Apple links. This is what the app *displays* on a match.
2. **A ShazamKit reference signature** — `catalog/signatures/<id>.shazamsignature`. This is what the app *matches against*. It's a compact acoustic fingerprint (~15 KB per track, so 3000 tracks ≈ a few tens of MB — that's how the whole catalog fits on the iPhone).

### ⚠️ A Python-only index does NOT work — signatures must come from ShazamKit

If you've indexed the sound library with a Python fingerprinting library (librosa hashes, dejavu, chromaprint, custom spectrogram peaks…), **that index cannot be used by the app**. On the iPhone, matching is done by Apple's [ShazamKit](https://developer.apple.com/shazamkit/) (`SHCustomCatalog` + `SHSession`), and ShazamKit **only matches against signatures produced by Apple's own `SHSignatureGenerator`**. The signature format is proprietary — no Python library can produce it, and ShazamKit cannot read any third-party fingerprint format.

That's why the pipeline is structured the way it is:

- `pipeline/ingest/fingerprint_catalog.py` (Python) is only the **driver and metadata builder**: it walks the folder, reads the tags, fills `catalog.sqlite`.
- For each track it shells out to `pipeline/ingest/make_signature.swift`, a small Swift helper that uses **ShazamKit's `SHSignatureGenerator`** (converts the file to 44.1 kHz mono PCM and emits the `.shazamsignature`). This requires **macOS 12+** (ShazamKit ships with the OS; you just need Xcode command-line tools — no Apple Developer account and no API key needed for signature generation).

So: keep whatever Python indexing you did as a sanity check if you like, but the catalog the app ships **must be rebuilt with the ShazamKit path**, on your Mac.

### How to (re)build it — step by step, on the Mac

```bash
# 0. one-time
xcode-select --install                      # Swift toolchain, if not already there
cd pipeline && pip install -r requirements.txt

# 1. clean tags at the source first — the app displays exactly what's in the tags

# 2. dry run on a handful of files
python ingest/fingerprint_catalog.py --music-dir ~/Music/crate --limit 10

# 3. check it actually produced signatures (not just DB rows)
sqlite3 ../data/catalog/catalog.sqlite \
  "SELECT COUNT(*), SUM(signature_ok) FROM tracks"
ls ../data/catalog/signatures/ | head

# 4. full run — overnight, a few hours for 3000 tracks
python ingest/fingerprint_catalog.py --music-dir ~/Music/crate

# 5. enrichment (links + artwork), demo subset first
python ingest/enrich_catalog.py --priority ../data/demo_set/demo_tracks.txt
```

Two things to watch (details in [pipeline/README.md](../pipeline/README.md)):

- **Run it on the Mac from the start.** A first run on another machine inserts DB rows without signatures, and the current resume logic skips already-inserted tracks — a rerun would *not* backfill the signatures until the resume bug is fixed. If you already have a rows-but-no-signatures catalog: delete `data/catalog/` and rebuild on the Mac (or wait for the fix).
- After the full run, verify: `SUM(signature_ok)` should equal the track count, and every id in `signatures/` should exist in the DB. Spot-check 2–3 rarities by playing them into the demo app once gate 2 exists.

## Once indexed: how matching works (pendant → app)

The chain at the party, end to end — fully offline:

1. **The pendant captures** — on-board PDM mic, 16 kHz mono, packed into 20 ms UDP frames (320 samples of int16) per [contracts/pendant_protocol.md](../contracts/pendant_protocol.md), fired at the iPhone over the hotspot. No acks; losing frames is fine.
2. **The app buffers** — `UDPAudioReceiver` reorders by sequence number into a rolling ring buffer of the last few seconds of audio.
3. **The app makes a *query* signature** — every few seconds, `ShazamKitMatcher` takes a rolling window (~5–10 s of PCM, converted to the `AVAudioPCMBuffer` format ShazamKit expects) and runs it through the same `SHSignatureGenerator` — this time on the phone, over live party audio.
4. **ShazamKit matches locally** — at app start, the app loads every `signatures/<id>.shazamsignature` (plus title/artist from `catalog.sqlite`, attached as `SHMediaItem` metadata carrying the track id) into an **`SHCustomCatalog`**, and opens an `SHSession` against it. The query signature is compared to the reference signatures **on-device, in milliseconds — zero network**. That robustness to noise, pitch shifts and partial overlap is exactly the Shazam algorithm, which is why we ride ShazamKit instead of a homemade Python matcher.
5. **Match → the night's record** — a hit returns the media item (with our track id) + the time offset: the app looks up the full row in `catalog.sqlite` (title, artist, links, artwork — already enriched, so the complete card appears instantly, offline) and appends a `track_match` event to the journal ([contracts/journal.schema.json](../contracts/journal.schema.json)); the timeline updates. Typical time from a track starting to it appearing: **3–5 s**.
6. **No match → the ladder continues** — embeddings (bonus) → Shazam world catalog if online (bonus) → **Gemma ID card**: the 20 s clip is saved and described, and resolved later via SerpAPI when network returns. Nothing is ever lost.

Note the symmetry: **your overnight build and the live app use the exact same ShazamKit primitives** — reference signatures from files (Mac, step 4 above builds them), query signatures from the mic stream (iPhone). That symmetry is what makes the offline match work; it only holds if both sides are ShazamKit.

## Tasks to be accomplished (before the 25th — critical path)

- [ ] Export the library cleanly: reliable title/artist tags at the source (the whole product displays what's in the DB).
- [ ] **Rebuild the index via ShazamKit on the Mac** (see above — a Python-only fingerprint index can't be used by the app), after the resume-bug fix in [pipeline/README.md](../pipeline/README.md). Verify `SUM(signature_ok) == COUNT(*)`.
- [ ] Fill `demo_tracks.txt` (~50 tracks) and run priority enrichment.
- [ ] Anti-Shazam audit: fill `rare_tracks_audit.md`, keep only confirmed Shazam failures.
- [ ] Record the 6 golden clips into `samples/`.
- [ ] Produce the fake unreleased beat (30 s is enough) — demo beat 6.
