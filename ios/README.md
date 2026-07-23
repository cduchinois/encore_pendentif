# ios/ — the brain (Swift app, all local)

[← Main README](../README.md) · Contracts: [contracts/](../contracts/README.md) · Owner: ios-dev agent

Everything intelligent runs here, on-device: audio receive, the 4-stage recognition ladder, Gemma E2B, the journal, the recap, and the Apple Music playlist. All files under `Encore/` are **stubs showing the intended module layout** — they are implemented on hackathon day. The demo dashboard is this app's screen, projected.

## Setup (one-time, on the Mac — the .xcodeproj is not committed)

1. Xcode → New Project → iOS App "Encore", SwiftUI, bundle id `dev.encore.app`. Save in `ios/` (replace this folder's `Encore/` with the generated one, then copy the stub .swift files back in).
2. Signing: Personal Team (free Apple ID) — app valid 7 days, install the evening before. Enable Developer Mode on the iPhone.
3. Capabilities: Background Modes (Uses BLE accessories), MusicKit. Add ShazamKit.framework.
4. For Gemma: add the llama.cpp Swift package (or MediaPipe LLM pod) + the E2B GGUF in app resources. Test llama.cpp AND Google AI Edge on the Mac beforehand; keep the winner.

## Module map — how the app is supposed to work

| Module | Role | Gate |
|---|---|---|
| `Audio/UDPAudioReceiver.swift` | Listen on `:7777`, unpack `AUDIO`/`EVENT`/`HEARTBEAT` packets per [pendant_protocol.md](../contracts/pendant_protocol.md), ring buffer + debug waveform, send `CMD_LED` back | 1 (10:30) |
| `Recognition/ShazamKitMatcher.swift` | Load `.shazamsignature` files from the catalog build into an `SHCustomCatalog`; offline match in 3–5 s | 2 (12:00) |
| `Recognition/RecognitionStage.swift` | The ladder: local catalog → embeddings (bonus) → world catalog (bonus) → Gemma ID card; every unknown keeps clip + fingerprint + ID card | 2–3 |
| `Gemma/LlamaRunner.swift` | Gemma 4 E2B local runtime; structured JSON output validated against [id_card.schema.json](../contracts/id_card.schema.json); prompt in `Gemma/prompts/id_card.md` (BPM injected by DSP, never guessed) | 3 (13:30) |
| `Gemma/ContextCompiler.swift` | Swift twin of `pipeline/context/compiler.py`: compact party state (setlist tail, BPM curve, crowd, pins) feeding every Gemma call | 3–4 |
| `Journal/SessionStore.swift` | Append-only session journal per [journal.schema.json](../contracts/journal.schema.json): matches, ID cards, pins, moments, transitions, energy curve | 2+ |
| `UI/TimelineView.swift` | The projected dashboard: live timeline, pins, energy — design reference in [demo/dashboard/recap_mockup.html](../demo/dashboard/recap_mockup.html) | 2 |
| `Playlist/MusicKitExporter.swift` | "Want to live this night Encore?" → recap (Gemma) + playlist in Apple Music, pins first | 4 (15:00) |
| `Resolve/SerpAPIClient.swift` | Bonus: deferred resolution client when WiFi returns (mirrors `pipeline/resolve/`) | bonus |

## Tasks to be accomplished (day-of, in gate order)

- [ ] UDP receiver + ring buffer + visible waveform (gate 1 — streaming is the biggest risk, validate first).
- [ ] ShazamKit custom catalog matching on the prepared signatures (gate 2).
- [ ] Journal + timeline UI per schema + mockup (gate 2).
- [ ] Pin end-to-end: `EVENT(1)` → journal pin → UI badge → `CMD_LED` flash (gate 3).
- [ ] Gemma runner + ID card on an unknown clip — output MUST validate the schema (gate 3).
- [ ] Recap generation from compiled party state + energy curve (gate 4).
- [ ] MusicKit playlist export (gate 4).
- [ ] Bonus, on branches: embeddings stage, world-catalog stage, SerpAPI client, background BLE mode.
