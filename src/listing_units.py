r"""
listing_units.py
----------------
One row per unit of a multi-unit advert (task S38). A developer advert usually lists several flats
("ባለ 2 መኝታ 90ካሬ … 10.8 ሚልዮን / ባለ 3 መኝታ 121ካሬ … 14.5 ሚልዮን"); processed_listings keeps only the
first, so the others are lost to the hedonic and discount-rate samples. listing_units holds them all,
one row per unit and payment option, beside the listing (which is left as it is):

  listing_id, unit_no     the listing, and the unit's number in the advert (1, 2, …, by size order of first mention)
  size_sqm, bedrooms      the unit's size, and the bedrooms written on its line or the line before
  payment_option          "100" (paid at once), a share paid at once ("65"), "slow" (paid over time) or "list"
  finish                  "semi-finished", "fully finished" or empty
  price_birr              the total price of the unit under that option
  price_per_sqm           price_birr / size_sqm

Only totals the advert states, of adverts with 2 or more priced units, for sale, whose text was read. The table is rebuilt from the
stored listings each time (it is derived data: change the rules here, not the rows), and a deleted listing
takes its units with it. tests/test_units.py checks the rules.

Usage:
    venv\Scripts\python.exe src\listing_units.py            (report only)
    venv\Scripts\python.exe src\listing_units.py --apply    (rebuild the table)
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import Counter

from sqlalchemy import create_engine, text

from payment_terms import price_entries
from processor import (BEDROOM_RE, PRICE_PER_SQM_RE, _NOT_A_UNIT_AFTER_RE, _NOT_A_UNIT_BEFORE_RE, _clean_area_value,
                       extract_bedrooms, normalize_numbers)
from settings import DB_URL

PER_SQM_MIN, PER_SQM_MAX = 10_000, 1_000_000     # a total that makes another price per m² is not this unit's
_SIZE_LIST_RE = re.compile(r"(?<![\d.,])(\d{2,4})(?:\.\d+)?\s*(?:\(\d+(?:\.\d+)?\)\s*)?(?:ካሬ|kare|sqm|sq\.?\s*m\b|m2|m²)", re.I)

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS public.listing_units (
    listing_id         text    NOT NULL REFERENCES public.processed_listings(id) ON DELETE CASCADE,
    unit_no            integer NOT NULL,
    size_sqm           numeric NOT NULL,
    bedrooms           integer,
    payment_option     text    NOT NULL,
    finish             text    NOT NULL DEFAULT '',
    price_birr         numeric NOT NULL,
    price_per_sqm      numeric NOT NULL,
    PRIMARY KEY (listing_id, unit_no, payment_option, finish)
)"""


def _prepare(raw: str) -> str:
    t = normalize_numbers(unicodedata.normalize("NFKC", raw or ""))
    return re.sub(r"(?<=\d)ዐ|ዐ(?=\d)", "0", t)


def unit_sizes(raw: str) -> list[int]:
    """The unit sizes an advert lists, in order, without the land or the building's footprint."""
    t = PRICE_PER_SQM_RE.sub(lambda m: " " * len(m.group(0)), _prepare(raw))
    sizes = []
    for m in _SIZE_LIST_RE.finditer(t):
        value = _clean_area_value(m.group(1))
        if value is None or _NOT_A_UNIT_AFTER_RE.match(t, m.end()):
            continue
        if _NOT_A_UNIT_BEFORE_RE.search(t[max(0, m.start() - 30):m.start()]):
            continue
        if value not in sizes:
            sizes.append(value)
    return sizes


_BEDS_RE = re.compile(BEDROOM_RE.pattern + r"|(\d{1,2})\s*(?:bed(?:room)?s?|br)\b", re.I)


