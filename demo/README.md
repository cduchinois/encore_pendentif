# demo/ — the 5 minutes everything serves

[← Main README](../README.md) · Plan & gates: [PLAN.md](../PLAN.md)

The demo path is sacred (gate rule: cut scope, never extend). This folder holds the script, the test plan that protects it, and the backup dashboard.

## Contents

- **[`demo_script.md`](demo_script.md)** — the 5-minute, 7-beat script: decor → passive recognition → **the Shazam duel** (the key moment: a judge Shazams a rare bootleg live and fails; Encore displays, offline) → airplane mode → pin + privacy → the unreleased beat (Gemma fiche, then live SerpAPI resolve) → recap + Apple Music playlist in front of the jury. Rehearse ×2 minimum.
- **[`TESTPLAN.md`](TESTPLAN.md)** — three layers: the 6 golden clips (`data/samples/`, automated where possible), contract checks (Gemma output ↔ id_card schema, journal writes ↔ journal schema, Swift/Python constants ↔ protocol doc), and the manual pre-rehearsal checklist (airplane mode, pin <1 s, privacy = zero packets, recap <30 s, 1 h battery).
- **[`dashboard/recap_mockup.html`](dashboard/recap_mockup.html)** — finished dark-theme phone-frame mockup of the recap screen. It is (1) the design reference for `ios/Encore/UI/TimelineView.swift` and (2) the **backup dashboard** if the SwiftUI recap slips past the freeze.

## Tasks to be accomplished

- [ ] Before the 25th: rehearse the Shazam duel ×10 with audited rarities; time the full script.
- [ ] Day-of, before each rehearsal: run the manual checklist in TESTPLAN.md.
- [ ] Day-of 15:00–17:00: full script rehearsed twice with the real speaker; freeze check with the verifier agent.
- [ ] Wire the golden clips into automated tests once recorded ([data/](../data/README.md)).
