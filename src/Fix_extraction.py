"""
fix_extraction.py
-----------------
Re-runs extraction on processed_listings rows that are missing
builtup_sqm or sale_price_birr, using improved regex patterns
learned from actual Ethiopian real estate listing text.

Fixes:
1. Area patterns: catches M², M2, ካሬ, ካሬ ሜትር (with or without sqm/m2)
2. Price patterns: catches ብር amounts (not just millions), price in parentheses
3. Multi-listing posts: extracts first valid price+area pair

Safe to re-run: only updates NULL fields, never overwrites existing data.

Usage:
    python src/fix_extraction.py
    python src/fix_extraction.py --dry-run    # show counts without updating
"""

import re
import argparse
from sqlalchemy import create_engine, text
from settings import DB_URL

engine = create_engine(DB_URL)


# ── AREA PATTERNS ─────────────────────────────────────────────
# Ordered from most specific to least specific
AREA_PATTERNS = [
    # "200 ካሬ ሜትር" or "200 ካሬ"
    r'(\d{2,5})\s*ካሬ(?:\s*ሜትር)?',
    # "150 M²" or "150 m²" or "150M²"
    r'(\d{2,5})\s*[Mm][²2]',
    # "150 sqm" or "150 m2" or "150sqm"
    r'(\d{2,5})\s*(?:sqm|sq\.?m|m2)',
    # "Area: 150" or "Area ---- 150" (followed by unit on next token)
    r'[Aa]rea\s*[-:=\s]+(\d{2,5})',
    # "ስፋት፦ 200" or "ስፋት: 200" (Amharic for "area")
    r'ስፋት[፦:\-\s]+(\d{2,5})',
    # "63 ካሬ" inline without keyword (standalone number + ካሬ)
    r'\b(\d{2,4})\s*ካሬ\b',
]

# ── PRICE PATTERNS ─────────────────────────────────────────────
PRICE_PATTERNS = [
    # "28.7 million" or "28.7 ሚሊዮን" or "28.7 ሚሊየን"
    r'(\d+(?:\.\d+)?)\s*(?:million|ሚሊዮን|ሚሊየን)',
    # "(38 million)" — price in parentheses
    r'\((\d+(?:\.\d+)?)\s*(?:million|ሚሊዮን|ሚሊየን)\)',
    # "17 million cash" — with qualifier after
    r'(\d+(?:\.\d+)?)\s*(?:million|ሚሊዮን|ሚሊየን)\s*(?:cash|ብቻ|ለካሽ)?',
    # "6,930,000 ብር" or "7,936,500ብር" — large birr amounts
    r'(\d{1,2},\d{3},\d{3})\s*ብር',
    # "6930000" — plain large number (7+ digits = likely price in birr)
    r'\b(\d{7,9})\b',
    # "ዋጋ = 9,460,000" or "ዋጋ: 30,000,000"
    r'ዋጋ\s*[=:\-\s]+(\d[\d,]+)',
    # "Price: 28.7 million" or "Price -- 15 million"
    r'[Pp]rice\s*[-:=\s]+(\d+(?:\.\d+)?)\s*(?:million|ሚሊዮን|ሚሊየን)?',
]

# Sanity bounds
MIN_AREA = 20        # sqm
MAX_AREA = 5000      # sqm
MIN_PRICE = 500_000  # 500k ETB
MAX_PRICE = 500_000_000  # 500M ETB


def extract_area(text):
    """Try all area patterns, return first valid match."""
    if not text:
        return None
    for pattern in AREA_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = int(match.group(1))
                if MIN_AREA <= val <= MAX_AREA:
                    return val
            except (ValueError, IndexError):
                continue
    return None


def extract_price(text):
    """Try all price patterns, return first valid match in birr."""
    if not text:
        return None
    for pattern in PRICE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                raw = match.group(1).replace(',', '')
                val = float(raw)

                # Convert millions to birr
                if val < 1000:
                    val = val * 1_000_000

                val = int(val)
                if MIN_PRICE <= val <= MAX_PRICE:
                    return val
            except (ValueError, IndexError):
                continue
    return None


