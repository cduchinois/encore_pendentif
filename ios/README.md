# ios/ — the brain (Swift app, all local)

[← Main README](../README.md) · Contracts: [contracts/](../contracts/README.md) · Owner: ios-dev agent

Everything intelligent runs here, on-device: audio receive, the 4-stage recognition ladder, Gemma E2B, the journal, the recap, and the Apple Music playlist. Most files under `Encore/` are **stubs showing the intended module layout** — they are implemented on hackathon day. Exceptions already implemented: `App/`, `DesignSystem/`, `UI/DemoPage.swift` + `UI/PlaylistTrack.swift` (Jade's design mockup with demo data, the visual reference for all other pages) and `Assets.xcassets` (background image, app icon set). The demo dashboard is this app's screen, projected.

> Naming heads-up: `DemoPage` uses SwiftUI's built-in `TimelineView` for animations. When implementing the dashboard in `UI/TimelineView.swift`, name the type something else (e.g. `DashboardTimeline`) or it will shadow SwiftUI's and break those call sites.

## Getting started (for anyone on the team)

`Encore.xcodeproj` **is committed** (decision 2026-07-24). It uses Xcode's synchronized-folder format: everything under `Encore/` is picked up automatically — new files added on disk or by a teammate appear in the project without touching the .xcodeproj.

**Prerequisites:** Xcode 26+ (the UI uses the iOS 26 Liquid Glass API `.glassEffect`; older Xcode will not compile it). For device runs: an iPhone on iOS 26.

**Build (simulator) — no setup at all:**

```bash
git clone https://github.com/cduchinois/encore_pendentif.git
cd encore_pendentif
git checkout claude/ios-app-dev-l4ph2o   # current iOS branch
open ios/Encore.xcodeproj
```

Pick an iPhone simulator, ⌘R. Four tabs: **Pendant** (live capture from the pendant), **Phone** (recognition via the iPhone mic), **Demo** (the design mockup) and **Settings** (custom background).

**Run on your iPhone (one-time per Mac/phone):**

1. Target "Encore" → Signing & Capabilities → Team: select your Personal Team (free Apple ID). The committed project has no team set, so this stays a local-only change — **don't commit the `DEVELOPMENT_TEAM` diff** if Xcode writes it into the pbxproj.
2. On the iPhone: Settings → Privacy & Security → Developer Mode → on (reboots). First launch: Settings → General → VPN & Device Management → trust your certificate.
3. Free-account quirks: if Xcode says the bundle id `jade.encore.pendant` is unavailable for your team, suffix it locally (e.g. `.mat`). Apps signed with a Personal Team expire after 7 days — reinstall the evening before demo day.

**Push your work:**

```bash
git checkout claude/ios-app-dev-l4ph2o   # or a feat/<issue#>-name branch off it
git add ios/
git commit -m "ios: <what you did>"      # module prefix, see repo rules
git push -u origin <branch>
```

Before committing, check `git diff ios/Encore.xcodeproj` — only commit project changes that are intentional (new capability, new package), never your signing team or `xcuserdata` (gitignored).

**Still to add when the corresponding modules land** (not needed for the mockup):

- Capabilities: Background Modes (BLE accessories), MusicKit; ShazamKit.framework.
- Gemma: llama.cpp Swift package (or MediaPipe LLM pod) + the E2B GGUF in app resources. Test llama.cpp AND Google AI Edge on the Mac beforehand; keep the winner.

## Module map — how the app is supposed to work

| Module | Role | Gate |
|---|---|---|
| `App/EncoreApp.swift` | `@main` entry point — Pendant / Phone / Demo / Settings tabs | done |
| `DesignSystem/EncoreTheme.swift` | Design tokens: palette, radii, spacing, typography, `Color(hex:)` — **the reference for every page** | done |
| `DesignSystem/EncoreBackground.swift` | Photographic backdrop + gradient veils (asset `BackgroundImage`) | done |
| `UI/DemoPage.swift` | Recap page mockup: header, summary card, setlist timeline (aurora pin glow, pulsing live dot), floating CTA — all Liquid Glass (`.glassEffect`, iOS 26) | done |
| `UI/PlaylistTrack.swift` | View model + demo dataset for DemoPage; live pages map the journal onto it (`UI/JournalTracks.swift`) | done |
| `Audio/UDPAudioReceiver.swift` | Listen on `:7777`, unpack `AUDIO`/`EVENT`/`HEARTBEAT` packets per [pendant_protocol.md](../contracts/pendant_protocol.md), ring buffer + debug waveform, send `CMD_LED` back | 1 (10:30) |
| `Recognition/ShazamKitMatcher.swift` | Load `.shazamsignature` files from the catalog build into an `SHCustomCatalog`; offline match in 3–5 s | 2 (12:00) |
| `Recognition/RecognitionStage.swift` | The ladder: local catalog → embeddings (bonus) → world catalog (bonus) → Gemma ID card; every unknown keeps clip + fingerprint + ID card | 2–3 |
| `Gemma/LlamaRunner.swift` | Gemma 4 E2B local runtime; structured JSON output validated against [id_card.schema.json](../contracts/id_card.schema.json); prompt in `Gemma/prompts/id_card.md` (BPM injected by DSP, never guessed) | 3 (13:30) |
| `Gemma/ContextCompiler.swift` | Swift twin of `pipeline/context/compiler.py`: compact party state (setlist tail, BPM curve, crowd, pins) feeding every Gemma call | 3–4 |
| `Journal/SessionStore.swift` | Append-only session journal per [journal.schema.json](../contracts/journal.schema.json): matches, ID cards, pins, moments, transitions, energy curve | 2+ |
| `UI/TimelineView.swift` | The projected dashboard: live timeline, pins, energy — design reference in [demo/dashboard/recap_mockup.html](../demo/dashboard/recap_mockup.html) | 2 |
| `Playlist/MusicKitExporter.swift` | "Want to live this night Encore?" → recap (Gemma) + playlist in Apple Music, pins first | 4 (15:00) |
| `Resolve/SerpAPIClient.swift` | Bonus: deferred resolution client when WiFi returns (mirrors `pipeline/resolve/`) | bonus |

## Gates 1-2 are implemented — how to test (2026-07-25)

Implemented: `UDPAudioReceiver`, `ShazamKitMatcher`, `RecognitionStage`,
`SessionStore`, `CatalogStore` + the bundled catalog (`Catalog/catalog.json`
+ 388 `Catalog/signatures/*.shazamsignature`, see `data/catalog_manifest.md`).
The app opens on the **Pendant** tab (capture card + live setlist); the
**Phone** tab does the same through the iPhone mic (no pendant needed —
Mathieu's rig), and the **Demo** tab keeps the design mockup.

1. Open `Encore.xcodeproj`, build on the iPhone that hosts the hotspot.
2. First launch: **accept the "local network" permission popup** — without it
   zero packets arrive (the key is set via `INFOPLIST_KEY_NSLocalNetworkUsageDescription`).
3. Pendant on → green dot, ~50 fps, waveform moves (gate 1). Double-tap → a
   `pin` event in the list.
4. Wait for "catalog…" to disappear (~few s: 388 signatures load into the
   `SHCustomCatalog`), play a track from Mathieu's `Ultimate/` folder on a
   speaker → title appears in <10 s, pendant flashes purple (gate 2).
   A match needs 3-5 s of audio; frequent no-matches between tracks are normal.

## Tasks to be accomplished (day-of, in gate order)

- [ ] UDP receiver + ring buffer + visible waveform (gate 1 — streaming is the biggest risk, validate first).
- [ ] ShazamKit custom catalog matching on the prepared signatures (gate 2).
- [ ] Journal + timeline UI per schema + mockup (gate 2).
- [ ] Pin end-to-end: `EVENT(1)` → journal pin → UI badge → `CMD_LED` flash (gate 3).
- [ ] Gemma runner + ID card on an unknown clip — output MUST validate the schema (gate 3).
- [ ] Recap generation from compiled party state + energy curve (gate 4).
- [ ] MusicKit playlist export (gate 4).
- [ ] Bonus, on branches: embeddings stage, world-catalog stage, SerpAPI client, background BLE mode.
