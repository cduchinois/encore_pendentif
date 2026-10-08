# Encore MVP: product requirements (branch `MVP`)

Status: in development on branch `MVP`. Supersedes the hackathon architecture for this branch only; `docs/PROPOSAL.md` stays the pitch reference.

## 1. Goal

Ship a simple, reliable version of Encore that a real person can wear to a real party:

1. **Recognition = Shazam's cloud catalog via ShazamKit.** No bundled local catalog, no Gemma or Gemini, no llama-server. If a song is on Shazam, Encore names it.
2. **Pendant to phone over Bluetooth Low Energy.** No more iPhone hotspot, no WiFi credentials flashed into the pendant, the phone keeps its normal internet connection (needed for step 1).

Everything else (setlist timeline, pins by double tap, LED feedback, phone mic mode) is kept.

## 2. Feasibility

| Question | Answer |
|---|---|
| Can ShazamKit match against Shazam's own catalog? | Yes. `SHSession()` with no custom catalog matches against the Shazam music catalog (cloud). It accepts the same 16 kHz mono buffers we already feed it via `matchStreamingBuffer`. Results carry title, artist, ISRC, Apple Music ID, artwork URL, Shazam ID. |
| What does it require? | (a) Internet on the phone at match time. (b) The **ShazamKit App Service enabled on the app's App ID** in the Apple Developer portal (Certificates, Identifiers & Profiles → Identifiers → the app → App Services → ShazamKit). This needs a paid Apple Developer Program membership; a free Personal Team cannot enable it. Custom catalogs (what the hackathon used) did not need this. |
| Can the XIAO ESP32-S3 stream mic audio over BLE? | Yes. Raw 16 kHz/16-bit PCM is 32 kB/s, which is at the edge of what iOS sustains over BLE. We encode with G.711 μ-law (8 bit per sample, 2:1, trivial on both sides) for **16 kB/s**, well inside the budget. μ-law keeps the spectral peaks ShazamKit fingerprints on. |
| Does it keep working with the phone in a pocket? | The app declares the `bluetooth-central` background mode, so BLE notifications (and our matching) keep flowing while backgrounded. Validated on device in step 7. |

Known trade-off: **no network = no recognition** at the moment the song plays. Clubs in basements are a real risk; the offline signature queue (section 6, first post-MVP item) fixes it by matching later.

## 3. Architecture

```
[Pendant: XIAO ESP32-S3 Sense]                [iPhone app]
  PDM mic 16 kHz -> μ-law, 10 ms packets        PendantBLEClient (CoreBluetooth central)
  BLE peripheral "Encore" (NimBLE)  --notify-->   decode μ-law -> 0.5 s chunks
  touch: double tap = PIN event                   CapturePipeline
  WS2812B LED  <--write CMD_LED--                   SHSession() = Shazam cloud catalog
                                                    MusicDetector (unknown rows)
                                                  SessionStore journal -> setlist UI
```

Contract: `contracts/pendant_protocol.md` (v2, BLE) and `contracts/journal.schema.json` (`track` object for cloud matches).

## 4. Step by step plan

Each step has an exit gate. Do not start the next step on hardware before the gate passes.

### Step 0. Accounts and prerequisites (Jade, 30 min)
- Paid Apple Developer account; App ID for the bundle id with **ShazamKit** App Service enabled.
- Xcode 26+, iPhone on iOS 26.
- **Gate:** Phone tab of the current app on `main`, with `SHSession()` (any quick test), names a song playing from a speaker.

### Step 1. Contracts v2 (done on this branch)
- `pendant_protocol.md` v2: BLE GATT service, TX notify / RX write characteristics, `AUDIO_ULAW` packet, unchanged `EVENT`, `HEARTBEAT`, `CMD_LED`.
- `journal.schema.json`: `track` object on `track_match` and `pin` events (`shazam_id`, `title`, `artist`, `isrc`, `apple_music_id`, `artwork_url`, `apple_music_url`). `track_id` kept as a legacy field.
- **Gate:** `cd pipeline && pytest` green (schema + μ-law codec tests).

