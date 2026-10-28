"""
etl_runner.py
-------------
Reads all rows from telegram_listings, runs ValuationPipeline on each,
and inserts structured results into:
  - processed_listings  (all intents: for valuation engine)
  - rental_listings     (RENT intent: for yield calculation)

Safe to re-run: uses ON CONFLICT DO NOTHING, so it only adds new messages.
Messages listed in processing_exclusions (deleted duplicates) are skipped.
To bring parser fixes to listings that already exist, use reprocess.py.

Usage:
    python src/etl_runner.py
    python src/etl_runner.py --limit 100
"""

import argparse
import json
import re
import sys
from sqlalchemy import create_engine, text
from protection import PARSER_WRITE_SQL
from settings import DB_URL

try:
    from run_pipeline import ValuationPipeline
except ImportError:
    print("ERROR: run_pipeline.py not found.")
    sys.exit(1)

engine = create_engine(DB_URL)

# ── processed_listings insert ─────────────────────────────────
INSERT_PROCESSED = """
INSERT INTO processed_listings (
    id, listing_status, intent, listing_class,
    valuation_eligible, sale_analytics_eligible, developer_analytics_eligible,
    property_type, property_subtype, location, city,
    plot_sqm, builtup_sqm,
    bedrooms, bathrooms,
    sale_price_birr, rent_price_birr, rent_advance_birr,
    payment_type, bank_loan_pct, down_payment_pct,
    finish_state, developer,
    price_currency, price_usd, floor_level,
    contact_phone, contact_username,
    price_per_builtup_sqm, price_per_plot_sqm,
    confidence_json, source_channel, raw_text, posted_at
)
VALUES (
    :id, :listing_status, :intent, :listing_class,
    :valuation_eligible, :sale_analytics_eligible, :developer_analytics_eligible,
    :property_type, :property_subtype, :location, :city,
    :plot_sqm, :builtup_sqm,
    :bedrooms, :bathrooms,
    :sale_price_birr, :rent_price_birr, :rent_advance_birr,
    :payment_type, :bank_loan_pct, :down_payment_pct,
    :finish_state, :developer,
    :price_currency, :price_usd, :floor_level,
    :contact_phone, :contact_username,
    :price_per_builtup_sqm, :price_per_plot_sqm,
    :confidence_json, :source_channel, :raw_text, :posted_at
)
ON CONFLICT (id) DO NOTHING;
"""

# Forum topic project UPSERT (id is the project key)
UPSERT_FORUM_PROJECT = """
INSERT INTO processed_listings (
    id, listing_status, intent, listing_class,
    valuation_eligible, sale_analytics_eligible, developer_analytics_eligible,
    property_type, property_subtype, location, city,
    plot_sqm, builtup_sqm,
    bedrooms, bathrooms,
    sale_price_birr, rent_price_birr, rent_advance_birr,
    payment_type, bank_loan_pct, down_payment_pct,
    finish_state, developer,
    price_currency, price_usd, floor_level,
    contact_phone, contact_username,
    price_per_builtup_sqm, price_per_plot_sqm,
    confidence_json, source_channel, raw_text, posted_at
)
VALUES (
    :id, :listing_status, :intent, :listing_class,
    :valuation_eligible, :sale_analytics_eligible, :developer_analytics_eligible,
    :property_type, :property_subtype, :location, :city,
    :plot_sqm, :builtup_sqm,
    :bedrooms, :bathrooms,
    :sale_price_birr, :rent_price_birr, :rent_advance_birr,
    :payment_type, :bank_loan_pct, :down_payment_pct,
    :finish_state, :developer,
    :price_currency, :price_usd, :floor_level,
    :contact_phone, :contact_username,
    :price_per_builtup_sqm, :price_per_plot_sqm,
    :confidence_json, :source_channel, :raw_text, :posted_at
)
ON CONFLICT (id) DO UPDATE
SET
    listing_status = CASE
        WHEN EXCLUDED.listing_status = 'INACTIVE' THEN 'INACTIVE'
        ELSE COALESCE(processed_listings.listing_status, EXCLUDED.listing_status)
    END,
    sale_price_birr = COALESCE(processed_listings.sale_price_birr, EXCLUDED.sale_price_birr),
    rent_price_birr = COALESCE(processed_listings.rent_price_birr, EXCLUDED.rent_price_birr),
    builtup_sqm = COALESCE(processed_listings.builtup_sqm, EXCLUDED.builtup_sqm),
    plot_sqm = COALESCE(processed_listings.plot_sqm, EXCLUDED.plot_sqm),
    property_type = CASE
        WHEN processed_listings.property_type IS NULL OR processed_listings.property_type = 'UNKNOWN'
        THEN COALESCE(EXCLUDED.property_type, processed_listings.property_type)
        ELSE processed_listings.property_type
    END,
    location = CASE
        WHEN processed_listings.location = 'other_addis'
        THEN COALESCE(EXCLUDED.location, processed_listings.location)
        ELSE processed_listings.location
    END,
    city = COALESCE(processed_listings.city, EXCLUDED.city),
    developer = COALESCE(processed_listings.developer, EXCLUDED.developer),
    finish_state = COALESCE(processed_listings.finish_state, EXCLUDED.finish_state),
    posted_at = GREATEST(processed_listings.posted_at, EXCLUDED.posted_at),
    raw_text = CASE
        WHEN EXCLUDED.sale_price_birr IS NOT NULL THEN EXCLUDED.raw_text
        ELSE processed_listings.raw_text
    END;
"""

