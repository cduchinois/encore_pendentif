# Catalog pack audit — iOS bundle (Mathieu)

## 2026-07-25 — enriched to the full Ultimate set (391 tracks)

Replaced the 388-track pack with **391 tracks, 391 signatures (100%)** so the whole
demo setlist is recognizable. `id` ↔ `signatures/<id>.shazamsignature` ↔ `catalog.json`
join verified: 0 missing, 0 orphans.

- **Content = all of "Ultimate" (389) + 2 additions** copied into Ultimate and signed:
  New Order – Blue Monday (id 16817, the **1983 EP** original, 7:28 — not a compilation)
  and Drum Club – Follow The Sun (id 16818, the **Shazam-duel** track).
- **ids come from the full `data/catalog` build** (not the old 1–388). The 388 Ultimate
  signatures are byte-identical to the previous pack (git shows them as renames), just
  re-keyed to their real ids; `catalog.json` maps them correctly.
- Demo setlist reworked to be **Ultimate-only** (`data/demo_set/demo_tracks.txt`, 18 tracks),
  same Madchester → free-party-techno arc.
- **The "mystery" track (Dub techno 1) is deliberately NOT in the bundle** — it must fail the
  whole recognition ladder so Gemma describes it. It lives in the Ultimate *folder* (for
  playback in the setlist) but is unsigned and absent from `catalog.json`.
- Xcode: `ios/Encore/` is a `PBXFileSystemSynchronizedRootGroup`, so the new signature files
  are picked up automatically — no project changes needed.
- Final proof (a real `SHSession` match) runs on device — gate-2 test.

## Where things live

- `ios/Encore/Catalog/signatures/*.shazamsignature` + `catalog.json` — **committed**, bundled
  into the app. `catalog.json` is generated from `catalog.sqlite` (id, title, artist, album,
  duration, bpm); regenerate it if the sqlite changes.
- `catalog.sqlite` + audio — **not in git** (gitignored payloads; audio on the Synology / SSD).
