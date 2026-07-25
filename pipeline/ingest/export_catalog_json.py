#!/usr/bin/env python3
"""Regenerate the app's bundled catalog.json from catalog.sqlite.

Run after (re)building or enriching the catalog, then commit the JSON:

    python pipeline/ingest/export_catalog_json.py \
        --sqlite <pack>/catalog/catalog.sqlite \
        --signatures <pack>/catalog/signatures \
        --out ios/Encore/Catalog

Copies the signatures alongside and refuses to export if the sqlite ids and
signature files don't match 1:1 (the id is the join, see data/catalog_manifest.md).
"""
import argparse, json, shutil, sqlite3, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, type=Path)
    ap.add_argument("--signatures", required=True, type=Path)
    ap.add_argument("--out", default=Path("ios/Encore/Catalog"), type=Path)
    args = ap.parse_args()

    db = sqlite3.connect(args.sqlite)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM tracks ORDER BY id").fetchall()

    ids = {str(r["id"]) for r in rows}
    sigs = {p.stem for p in args.signatures.glob("*.shazamsignature")}
    if ids != sigs:
        print(f"MISMATCH: {len(ids - sigs)} ids without signature, "
              f"{len(sigs - ids)} orphan signatures — fix the pack first.")
        sys.exit(1)

    tracks = [{"id": r["id"], "title": r["title"], "artist": r["artist"],
               "album": r["album"], "duration": r["duration"], "bpm": r["bpm"]}
              for r in rows]

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "catalog.json").write_text(
        json.dumps(tracks, ensure_ascii=False, indent=1), encoding="utf-8")

    sig_out = args.out / "signatures"
    if sig_out.exists():
        shutil.rmtree(sig_out)
    shutil.copytree(args.signatures, sig_out)
    print(f"{len(tracks)} tracks -> {args.out}/catalog.json + signatures/")


if __name__ == "__main__":
    main()
