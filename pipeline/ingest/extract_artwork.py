#!/usr/bin/env python3
"""Extract embedded cover art from the catalog, de-duplicated by content hash.

    python extract_artwork.py --out ../../data/catalog [--max-px 300]

Why de-dup by content hash: a compilation is 10-20 tracks sharing ONE cover, so
hashing the image bytes collapses them to a single file automatically (robust to
folder layout). ~16k tracks typically reduce to ~1.3k unique covers.

Contract-neutral by design: this does NOT modify catalog.sqlite. It writes, under
--out/artwork/:
  <sha1>.jpg            one file per UNIQUE cover
  index.json            { "by_track": {track_id: "<sha1>.jpg"}, "stats": {...} }

Wiring the covers into the DB (reuse artwork_url as a relative path, or add a new
field) is a later 1-line step once the iOS side (Jade) agrees the contract — the
slow part (scanning every file) is done here, once.

--max-px N downsizes each unique cover to N px on the long side via `sips` (native
macOS, no extra dependency). Omit it to keep full-resolution covers.
"""
import argparse, hashlib, json, os, sqlite3, subprocess, sys, tempfile
from pathlib import Path
from mutagen import File as MFile


def embedded_art(path):
    """Return raw cover bytes embedded in an audio file, or None."""
    try:
        m = MFile(path)
    except Exception:
        return None
    if not m or not m.tags:
        return None
    for k in m.tags.keys():                     # ID3 APIC (mp3)
        if k.startswith("APIC"):
            return m.tags[k].data
    covr = m.tags.get("covr")                   # MP4 covr (m4a/aac)
    if covr:
        return bytes(covr[0])
    return None


def art_ext(data):
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return "img"


def resize(src, dst, max_px):
    """Downscale to max_px on the long side via native sips. Returns True on success."""
    r = subprocess.run(["sips", "-Z", str(max_px), "-s", "format", "jpeg", src, "--out", dst],
                       capture_output=True, text=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=Path(__file__).parents[2] / "data/catalog", type=Path)
    ap.add_argument("--max-px", type=int, default=0, help="downscale long side (0 = full res)")
    args = ap.parse_args()

    db = sqlite3.connect(args.out / "catalog.sqlite")
    art_dir = args.out / "artwork"; art_dir.mkdir(parents=True, exist_ok=True)
    rows = db.execute("SELECT id, path FROM tracks WHERE signature_ok=1 ORDER BY id").fetchall()

    by_track = {}; seen = {}                     # sha1 -> stored filename
    no_art = []
    for i, (tid, path) in enumerate(rows, 1):
        data = embedded_art(path)
        if not data:
            no_art.append(tid); continue
        h = hashlib.sha1(data).hexdigest()
        if h not in seen:
            if args.max_px:                      # write raw to temp, sips-resize
                fd, tmp = tempfile.mkstemp(suffix="." + art_ext(data)); os.close(fd)
                Path(tmp).write_bytes(data)
                dst = art_dir / f"{h}.jpg"
                ok = resize(tmp, str(dst), args.max_px)
                os.unlink(tmp)
                if not ok:                        # fallback: keep original bytes
                    dst = art_dir / f"{h}.{art_ext(data)}"; dst.write_bytes(data)
                seen[h] = dst.name
            else:
                dst = art_dir / f"{h}.{art_ext(data)}"; dst.write_bytes(data)
                seen[h] = dst.name
        by_track[tid] = seen[h]
        if i % 1000 == 0:
            print(f"  {i}/{len(rows)}  unique so far: {len(seen)}")

    total_bytes = sum((art_dir / n).stat().st_size for n in set(seen.values()))
    stats = {"tracks": len(rows), "with_art": len(by_track), "without_art": len(no_art),
             "unique_covers": len(seen), "total_mb": round(total_bytes / 1e6, 1),
             "max_px": args.max_px or "full"}
    (art_dir / "index.json").write_text(json.dumps({"by_track": by_track, "stats": stats}, indent=1))

    print(f"\n{stats['with_art']}/{stats['tracks']} tracks with art -> "
          f"{stats['unique_covers']} unique covers, {stats['total_mb']} MB "
          f"({stats['max_px']} px). without art: {stats['without_art']}")
    print(f"index -> {art_dir / 'index.json'}")


if __name__ == "__main__":
    main()
