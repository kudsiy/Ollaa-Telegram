"""
advert_classifier.py
--------------------
Classifies listing_class for rows that are NULL or 'MEDIA_PENDING'.
NEVER overwrites existing Gemini classifications.

Gemini's existing taxonomy (preserved as-is):
  PURE_SALE       — confirmed sale listing
  PURE_RENT       — confirmed rental listing
  DEVELOPER       — developer project content
  ADVERTISEMENT   — adverts (Gemini already caught 100)
  PROMOTIONAL     — promotional content (13 rows)
  DIRECT_LISTING  — direct property listings
  INQUIRY         — buyer/renter inquiries
  MIXED           — mixed intent
  MEDIA_PENDING   — media-only, no text (2,209 rows — we classify these)
  INVALID         — junk/irrelevant

New classes this script adds:
  ADVERT          — channel promo, recruitment, congratulations (no property)
  PROJECT_LAUNCH  — developer announcing a new project with intel value
  DEVELOPER_PROMO — developer brand/award/news posts

RULE: Only touches rows where listing_class IS NULL or = 'MEDIA_PENDING'
      (unless --reclassify flag is passed)

Usage:
  python src/advert_classifier.py            # dry run
  python src/advert_classifier.py --apply    # write to database
  python src/advert_classifier.py --stats    # stats only
  python src/advert_classifier.py --reclassify  # also reclassify existing (careful)

Import:
  from advert_classifier import classify_listing
"""

from __future__ import annotations

import re
import sys
import psycopg2
from typing import Optional

DB_CONFIG = {
    "dbname": "ollaa",
    "user": "postgres",
    "password": "REMOVED_OLD_PASSWORD",
    "host": "localhost",
    "port": 5432,
}

# ── Property content guard ────────────────────────────────────────────────────
PROPERTY_SIGNALS = [re.compile(p, re.IGNORECASE) for p in [
    r"\b(?:villa|apartment|condominium|office|warehouse|land|studio|townhouse)\b",
    r"\b(?:ቪላ|አፓርትማ|ኮንዶ|ቢሮ|መጋዘን|ሱቅ|መሬት|ስቱዲዮ)\b",
    r"\b\d+\s*(?:sqm|m2|ካሬ|ካሬ\s*ሜትር|m²)\b",
    r"\b\d+\s*(?:bed|br|bedroom|ክፍል|ኪፍሎ)\b",
    r"\b(?:birr|etb|ብር)\b",
    r"\b(?:for\s+sale|ለሽያጭ|ይሸጣል|ይሸጠናል)\b",
    r"\b(?:for\s+rent|ለኪራይ|ይከራያል|ለሚከራዩ)\b",
    r"\b(?:title\s*deed|carta|ካርታ|ሊዝ|lease\s*hold)\b",
    r"\b(?:g\+\d|ground\s*\+)\b",
    r"\b(?:plot|compound|ቦታ)\b",
]]


def _has_property_content(text: str) -> bool:
    return sum(1 for p in PROPERTY_SIGNALS if p.search(text)) >= 2


# ── ADVERT signals ────────────────────────────────────────────────────────────
ADVERT_UNAMBIGUOUS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in [
    r"ቻናላችንን\s*ይቀላቀሉ",
    r"ቻናሉን\s*ይቀላቀሉ",
    r"ሻናሉን\s*ይቀላቀሉ",
    r"join\s+(?:our|the)\s+channel",
    r"subscribe\s+to\s+our\s+channel",
    r"forward\s+this\s+(?:message|post|channel)",
    r"ቻናሉን\s*share\s*አድርጉ",
    r"የሽያጭ\s*ወኪል\s*እንፈልጋለን",
    r"sales\s*agent\s*(?:needed|wanted|hiring|vacancy)",
    r"broker\s*(?:needed|wanted|hiring)",
    r"we\s*(?:are\s*)?hiring\b",
    r"ስራ\s*ፈላጊ",
    r"እንኳን\s*ደህና\s*መጡ\b",
    r"congratulations?\s+to\s+(?:our|the)\s+(?:team|staff|top\s+performer)",
    r"top\s+performer",
    r"hard\s+work\s+recognized",
    r"ሽልማት\s*(?:ተቀበለ|አሸነፈ|ተሸለመ)",
]]