def bedrooms_before(t: str, size) -> int | None:
    """The bedrooms written last before this size: on its line ("👉2መኝታ 106ካሬ … 👉3መኝታ 139ካሬ": 3 for 139), else on
    one of the 4 lines above it, under a heading such as "📍2bed" or "ባለ ሁለት መኝታ"."""
    wanted = re.compile(rf"(?<![\d.,]){int(size)}(?:\.\d+)?\s*(?:\(\d+(?:\.\d+)?\)\s*)?(?:ካሬ|kare|sqm|sq\.?m|m2|m²)", re.I)
    lines = t.split("\n")
    for i, line in enumerate(lines):
        m = wanted.search(line)
        if not m:
            continue
        for segment in [line[:m.start()]] + lines[max(0, i - 4):i][::-1]:
            found = [int(b.group(1) or b.group(2)) for b in _BEDS_RE.finditer(segment)]
            found = [b for b in found if 0 < b <= 10]
            if found:
                return found[-1]
            words = extract_bedrooms(segment)            # "ባለ ሁለት መኝታ", "Bedroom: 3"
            if words:
                return words
        return None
    return None


def extract_units(raw: str) -> list[dict]:
    """One dict per unit and payment option; empty unless the advert prices 2 or more units."""
    entries = price_entries(raw)
    units = set(unit_sizes(raw))          # not the land or the building's footprint ("353 ካሬ ላይ ያረፈ ህንፃ")
    rows, seen = [], set()
    for option, finish, value, per_sqm, size in entries:
        if per_sqm or size not in units or not PER_SQM_MIN <= value / size <= PER_SQM_MAX:
            continue
        key = (size, option, finish or "")
        if key not in seen:
            seen.add(key)
            rows.append({"size_sqm": size, "payment_option": option, "finish": finish or "", "price_birr": value})
    # Only totals the advert states. A size times the advert's price per m² is not used: in an advert for several
    # sites the sizes of one site meet the price per m² of another, and a resale's gross and net sizes are one flat.
    sizes = sorted({r["size_sqm"] for r in rows}, key=lambda s: next(i for i, r in enumerate(rows) if r["size_sqm"] == s))
    if len(sizes) < 2:
        return []
    text_for_beds = _prepare(raw)
    for r in rows:
        r["unit_no"] = sizes.index(r["size_sqm"]) + 1
        r["bedrooms"] = bedrooms_before(text_for_beds, r["size_sqm"])
        r["price_per_sqm"] = round(r["price_birr"] / r["size_sqm"])
    return sorted(rows, key=lambda r: (r["unit_no"], r["payment_option"], r["finish"]))


def build(conn):
    """{listing id: units} for every sale listing whose text was read."""
    rows = conn.execute(text("""
        SELECT p.id, t.text FROM processed_listings p JOIN telegram_listings t ON p.id = t.id::text
        WHERE p.listing_class <> 'MEDIA_PENDING' AND p.intent IN ('SALE', 'MIXED', 'UNKNOWN')""")).fetchall()
    return {r.id: units for r in rows if (units := extract_units(r.text))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="rebuild listing_units (default: report only)")
    args = parser.parse_args()
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        units = build(conn)
        exists = conn.execute(text("SELECT to_regclass('public.listing_units')")).scalar() is not None
        before = conn.execute(text("SELECT count(*) FROM listing_units")).scalar() if exists else 0
    rows = [dict(u, listing_id=i) for i, us in units.items() for u in us]
    print(f"Listings with 2 or more priced units: {len(units):,}")
    print(f"Unit rows: {len(rows):,} (now {before:,}); units: {len({(r['listing_id'], r['unit_no']) for r in rows}):,}")
    print(f"  by payment option: {dict(Counter(r['payment_option'] for r in rows).most_common())}")
    if not args.apply:
        print("REPORT ONLY: nothing was changed (use --apply).")
        return
    with engine.begin() as conn:
        conn.execute(text(CREATE_SQL))
        conn.execute(text("DELETE FROM listing_units"))
        if rows:
            conn.execute(text("""
                INSERT INTO listing_units (listing_id, unit_no, size_sqm, bedrooms, payment_option, finish, price_birr,
                                           price_per_sqm)
                VALUES (:listing_id, :unit_no, :size_sqm, :bedrooms, :payment_option, :finish, :price_birr,
                        :price_per_sqm)"""), rows)
    print(f"APPLIED: listing_units rebuilt with {len(rows):,} rows.")


if __name__ == "__main__":
    sys.exit(main())
