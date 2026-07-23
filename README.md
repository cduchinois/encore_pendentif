# Encore

**Encore is an intelligent pendant that captures every track, transition, and emotion of a DJ set — in real time and entirely on-device — so you can stay present, have fun, and enjoy the party without reaching for your phone. Then, Encore turns it all into a playlist that lets you relive the party, encore and encore.**

Built at the **Gemma 4 Hackathon Paris (2026-07-25)**. Tracks: Edge/On-Device (main), Context Engineering for SLMs (Alien Intelligence), NVIDIA GPU Challenge (optional stretch).
Team: **Jade** (iOS + firmware), **Mathieu** (pipeline + data).

> Start here: [`CLAUDE.md`](CLAUDE.md) (context + repo rules) → [`PLAN.md`](PLAN.md) (the day, gate by gate) → [`docs/PROPOSAL.md`](docs/PROPOSAL.md) (full PRD).
> After creating the GitHub repo, run `./bootstrap.sh` once to create labels, the freeze milestone and all work-item issues.

---

## 1. The problem

**Music is supposed to make you forget time, space, and your phone.**

But apps like Shazam have taught us to do the opposite. The moment you hear a track you love, you reach into your pocket, unlock your phone, open the app, and point it toward the room.

***The moment is gone.***

Sometimes you are not quick enough to catch the track. The fear of missing it pulls you away from the music, the people around you, and the experience itself. Instead of living the night, you are looking at a screen.

**And even worse, Shazam does not always find the song.** DJ transitions, edits, pitched tracks, bootlegs, rarities, and unreleased music are often the sounds that define an unforgettable night — and they are exactly the sounds traditional recognition struggles to identify.

Even when it works, all you receive is a flat list of song titles.

**You found the track, but you lost the momentum, the vibe, the people around you...**

## 2. The solution

**Encore is an intelligent pendant that captures your entire DJ set while you fully live the party.**

The pendant listens discreetly while your phone identifies, understands, and organizes the music in real time. No need to unlock a screen, open an app, or interrupt the moment.

**No screens. No interruptions. No cloud.**

At the heart of Encore is **Gemma, a powerful local AI model running directly on your phone**. It understands context, connects moments, organizes tracks, detects highlights, and transforms raw music recognition into a meaningful memory of your night.

It does not simply collect song titles.

**It reconstructs the experience around them.**

When a track means something, there is only one gesture:

***Tap the pendant.***

Encore instantly pins the moment, so you can return to it later without leaving the dance floor.

Later, Encore lets you live the night *one more time*: a timestamped setlist, the transitions between tracks, your highlighted moments, the atmosphere of the room, and a complete playlist ready for Apple Music or Spotify.

**All the intelligence lives on your phone. Nothing is sent to the cloud.**

For the hackathon, we are building an embedded catalog of **3,000 tracks — including rare edits, bootlegs, and unreleased music — that fits within just a few dozen megabytes on an iPhone.**

**No servers. No network dependency. No compromise on privacy.**

Positioning: **Shazam identifies songs. Encore captures the emotion of the party — so you can live it encore and encore.**

## 3. Architecture

```
[Pendant: XIAO ESP32-S3 Sense]
  mic PDM -> audio frames --WiFi/UDP (BLE fallback)--> [iPhone app]
  touch: double tap = PIN, long press = PRIVACY        |
  WS2812B LED <-- CMD_LED (ambiance color / pin flash) |
                                                       v
[iPhone (all local)]                          [Mac (prep + fallback)]
  1. ShazamKit custom catalog (offline match)   pipeline/ = same logic in Python
  2. embeddings similarity                      data prep runs the night before
  3. ShazamKit world catalog (if online)
  4. Gemma 4 E2B ID card (native audio in)
  journal -> recap -> MusicKit playlist
                                     [deferred, online only]
                                       SerpAPI lyrics/tracklist resolve
                                       iTunes/Spotify enrichment
```

**The recognition ladder** (most precise → most robust): local fingerprint (ShazamKit custom catalog, 100% offline, 3–5 s) → embeddings similarity → Shazam world catalog (if online) → **Gemma ID card** (the model listens and describes what nothing else recognizes). Nothing is ever lost: every unknown keeps its clip, fingerprint, embedding and ID card for deferred resolution when network returns (SerpAPI lyrics/tracklist search, arbitrated by Gemma).

**Gemma 4 E2B is the permanent brain** (llama.cpp or Google AI Edge, on-iPhone): it detects and qualifies transitions, tags highlight moments from crowd volume + pins, produces structured ID cards for unknowns (BPM/key injected by DSP, never guessed), arbitrates deferred-resolution candidates, and writes the end-of-night recap.

**Context engineering layer** (Alien Intelligence track): a two-stage context compiler keeps a small edge model useful — (1) the party state compressed into an ultra-compact structured representation, (2) ~50 KB of raw SERP JSON reduced to <1000 tokens of structured evidence. A benchmark (correct resolutions per context token) is the jury artifact.

**What is "edge"?** The entire critical path: capture on the pendant; fingerprint, embeddings, Gemma inference, timeline and recap on the iPhone. No server of ours. Party audio is processed and discarded on the spot — privacy by construction. The cloud (SerpAPI, links, playlist) is deferred, optional enrichment only. **The cloud improves Encore, but Encore doesn't need the cloud.**

## 4. Repository map

