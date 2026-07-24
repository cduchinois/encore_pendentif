# Decisions log — one line each: what + why. Append only.

- 2026-07-22 ShazamKit custom catalog over Olaf: on-device matching, zero porting risk, signatures generated on Mac.
- 2026-07-22 Phone = brain, pendant = smart mic: nothing pendant-sized runs Gemma E2B (needs ~2 GB RAM).
- 2026-07-22 Fingerprint before Gemma in the ladder: a 2B model cannot memorize exact track identity; Gemma is the permanent brain (transitions, moments, recap, ID card), not the lookup.
- 2026-07-22 Double tap = pin, long press = privacy. Highlights are automatic (crowd volume), no dedicated gesture.
- 2026-07-22 Deep-sleep listening management -> roadmap, not hackathon scope.
- 2026-07-22 NVIDIA challenge = conditional stretch goal only (vLLM night-batch variant), never before the core demo works.
- 2026-07-25 Catalog scope = ~16.8k tracks (Compilations + Ultimate from Mathieu's SSDMusic), not the planned 3k: real library is 160k but only ~16.8k are signable in one night — a scene pack, exactly the roadmap answer.
- 2026-07-25 Signatures = full-file, never windowed: a 30-60s window would only match the signed portion; a DJ can play any part -> guaranteed demo miss.
- 2026-07-25 Build speedups: precompile the swift helper once (swiftc binary) ~6.5x faster; on AVFoundation decode failure, transcode via afconvert then retry (recovers ~3% "nilError" MP3s). 16814/16815 signed.
- 2026-07-25 Artwork from embedded covers, de-duplicated by content hash (16.8k tracks -> 1274 unique), NOT iTunes artwork_url: local = offline (a URL needs network to render) + instant. Shipped form (thumbnail size, DB field) still OPEN — decide with Jade.
- 2026-07-25 Demo set = Madchester -> free-party-techno arc (demo_tracks.txt), drawn from the whole catalog not just Ultimate. Spiral Tribe "Forward The Revolution" = the Shazam-duel finale (signed, so Encore wins offline).