# ── rental_listings insert ────────────────────────────────────
INSERT_RENTAL = """
INSERT INTO rental_listings (
    id, location, city, property_type, property_subtype,
    bedrooms, bathrooms, builtup_sqm, plot_sqm,
    monthly_rent_birr, rent_advance_birr, rent_per_sqm,
    finish_state, floor_level,
    contact_phone, contact_username,
    source_channel, posted_at, raw_text
)
VALUES (
    :id, :location, :city, :property_type, :property_subtype,
    :bedrooms, :bathrooms, :builtup_sqm, :plot_sqm,
    :monthly_rent_birr, :rent_advance_birr, :rent_per_sqm,
    :finish_state, :floor_level,
    :contact_phone, :contact_username,
    :source_channel, :posted_at, :raw_text
)
ON CONFLICT (id) DO NOTHING;
"""


def safe_divide(price, sqm):
    try:
        if price and sqm and sqm >= 1:
            return round(price / sqm, 2)
    except (TypeError, ZeroDivisionError):
        pass
    return None


def build_processed_values(pipeline, row):
    """
    Run the parser on one telegram_listings row and apply the channel rules.
    Returns (values, blob, is_forum): values holds every processed_listings
    column the ETL writes; blob is the text the parser saw. reprocess.py uses
    this too, so both always produce the same values. Raises if the parser fails.
    """
    is_forum = getattr(row, "reply_to_top_id", None) is not None
    processed_id = str(row.id)
    if is_forum:
        processed_id = f"{getattr(row, 'channel', None)}::topic::{int(row.reply_to_top_id)}"

    # Include topic_title in the text blob so forum metadata can help extraction.
    blob = (row.text or "")
    if getattr(row, "topic_title", None):
        blob = f"{row.topic_title}\n{blob}"

    _channel = getattr(row, "channel", None) or ""
    record = {"id": processed_id, "text": blob, "extracted_area": None, "source_channel": _channel}
    result = pipeline.process(record)

    # ── Post-classification overrides ─────────────────────────────
    # Rule 1: Bet_afri family channels are rent-only sources. Bet_afri and
    # Betafrivip list single rooms, apart from whole compounds ("ሙሉ ግቢ", houses);
    # Bet_afri_Business lists offices and shops.
    if "Bet_afri" in _channel or "Betafrivip" in _channel:
        result["intent"] = "RENT"
        if "Bet_afri_Business" not in _channel:
            result["property_type"] = "VILLA" if "ሙሉ ግቢ" in blob else "SINGLE_ROOM"

    # Rule 2: Single-room keyword signals: "አንድ ክፍል", "1 ክፍል" (one room), "#1_ክፍል".
    # (Not "አንድ" and "ክፍል" anywhere: "ንግድ ክፍል … አንድ ሚሊዮን" is a building.)
    if re.search(r"(?:አንድ|1)\s*ክፍል|#1_", blob):
        result["property_type"] = "SINGLE_ROOM"

    values = {
        "id":                            result["id"],
        "listing_status":                result.get("listing_status"),
        "intent":                        result.get("intent"),
        "listing_class":                 result.get("listing_class"),
        "valuation_eligible":            result.get("valuation_eligible"),
        "sale_analytics_eligible":       result.get("sale_analytics_eligible"),
        "developer_analytics_eligible":  result.get("developer_analytics_eligible"),
        "property_type":                 result.get("property_type"),
        "property_subtype":              result.get("property_subtype"),
        "location":                      result.get("location"),
        "city":                          result.get("city"),
        "plot_sqm":                      result.get("plot_sqm"),
        "builtup_sqm":                   result.get("builtup_sqm"),
        "bedrooms":                      result.get("bedrooms"),
        "bathrooms":                     result.get("bathrooms"),
        "sale_price_birr":               result.get("sale_price_birr"),
        "rent_price_birr":               result.get("rent_price_birr"),
        "rent_advance_birr":             result.get("rent_advance_birr"),
        "payment_type":                  result.get("payment_type"),
        "bank_loan_pct":                 result.get("bank_loan_pct"),
        "down_payment_pct":              result.get("down_payment_pct"),
        "finish_state":                  result.get("finish_state"),
        "developer":                     result.get("developer"),
        "price_currency":                result.get("price_currency"),
        "price_usd":                     result.get("price_usd"),
        "floor_level":                   result.get("floor_level"),
        "contact_phone":                 result.get("contact_phone"),
        "contact_username":              result.get("contact_username"),
        "confidence_json":               json.dumps(result.get("confidence", {})),
        "source_channel":                getattr(row, "channel", None),
        "raw_text":                      (row.text or "")[:2000],
        "posted_at":                     getattr(row, "posted_at", None),
        # Not a column: the price per m² the text gave, kept for price_per_sqm_values().
        "asking_price_per_sqm":          result.get("price_per_sqm_birr"),
    }
    values["price_per_builtup_sqm"], values["price_per_plot_sqm"] = price_per_sqm_values(values)
    return values, blob, is_forum


