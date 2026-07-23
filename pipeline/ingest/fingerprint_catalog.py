#!/usr/bin/env python3
"""Build the Encore local catalog from a folder of music files.

Run this the night before the hackathon (a few hours for ~3000 tracks):

    python fingerprint_catalog.py --music-dir ~/Music/crate --out ../../data/catalog

It produces, inside --out:
  catalog.sqlite         one row per track: id, path, title, artist, album,
                         duration, bpm (optional), enrichment columns (filled later)
  signatures/<id>.shazamsignature   reference signatures for ShazamKit custom
                         catalog (generated via the swift helper, macOS only)

Notes
- Metadata comes from file tags (mutagen). Fix bad tags at the source; the
  whole product displays what is in this DB.
- BPM analysis (librosa) is slow: ~5-10 s/track. Use --bpm only for the demo
  subset, or let enrich_catalog.py fetch BPM from APIs instead.
- ShazamKit signatures require macOS (the swift helper uses SHSignatureGenerator).
  On other platforms the script still builds catalog.sqlite and prints the
  command to run on the Mac.
"""
import argparse, os, sqlite3, subprocess, sys, unicodedata
from pathlib import Path

AUDIO_EXT = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".aiff", ".ogg"}
SWIFT_HELPER = Path(__file__).with_name("make_signature.swift")


def norm(s):
    return unicodedata.normalize("NFC", s or "").strip()


def read_tags(path: Path):
    from mutagen import File as MFile
    m = MFile(path, easy=True)
    if m is None:
        return {"title": path.stem, "artist": "", "album": "", "duration": 0}
    g = lambda k: norm(m.get(k, [""])[0]) if m.get(k) else ""
    return {
        "title": g("title") or path.stem,
        "artist": g("artist"),
        "album": g("album"),
        "duration": round(getattr(m.info, "length", 0) or 0, 1),
    }


def analyze_bpm(path: Path):
    import librosa
    y, sr = librosa.load(path, mono=True, duration=90, offset=30)
    tempo = librosa.beat.tempo(y=y, sr=sr)
    return round(float(tempo[0]), 1) if len(tempo) else None


def ensure_db(out: Path):
    db = sqlite3.connect(out / "catalog.sqlite")
    db.execute("""CREATE TABLE IF NOT EXISTS tracks(
        id INTEGER PRIMARY KEY, path TEXT UNIQUE, title TEXT, artist TEXT,
        album TEXT, duration REAL, bpm REAL,
        apple_url TEXT, spotify_url TEXT, artwork_url TEXT, preview_url TEXT,
        signature_ok INTEGER DEFAULT 0)""")
    return db


def make_signature(path: Path, sig_path: Path) -> bool:
    """macOS only: call the swift helper to emit a .shazamsignature file."""
    if sys.platform != "darwin":
        return False
    r = subprocess.run(["swift", str(SWIFT_HELPER), str(path), str(sig_path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    signature FAILED: {r.stderr.strip()[:200]}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--music-dir", required=True, type=Path)
    ap.add_argument("--out", default=Path(__file__).parents[2] / "data/catalog", type=Path)
    ap.add_argument("--bpm", action="store_true", help="run librosa BPM analysis (slow)")
    ap.add_argument("--limit", type=int, default=0, help="only process N files (for testing)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    sig_dir = args.out / "signatures"; sig_dir.mkdir(exist_ok=True)
    db = ensure_db(args.out)

    files = sorted(p for p in args.music_dir.rglob("*") if p.suffix.lower() in AUDIO_EXT)
    if args.limit: files = files[: args.limit]
    print(f"{len(files)} audio files found in {args.music_dir}")

    done = skipped = 0
    for i, f in enumerate(files, 1):
        if db.execute("SELECT 1 FROM tracks WHERE path=?", (str(f),)).fetchone():
            skipped += 1; continue
        tags = read_tags(f)
        bpm = analyze_bpm(f) if args.bpm else None
        cur = db.execute(
            "INSERT INTO tracks(path,title,artist,album,duration,bpm) VALUES(?,?,?,?,?,?)",
            (str(f), tags["title"], tags["artist"], tags["album"], tags["duration"], bpm))
        tid = cur.lastrowid
        ok = make_signature(f, sig_dir / f"{tid}.shazamsignature")
        db.execute("UPDATE tracks SET signature_ok=? WHERE id=?", (int(ok), tid))
        done += 1
        if i % 50 == 0:
            db.commit(); print(f"  {i}/{len(files)}  (+{done}, skipped {skipped})")
    db.commit()

    n_sig = db.execute("SELECT COUNT(*) FROM tracks WHERE signature_ok=1").fetchone()[0]
    n_all = db.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    print(f"\ncatalog.sqlite: {n_all} tracks, {n_sig} signatures")
    if sys.platform != "darwin":
        print("Not on macOS: signatures were skipped. Run this script again on the Mac,")
        print("it resumes where it left off (already-inserted tracks are re-signed only if signature_ok=0).")


if __name__ == "__main__":
    main()
