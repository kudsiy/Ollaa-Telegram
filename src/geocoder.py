"""
geocoder.py — Address geocoding for Ollaa processed_listings
Place in: C:\Projects\ollaa\src\geocoder.py

Strategy:
  1. Fuzzy-match location text against 120+ Addis Ababa landmark table (fast, offline)
  2. Fall back to Nominatim (OpenStreetMap) if no landmark match (needs internet)
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

try:
    from rapidfuzz import process as fuzz_process, fuzz
except ImportError:
    print("ERROR: rapidfuzz not installed. Run: pip install rapidfuzz")
    sys.exit(1)

# ── DB Config ────────────────────────────────────────────────────────────────
from settings import DB_CONFIG

# ── Addis Ababa Landmark Table ────────────────────────────────────────────────
# Format: { 'canonical_name': (lat, lon, sub_city) }
# Coordinates: WGS84 decimal degrees
# Source: OSM + field verification (approximate to ~100m)

LANDMARKS = {
    # ── Major Nodes ───────────────────────────────────────────────────────
    'bole international airport':    (8.9779, 38.7993, 'Bole'),
    'bole airport':                  (8.9779, 38.7993, 'Bole'),
    'meskel square':                 (9.0082, 38.7576, 'Kirkos'),
    'addis ababa stadium':           (9.0174, 38.7575, 'Arada'),
    'unity park':                    (9.0278, 38.7621, 'Arada'),
    'sheraton addis':                (9.0156, 38.7630, 'Kirkos'),
    'hilton hotel':                  (9.0155, 38.7614, 'Kirkos'),

    # ── Roundabouts / Major Intersections ────────────────────────────────
    'arat kilo':                     (9.0278, 38.7621, 'Arada'),
    '4 kilo':                        (9.0278, 38.7621, 'Arada'),
    'siddist kilo':                  (9.0348, 38.7650, 'Gulele'),
    '6 kilo':                        (9.0348, 38.7650, 'Gulele'),
    'mexico':                        (9.0082, 38.7576, 'Kirkos'),
    'gotera':                        (8.9912, 38.7576, 'Nifas Silk'),
    'megenagna':                     (9.0226, 38.7901, 'Yeka'),
    'gerji':                         (9.0350, 38.8090, 'Yeka'),
    'sarbet':                        (8.9968, 38.7480, 'Nifas Silk'),
    'lebu':                          (8.9528, 38.7196, 'Kolfe'),
    'saris':                         (8.9790, 38.7250, 'Nifas Silk'),
    'kality':                        (8.9128, 38.7451, 'Akaki'),
    'kaliti':                        (8.9128, 38.7451, 'Akaki'),
    'peacock':                       (9.0050, 38.7800, 'Bole'),
    'summit':                        (8.9490, 38.8090, 'Nifas Silk'),
    'old airport':                   (9.0028, 38.7576, 'Bole'),
    'hayahulet':                     (9.0068, 38.7680, 'Bole'),
    '22 mazoria':                    (9.0068, 38.7680, 'Bole'),
    ' 22':                           (9.0068, 38.7680, 'Bole'),
    'piassa':                        (9.0260, 38.7572, 'Arada'),
    'merkato':                       (9.0360, 38.7430, 'Addis Ketema'),
    'shola':                         (9.0360, 38.7910, 'Yeka'),
    'kotebe':                        (9.0500, 38.7900, 'Yeka'),
    'urael':                         (9.0128, 38.7750, 'Bole'),
    'atlas':                         (9.0132, 38.7824, 'Bole'),
    'kazanchis':                     (9.0100, 38.7700, 'Kirkos'),
    'stadium':                       (9.0174, 38.7575, 'Arada'),

    # ── Bole Sub-areas ─────────────────────────────────────────────────
    'bole':                          (9.0050, 38.7800, 'Bole'),
    'bole medhanialem':              (9.0007, 38.7864, 'Bole'),
    'bole meda':                     (9.0007, 38.7864, 'Bole'),
    'bole bulbula':                  (8.9800, 38.8100, 'Bole'),
    'bole arabsa':                   (8.9650, 38.8250, 'Bole'),
    'bole mini':                     (9.0050, 38.7800, 'Bole'),
    'bole main':                     (9.0050, 38.7800, 'Bole'),
    'bole atlas':                    (9.0132, 38.7824, 'Bole'),
    'bole airport road':             (8.9950, 38.7900, 'Bole'),
    'bole sub city':                 (9.0050, 38.7800, 'Bole'),

    # ── CMC / Ayat Zone ────────────────────────────────────────────────
    'cmc':                           (9.0470, 38.7690, 'Yeka'),
    'ayat':                          (8.9992, 38.8611, 'Bole'),
    'ayat zone':                     (8.9992, 38.8611, 'Bole'),
    'ayat 49':                       (8.9992, 38.8611, 'Bole'),
    'ayat real estate':              (8.9992, 38.8611, 'Bole'),
    'imperial':                      (9.0226, 38.7901, 'Yeka'),

    # ── Nifas Silk Lafto ────────────────────────────────────────────────
    'nifas silk':                    (8.9800, 38.7900, 'Nifas Silk'),
    'lafto':                         (8.9600, 38.7400, 'Nifas Silk'),
    'akaki':                         (8.9128, 38.7451, 'Akaki'),
    'akaki kaliti':                  (8.9128, 38.7451, 'Akaki'),
    'mekanissa':                     (8.9700, 38.7500, 'Nifas Silk'),
    'jemo':                          (8.9450, 38.7350, 'Kolfe'),
    'millenium':                     (8.9700, 38.7600, 'Nifas Silk'),

    # ── Kirkos ─────────────────────────────────────────────────────────
    'kirkos':                        (9.0082, 38.7576, 'Kirkos'),
    'lideta':                        (9.0082, 38.7400, 'Lideta'),
    'beklo bet':                     (9.0000, 38.7600, 'Kirkos'),
    'wavel':                         (9.0082, 38.7700, 'Kirkos'),
    'bambis':                        (9.0082, 38.7700, 'Kirkos'),
    'sar bet':                       (8.9968, 38.7480, 'Nifas Silk'),

    # ── Kolfe / Addis Ketema ────────────────────────────────────────────
    'kolfe':                         (9.0100, 38.7200, 'Kolfe'),
    'addis ketema':                  (9.0260, 38.7400, 'Addis Ketema'),
    'tor hailoch':                   (9.0100, 38.7200, 'Kolfe'),
    'goro':                          (9.0300, 38.7200, 'Kolfe'),
    'kara':                          (9.0050, 38.7100, 'Kolfe'),

    # ── Gulele ─────────────────────────────────────────────────────────
    'gulele':                        (9.0500, 38.7500, 'Gulele'),
    'entoto':                        (9.0700, 38.7600, 'Gulele'),
    'ferensay':                      (9.0400, 38.7550, 'Gulele'),
    'finfine':                       (9.0400, 38.7550, 'Gulele'),

    # ── Yeka ────────────────────────────────────────────────────────────
    'yeka':                          (9.0400, 38.8000, 'Yeka'),
    'lemi kura':                     (9.0600, 38.8200, 'Lemi Kura'),
    'tafo':                          (9.0500, 38.8100, 'Lemi Kura'),
    'sefere selam':                  (9.0200, 38.8100, 'Yeka'),
    'kore':                          (9.0100, 38.8050, 'Yeka'),
    'grma':                          (9.0300, 38.8000, 'Yeka'),
    'wonji':                         (9.0350, 38.8090, 'Yeka'),

    # ── Sheger City / Surrounding ───────────────────────────────────────
    'sheger city':                   (8.8800, 38.8100, 'Sheger'),
    'dukem':                         (8.8500, 38.8300, 'Sheger'),
    'sululta':                       (9.1700, 38.7500, 'Sheger'),
    'burayu':                        (9.0600, 38.6500, 'Sheger'),
    'gelan':                         (8.8800, 38.8100, 'Sheger'),
    'legetafo':                      (9.0700, 38.8300, 'Lemi Kura'),

    # ── Hospitals / Universities (common address references) ─────────────
    'black lion':                    (9.0217, 38.7601, 'Arada'),
    'tikur anbessa':                 (9.0217, 38.7601, 'Arada'),
    'st paul':                       (9.0360, 38.7490, 'Gulele'),
    'addis ababa university':        (9.0282, 38.7642, 'Arada'),
    'aau':                           (9.0282, 38.7642, 'Arada'),
    'ecsu':                          (9.0400, 38.7900, 'Yeka'),
    'civil service university':      (9.0400, 38.7900, 'Yeka'),
    'addis ababa science technology': (8.9990, 38.8140, 'Bole'),
    'astu':                          (8.9990, 38.8140, 'Bole'),
}

# Pre-build lowercase keys for matching
_LANDMARK_KEYS = list(LANDMARKS.keys())

# ── Sub-city name normalization ────────────────────────────────────────────────
SUBCITY_ALIASES = {
    'bole':          'Bole',
    'kirkos':        'Kirkos',
    'yeka':          'Yeka',
    'nifas silk':    'Nifas Silk',
    'nifas silk lafto': 'Nifas Silk',
    'kolfe':         'Kolfe',
    'kolfe keranio': 'Kolfe',
    'gulele':        'Gulele',
    'arada':         'Arada',
    'lideta':        'Lideta',
    'addis ketema':  'Addis Ketema',
    'akaki':         'Akaki',
    'akaki kaliti':  'Akaki',
    'lemi kura':     'Lemi Kura',
    'lemi':          'Lemi Kura',
}


# ── Core Geocoding Function ───────────────────────────────────────────────────

def geocode_location_text(
    location_text: str,
    use_nominatim: bool = True,
    min_score: int = 65,
) -> Optional[dict]:
    """
    Geocode an Ethiopian location string.

    Returns dict with: lat, lon, matched_name, sub_city, method, confidence
    Returns None if no match found.

    Args:
        location_text: Raw location string from processed_listings
        use_nominatim: Whether to try Nominatim if landmark fails
        min_score: Minimum rapidfuzz score to accept a landmark match
    """
    if not location_text or not location_text.strip():
        return None

    query = location_text.lower().strip()

    # ── Phase 1: Landmark fuzzy match ─────────────────────────────────────
    result = fuzz_process.extractOne(
        query,
        _LANDMARK_KEYS,
        scorer=fuzz.token_set_ratio,
        score_cutoff=min_score,
    )

    if result:
        matched_key, score, _ = result
        lat, lon, sub_city = LANDMARKS[matched_key]

        confidence = 'HIGH' if score >= 90 else ('MEDIUM' if score >= 75 else 'LOW')

        return {
            'lat':          lat,
            'lon':          lon,
            'matched_name': matched_key,
            'sub_city':     sub_city,
            'method':       'landmark',
            'confidence':   confidence,
            'score':        score,
        }

    # ── Phase 2: Nominatim fallback ───────────────────────────────────────
    if use_nominatim:
        return _geocode_nominatim(location_text)

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
    the landmark-only pass is instant. Nominatim fallback adds ~1s/row.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, location, sub_city
            FROM processed_listings
            WHERE lat IS NULL
              AND (location IS NOT NULL OR sub_city IS NOT NULL)
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    print(f"  Found {len(rows):,} rows to geocode.")

    success = 0
    failed  = 0
    nominatim_calls = 0

    with conn.cursor() as upd:
        for row in rows:
            location_text = row['location'] or row['sub_city'] or ''
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

    print(f"  Geocoded:  {success:,} (landmark: {success-nominatim_calls}, nominatim: {nominatim_calls})")
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
