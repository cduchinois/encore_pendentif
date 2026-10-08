# contracts/ — the source of truth between modules

[← Main README](../README.md) · Rules: [CLAUDE.md](../CLAUDE.md)

Three small files bind the three codebases (firmware C++, iOS Swift, Python pipeline). **The contracts rule is non-negotiable**: never change a message format or JSON shape directly in code. Change the file here first, then update every consumer (Swift AND Python) in the same branch. The verifier agent checks this before every merge and before the 15:00 freeze.

## The files

### [`pendant_protocol.md`](pendant_protocol.md) — pendant ↔ iPhone wire format (v2, BLE, `MVP` branch)
GATT service with one TX notify and one RX write characteristic, one packet per notification/write, little-endian.
- **Pendant → phone**: `0x04 AUDIO_ULAW` (seq u16, 160 μ-law bytes = 10 ms @ 16 kHz mono), `0x02 EVENT` (1=PIN double tap, 2=PRIVACY_ON, 3=PRIVACY_OFF), `0x03 HEARTBEAT` (battery %, RSSI 0, every 5 s).
- **Phone → pendant**: `0x10 CMD_LED` (mode off/solid/pulse/flash-once + RGB).
- Behavioral rules: audio only while the phone is subscribed; while PRIVACY_ON nothing but HEARTBEAT; nothing is acked.
- Consumers: `firmware/src/main.cpp` (packing, μ-law encode), `ios/Encore/Audio/PendantBLEClient.swift` (unpacking), `pipeline/tools/pendant_codec.py` + `ble_listen.py` (reference codec, Mac smoke test).

### [`id_card.schema.json`](id_card.schema.json) — the Gemma ID card for an unknown track
What the model must emit when the whole recognition ladder fails: genre, description, has_vocals, confidence, ts_start_ms (required) + lyrics_snippet, key, clip_ref. **`bpm` is injected from DSP (librosa), never guessed by the model.** Not produced by the app on the `MVP` branch (no Gemma); kept for the pipeline and `main`. `additionalProperties: false` keeps Gemma's structured output strict.
- Consumers: `pipeline/resolve/serp_resolver.py` (input), tests. (The iOS Gemma runner exists on `main` only.)

### [`journal.schema.json`](journal.schema.json) — the record of the night
One session = id, start/end, an `events` array (kinds: `track_match`, `id_card`, `pin`, `moment`, `transition`, `privacy_on/off`; with a `track` object for Shazam cloud matches on the MVP branch (`shazam_id`, `title`, `artist`, `isrc`, `apple_music_id`, `artwork_url`, `apple_music_url`), legacy `track_id` pointing into catalog.sqlite, `source` naming the ladder stage, `transition_style`) and an `energy` time series (0–1) for the recap curve. It `$ref`s `id_card.schema.json`.
- Consumers: `ios/Encore/Journal/SessionStore.swift`, `pipeline/context/compiler.py` (party-state input), recap + playlist export.

## How it's verified

`pipeline/tests/test_contracts.py` checks both schemas are valid Draft 2020-12 and validates an example ID card. `pipeline/tests/test_pendant_protocol.py` pins the μ-law codec, the packet shapes, the GATT UUIDs against this doc, and validates an example cloud journal (with the `$ref` resolved). The full test plan ([demo/TESTPLAN.md](../demo/TESTPLAN.md)) additionally requires: every Gemma output validates against the id_card schema, every journal write validates against the journal schema, and Swift/Python protocol constants match this protocol doc.

## Tasks to be accomplished

- [x] Add an **instance-level** journal validation test with a ref resolver/registry — the relative `$ref` to `id_card.schema.json` needs a base URI to resolve; today only schema self-validity is tested, and the first real journal validation would hit an unresolved-reference error.
- [ ] Day-of: mirror these shapes as Swift `Codable` structs (the de-facto Swift-side validation) and keep field names identical.
- [ ] Any protocol change → bump the version line in `pendant_protocol.md` and update firmware + iOS in the same branch.
