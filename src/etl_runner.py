"""
etl_runner.py
-------------
Reads all rows from telegram_listings, runs ValuationPipeline on each,
and inserts structured results into:
  - processed_listings  (all intents: for valuation engine)
  - rental_listings     (RENT intent: for yield calculation)

Safe to re-run: uses ON CONFLICT DO NOTHING.

Usage:
    python src/etl_runner.py
    python src/etl_runner.py --limit 100
    python src/etl_runner.py --reset      # clears both tables first
"""

import argparse
import json
import sys
from sqlalchemy import create_engine, text

try:
    from run_pipeline import ValuationPipeline
except ImportError:
    print("ERROR: run_pipeline.py not found.")
    sys.exit(1)

DB_URL = "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"
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


def run(limit=None, reset=False):
    pipeline = ValuationPipeline()

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS reply_to_top_id BIGINT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS listing_status TEXT;"))
        conn.execute(text("ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS rent_price_birr BIGINT;"))
        if reset:
            conn.execute(text("DELETE FROM processed_listings;"))
            conn.execute(text("DELETE FROM rental_listings;"))
            print("processed_listings and rental_listings cleared.")

        # Fetch raw listings including posted_at
        query = "SELECT id, text, channel, posted_at, reply_to_top_id, topic_title FROM telegram_listings"
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(text(query)).fetchall()

    total    = len(rows)
    inserted = 0
    rental   = 0
    skipped  = 0
    errors   = 0

    print(f"\nProcessing {total} rows...\n")

    for i, row in enumerate(rows, 1):
        if i % 100 == 0:
            print(f"  {i}/{total} processed | inserted={inserted} rental={rental} errors={errors}")

        is_forum = getattr(row, "reply_to_top_id", None) is not None
        processed_id = str(row.id)
        if is_forum:
            processed_id = f"{getattr(row, 'channel', None)}::topic::{int(row.reply_to_top_id)}"

        # Include topic_title in the text blob so forum metadata can help extraction.
        blob = (row.text or "")
        if getattr(row, "topic_title", None):
            blob = f"{row.topic_title}\n{blob}"

        record = {"id": processed_id, "text": blob, "extracted_area": None}

        try:
            result = pipeline.process(record)
        except Exception as e:
            errors += 1
            continue

        # ── Post-classification overrides ─────────────────────────────
        # Rule 1: Bet_afri family channels are rent-only sources.
        _channel = getattr(row, "channel", None) or ""
        if "Bet_afri" in _channel or "Betafrivip" in _channel:
            result["intent"] = "RENT"
            result["property_type"] = "SINGLE_ROOM"

        # Rule 2: Single-room keyword signals (Amharic + hashtag forms).
        _text = blob
        if 'ክፍል' in _text and ('አንድ' in _text or '#1_' in _text):
            result["property_type"] = "SINGLE_ROOM"

        price_per_built = safe_divide(result.get("sale_price_birr"), result.get("builtup_sqm"))
        price_per_plot  = safe_divide(result.get("sale_price_birr"), result.get("plot_sqm"))
        rent_per_sqm    = safe_divide(result.get("rent_price_birr"), result.get("builtup_sqm"))

        # ── Insert/Upsert into processed_listings (all records) ──────
        try:
            with engine.begin() as conn:
                stmt = UPSERT_FORUM_PROJECT if is_forum else INSERT_PROCESSED
                conn.execute(text(stmt), {
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
                    "price_per_builtup_sqm":         price_per_built,
                    "price_per_plot_sqm":            price_per_plot,
                    "confidence_json":               json.dumps(result.get("confidence", {})),
                    "source_channel":                getattr(row, "channel", None),
                    "raw_text":                      (row.text or "")[:2000],
                    "posted_at":                     getattr(row, "posted_at", None),
                })
                inserted += 1
        except Exception as e:
            errors += 1
            continue

        # ── Insert into rental_listings (RENT intent only) ────
        if result.get("intent") in ("RENT", "MIXED") and result.get("rent_price_birr") and result.get("property_type") != "ADVERTISEMENT":
            try:
                with engine.begin() as conn:
                    conn.execute(text(INSERT_RENTAL), {
                        "id":                  result["id"] + "_rent",
                        "location":            result.get("location"),
                        "city":                result.get("city"),
                        "property_type":       result.get("property_type"),
                        "property_subtype":    result.get("property_subtype"),
                        "bedrooms":            result.get("bedrooms"),
                        "bathrooms":           result.get("bathrooms"),
                        "builtup_sqm":         result.get("builtup_sqm"),
                        "plot_sqm":            result.get("plot_sqm"),
                        "monthly_rent_birr":   result.get("rent_price_birr"),
                        "rent_advance_birr":   result.get("rent_advance_birr"),
                        "rent_per_sqm":        rent_per_sqm,
                        "finish_state":        result.get("finish_state"),
                        "floor_level":         result.get("floor_level"),
                        "contact_phone":       result.get("contact_phone"),
                        "contact_username":    result.get("contact_username"),
                        "source_channel":      getattr(row, "channel", None),
                        "posted_at":           getattr(row, "posted_at", None),
                        "raw_text":            record["text"][:2000],
                    })
                    rental += 1
            except Exception:
                pass  # rental insert failure should not block main insert

    # ── Final summary ─────────────────────────────────────────
    print(f"""
========================================
  ETL COMPLETE
========================================
  Total rows read        : {total}
  Inserted (all)         : {inserted}
  Rental listings        : {rental}
  Skipped (dupes)        : {total - inserted - errors}
  Errors                 : {errors}
========================================
""")

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
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    run(limit=args.limit, reset=args.reset)
