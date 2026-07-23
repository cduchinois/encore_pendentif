#!/usr/bin/env python3
"""Enrich catalog.sqlite with playable links + artwork.

    python enrich_catalog.py                       # enrich everything, iTunes only
    python enrich_catalog.py --priority demo.txt   # enrich these "Artist - Title" lines first
    python enrich_catalog.py --spotify             # also fill spotify_url (needs .env)

- iTunes Search API: free, no auth, ~20 req/min -> we sleep 3.1 s between calls.
  3000 tracks ≈ 2h40. Run overnight, or enrich only the demo subset.
- Spotify: set SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in ../../.env
"""
import argparse, os, sqlite3, time, urllib.parse, urllib.request, json
from pathlib import Path

DB = Path(__file__).parents[2] / "data/catalog/catalog.sqlite"
ITUNES_SLEEP = 3.1


def http_json(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def itunes_lookup(artist, title):
    q = urllib.parse.quote(f"{artist} {title}")
    j = http_json(f"https://itunes.apple.com/search?term={q}&entity=song&limit=3")
    for hit in j.get("results", []):
        return {
            "apple_url": hit.get("trackViewUrl"),
            "artwork_url": (hit.get("artworkUrl100") or "").replace("100x100", "600x600"),
            "preview_url": hit.get("previewUrl"),
        }
    return {}


def spotify_token():
    import base64
    cid, sec = os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"]
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    j = http_json("https://accounts.spotify.com/api/token",
                  headers={"Authorization": f"Basic {auth}",
                           "Content-Type": "application/x-www-form-urlencoded"},
                  data=b"grant_type=client_credentials")
    return j["access_token"]


def spotify_lookup(token, artist, title):
    q = urllib.parse.quote(f"track:{title} artist:{artist}")
    j = http_json(f"https://api.spotify.com/v1/search?q={q}&type=track&limit=1",
                  headers={"Authorization": f"Bearer {token}"})
    items = j.get("tracks", {}).get("items", [])
    return items[0]["external_urls"]["spotify"] if items else None


def load_env():
    env = Path(__file__).parents[2] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", type=Path, help='file of "Artist - Title" lines to do first')
    ap.add_argument("--spotify", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_env()

    db = sqlite3.connect(DB); db.row_factory = sqlite3.Row
    rows = db.execute("SELECT id,title,artist FROM tracks WHERE apple_url IS NULL").fetchall()

    if args.priority and args.priority.exists():
        wanted = {l.strip().lower() for l in args.priority.read_text().splitlines() if l.strip()}
        key = lambda r: 0 if f"{r['artist']} - {r['title']}".lower() in wanted else 1
        rows = sorted(rows, key=key)
    if args.limit: rows = rows[: args.limit]

    token = spotify_token() if args.spotify else None
    print(f"enriching {len(rows)} tracks (iTunes{' + Spotify' if token else ''})")

    for i, r in enumerate(rows, 1):
        try:
            info = itunes_lookup(r["artist"], r["title"])
            sp = spotify_lookup(token, r["artist"], r["title"]) if token else None
            db.execute("""UPDATE tracks SET apple_url=?, artwork_url=?, preview_url=?,
                          spotify_url=COALESCE(?, spotify_url) WHERE id=?""",
                       (info.get("apple_url"), info.get("artwork_url"),
                        info.get("preview_url"), sp, r["id"]))
        except Exception as e:
            print(f"  #{r['id']} {r['artist']} - {r['title']}: {e}")
        if i % 25 == 0:
            db.commit(); print(f"  {i}/{len(rows)}")
        time.sleep(ITUNES_SLEEP)
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM tracks WHERE apple_url IS NOT NULL").fetchone()[0]
    print(f"done. {n} tracks have links.")


if __name__ == "__main__":
    main()
