# Test plan

## Golden clips (automated where possible) — data/samples/
| clip | expectation |
|---|---|
| clean_catalog_track.wav | local match < 5 s, correct id |
| pitched_+4pct.wav | local match (fingerprint robustness) |
| two_tracks_overlap.wav | at least one correct match |
| crowd_noise_heavy.wav | match or graceful id_card, no crash |
| unreleased_beat.wav | NO match anywhere -> valid id_card (schema-checked) |
| silence_speech.wav | no false track_match |

## Contract checks (automated)
- Every Gemma output validates against contracts/id_card.schema.json
- Journal writes validate against contracts/journal.schema.json
- Swift/Python protocol constants match contracts/pendant_protocol.md

## Manual demo checks (before each rehearsal)
- [ ] airplane mode: recognition still works
- [ ] double tap -> pin < 1 s, LED flash
- [ ] ~~long press -> privacy~~ disabled for demo day (PRIVACY_GESTURE=0, see DECISIONS.md): grabbing the pendant fired it; re-enable the flag to test
- [ ] recap generates < 30 s; playlist appears in Apple Music
- [ ] battery: pendant survives 1 h streaming
