"""
geocoder.py — Address geocoding for Ollaa processed_listings
Place in: C:\Projects\ollaa\src\geocoder.py

Strategy:
  1. Look up the listing's location code in the shared place table, locations.py
     (offline). A place without coordinates uses its wider area's.
  2. Fall back to Nominatim (OpenStreetMap) with the place name (needs internet)
  3. Store lat, lon, geocode_method, geocode_confidence on each row

Usage:
  python src\geocoder.py --dry-run   # show matches without writing
  python src\geocoder.py --apply     # geocode all rows missing lat/lon
  python src\geocoder.py --stats     # show coverage stats

Import:
  from geocoder import geocode_location_text
"""

import sys
import os
import time
import argparse
from typing import Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed.")
    sys.exit(1)

# ── DB Config ────────────────────────────────────────────────────────────────
from settings import DB_CONFIG

# ── Places ───────────────────────────────────────────────────────────────────
# Coordinates come from the shared place table (moved there from this file in S6).
from locations import NOISE, PLACES, UNKNOWN, canonical, coordinates, match_text


# ── Core Geocoding Function ───────────────────────────────────────────────────

def geocode_location_text(
    location_text: str,
    use_nominatim: bool = True,
) -> Optional[dict]:
    """
    Geocode a location code as stored in processed_listings.location
    ('bole_bulbula'), or any text that names a place.
    Returns dict with: lat, lon, matched_name, sub_city, method, confidence
    Returns None if no match found.

    Args:
        location_text: Location code or place name
        use_nominatim: Whether to try Nominatim if the place has no coordinates
    """
    if not location_text or not location_text.strip():
        return None

    code = canonical(location_text.strip())
    if code in (NOISE, UNKNOWN):
        return None
    if code not in PLACES:
        code = match_text(location_text)

    # ── Phase 1: shared place table ───────────────────────────────────────
    found = coordinates(code)
    if found:
        lat, lon, sub_city = found
        return {
            'lat':          lat,
            'lon':          lon,
            'matched_name': code,
            'sub_city':     sub_city,
            'method':       'place',
            # The place's own coordinates, or only its wider area's.
            'confidence':   'HIGH' if PLACES[code].lat is not None else 'MEDIUM',
            'score':        100,
        }

    # ── Phase 2: Nominatim fallback ───────────────────────────────────────
    if use_nominatim:
        return _geocode_nominatim(PLACES[code].name if code in PLACES else location_text)
    return None


