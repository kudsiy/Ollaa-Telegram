"""
audit_processor.py
------------------
Verifies the new processor.py extraction logic by sampling listings that
previously had UNKNOWN property_type or missing/zero prices.

It prints a side-by-side comparison:
  - Raw text snippet
  - Old values (from processed_listings)
  - New values (from processor.py + updated listing_class rules)

It also highlights rows where a million string (ሚሊዮን / ሚ) was converted.

Run:
  python src/audit_processor.py

Env:
  DB_PASSWORD and the other DB_* settings come from .env (see settings.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, text

from processor import DOWNPAYMENT_RE, extract_bedrooms, extract_price_birr, parse_million_amount
from run_pipeline import ValuationPipeline
from settings import DB_URL


engine = create_engine(DB_URL)


@dataclass
class OldValues:
    processed_id: str
    listing_class: Optional[str]
    property_type: Optional[str]
    bedrooms: Optional[int]
    sale_price_birr: Optional[int]


def snippet(s: str, n: int = 220) -> str:
    s = (s or "").replace("\r", " ").replace("\n", " ").strip()
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def main() -> None:
    # Ensure the forum topic id column exists for project-based tracking.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS reply_to_top_id BIGINT;"))

    q = text("""
        WITH base AS (
            SELECT
                tl.id            AS telegram_id,
                tl.channel       AS channel,
                tl.message_id    AS message_id,
                tl.reply_to_top_id AS reply_to_top_id,
                tl.text          AS raw_text,
                COALESCE(tl.topic_title, '') AS topic_title,
                CASE
                    WHEN tl.reply_to_top_id IS NOT NULL
                    THEN tl.channel || '::topic::' || tl.reply_to_top_id::text
                    ELSE CAST(tl.id AS TEXT)
                END AS key_id
            FROM telegram_listings tl
        )
        SELECT
            b.*,
            pl.id              AS processed_id,
            pl.listing_class   AS old_listing_class,
            pl.property_type   AS old_property_type,
            pl.bedrooms        AS old_bedrooms,
            pl.sale_price_birr AS old_sale_price_birr,
            CASE WHEN b.reply_to_top_id IS NOT NULL THEN (
                SELECT COUNT(*)
                FROM telegram_listings tl2
                WHERE tl2.channel = b.channel AND tl2.reply_to_top_id = b.reply_to_top_id
            ) ELSE NULL END AS topic_msg_count
        FROM base b
        LEFT JOIN processed_listings pl
          ON pl.id = b.key_id
        WHERE
            pl.id IS NOT NULL
            AND (
                pl.property_type IS NULL
             OR pl.property_type = 'UNKNOWN'
             OR pl.sale_price_birr IS NULL
             OR pl.sale_price_birr = 0
            )
        ORDER BY RANDOM()
        LIMIT 50;
    """)

    with engine.begin() as conn:
        rows = conn.execute(q).mappings().all()

    pipeline = ValuationPipeline()

    million_converted = 0
    any_rows = 0

    print("\n" + "=" * 100)
    print("PROCESSOR AUDIT (sample of 50)")
    print("=" * 100)

    for i, r in enumerate(rows, 1):
        any_rows += 1
        raw_text = (r.get("raw_text") or "").strip()
        topic_title = (r.get("topic_title") or "").strip()
        blob = f"{topic_title}\n{raw_text}".strip()

        old = OldValues(
            processed_id=str(r.get("processed_id")),
            listing_class=r.get("old_listing_class"),
            property_type=r.get("old_property_type"),
            bedrooms=r.get("old_bedrooms"),
            sale_price_birr=r.get("old_sale_price_birr"),
        )

        new_price = extract_price_birr(blob)
        new_bedrooms = extract_bedrooms(blob)
        # listing_class logic lives in ValuationPipeline.classify_listing_class
        new_listing_class = pipeline.classify_listing_class(blob, intent=None)

        million_raw = parse_million_amount(blob)
        converted_flag = bool(million_raw and new_price and new_price == million_raw)
        if converted_flag:
            million_converted += 1

        # Down-payment math highlight: "25% = 2.8m" => 11.2M
        dp_flag = False
        expected_total = None
        m_dp = DOWNPAYMENT_RE.search(blob)
        if m_dp:
            try:
                pct = float(m_dp.group(1))
                amt_m = float(m_dp.group(2))
                if 1 <= pct <= 99 and amt_m > 0:
                    expected_total = int((amt_m * 1_000_000) / (pct / 100.0))
                    dp_flag = bool(new_price and expected_total and new_price == expected_total)
            except Exception:
                dp_flag = False

        print("\n" + "-" * 100)
        is_forum = r.get("reply_to_top_id") is not None
        project_key = r.get("key_id")
        msg_count = r.get("topic_msg_count")

        print(
            f"[{i:02d}] processed_id={old.processed_id} "
            f"forum={is_forum} key={project_key} "
            f"channel={r.get('channel')} msg={r.get('message_id')}"
        )
        if is_forum and msg_count is not None:
            print(f"  forum_topic_id={r.get('reply_to_top_id')} topic_messages={msg_count} (UPSERT target)")
        if converted_flag:
            print("** MILLION CONVERTED **")
        if dp_flag:
            print("** TOTAL VALUE MATH APPLIED (pct=downpayment) **")

        print("\nRaw Text Snippet:")
        print(f"  {snippet(blob)}")

        print("\nOld Value (processed_listings):")
        print(f"  listing_class : {old.listing_class}")
        print(f"  property_type : {old.property_type}")
        print(f"  bedrooms      : {old.bedrooms}")
        print(f"  sale_price    : {old.sale_price_birr}")

        print("\nNew Value (processor/run_pipeline):")
        print(f"  listing_class : {new_listing_class}")
        print(f"  bedrooms      : {new_bedrooms}")
        print(f"  sale_price    : {new_price}")

        if million_raw:
            print(f"  million_parse : {million_raw}")
        if expected_total is not None:
            print(f"  dp_total_calc : {expected_total}")

    print("\n" + "=" * 100)
    print(f"Rows audited             : {any_rows}")
    print(f"Million strings converted: {million_converted}")
    print("=" * 100 + "\n")


if __name__ == "__main__":
    main()

