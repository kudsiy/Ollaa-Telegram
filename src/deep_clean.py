"""
deep_clean.py
-------------
Temporary cleanup script to reduce unresolved records by using simple
developer-name heuristics on raw_text + forum topic_title.

Targets only:
  - processed_listings.property_type in ('UNKNOWN', NULL)
    OR processed_listings.location = 'other_addis'

Rules:
  - Topic commercial override: if topic_title mentions Suq/Shop/Mall -> COMMERCIAL
  - Apartment specialists: Metropolitan/Ovid/Noah -> APARTMENT
  - Villa specialists: Eniy/Enyi -> VILLA
  - Gift: if 'Gift' and 'CMC' -> VILLA
  - Flintstone: Village -> VILLA, Classic/Tower -> APARTMENT, else -> APARTMENT

Run:
  python src/deep_clean.py          # dry run (no DB writes)
  python src/deep_clean.py --apply  # apply updates

Env:
  DB_PASSWORD and the other DB_* settings come from .env (see settings.py)
"""

from __future__ import annotations

import re
import sys
from sqlalchemy import create_engine, text
from settings import DB_URL


engine = create_engine(DB_URL)


APARTMENT_KEYWORDS = [
    # Developers / brands
    "noah",
    "metropolitan",
    "ovid",
    "bora",
    "yotek",
    "zemen",
    "eagle hills",
    "la gare",
    "tsehay",
    "real-estate",
    "realestate",
    "real estate",
    # Amharic + transliteration listing signals
    "አፓርታማ",
    "ፎቅ",
    "ባለ 1",
    "ባለ 2",
    "ባለ 3",
    "ባለ1",
    "ባለ2",
    "ባለ3",
    "floor",
    "sqm",
    "m2",
    "studio",
]

VILLA_KEYWORDS = [
    # Developers / brands
    "gift",
    "flintstone",
    "eniy",
    "enyi",
    "sunshine",
    "country club",
    "awas",
    "omo",
    "abay",
    "jambo",
    # Amharic + typical villa signals
    "ቪላ",
    "ጂ+1",
    "ጂ +1",
    "ጂ + 1",
    "g+0",
    "g+1",
    "g+2",
    "ካርታ",
    "compound",
]

COMMERCIAL_KEYWORDS = [
    "ሱቅ",
    "መጋዘን",
    "መሸጫ",
    "shop",
    "mall",
    "store",
    "warehouse",
    "office",
    "ቢሮ",
]

# For summary only: "did we detect any of our expanded vocab?"
DETECT_KEYWORDS = sorted(set(
    APARTMENT_KEYWORDS
    + VILLA_KEYWORDS
    + COMMERCIAL_KEYWORDS
    + ["bank", "50%"]
))


def contains_any(blob: str, keywords: list[str]) -> bool:
    return any(k in blob for k in keywords)


PRICE_TAG_RE = re.compile(r"(?:ዋጋ)\s*[:፦]?\s*([\d,]{7,})", re.UNICODE)