### Step 2. Firmware over BLE (done on this branch, needs hardware validation)
- WiFi and UDP removed; NimBLE-Arduino peripheral advertising as `Encore`.
- I2S capture unchanged; each 20 ms read becomes two 10 ms μ-law packets (163 bytes each).
- Audio only flows while the phone is subscribed; idle = blue pulse LED, advertising.
- Asks iOS for a 15 to 30 ms connection interval.
- No `secrets.h` anymore.
- **Gate:** `pio run` compiles; on hardware the serial log shows `connected`, `subscribed`, and ~100 notifications/s with near-zero failures.

### Step 3. Mac validation tool (done on this branch)
- `pipeline/tools/ble_listen.py` (bleak): connects to the pendant, records a WAV, prints events, heartbeats and packet loss.
- **Gate:** 60 s recording with < 1 % packet loss; the WAV, played back, is recognised by the Shazam app on another phone. This proves BLE audio quality is enough for Shazam before touching the app.

### Step 4. iOS BLE client (done on this branch, needs device validation)
- `Audio/PendantBLEClient.swift` replaces `UDPAudioReceiver`: scans for the Encore service, auto connects, remembers the pendant, reconnects after loss, state restoration for background relaunch.
- Same published stats as before (packets/s, loss, battery, RSSI, waveform) so the Pendant tab works unchanged.
- Info.plist: `NSBluetoothAlwaysUsageDescription`, `UIBackgroundModes = bluetooth-central`. Local network permission removed.
- **Gate:** Pendant tab shows connected, ~100 pkt/s, moving waveform; double tap produces a pin; LED flashes on match.

### Step 5. Cloud recognition (done on this branch, needs device validation)
- `CapturePipeline` uses `SHSession()` (Shazam catalog). Shazam's streaming answers are voted on (`MatchVoter`): covers and karaoke versions of the same title count as the same song, a new song needs 2 agreeing answers (3 to replace the one playing). First field test without voting gave wrong versions and a new row every few seconds.
- Journal stores the full `track` object; setlist rows show title, artist and artwork; pins reference the track.
- Unknown rows kept (20 s of music with no match), labelled "pas de réseau" when the phone was offline.
- Offline banner on the capture cards.
- **Gate:** 5 songs from a speaker, pendant 1 to 2 m away: at least 4 named within 15 s each, no duplicate rows.

### Step 6. Cleanup (done on this branch)
- Removed: `Gemma/`, `Catalog/` (catalog.json + 388 signatures), `Resolve/`, `UnknownClipRecorder`, `ClipPlayer`, Gemma settings. App size drops by ~30 MB.

### Step 7. Field test (Jade + Mathieu)
- 1 hour session in a real room with the phone in a pocket and screen locked.
- **Gate:** journal complete after unlocking, no disconnect longer than 10 s, pendant battery survives 1 h.

## 5. Out of scope for the MVP
- Gemma / Gemini ID cards, local catalog, embeddings, SerpAPI enrichment.
- WiFi transport (protocol v1 lives on `main`).
- Privacy gesture (still disabled in firmware, see DECISIONS.md 2026-07-25).

## 6. Next, after the MVP
1. **Offline signature queue**: when offline, keep 12 s signatures of unmatched music, match them with `SHSession.match(_:)` when the network returns, insert into the journal at the original timestamp.
2. **Export**: add the night's songs to the user's Shazam library (`SHLibrary`) and/or an Apple Music playlist (MusicKit), pins first.
3. Recap screen built from the journal (replaces the Demo tab mock data).
4. Firmware power: modem-free BLE already saves a lot; add light sleep between I2S reads and a real battery curve.

## 7. Risks
| Risk | Mitigation |
|---|---|
| ShazamKit service not enabled / free account | Step 0 gate before any other work. |
| BLE throughput lower than planned on some iPhones | μ-law gives 2x margin; packets are 163 bytes so they fit the 185 byte MTU iOS negotiates. Loss is visible in the UI and in `ble_listen.py`. |
| No network in the venue | Unknown rows say "pas de réseau"; offline queue is next priority. |
| iOS kills the app in background | `bluetooth-central` background mode + CoreBluetooth state restoration. |