ADVERT_CONDITIONAL = [re.compile(p, re.IGNORECASE) for p in [
    r"don['\u2019t]+\s*miss\s+(?:out|this)",
    r"limited[\s\-]time\s+(?:offer|deal|opportunity|discount)",
    r"exclusive\s+discount",
    r"expo\s+(?:event|date|location)",
    r"(?:christmas|new\s*year|holiday)\s+(?:sale|offer|gift|event)",
    r"invite\s+(?:your\s+)?friends",
    r"like\s+and\s+share",
    r"ያስተዋውቁ",
    r"advertisement",
    r"sponsored\s+post",
]]

PROJECT_LAUNCH_STRONG = [re.compile(p, re.IGNORECASE) for p in [
    r"\blaunch(?:ing)?\s+soon\b",
    r"\bpre[\-\s]?(?:launch|sale)\b",
    r"\boff[\-\s]?plan\b",
    r"\bgrand\s+(?:launch|opening)\b",
    r"\bproject\s+launch\b",
    r"\bnew\s+project\s+(?:launch|announcement|reveal|by|from)\b",
    r"\bcoming\s+soon\b",
    r"ቅድሚያ\s*ሽያጭ",
    r"ምዝገባ\s*ተጀምሯል",
    r"ምዝገባ\s*ይጀምሩ",
    r"አዲስ\s*ፕሮጀክት\s*(?:ጀምሯል|ተጀምሯል|ይፋ)",
    r"show\s*(?:room|flat|unit)\s*(?:open|ready|available|now)",
    r"site\s*visit\s*(?:welcome|free|available|open)",
    r"ጣቢያ\s*ጉብኝት",
]]

PROJECT_LAUNCH_SUPPORTING = [re.compile(p, re.IGNORECASE) for p in [
    r"\bfloor\s*plan\b",
    r"\bpayment\s*plan\b",
    r"ክፍያ\s*ሰሌዳ",
    r"\bcompletion\s*(?:date|q[1-4]|\d{4})\b",
    r"\bbank\s+(?:loan|financing)\s+(?:available|up\s+to)\b",
    r"ባንክ\s*ብድር\s*(?:ይቻላል|ይገኛል)",
    r"\bunit\s*(?:type|mix|available)\b",
    r"starting\s+(?:from|at|price)",
]]

DEVELOPER_PROMO_SIGNALS = [re.compile(p, re.IGNORECASE) for p in [
    r"years?\s+of\s+(?:experience|excellence)\s+in\s+real\s+estate",
    r"trusted\s+(?:developer|builder|real\s+estate\s+firm)",
    r"award[\-\s]winning\s+(?:developer|project|firm)",
    r"ኩባንያችን\b",
    r"ድርጅታችን\b",
    r"(?:about|ስለ)\s+(?:us|jambo|ayat|temer|gift|dmc|jembo|visco)",
    r"media\s+(?:partner|partnership|agreement)",
    r"የሚዲያ\s*አጋርነት",
    r"(?:signed|entered)\s+(?:a\s+)?(?:partnership|agreement|mou)\b",
    r"ስምምነት\s*(?:ፈፀመ|ተፈረመ)",
    r"(?:won|received|awarded)\s+(?:the\s+)?(?:diamond|gold|silver|best)",
    r"ሽልማት\s*(?:ተሸለምን|ተሸለሙ|ወሰዱ)",
]]


def classify_listing(text: str, topic_title: Optional[str] = None) -> str:
    """
    Classify listing text. Returns: LISTING, ADVERT, PROJECT_LAUNCH, DEVELOPER_PROMO
    Safe to import in listener.py and etl_runner.py.
    """
    if not text or text.strip() in ("[MEDIA ONLY]", ""):
        return "LISTING"

    combined = f"{topic_title}\n{text}" if topic_title else text
    has_property = _has_property_content(combined)

    # 1. Unambiguous ADVERT — overrides everything
    for p in ADVERT_UNAMBIGUOUS:
        if p.search(combined):
            return "ADVERT"

    # 2. PROJECT LAUNCH
    strong_launch = sum(1 for p in PROJECT_LAUNCH_STRONG if p.search(combined))
    supporting = sum(1 for p in PROJECT_LAUNCH_SUPPORTING if p.search(combined))
    if strong_launch >= 1 and supporting >= 1:
        return "PROJECT_LAUNCH"
    if strong_launch >= 2:
        return "PROJECT_LAUNCH"

    # 3. Conditional ADVERT — only if no property content
    if not has_property:
        if sum(1 for p in ADVERT_CONDITIONAL if p.search(combined)) >= 2:
            return "ADVERT"

    # 4. Developer promo — only if no property content
    if not has_property:
        if sum(1 for p in DEVELOPER_PROMO_SIGNALS if p.search(combined)) >= 1:
            return "DEVELOPER_PROMO"

    return "LISTING"


