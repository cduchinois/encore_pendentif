# contracts/ — the source of truth between modules

[← Main README](../README.md) · Rules: [CLAUDE.md](../CLAUDE.md)

Three small files bind the three codebases (firmware C++, iOS Swift, Python pipeline). **The contracts rule is non-negotiable**: never change a message format or JSON shape directly in code. Change the file here first, then update every consumer (Swift AND Python) in the same branch. The verifier agent checks this before every merge and before the 15:00 freeze.

## The files

### [`pendant_protocol.md`](pendant_protocol.md) — pendant ↔ iPhone wire format (v1)
Binary packets over WiFi/UDP (iPhone hotspot), BLE fallback, little-endian.
- **Pendant → phone**: `0x01 AUDIO` (seq u16, ts_ms u32, 320× int16 PCM = 20 ms @ 16 kHz mono), `0x02 EVENT` (1=PIN double tap, 2=PRIVACY_ON, 3=PRIVACY_OFF), `0x03 HEARTBEAT` (battery %, RSSI, every 5 s).
- **Phone → pendant**: `0x10 CMD_LED` (mode off/solid/pulse/flash-once + RGB).
- Behavioral rules: while PRIVACY_ON the pendant sends nothing but HEARTBEAT; nothing is acked — recognition needs seconds of audio, not every frame.
- Consumers: `firmware/src/main.cpp` (packing) and `ios/Encore/Audio/UDPAudioReceiver.swift` (unpacking).

### [`id_card.schema.json`](id_card.schema.json) — the Gemma ID card for an unknown track
What the model must emit when the whole recognition ladder fails: genre, description, has_vocals, confidence, ts_start_ms (required) + lyrics_snippet, key, clip_ref. **`bpm` is injected from DSP (librosa), never guessed by the model** — the prompt in `ios/Encore/Gemma/prompts/id_card.md` enforces the same rule. `additionalProperties: false` keeps Gemma's structured output strict.
- Consumers: iOS Gemma runner (output validation), `pipeline/resolve/serp_resolver.py` (input), tests.

### [`journal.schema.json`](journal.schema.json) — the record of the night
One session = id, start/end, an `events` array (kinds: `track_match`, `id_card`, `pin`, `moment`, `transition`, `privacy_on/off`; with `track_id` pointing into catalog.sqlite, `source` naming the ladder stage, `transition_style`) and an `energy` time series (0–1) for the recap curve. It `$ref`s `id_card.schema.json`.
- Consumers: `ios/Encore/Journal/SessionStore.swift`, `pipeline/context/compiler.py` (party-state input), recap + playlist export.

## How it's verified

`pipeline/tests/test_contracts.py` checks both schemas are valid Draft 2020-12 and validates an example ID card. The full test plan ([demo/TESTPLAN.md](../demo/TESTPLAN.md)) additionally requires: every Gemma output validates against the id_card schema, every journal write validates against the journal schema, and Swift/Python protocol constants match this protocol doc.

## Tasks to be accomplished

- [ ] Add an **instance-level** journal validation test with a ref resolver/registry — the relative `$ref` to `id_card.schema.json` needs a base URI to resolve; today only schema self-validity is tested, and the first real journal validation would hit an unresolved-reference error.
- [ ] Day-of: mirror these shapes as Swift `Codable` structs (the de-facto Swift-side validation) and keep field names identical.
- [ ] Any protocol change → bump the version line in `pendant_protocol.md` and update firmware + iOS in the same branch.