Every module has its own README with how it works, its current status, and the tasks to accomplish:

| Folder | What it is | README |
|---|---|---|
| `contracts/` | **Source of truth**: pendant↔phone protocol + JSON schemas binding all three codebases | [contracts/README.md](contracts/README.md) |
| `firmware/` | XIAO ESP32-S3 pendant: PDM capture → UDP streaming, touch, LED (PlatformIO, C++) | [firmware/README.md](firmware/README.md) |
| `ios/` | The brain: Swift app — receiver, recognition ladder, Gemma, journal, recap, playlist | [ios/README.md](ios/README.md) |
| `pipeline/` | Python (Mac): catalog fingerprint + enrichment, context compiler, SerpAPI resolver, benchmark | [pipeline/README.md](pipeline/README.md) |
| `data/` | Catalog + demo set + golden clips (payloads gitignored; manifests committed) | [data/README.md](data/README.md) |
| `demo/` | 5-minute demo script, test plan, backup HTML dashboard | [demo/README.md](demo/README.md) |
| `hardware/` | 3D-printed case generator + STLs, wiring guide | [hardware/README.md](hardware/README.md) |
| `docs/` | The full PRD ([PROPOSAL.md](docs/PROPOSAL.md)) — product reference, edits are product decisions | — |

## 5. Scaffold status (what's real today)

**Working code**: firmware capture/streaming core, catalog fingerprinting + enrichment scripts, the macOS ShazamKit signature helper, the case generator, the recap dashboard mockup.

**Stubs awaiting day-of implementation**: all iOS Swift modules (the Xcode project is created locally, see [ios/README.md](ios/README.md)), the context compiler, the SerpAPI resolver, the benchmark, firmware touch/LED/heartbeat.

**To produce before the 25th** (prep, allowed by the rules): the fingerprinted catalog, the enriched demo subset, the anti-Shazam audit, the golden clips, the fake unreleased beat, the printed case. See each module README for the precise task list.

## 6. Day-of plan and gates

Full schedule in [`PLAN.md`](PLAN.md). The demo path is sacred:

- **10:30** — audio frames land in the iOS app (gate 1)
- **12:00** — local catalog match on a minimal timeline (gate 2)
- **13:30** — pin event + Gemma ID card on an unknown clip (gate 3)
- **15:00** — **FREEZE**: recap + playlist work, demo rehearsed (gate 4). After freeze, `main` accepts demo fixes only; bonuses stay on branches.

Miss a gate by >45 min → cut scope downward, never extend.

**Must work**: pendant→iPhone streaming, local fingerprint, timeline, pin, Gemma ID card, recap, playlist.
**Bonus if time**: live SerpAPI resolution, context benchmark chart, embeddings stage, world-catalog stage.
**Roadmap (cut without regret)**: autonomous listening (deep sleep + music-onset wake), multi-user, accounts, App Store, final enclosure, per-scene catalog packs (a 1M-track catalog would be 10–20 GB at ~15 KB/track; the real product answer is scene packs of a few hundred MB).

## 7. The demo (5 minutes)

Full script: [`demo/demo_script.md`](demo/demo_script.md). Seven beats: passive recognition → **the Shazam duel** (rare bootleg + overlapped transition; a judge Shazams live and fails, Encore displays offline) → airplane mode → the pin → our unreleased beat (Gemma ID card, then live SerpAPI resolution) → *"Want to live this night Encore?"* → recap + Apple Music playlist created in front of the jury.

Closing line: *"Shazam gives you a title. Encore gives you back your night."*

## 8. Sponsor technologies

| Sponsor | Use |
|---|---|
| **Gemma 4 (Google DeepMind)** | E2B local on iPhone, permanent brain: ID cards (native audio in), transitions, moments, recap, candidate arbitration. Native function calling + structured JSON output. |
| **SerpAPI** | Deferred ID resolution (lyrics, YouTube, tracklists) + cultural enrichment of the recap (artwork, upcoming shows). |
| **Alien Intelligence** | Context Engineering track: the two-stage context compiler + accuracy-per-token benchmark. |
| **NVIDIA (optional)** | Server variant: same pipeline on Gemma 4 + vLLM for the multi-stream "whole club" case, only if time allows. |

## 9. Quick commands

```bash
# Pipeline setup
cd pipeline && pip install -r requirements.txt

# Catalog fingerprint (Mathieu, overnight, on the Mac)
python pipeline/ingest/fingerprint_catalog.py --music-dir <dir>

# Enrichment (demo subset first)
python pipeline/ingest/enrich_catalog.py --priority data/demo_set/demo_tracks.txt

# Pipeline tests
cd pipeline && pytest

# Firmware build + flash (XIAO plugged in)
cd firmware && pio run -t upload

# Context benchmark
python pipeline/bench/context_bench.py
```

Secrets live in `.env` (gitignored) — names listed in `.env.example`. Never in git; if a key lands in a commit, rotate it immediately.

## 10. Repo rules (short version)

Trunk-based; branches `feat/<issue#>-short-name`; commit prefixes `ios:` / `fw:` / `pipe:` / `data:` / `docs:`; merge to `main` only with green tests; never change a message format or JSON shape in code before changing [`contracts/`](contracts/README.md) first. Decisions get one line each in [`DECISIONS.md`](DECISIONS.md). Full rules: [`CLAUDE.md`](CLAUDE.md).
