"""
dedup_fast.py — Fast pre-deduplication for Ollaa processed_listings
Place in: C:\Projects\ollaa\src\dedup_fast.py

Run BEFORE semantic_dedup.py. This catches ~70% of duplicates in seconds
using phone number + price + location fingerprinting and fuzzy matching.
Semantic dedup then handles the rest (same listing, no phone number).

Usage:
  python src\dedup_fast.py            # dry run — shows what would be flagged
  python src\dedup_fast.py --apply    # write duplicate_of / is_duplicate to DB
  python src\dedup_fast.py --stats    # show current duplicate stats only
"""

import sys
import os
import argparse
import hashlib
from collections import defaultdict
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not found. Run: pip install psycopg2-binary")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: rapidfuzz not found. Run: pip install rapidfuzz")
    sys.exit(1)

# ── DB Config ────────────────────────────────────────────────────────────────
from settings import DB_CONFIG

# ── Thresholds ────────────────────────────────────────────────────────────────
PHONE_EXACT_MATCH    = True   # Same canonical phone → always duplicate
PRICE_TOLERANCE_PCT  = 0.05   # 5% price difference still = same listing
LOCATION_SIM_THRESH  = 75     # rapidfuzz score 0-100 for location match
TEXT_SIM_THRESH      = 88     # rapidfuzz score for full text similarity


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def ensure_columns(conn):
    """Add is_duplicate and duplicate_of columns if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            ALTER TABLE processed_listings
            ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE;
        """)
        cur.execute("""
            ALTER TABLE processed_listings
            ADD COLUMN IF NOT EXISTS duplicate_of INTEGER REFERENCES processed_listings(id);
        """)
        conn.commit()
    print("  ✅ Columns is_duplicate, duplicate_of ensured.")


