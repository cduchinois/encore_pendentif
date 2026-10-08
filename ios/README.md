# ios/ — the Encore app (MVP branch)

[← Main README](../README.md) · Contracts: [contracts/](../contracts/README.md) · PRD: [docs/MVP_PRD.md](../docs/MVP_PRD.md) · Owner: ios-dev agent

The MVP app does two things: it receives the pendant's audio over **Bluetooth Low Energy** and names the songs with **ShazamKit against Shazam's cloud catalog**. No local catalog, no Gemma. The journal of the night (setlist, pins, energy) is written per [journal.schema.json](../contracts/journal.schema.json).

## Getting started (for anyone on the team)

`Encore.xcodeproj` **is committed** (decision 2026-07-24). It uses Xcode's synchronized-folder format: everything under `Encore/` is picked up automatically — new files added on disk or by a teammate appear in the project without touching the .xcodeproj.

**Prerequisites:** Xcode 26+ (the UI uses the iOS 26 Liquid Glass API `.glassEffect`; older Xcode will not compile it). For device runs: an iPhone on iOS 26.

**Build (simulator) — no setup at all:**

```bash
git clone https://github.com/cduchinois/encore_pendentif.git
cd encore_pendentif
git checkout MVP
open ios/Encore.xcodeproj
```

Pick an iPhone simulator, ⌘R. Four tabs: **Pendant** (live capture from the pendant over BLE), **Phone** (recognition via the iPhone mic), **Demo** (the design mockup) and **Settings** (pendant link, custom background). The simulator has no Bluetooth: use the Phone tab there.

**Run on your iPhone (one-time per Mac/phone):**

1. Target "Encore" → Signing & Capabilities → Team: select your Personal Team (free Apple ID). The committed project has no team set, so this stays a local-only change — **don't commit the `DEVELOPMENT_TEAM` diff** if Xcode writes it into the pbxproj.
2. On the iPhone: Settings → Privacy & Security → Developer Mode → on (reboots). First launch: Settings → General → VPN & Device Management → trust your certificate.
3. Free-account quirks: if Xcode says the bundle id `jade.encore.pendant` is unavailable for your team, suffix it locally (e.g. `.mat`). Apps signed with a Personal Team expire after 7 days — reinstall the evening before demo day.

**Push your work:**

```bash
git checkout MVP                         # or a feat/<issue#>-name branch off it
git add ios/
git commit -m "ios: <what you did>"      # module prefix, see repo rules
git push -u origin <branch>
```

Before committing, check `git diff ios/Encore.xcodeproj` — only commit project changes that are intentional (new capability, new package), never your signing team or `xcuserdata` (gitignored).

**ShazamKit (required, one time):** recognition uses Shazam's catalog, which needs the **ShazamKit App Service enabled on the App ID** (developer.apple.com → Certificates, Identifiers & Profiles → Identifiers → the app's bundle id → App Services → ShazamKit). This needs a paid Apple Developer Program team; a free Personal Team cannot enable it. Without it, every match fails silently and every row ends up "non reconnu".

## Module map

| Module | Role |
|---|---|
| `App/EncoreApp.swift` | `@main` entry point: Pendant / Phone / Demo / Settings tabs |
| `Audio/PendantBLEClient.swift` | CoreBluetooth central for [pendant_protocol.md](../contracts/pendant_protocol.md) v2: scan, connect, remember and auto-reconnect the pendant, decode μ-law audio, events, heartbeats; writes `CMD_LED`. State restoration + `bluetooth-central` background mode keep it alive with the screen locked |
| `Recognition/RecognitionStage.swift` | Owns the two capture pipelines (pendant, phone mic), network monitor, LED feedback |
| `Recognition/CapturePipeline.swift` | One `SHSession()` (Shazam cloud catalog) per source, one row per song via `MatchVoter`, unknown rows after 20 s of unmatched music ("pas de réseau" when offline) |
| `Recognition/MatchVoter.swift` | Raw Shazam answers → confirmed songs: versions of the same title are one song, a new song needs 2 agreeing answers (3 to replace the one playing), the most reported version wins |
| `Recognition/ShazamKitMatcher.swift` | `SHMatchedMediaItem` → `MatchedTrack` (the journal's `track` object) |
| `Recognition/MusicDetector.swift` | Apple's sound classifier: music vs talk/noise, gates unknown rows |
| `Journal/SessionStore.swift` | Append-only session journal, persisted to Documents |
| `UI/` | `PendantPage`, `PhonePage` (live setlists with artwork), `DemoPage` (design mockup, owns `SetlistTimeline`), `SettingsView` |
| `DesignSystem/` | Design tokens, background, app settings |
| `Playlist/MusicKitExporter.swift`, `UI/TimelineView.swift` | stubs, post-MVP |

`Info.plist` (next to the xcodeproj) only carries `UIBackgroundModes`; every other key is generated from `INFOPLIST_KEY_*` build settings (Bluetooth and microphone usage strings).

## How to test on device

1. Flash the MVP firmware (`firmware/README.md`), pendant LED pulses blue = advertising.
2. Run the app on the iPhone, accept the **Bluetooth** permission popup.
3. Pendant tab: subtitle goes "recherche du pendentif" → "en direct", ~100 pkt/s, waveform moves, the pendant LED turns to a green pulse.
4. Play a song on a speaker: title, artist and artwork appear in < 15 s and the pendant flashes purple.
5. Double tap the pendant: the current song's card gets the aurora pin outline.
6. Lock the phone for 5 minutes with music playing, unlock: the setlist kept growing.

## Tasks

- [ ] Device validation of steps 4 and 5 of the PRD.
- [ ] Offline signature queue (match later when the network returns).
- [ ] Export the night: Shazam library (`SHLibrary`) and/or Apple Music playlist.