def price_per_sqm_values(values):
    """
    (price_per_builtup_sqm, price_per_plot_sqm) from the total price and the sizes.
    When the text gave a price per m² but no size to turn it into a total, that
    price per m² is kept instead (on the plot for land).
    """
    per_built = safe_divide(values["sale_price_birr"], values["builtup_sqm"])
    per_plot = safe_divide(values["sale_price_birr"], values["plot_sqm"])
    asking = values.get("asking_price_per_sqm")
    if asking and values["sale_price_birr"] is None:
        if values["property_type"] == "LAND":
            per_plot = asking
        else:
            per_built = asking
    return per_built, per_plot


def run(limit=None):
    pipeline = ValuationPipeline()

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS reply_to_top_id BIGINT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS listing_status TEXT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS rent_price_birr BIGINT;"))

        # Fetch raw listings including posted_at, except messages deliberately
        # kept out (deleted duplicates and clean-ups, see processing_exclusions).
        query = """
            SELECT id, text, channel, posted_at, reply_to_top_id, topic_title
            FROM telegram_listings t
            WHERE NOT EXISTS (SELECT 1 FROM processing_exclusions e WHERE e.raw_id = t.id)
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(text(query)).fetchall()

    total    = len(rows)
    inserted = 0
    rental   = 0
    skipped  = 0
    errors   = 0
    error_log = []   # (raw message id, step, error), listed at the end

    print(f"\nProcessing {total} rows...\n")

    for i, row in enumerate(rows, 1):
        if i % 100 == 0:
            print(f"  {i}/{total} processed | inserted={inserted} rental={rental} errors={errors}")

        try:
            values, blob, is_forum = build_processed_values(pipeline, row)
        except Exception as e:
            errors += 1
            error_log.append((row.id, "parser", f"{type(e).__name__}: {e}"))
            continue

        rent_per_sqm = safe_divide(values["rent_price_birr"], values["builtup_sqm"])

        # ── Insert/Upsert into processed_listings (all records) ──────
        try:
            with engine.begin() as conn:
                conn.execute(text(PARSER_WRITE_SQL))
                stmt = UPSERT_FORUM_PROJECT if is_forum else INSERT_PROCESSED
                if conn.execute(text(stmt), values).rowcount:
                    inserted += 1
                else:
                    skipped += 1   # already processed (ON CONFLICT DO NOTHING)
                    continue       # its rental row, if any, was made when it was new
        except Exception as e:
            errors += 1
            error_log.append((row.id, "save listing", f"{type(e).__name__}: {e}"))
            continue

        # ── Insert into rental_listings (RENT intent only, new listings) ────
        if values["intent"] in ("RENT", "MIXED") and values["rent_price_birr"] and values["property_type"] != "ADVERTISEMENT":
            try:
                with engine.begin() as conn:
                    result = conn.execute(text(INSERT_RENTAL), {
                        "id":                  values["id"] + "_rent",
                        "location":            values["location"],
                        "city":                values["city"],
                        "property_type":       values["property_type"],
                        "property_subtype":    values["property_subtype"],
                        "bedrooms":            values["bedrooms"],
                        "bathrooms":           values["bathrooms"],
                        "builtup_sqm":         values["builtup_sqm"],
                        "plot_sqm":            values["plot_sqm"],
                        "monthly_rent_birr":   values["rent_price_birr"],
                        "rent_advance_birr":   values["rent_advance_birr"],
                        "rent_per_sqm":        rent_per_sqm,
                        "finish_state":        values["finish_state"],
                        "floor_level":         values["floor_level"],
                        "contact_phone":       values["contact_phone"],
                        "contact_username":    values["contact_username"],
                        "source_channel":      values["source_channel"],
                        "posted_at":           values["posted_at"],
                        "raw_text":            blob[:2000],
                    })
                    rental += result.rowcount   # 0 when already there (ON CONFLICT DO NOTHING)
            except Exception as e:
                # A rental insert failure should not block the main insert, but is reported.
                error_log.append((row.id, "save rental", f"{type(e).__name__}: {e}"))

    # ── Final summary ─────────────────────────────────────────
    print(f"""
