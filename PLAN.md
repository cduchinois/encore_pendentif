# PLAN — Encore @ Gemma 4 Hackathon (2026-07-25)

PRD: docs/PROPOSAL.md. Board: GitHub issues, milestone "Demo freeze 15h".

## Before the 25th
- Mathieu: run fingerprint_catalog.py on the 3000 tracks (overnight), enrich demo subset, anti-Shazam audit of rare tracks.
- Jade: flash XIAO, validate audio streaming (BIGGEST RISK — do this first), power (LiPo or power bank), Gemma E2B running on Mac AND iPhone (llama.cpp vs AI Edge, keep the winner), print the case at 42's fablab.
- Together: produce the fake unreleased beat, rehearse the Shazam duel.

## Day of — the hour lines
- 09:00 setup, sponsors talked to (Alien Intelligence API!), issues assigned
- 10:30 audio frames land in the iOS app (visible waveform)   [gate 1]
- 12:00 local catalog match shows on a minimal timeline        [gate 2]
- 13:30 pin event + Gemma fiche ID on unknown clip             [gate 3]
- 15:00 FREEZE: recap + playlist work; demo rehearsed once     [gate 4]
- 15:00+ bonuses only, on branches: SerpAPI live resolve, context benchmark,
         LED ambiance polish, embeddings stage, world-catalog stage
- 17:00 demo rehearsed twice with the real speaker + Shazam duel

## Gate rule
Miss a gate by >45 min -> cut scope downward (drop bonus features, simplify UI),
never extend. The demo path is sacred; docs/PROPOSAL.md §6 lists what dies first.