# ── Database runner ───────────────────────────────────────────────────────────

PROTECTED_CLASSES = {
    "PURE_SALE", "PURE_RENT", "DEVELOPER", "ADVERTISEMENT",
    "PROMOTIONAL", "DIRECT_LISTING", "INQUIRY", "MIXED", "INVALID",
}


def print_stats(conn, label="CURRENT STATE"):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(listing_class, 'NULL') as cls, COUNT(*) as cnt
            FROM processed_listings
            GROUP BY listing_class ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
    total = sum(r[1] for r in rows)
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    for cls, cnt in rows:
        pct = cnt / total * 100 if total else 0
        mark = " [protected]" if cls in PROTECTED_CLASSES else ""
        print(f"  {cls:<25} {cnt:>7,}  {pct:>5.1f}%{mark}")
    print(f"  {'TOTAL':<25} {total:>7,}")
    print(f"{'='*55}")


def main():
    dry_run = "--apply" not in sys.argv
    stats_only = "--stats" in sys.argv
    reclassify = "--reclassify" in sys.argv

    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected.")

    if stats_only:
        print_stats(conn)
        conn.close()
        return

    print_stats(conn, "BEFORE")

    with conn.cursor() as cur:
        if reclassify:
            cur.execute("""
                SELECT id, raw_text, listing_class FROM processed_listings
                WHERE listing_class NOT IN %s OR listing_class IS NULL
            """, (tuple(PROTECTED_CLASSES),))
        else:
            cur.execute("""
                SELECT id, raw_text, listing_class FROM processed_listings
                WHERE listing_class IS NULL OR listing_class = 'MEDIA_PENDING'
            """)
        rows = cur.fetchall()

    candidates = [{"id": r[0], "raw_text": r[1], "cls": r[2]} for r in rows]
    print(f"\nCandidates to classify: {len(candidates):,}")

    counts = {}
    changes = []
    for row in candidates:
        new = classify_listing(row["raw_text"] or "")
        counts[new] = counts.get(new, 0) + 1
        if new != "LISTING":
            changes.append({"id": row["id"], "raw_text": row["raw_text"], "new": new})

    print("\nResults:")
    for cls, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        pct = cnt / len(candidates) * 100 if candidates else 0
        print(f"  {cls:<25} {cnt:>6,}  ({pct:.1f}%)")
    print(f"\n  Non-LISTING rows to write: {len(changes):,}")

    # Show samples of what will be written
    from collections import defaultdict
    by_class = defaultdict(list)
    for r in changes:
        by_class[r["new"]].append(r)

    for cls in ["ADVERT", "PROJECT_LAUNCH", "DEVELOPER_PROMO"]:
        samples = by_class.get(cls, [])
        if not samples:
            continue
        print(f"\n--- {cls} ({len(samples)} rows, showing 5) ---")
        for r in samples[:5]:
            print(f"  id={r['id']}: {(r['raw_text'] or '')[:160].replace(chr(10), ' ')}")

    if dry_run:
        print(f"\n{'='*55}")
        print("  DRY RUN — nothing written.")
        print("  Run with --apply to write.")
        print(f"{'='*55}")
    else:
        print(f"\nWriting {len(changes):,} classifications...")
        with conn.cursor() as cur:
            for r in changes:
                cur.execute(
                    "UPDATE processed_listings SET listing_class = %s WHERE id = %s",
                    (r["new"], r["id"])
                )
        conn.commit()
        print("Done.")
        print_stats(conn, "AFTER")

    conn.close()


if __name__ == "__main__":
    main()