def _geocode_nominatim(location_text: str) -> Optional[dict]:
    """Geocode via Nominatim (OpenStreetMap). Needs internet. Rate limited."""
    try:
        import urllib.request
        import urllib.parse
        import json as _json

        query = f"{location_text}, Addis Ababa, Ethiopia"
        encoded = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1"

        req = urllib.request.Request(url, headers={'User-Agent': 'OllaaPropertyPlatform/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode())

        if data:
            item = data[0]
            lat = float(item['lat'])
            lon = float(item['lon'])

            # Only accept if result is near Addis Ababa
            # AA bounding box: lat 8.7–9.2, lon 38.5–39.0
            if 8.7 <= lat <= 9.2 and 38.5 <= lon <= 39.0:
                return {
                    'lat':          lat,
                    'lon':          lon,
                    'matched_name': item.get('display_name', location_text)[:80],
                    'sub_city':     None,
                    'method':       'nominatim',
                    'confidence':   'MEDIUM',
                    'score':        70,
                }

    except Exception as e:
        # Nominatim failed — don't crash the pipeline
        pass

    return None


# ── Database Operations ────────────────────────────────────────────────────────

def ensure_geocode_columns(conn):
    """Add geocoding columns to processed_listings if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION;")
        cur.execute("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION;")
        cur.execute("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS geocode_method VARCHAR(20);")
        cur.execute("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS geocode_confidence VARCHAR(10);")
        cur.execute("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS geocode_matched_name VARCHAR(100);")
        conn.commit()
    print("  ✅ Geocode columns ensured.")


def batch_geocode(conn, dry_run: bool = True, limit: int = 5000):
    """
    Geocode all processed_listings rows where lat IS NULL.

    Nominatim rate limit: 1 request/second. For large batches,
    the place-table pass is instant. Nominatim fallback adds ~1s/row.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, location
            FROM processed_listings
            WHERE lat IS NULL
              AND location IS NOT NULL
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    print(f"  Found {len(rows):,} rows to geocode.")

    success = 0
    failed  = 0
    nominatim_calls = 0

    with conn.cursor() as upd:
        for row in rows:
            location_text = row['location'] or ''
            geo = geocode_location_text(location_text, use_nominatim=True)

            if geo:
                success += 1
                if geo['method'] == 'nominatim':
                    nominatim_calls += 1
                    time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

                if not dry_run:
                    upd.execute("""
                        UPDATE processed_listings
                        SET lat                  = %s,
                            lon                  = %s,
                            geocode_method       = %s,
                            geocode_confidence   = %s,
                            geocode_matched_name = %s
                        WHERE id = %s
                    """, (
                        geo['lat'], geo['lon'],
                        geo['method'], geo['confidence'],
                        geo['matched_name'],
                        row['id']
                    ))
            else:
                failed += 1

        if not dry_run:
            conn.commit()

    print(f"  Geocoded:  {success:,} (place table: {success-nominatim_calls}, nominatim: {nominatim_calls})")
    print(f"  Failed:    {failed:,}")
    if dry_run:
        print("  DRY RUN — no changes written.")


def print_geocode_stats(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM processed_listings")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM processed_listings WHERE lat IS NOT NULL")
        geocoded = cur.fetchone()[0]
        cur.execute("""
            SELECT geocode_method, COUNT(*)
            FROM processed_listings
            WHERE geocode_method IS NOT NULL
            GROUP BY geocode_method
        """)
        by_method = cur.fetchall()

    print(f"\n  Total rows:     {total:,}")
    print(f"  Geocoded:       {geocoded:,}  ({geocoded/total*100:.1f}%)")
    print(f"  Not geocoded:   {total-geocoded:,}")
    print(f"\n  By method:")
    for method, count in by_method:
        print(f"    {method}: {count:,}")


# ── Standalone CLI ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Geocoder for Ollaa processed_listings')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show matches without writing (default)')
    parser.add_argument('--apply',   action='store_true', help='Write geocode results to DB')
    parser.add_argument('--stats',   action='store_true', help='Show coverage stats')
    parser.add_argument('--test',    type=str, default=None,
                        help='Test a single location string')
    parser.add_argument('--limit',   type=int, default=1000,
                        help='Max rows to geocode per run (default 1000)')
    args = parser.parse_args()

    if args.test:
        print(f"\n  Testing: '{args.test}'")
        result = geocode_location_text(args.test)
        if result:
            print(f"  ✅ Match: {result['matched_name']}")
            print(f"  Lat/Lon: {result['lat']}, {result['lon']}")
            print(f"  Sub-city: {result['sub_city']}")
            print(f"  Method: {result['method']} | Confidence: {result['confidence']} | Score: {result['score']}")
        else:
            print("  ❌ No match found.")
        sys.exit(0)

    conn = psycopg2.connect(**DB_CONFIG)
    ensure_geocode_columns(conn)

    if args.stats:
        print_geocode_stats(conn)
    elif args.apply:
        print(f"\n  Running geocoder (apply mode, limit={args.limit})...")
        batch_geocode(conn, dry_run=False, limit=args.limit)
        print_geocode_stats(conn)
    else:
        print(f"\n  Running geocoder (dry run, limit={args.limit})...")
        batch_geocode(conn, dry_run=True, limit=args.limit)

    conn.close()
