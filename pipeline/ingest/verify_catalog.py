#!/usr/bin/env python3
"""Verify a built Encore catalog: DB <-> signatures consistency + failure list.

    python verify_catalog.py --out ../../data/catalog

Checks (read-only, safe to run while a build is in progress):
  1. every track has a signature        (SUM(signature_ok) == COUNT(*))
  2. every signature_ok=1 row has a .shazamsignature file on disk
  3. every .shazamsignature file maps back to a signature_ok=1 row
  4. reports failures (signature_ok=0) with their path, and signature sizes

Exit code is non-zero if any inconsistency is found (usable in CI / a gate check).
"""
import argparse, sqlite3, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=Path(__file__).parents[2] / "data/catalog", type=Path)
    ap.add_argument("--show", type=int, default=20, help="max failing paths to print")
    args = ap.parse_args()

    db_path = args.out / "catalog.sqlite"
    sig_dir = args.out / "signatures"
    if not db_path.exists():
        print(f"no catalog at {db_path}"); sys.exit(2)

    db = sqlite3.connect(db_path)
    total = db.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    signed = db.execute("SELECT COUNT(*) FROM tracks WHERE signature_ok=1").fetchone()[0]
    db_ids = {r[0] for r in db.execute("SELECT id FROM tracks WHERE signature_ok=1")}
    file_ids = {int(p.stem) for p in sig_dir.glob("*.shazamsignature")} if sig_dir.exists() else set()

    missing_files = db_ids - file_ids          # DB says signed, no file
    orphan_files = file_ids - db_ids            # file exists, DB doesn't mark it signed
    failures = db.execute(
        "SELECT path FROM tracks WHERE signature_ok=0 ORDER BY id").fetchall()

    sizes = [p.stat().st_size for p in sig_dir.glob("*.shazamsignature")] if sig_dir.exists() else []
    total_mb = sum(sizes) / 1e6
    avg_kb = (sum(sizes) / len(sizes) / 1e3) if sizes else 0

    print(f"catalog: {db_path}")
    print(f"  tracks in DB          : {total}")
    print(f"  signed (signature_ok) : {signed}  ({100*signed/total:.1f}%)" if total else "  (empty)")
    print(f"  signature files       : {len(file_ids)}")
    print(f"  signatures on disk     : {total_mb:.1f} MB total, {avg_kb:.1f} KB avg")
    print(f"  missing files (DB says signed, no file) : {len(missing_files)}")
    print(f"  orphan files (file, DB not signed)      : {len(orphan_files)}")
    print(f"  failures (signature_ok=0)               : {len(failures)}")

    for (p,) in failures[: args.show]:
        print(f"    FAIL  {p}")
    if len(failures) > args.show:
        print(f"    ... and {len(failures) - args.show} more")

    ok = signed == total and not missing_files and not orphan_files
    print("\nRESULT:", "OK — catalog consistent" if ok else "INCONSISTENT (see above)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
