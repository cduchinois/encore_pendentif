# ENCORE

**The pendant that captures the setlist while you fully enjoy your night, and lets you relive the emotion, one more time, the next day.**

*Gemma 4 Hackathon Paris, July 25, 2026. Target tracks: Edge/On-Device (main), Context Engineering for SLMs (Alien Intelligence), NVIDIA GPU Challenge (optional).*

**Team**: Jade (iOS + pipeline), Mathieu (data + catalog).

---

## 1. The problem

Pulling out your phone to Shazam in the middle of an emotional moment is inhuman: it kills the vibe, yours and everyone else's. And the worst part is that it doesn't even work: Shazam chokes on DJ transitions, pitched tracks, bootlegs and unreleased songs, and without network it only answers the next day. In the end you're left with, at best, a flat list of titles. The night itself is lost.

## 2. The solution

**Encore** captures the setlist for you while you live your night. You never pull out your iPhone to Shazam again: the pendant listens, identifies in real time, and the next day it gives you back the complete memory of your night: timestamped setlist, transitions, highlight moments, and the playlist ready in Apple Music or Spotify.

One single gesture: you love what's playing, you tap the pendant, the track is pinned.

The brain is your phone: **Gemma 4 running locally + an embedded recognition catalog**. Everything happens on-device, nothing goes to the cloud. For this hackathon, we prepared and scanned a catalog of 3000 tracks (Mathieu's collection, rarities included) that fits in a few tens of MB on the iPhone: proof that a serious local database is possible without a single server call.

**Roadmap**: at this ratio (~15 KB per track), a one-million-title catalog would fit in 10 to 20 GB; the real product answer is per-scene catalog packs (techno, house, hip-hop...) of a few hundred MB, downloaded once, up to date, and yours.

Positioning: **Shazam identifies tracks, Encore captures nights — in real time, without the cloud.**

## 3. How it works

### The hardware

- **Pendant**: Seeed XIAO ESP32-S3 Sense (built-in PDM mic), translucent 3D-printed case (STL files ready: `encore_body.stl` + `encore_lid.stl`, Ø42 x 23 mm, integrated lanyard tab, mic holes, USB-C notch).
- **Ambiance LED**: one WS2812B (NeoPixel, ~2 euros, 3 wires) behind the frosted case: the pendant changes color with the room's mood (calm blue → warm pink/red, pulses on the drop), white flash on pin. Driven locally (sound level + bass) or by the iPhone via the party state. Private mode = everything off, unambiguous.
- **Power**: 3.7 V 500-600 mAh LiPo (matchbox-sized, ~10 g) soldered to the BAT pads; charging circuit built into the XIAO, USB-C recharge. No-solder option: a mini USB-C power bank inside the case.
- **Interaction, one single touch zone** (ESP32-S3 capacitive touch, copper pad on the front face): **double tap = pin the track** (LED flash), **long press = private mode** (listening cut, LED off). Highlight moments are detected automatically from crowd volume — no gesture needed.
- **iPhone (private iOS app, installed via Xcode, no App Store)**: the whole brain runs here, locally. The app keeps running in the background with the screen off (iOS background modes, BLE link with the pendant); for the demo, the screen stays on since it is the dashboard.

**Hardware roadmap**: autonomous listening management (deep sleep, wake when music starts, RMS + spectral-regularity detection), final enclosure, multi-night battery life.

### Gemma 4, the permanent brain

Gemma 4 E2B runs locally on the iPhone (llama.cpp or Google AI Edge) and it is what understands the night. Fingerprinting is just a specialized sensor in its service: it provides exact names, Gemma provides the meaning. Continuously, Gemma:

- **detects and qualifies transitions** (long blend, hard cut, BPM ramp) from the compiled party state;
- **tags highlight moments** by crossing crowd volume, pins and track sequences;
- **listens to what nobody recognizes** (native audio input — something neither fingerprinting nor Apple's models can do) and produces a structured ID card: genre, description, vocals, transcribed lyrics snippet, with BPM and key computed by DSP (librosa);
- **arbitrates candidates** during deferred resolution, with native structured JSON output;
- **writes the end-of-night recap**.

### Recognition, from most precise to most robust

1. **Local fingerprint, instant and offline**: ShazamKit custom catalog (100% on-device matching) on the embedded catalog; alternative: Olaf compiled for iOS. Identification in 3 to 5 seconds, lookup in milliseconds, zero network.
2. **Embeddings similarity**: catches tracks that are filtered, overlapped or too degraded for an exact match.
3. **Shazam world catalog (if online)**: free safety net for mainstream tracks outside the local catalog.
4. **Gemma ID card**: when everything fails, the model listens and describes (see above).
5. **Nothing is ever lost**: for every unknown, we save the audio clip, the fingerprint, the embedding and the ID card. The card serves the human; the clip and fingerprint serve the machines for deferred resolution.

### The catalog (prepared the night before)

- The 3000 tracks are fingerprinted in batch on a Mac (a few hours, one night is enough).
- Every track is **enriched in advance**: Spotify and Apple Music links (iTunes Search API, Spotify Web API), artwork, BPM. On match, the complete card appears instantly, offline, links included. Priority to the ~50 tracks of the demo set.
- **Anti-Shazam audit**: find a few tracks confirmed unfindable by Shazam, because the demo will compare Encore and Shazam live.

### Deferred resolution (SerpAPI at the core)

When network returns, a background job resolves the unknowns:

- **SerpAPI**: Google search of the transcribed lyrics in quotes, search by description, YouTube results to verify candidates, cross-checking against published tracklists (1001Tracklists-style). As a bonus for the recap: artwork (Google Images) and the artist's upcoming dates (Google Events).
- **Exact recognition on the clip**: AudD or ACRCloud on the saved excerpt.
- **Playable enrichment**: iTunes Search API and Spotify Web API turn "title + artist" into playable links.

### The context engineering layer (Alien Intelligence track)

A small model at the edge has neither the RAM nor the tokens for raw context. Encore embeds a **two-stage context compiler**:

1. **The compressed party state**: setlist, BPM curve, crowd volume and pins maintained in an ultra-compact structured representation. This compiled context is what lets E2B detect transitions, tag highlight moments and write the recap.
2. **Compilation of SerpAPI results**: a raw SERP response is ~50 KB of JSON; the compiler reduces it to under 1000 tokens of structured evidence (candidates, lyrics concordances, sources), and E2B decides with a confidence score.

Mini-benchmark presented to the jury: correct-resolution rate per context token, small model + compiled context versus big model + raw JSON.

### The final product

End of the night, one button: **"Want to live this night Encore?"** Gemma generates the recap (full setlist, energy curve, the moments the room exploded, your pins on top), and the app creates the playlist directly in Apple Music (MusicKit) or Spotify (Web API). We don't play music in our app: we deliver the night into the music app people already use.

### What is "edge"?

The entire critical path: capture on the pendant; fingerprint, embeddings, Gemma inference, timeline and recap on the iPhone. No server of ours. The audio of a private party is processed and discarded on the spot: privacy by construction. The cloud (SerpAPI, links, playlist) is only deferred, optional enrichment. **The cloud improves Encore, but Encore doesn't need the cloud.**

## 4. Sponsor technologies used

| Sponsor | Use |
|---|---|
| **Gemma 4 (Google DeepMind)** | E2B locally on iPhone, permanent brain: ID cards for unknowns (native audio input), transition detection, highlight moments, recap, arbitration of SerpAPI candidates. Native function calling and structured JSON output. |
| **SerpAPI** | Deferred ID resolution (lyrics, YouTube, tracklists) and cultural enrichment of the recap (artwork, upcoming concerts). Puts the offered credits at the core of the product. |
| **Alien Intelligence** | Context Engineering track: the two-stage context compiler + accuracy/token benchmark. To be refined with their mentors that morning depending on their API. |
| **NVIDIA (optional)** | Server variant: the same pipeline served by Gemma 4 on vLLM for the multi-stream "whole club" case, if time allows. |

## 5. The demo (5 minutes)

The demo set is mixed entirely from the embedded catalog: fast recognition guaranteed, anti-Shazam traps pre-verified.

1. **Scene-setting (30 s)**: Bluetooth speaker, mini DJ set, pendant around the neck, iPhone dashboard projected.
2. **Passive recognition (1 min)**: tracks land in 3-4 seconds on the timeline. Nobody touched a phone.
3. **The duel (the key moment)**: a rare bootleg/edit, then a transition with two overlapping tracks. A judge Shazams at the same time, connection on. Shazam fails; Encore displays, offline.
4. **Airplane mode (30 s)**: all network cut, everything keeps working. "No data leaves the room."
5. **The pin (30 s)**: double tap on the pendant at the drop, LED flash, track pinned. Long press: LED off, private mode — the privacy question answered before it is asked.
6. **The unfindable track (1 min)**: a beat produced by the team the night before, unknown to the entire universe. Gemma ID card (genre, BPM, description, lyrics). WiFi back on: deferred SerpAPI resolution fires live.
7. **The finale (30 s)**: "Want to live this night Encore?", recap generated by Gemma, playlist created in Apple Music before the jury's eyes. *"Shazam gives you a title. Encore gives you back your night."*

## 6. Day-of scope

**Must work**: pendant → iPhone streaming, local fingerprint, timeline, pin, Gemma ID card, recap, playlist.
**Bonus if time allows**: live SerpAPI resolution during the demo, quantified context benchmark, embeddings, Shazam world-catalog stage.
**Cut without regret / roadmap**: autonomous listening management (deep sleep), multi-user, accounts, App Store, final enclosure, per-scene catalog packs.

## 7. Preparation before the 25th (checklist)

*To validate against the rules: open-source libs, prepared data and hardware are generally allowed; code is produced on the day.*

- [ ] **Mathieu**: export the library cleanly (audio files + reliable title/artist tags); run the fingerprinting script on the 3000 tracks (one night); Spotify/Apple enrichment of the ~50 demo-set tracks.
- [ ] **Anti-Shazam audit**: test the candidate rarities against Shazam, keep only confirmed failures.
- [ ] **Jade**: flash and test the XIAO on arrival (audio streaming = the biggest risk); power (soldered LiPo or power bank); install Gemma E2B on Mac and iPhone (test llama.cpp AND Google AI Edge, keep the best).
- [ ] **3D print the case at the 42 fablab**: bring `encore_body.stl` and `encore_lid.stl` (USB key or email), transparent or translucent filament (PETG or PLA), 0.2 mm, 2-3 perimeters, no supports, ~1h30 print. Ask the lab staff for help with the slicer. Sand the inside for the diffuse-glow effect.
- [ ] Buy the WS2812B LED (1-pixel breakout or 8-LED mini ring) + lanyard/cord.
- [ ] Produce the fake unreleased track (30 s of beat is enough).
- [ ] Rehearse the Shazam duel 10 times, time the demo.