def load_listings(conn) -> list:
    """Load all non-duplicate processed listings for analysis."""
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT
                id,
                raw_text,
                contact_phone,
                price_etb,
                location,
                sub_city,
                property_type,
                intent,
                bedrooms,
                area_sqm,
                posted_at,
                channel_name,
                is_duplicate,
                duplicate_of
            FROM processed_listings
            ORDER BY posted_at ASC, id ASC
        """)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def make_phone_key(phone: Optional[str]) -> Optional[str]:
    """Canonical phone key — strip all non-digit chars."""
    if not phone:
        return None
    digits = ''.join(c for c in phone if c.isdigit())
    # Normalize: remove leading country code prefix
    if digits.startswith('251') and len(digits) == 12:
        digits = digits[3:]   # → 9-digit local number
    elif digits.startswith('0') and len(digits) == 10:
        digits = digits[1:]   # → 9-digit local number
    return digits if len(digits) == 9 else None


def prices_match(p1: Optional[float], p2: Optional[float]) -> bool:
    """Return True if two prices are within PRICE_TOLERANCE_PCT of each other."""
    if p1 is None or p2 is None:
        return False
    if p1 == 0 or p2 == 0:
        return p1 == p2
    diff = abs(p1 - p2) / max(p1, p2)
    return diff <= PRICE_TOLERANCE_PCT


def location_matches(loc1: Optional[str], loc2: Optional[str]) -> bool:
    """Fuzzy location match using rapidfuzz."""
    if not loc1 or not loc2:
        return True   # unknown location — don't use to differentiate
    score = fuzz.token_sort_ratio(loc1.lower(), loc2.lower())
    return score >= LOCATION_SIM_THRESH


def text_similar(t1: Optional[str], t2: Optional[str]) -> bool:
    """High-threshold full text similarity — catches near-identical listings."""
    if not t1 or not t2:
        return False
    # Use partial_ratio for speed on long texts
    score = fuzz.partial_ratio(t1[:500], t2[:500])
    return score >= TEXT_SIM_THRESH


def run_fast_dedup(listings: list) -> list:
    """
    Core dedup logic. Returns list of (duplicate_id, canonical_id, reason) tuples.

    Strategy (in priority order):
      1. Exact phone match + price match → DUPLICATE (strongest signal)
      2. Exact phone match + location match → DUPLICATE
      3. High text similarity (no phone) → DUPLICATE
    """
    duplicates = []   # list of (dup_id, canonical_id, reason)
    seen_phones = {}  # phone_key → listing_id of first seen (canonical)
    seen_ids    = set()

    # Index by phone first
    for listing in listings:
        if listing.get('is_duplicate'):
            continue   # already marked

        phone_key = make_phone_key(listing.get('contact_phone'))
        lid = listing['id']

        if phone_key and phone_key in seen_phones:
            canonical_id = seen_phones[phone_key]
            # Verify with price or location
            canonical = next((l for l in listings if l['id'] == canonical_id), None)
            if canonical:
                if prices_match(listing.get('price_etb'), canonical.get('price_etb')):
                    duplicates.append((lid, canonical_id, 'phone+price'))
                    seen_ids.add(lid)
                    continue
                elif location_matches(listing.get('location'), canonical.get('location')):
                    duplicates.append((lid, canonical_id, 'phone+location'))
                    seen_ids.add(lid)
                    continue
        elif phone_key:
            seen_phones[phone_key] = lid

    # Text similarity pass for listings without phone matches
    no_phone = [l for l in listings
                if l['id'] not in seen_ids
                and not l.get('is_duplicate')
                and not make_phone_key(l.get('contact_phone'))]

    # O(n²) but only on no-phone subset, which is smaller
    # Stop after finding 500 duplicates to avoid very long runs
    checked = set()
    for i, l1 in enumerate(no_phone):
        if len(duplicates) > 500:
            print("  ⚠️  Hit 500 duplicate cap on text-similarity pass. Re-run after applying.")
            break
        for l2 in no_phone[i+1:]:
            pair = (min(l1['id'], l2['id']), max(l1['id'], l2['id']))
            if pair in checked:
                continue
            checked.add(pair)

            if (l1.get('intent') == l2.get('intent')
                    and l1.get('property_type') == l2.get('property_type')
                    and text_similar(l1.get('raw_text'), l2.get('raw_text'))):
                # older id = canonical
                canonical_id = min(l1['id'], l2['id'])
                dup_id       = max(l1['id'], l2['id'])
                if dup_id not in seen_ids:
                    duplicates.append((dup_id, canonical_id, 'text-similarity'))
                    seen_ids.add(dup_id)

    return duplicates


def apply_duplicates(conn, duplicates: list):
    """Write is_duplicate=True and duplicate_of=canonical_id to the DB."""
    if not duplicates:
        print("  No duplicates to write.")
        return

    with conn.cursor() as cur:
        for dup_id, canonical_id, reason in duplicates:
            cur.execute("""
                UPDATE processed_listings
                SET is_duplicate = TRUE,
                    duplicate_of = %s
                WHERE id = %s
            """, (canonical_id, dup_id))
    conn.commit()
    print(f"  ✅ Marked {len(duplicates)} rows as duplicates.")


def print_stats(conn):
    """Print current deduplication statistics."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM processed_listings")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM processed_listings WHERE is_duplicate = TRUE")
        dupes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM processed_listings WHERE is_duplicate IS FALSE OR is_duplicate IS NULL")
        unique = cur.fetchone()[0]

    print(f"\n  Total processed_listings : {total:,}")
    print(f"  Unique (not duplicate)   : {unique:,}")
    print(f"  Marked as duplicate      : {dupes:,}")
    print(f"  Duplicate rate           : {dupes/total*100:.1f}%\n")


def main():
    parser = argparse.ArgumentParser(description='Fast pre-deduplication for Ollaa')
    parser.add_argument('--apply', action='store_true', help='Write duplicates to DB')
    parser.add_argument('--stats', action='store_true', help='Show stats only')
    args = parser.parse_args()

    conn = get_connection()
    ensure_columns(conn)

    if args.stats:
        print_stats(conn)
        conn.close()
        return

    print("\n  Loading listings from processed_listings...")
    listings = load_listings(conn)
    print(f"  Loaded {len(listings):,} rows.")

    print("\n  Running fast deduplication...")
    print("  Phase 1: Phone + price/location fingerprinting...")
    duplicates = run_fast_dedup(listings)

    print(f"\n  Found {len(duplicates):,} duplicates.")

    # Show breakdown by reason
    reasons = defaultdict(int)
    for _, _, reason in duplicates:
        reasons[reason] += 1
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {count:,}")

    if args.apply:
        print("\n  Writing to database...")
        apply_duplicates(conn, duplicates)
        print_stats(conn)
    else:
        print("\n  DRY RUN — no changes written.")
        print("  Run with --apply to write to database.")
        if duplicates:
            print("\n  Sample duplicates (first 10):")
            for dup_id, canonical_id, reason in duplicates[:10]:
                print(f"    id={dup_id} is duplicate of id={canonical_id} [{reason}]")

    conn.close()


if __name__ == '__main__':
    main()
