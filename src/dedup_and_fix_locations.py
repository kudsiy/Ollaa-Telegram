"""
dedup_and_fix_locations.py
--------------------------
Two jobs in one script:

JOB 1 — DEDUPLICATION
  Removes duplicate listings from telegram_listings using two strategies:
  A) Exact duplicates: same raw text (after stripping whitespace)
  B) Fuzzy duplicates: same price + same area + same location
     (keeps the most recent entry)

JOB 2 — LOCATION RECLASSIFICATION
  Fixes rows currently tagged 'other_addis' with the shared place table
  in locations.py (the same one the parser uses).

Run:
    python src/dedup_and_fix_locations.py --dry-run
    python src/dedup_and_fix_locations.py
"""

import re
import argparse
from sqlalchemy import create_engine, text
from locations import match_text
from settings import DB_URL

engine = create_engine(DB_URL)


# ================================================================
# LOCATION RECLASSIFICATION
# Uses the shared place table in locations.py (the parser's own), so the
# codes written here are the same as everywhere else.
# ================================================================

def classify_location(text):
    """
    Returns a location code, or None if no place is named in the text.
    Applied only to rows currently tagged 'other_addis'.
    """
    return match_text(text) if text else None


# ================================================================
# JOB 1 — DEDUPLICATION
# ================================================================

def run_deduplication(dry_run=False):
    print("\n" + "="*50)
    print("JOB 1: DEDUPLICATION")
    print("="*50)

    # ── Strategy A: Exact text duplicates ────────────────────────
    with engine.connect() as conn:
        exact_dupes = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY TRIM(REGEXP_REPLACE(raw_text, '\\s+', ' ', 'g'))
                           ORDER BY created_at DESC
                       ) as rn
                FROM processed_listings
                WHERE raw_text IS NOT NULL
            ) sub
            WHERE rn > 1
        """)).scalar()

    print(f"\n  Exact text duplicates found:  {exact_dupes}")

    # ── Strategy B: Fuzzy duplicates (price + area + location) ───
    with engine.connect() as conn:
        fuzzy_dupes = conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY sale_price_birr, builtup_sqm, location
                           ORDER BY created_at DESC
                       ) as rn
                FROM processed_listings
                WHERE sale_price_birr IS NOT NULL
                AND builtup_sqm IS NOT NULL
                AND location IS NOT NULL
            ) sub
            WHERE rn > 1
        """)).scalar()

    print(f"  Fuzzy duplicates found:       {fuzzy_dupes}")

    if dry_run:
        print("\n  DRY RUN — no changes written.")
        return

    # Delete exact duplicates (keep most recent)
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM processed_listings
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY TRIM(REGEXP_REPLACE(raw_text, '\\s+', ' ', 'g'))
                               ORDER BY created_at DESC
                           ) as rn
                    FROM processed_listings
                    WHERE raw_text IS NOT NULL
                ) sub
                WHERE rn > 1
            )
        """))
    print(f"\n  Deleted {exact_dupes} exact duplicates.")

    # Delete fuzzy duplicates (keep most recent)
    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM processed_listings
            WHERE id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY sale_price_birr, builtup_sqm, location
                               ORDER BY created_at DESC
                           ) as rn
                    FROM processed_listings
                    WHERE sale_price_birr IS NOT NULL
                    AND builtup_sqm IS NOT NULL
                    AND location IS NOT NULL
                ) sub
                WHERE rn > 1
            )
        """))
    print(f"  Deleted {fuzzy_dupes} fuzzy duplicates.")

    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT COUNT(*) FROM processed_listings"
        )).scalar()
    print(f"\n  Rows remaining after dedup:   {remaining}")


# ================================================================
# JOB 2 — LOCATION RECLASSIFICATION
# ================================================================

def run_location_fix(dry_run=False):
    print("\n" + "="*50)
    print("JOB 2: LOCATION RECLASSIFICATION")
    print("="*50)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, raw_text
            FROM processed_listings
            WHERE location = 'other_addis'
            AND raw_text IS NOT NULL
        """)).fetchall()

    total = len(rows)
    print(f"\n  Rows with location='other_addis': {total}")

    updates = []
    location_counts = {}

    for row in rows:
        new_loc = classify_location(row.raw_text)
        if new_loc:
            updates.append({"id": row.id, "location": new_loc})
            location_counts[new_loc] = location_counts.get(new_loc, 0) + 1

    print(f"  Rows that can be reclassified:    {len(updates)}")
    print(f"\n  Breakdown of new locations:")
    for loc, count in sorted(location_counts.items(), key=lambda x: -x[1]):
        print(f"    {loc:<30} {count}")

    if dry_run:
        print("\n  DRY RUN — no changes written.")
        return

    with engine.begin() as conn:
        for u in updates:
            conn.execute(text("""
                UPDATE processed_listings
                SET location = :location
                WHERE id = :id
            """), u)

    print(f"\n  Updated {len(updates)} rows.")

    # Show remaining other_addis
    with engine.connect() as conn:
        still_unknown = conn.execute(text("""
            SELECT COUNT(*) FROM processed_listings
            WHERE location = 'other_addis'
        """)).scalar()
    print(f"  Still 'other_addis':              {still_unknown}")


# ================================================================
# FINAL SUMMARY
# ================================================================

def print_summary():
    print("\n" + "="*50)
    print("FINAL SEGMENT COVERAGE")
    print("="*50)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT location, property_type, COUNT(*) as samples
            FROM processed_listings
            WHERE valuation_eligible = true
            AND sale_price_birr IS NOT NULL
            AND builtup_sqm IS NOT NULL
            AND location != 'other_addis'
            GROUP BY location, property_type
            ORDER BY samples DESC
        """)).fetchall()

        total_usable = sum(r.samples for r in rows)
        high = sum(1 for r in rows if r.samples >= 10)
        medium = sum(1 for r in rows if 5 <= r.samples < 10)
        low = sum(1 for r in rows if r.samples < 5)

        print(f"\n  {'location':<25} {'type':<15} {'samples':>7}  confidence")
        print(f"  {'-'*25} {'-'*15} {'-'*7}  ----------")
        for r in rows:
            tier = 'HIGH' if r.samples >= 10 else 'MEDIUM' if r.samples >= 5 else 'LOW'
            print(f"  {r.location:<25} {r.property_type:<15} {r.samples:>7}  [{tier}]")

        print(f"\n  Total usable comparables: {total_usable}")
        print(f"  HIGH confidence segments: {high}")
        print(f"  MEDIUM confidence:        {medium}")
        print(f"  LOW confidence:           {low}")


# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing")
    parser.add_argument("--dedup-only", action="store_true",
                        help="Run deduplication only")
    parser.add_argument("--location-only", action="store_true",
                        help="Run location fix only")
    args = parser.parse_args()

    if args.location_only:
        run_location_fix(dry_run=args.dry_run)
    elif args.dedup_only:
        run_deduplication(dry_run=args.dry_run)
    else:
        run_deduplication(dry_run=args.dry_run)
        run_location_fix(dry_run=args.dry_run)

    if not args.dry_run:
        print_summary()