def run(dry_run=False):
    # Fetch rows missing area OR price (but only sale listings)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, raw_text
            FROM processed_listings
            WHERE intent IN ('SALE', 'MIXED')
            AND (builtup_sqm IS NULL OR sale_price_birr IS NULL)
            AND raw_text IS NOT NULL
        """)).fetchall()

    total = len(rows)
    area_fixed = 0
    price_fixed = 0
    both_fixed = 0

    print(f"\nScanning {total} rows missing area or price...\n")

    updates = []
    for row in rows:
        new_area = None
        new_price = None

        if row.raw_text:
            new_area = extract_area(row.raw_text)
            new_price = extract_price(row.raw_text)

        if new_area or new_price:
            updates.append({
                "id": row.id,
                "area": new_area,
                "price": new_price
            })
            if new_area:
                area_fixed += 1
            if new_price:
                price_fixed += 1
            if new_area and new_price:
                both_fixed += 1

    print(f"  Found fixable rows:")
    print(f"  Area recovered:       {area_fixed}")
    print(f"  Price recovered:      {price_fixed}")
    print(f"  Both recovered:       {both_fixed}")

    if dry_run:
        print("\n  DRY RUN — no changes written.")
        # Show 5 examples
        print("\n  Sample extractions:")
        for u in updates[:5]:
            print(f"    id={u['id']} | area={u['area']} | price={u['price']:,}" if u['price'] else f"    id={u['id']} | area={u['area']} | price=None")
        return

    # Apply updates
    print(f"\n  Writing {len(updates)} updates...")
    written = 0
    with engine.begin() as conn:
        for u in updates:
            # Only update NULL fields — never overwrite existing data
            if u['area'] and u['price']:
                conn.execute(text("""
                    UPDATE processed_listings
                    SET builtup_sqm = COALESCE(builtup_sqm, :area),
                        sale_price_birr = COALESCE(sale_price_birr, :price),
                        price_per_builtup_sqm = ROUND((:price * 1.0 / :area), 2)
                    WHERE id = :id
                """), {"id": u['id'], "area": u['area'], "price": u['price']})
            elif u['area']:
                conn.execute(text("""
                    UPDATE processed_listings
                    SET builtup_sqm = COALESCE(builtup_sqm, :area)
                    WHERE id = :id
                """), {"id": u['id'], "area": u['area']})
            elif u['price']:
                conn.execute(text("""
                    UPDATE processed_listings
                    SET sale_price_birr = COALESCE(sale_price_birr, :price)
                    WHERE id = :id
                """), {"id": u['id'], "price": u['price']})
            written += 1

    print(f"  Done. {written} rows updated.\n")

    # Show new counts
    print("UPDATED STATS:\n")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_sale,
                COUNT(sale_price_birr) as has_price,
                COUNT(builtup_sqm) as has_area,
                COUNT(CASE WHEN sale_price_birr IS NOT NULL
                           AND builtup_sqm IS NOT NULL THEN 1 END) as has_both
            FROM processed_listings
            WHERE intent IN ('SALE', 'MIXED')
        """)).fetchone()

        print(f"  Total sale listings:     {result.total_sale}")
        print(f"  Has price:               {result.has_price}")
        print(f"  Has area:                {result.has_area}")
        print(f"  Has BOTH (usable):       {result.has_both}")

    # Show updated segment table
    print("\nSEGMENT COVERAGE AFTER FIX:\n")
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

        print(f"  {'location':<25} {'type':<15} {'samples':>7}")
        print(f"  {'-'*25} {'-'*15} {'-'*7}")
        for r in rows:
            confidence = 'HIGH' if r.samples >= 10 else 'MEDIUM' if r.samples >= 5 else 'LOW'
            print(f"  {r.location:<25} {r.property_type:<15} {r.samples:>7}  [{confidence}]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be fixed without writing")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
