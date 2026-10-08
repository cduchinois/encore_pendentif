# Decisions log — one line each: what + why. Append only.

- 2026-07-22 ShazamKit custom catalog over Olaf: on-device matching, zero porting risk, signatures generated on Mac.
- 2026-07-22 Phone = brain, pendant = smart mic: nothing pendant-sized runs Gemma E2B (needs ~2 GB RAM).
- 2026-07-22 Fingerprint before Gemma in the ladder: a 2B model cannot memorize exact track identity; Gemma is the permanent brain (transitions, moments, recap, ID card), not the lookup.
- 2026-07-22 Double tap = pin, long press = privacy. Highlights are automatic (crowd volume), no dedicated gesture.
- 2026-07-22 Deep-sleep listening management -> roadmap, not hackathon scope.
- 2026-07-22 NVIDIA challenge = conditional stretch goal only (vLLM night-batch variant), never before the core demo works.
- 2026-07-24 Flash via PlatformIO not raw ESP-IDF (same esptool + BOOT/RESET recovery, zero toolchain setup); connection via iPhone hotspot + UDP to fixed 172.20.10.1:7777 (no IP discovery, loss-tolerant), protocol v1 unchanged. WiFi creds in gitignored firmware/src/secrets.h.
- 2026-07-24 Commit `ios/Encore.xcodeproj` (synchronized-folder format, no team id): clone → open → build must work for both of us on hackathon morning; overrides the earlier "no .xcodeproj in git" note.
- 2026-07-24 Jade's PagePlaylist mockup (Liquid Glass, iOS 26) merged as the app's design-system reference: `DesignSystem/` tokens + background, demo data stays in `UI/PlaylistTrack.swift` until the journal wires in.
- 2026-07-25 Long-press privacy gesture disabled (PRIVACY_GESTURE=0): grabbing the pendant reads as a long press and muted the capture; privacy stays in the product story, the gesture returns post-hackathon with a better trigger.
- 2026-10-08 MVP branch: recognition moves to ShazamKit's Shazam cloud catalog (`SHSession()`), dropping the local catalog and Gemma/Gemini. Simpler, names any song on Shazam; costs: network needed at match time, paid Apple Developer team with the ShazamKit App Service. Offline signature queue is the first post-MVP item.
- 2026-10-08 MVP branch: pendant link moves from iPhone hotspot + UDP to BLE (protocol v2). The phone keeps its own internet (needed for Shazam), no WiFi credentials in firmware, lower pendant power.
- 2026-10-08 BLE audio is G.711 μ-law, 10 ms / 163-byte packets: 16 kB/s (half of raw PCM) leaves margin on iOS BLE throughput, fits the 185-byte MTU iOS negotiates on every connection, codec is a few lines on each side.
- 2026-10-08 Shazam cloud answers are voted, not trusted one by one: first test journaled covers/karaoke versions and re-added the same song every few seconds. Same normalized title = same song; new song after 2 agreeing answers, 3 to replace the playing one.