def main() -> None:
    apply = "--apply" in sys.argv

    with engine.begin() as conn:
        # Build a de-duplicated view of (processed_listings ↔ telegram_listings)
        # using the same join strategy as topic_resolver.
        joined = text("""
            WITH joined AS (
                SELECT DISTINCT ON (pl.id)
                    pl.id AS processed_id,
                    pl.property_type,
                    pl.location,
                    pl.source_channel,
                    pl.raw_text,
                    tl.topic_title
                FROM processed_listings pl
                LEFT JOIN telegram_listings tl
                  ON pl.raw_text = tl.text
                 AND pl.source_channel = tl.channel
                WHERE
                    pl.property_type IS NULL
                 OR pl.property_type = 'UNKNOWN'
                 OR pl.location = 'other_addis'
                ORDER BY pl.id, tl.id DESC
            )
            SELECT
                processed_id,
                property_type,
                location,
                source_channel,
                raw_text,
                COALESCE(topic_title, '') AS topic_title,
                (LOWER(COALESCE(raw_text, '') || ' ' || COALESCE(topic_title, ''))) AS blob
            FROM joined
        """)

        rows = conn.execute(joined).mappings().all()

    # Decide updates in Python (keeps logic explicit/easy to adjust).
    to_apartment: list[str] = []
    to_villa: list[str] = []
    to_commercial: list[str] = []
    to_valuation_eligible: list[str] = []
    detected_any: int = 0
    bank_guess: int = 0

    for r in rows:
        blob = (r.get("blob") or "").lower()
        topic_title = (r.get("topic_title") or "").strip()
        topic_lower = topic_title.lower()
        if contains_any(blob, DETECT_KEYWORDS):
            detected_any += 1

        # Only set type when it's unknown/null (don't override known types)
        current = r.get("property_type")
        if current not in (None, "UNKNOWN"):
            continue

        pid = str(r["processed_id"])

        # Cleanup override: topic-title commercial keywords win regardless of developer naming.
        if any(k in topic_lower for k in ("suq", "shop", "mall")):
            to_commercial.append(pid)
            continue

        # COMMERCIAL: body/topic vocabulary
        if contains_any(blob, COMMERCIAL_KEYWORDS):
            to_commercial.append(pid)
            continue

        # Flintstone mixed-use catch (explicit precedence within Flintstone)
        if "flintstone" in blob:
            if "village" in blob:
                to_villa.append(pid)
            elif ("classic" in blob) or ("tower" in blob):
                to_apartment.append(pid)
            else:
                to_apartment.append(pid)
            continue

        # Gift CMC -> VILLA (explicit pattern)
        if ("gift" in blob) and ("cmc" in blob):
            to_villa.append(pid)
            continue

        # Direct keyword-based heuristics
        if contains_any(blob, VILLA_KEYWORDS):
            to_villa.append(pid)
            continue

        if contains_any(blob, APARTMENT_KEYWORDS):
            to_apartment.append(pid)
            continue

        # Smart bank-presale guess
        if ("bank" in blob) or ("50%" in blob):
            to_apartment.append(pid)
            bank_guess += 1
            continue

        # Price-preserving tag: if Amharic "ዋጋ" is followed by a 7+ digit amount,
        # keep it in a dedicated bucket so it can be reviewed without losing price signals.
        m = PRICE_TAG_RE.search(blob)
        if m:
            digits = re.sub(r"[^\d]", "", m.group(1))
            if len(digits) > 6:
                to_valuation_eligible.append(pid)
                continue

    would_update = len(set(to_apartment + to_villa + to_commercial + to_valuation_eligible))

    print("\n" + "=" * 60)
    print("DEEP CLEAN SUMMARY")
    print("=" * 60)
    print(f"Candidates scanned              : {len(rows):,}")
    print(f"Rows mentioning detect-list     : {detected_any:,}")
    print(f"Would set COMMERCIAL (topic kw) : {len(set(to_commercial)):,}")
    print(f"Would set APARTMENT             : {len(set(to_apartment)):,}")
    print(f"Would set VILLA                 : {len(set(to_villa)):,}")
    print(f"Would tag VALUATION_ELIGIBLE    : {len(set(to_valuation_eligible)):,}")
    print(f"Bank/50% → APARTMENT guesses    : {bank_guess:,}")
    print(f"Total rescued from UNKNOWN      : {would_update:,}")
    print("=" * 60)

    if not apply or would_update == 0:
        if not apply:
            print("\nDry run only. Re-run with --apply to write updates.")
        return

    with engine.begin() as conn:
        updated = 0

        if to_valuation_eligible:
            res = conn.execute(
                text("""
                    UPDATE processed_listings
                    SET property_type = 'VALUATION_ELIGIBLE'
                    WHERE id = ANY(:ids)
                      AND (property_type IS NULL OR property_type = 'UNKNOWN');
                """),
                {"ids": list(sorted(set(to_valuation_eligible)))},
            )
            updated += res.rowcount or 0

        if to_commercial:
            res = conn.execute(
                text("""
                    UPDATE processed_listings
                    SET property_type = 'COMMERCIAL'
                    WHERE id = ANY(:ids)
                      AND (property_type IS NULL OR property_type = 'UNKNOWN');
                """),
                {"ids": list(sorted(set(to_commercial)))},
            )
            updated += res.rowcount or 0

        if to_apartment:
            res = conn.execute(
                text("""
                    UPDATE processed_listings
                    SET property_type = 'APARTMENT'
                    WHERE id = ANY(:ids)
                      AND (property_type IS NULL OR property_type = 'UNKNOWN');
                """),
                {"ids": list(sorted(set(to_apartment)))},
            )
            updated += res.rowcount or 0

        if to_villa:
            res = conn.execute(
                text("""
                    UPDATE processed_listings
                    SET property_type = 'VILLA'
                    WHERE id = ANY(:ids)
                      AND (property_type IS NULL OR property_type = 'UNKNOWN');
                """),
                {"ids": list(sorted(set(to_villa)))},
            )
            updated += res.rowcount or 0

    print(f"\nApplied updates. Rows rescued from UNKNOWN: {updated:,}")


if __name__ == "__main__":
    main()