========================================
  ETL COMPLETE
========================================
  Total rows read        : {total}
  Inserted (all)         : {inserted}
  Rental listings        : {rental}
  Skipped (dupes)        : {skipped}
  Errors                 : {errors}
========================================
""")
    if error_log:
        print(f"ERRORS ({len(error_log)}, the first 10; message id, step, error):")
        for raw_id, step, err in error_log[:10]:
            print(f"  {raw_id:>7}  {step:<13} {err[:150]}")
        print()

    # ── Quick stats ───────────────────────────────────────────
    print("QUICK STATS:\n")
    queries = {
        "Total processed":          "SELECT COUNT(*) FROM processed_listings",
        "Valuation eligible":       "SELECT COUNT(*) FROM processed_listings WHERE valuation_eligible = true AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Sale listings":            "SELECT COUNT(*) FROM processed_listings WHERE intent = 'SALE' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Rent listings":            "SELECT COUNT(*) FROM rental_listings",
        "Has sale price":           "SELECT COUNT(*) FROM processed_listings WHERE sale_price_birr IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Has area (builtup)":       "SELECT COUNT(*) FROM processed_listings WHERE builtup_sqm IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Has contact phone":        "SELECT COUNT(*) FROM processed_listings WHERE contact_phone IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Sheger City listings":     "SELECT COUNT(*) FROM processed_listings WHERE city = 'SHEGER_CITY' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Warehouse listings":       "SELECT COUNT(*) FROM processed_listings WHERE property_type = 'WAREHOUSE' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Commercial listings":      "SELECT COUNT(*) FROM processed_listings WHERE property_type = 'COMMERCIAL' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Commercial buildings":     "SELECT COUNT(*) FROM processed_listings WHERE property_type = 'COMMERCIAL_BUILDING' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        "Avg price/sqm (residential builtup)": """
            SELECT ROUND(AVG(price_per_builtup_sqm)::numeric, 0)
            FROM processed_listings
            WHERE price_per_builtup_sqm IS NOT NULL
              AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)
              AND (
                    property_type = 'APARTMENT'
                 OR (property_type = 'VILLA' AND property_subtype IN ('G+1', 'G+2', 'G+3', 'G+4'))
              )
        """,
    }

    with engine.connect() as conn:
        for label, q in queries.items():
            try:
                val = conn.execute(text(q)).scalar()
                print(f"  {label:<30} {val}")
            except Exception as e:
                print(f"  {label:<30} ERROR: {e}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--reset", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reset:
        sys.exit("--reset was removed: it deleted every processed listing, including hand repairs.\n"
                 "To bring parser fixes to old listings, use: python src/reprocess.py")
    run(limit=args.limit)
