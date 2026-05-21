"""
check_outliers.py
-----------------
Diagnostics for impossible prices:
  - Computes price_per_sqm = sale_price_birr / sqm (builtup_sqm preferred)
  - Prints Top 10 most expensive listings with raw text snippets
  - Flags listings where sale_price_birr > 500,000,000 for review

Run:
  python src/check_outliers.py

Env:
  DB_URL (optional) defaults to local ollaa
"""

from __future__ import annotations

import os
from sqlalchemy import create_engine, text


DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa")
engine = create_engine(DB_URL)


def snippet(s: str, n: int = 280) -> str:
    s = (s or "").replace("\r", " ").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def main() -> None:
    top10 = text("""
        SELECT
            id,
            source_channel,
            location,
            city,
            property_type,
            listing_status,
            sale_price_birr,
            builtup_sqm,
            plot_sqm,
            CASE
                WHEN builtup_sqm IS NOT NULL AND builtup_sqm > 0 THEN builtup_sqm
                WHEN plot_sqm IS NOT NULL AND plot_sqm > 0 THEN plot_sqm
                ELSE NULL
            END AS sqm_used,
            CASE
                WHEN sale_price_birr IS NOT NULL
                 AND sale_price_birr > 0
                 AND (
                     (builtup_sqm IS NOT NULL AND builtup_sqm > 0)
                     OR (plot_sqm IS NOT NULL AND plot_sqm > 0)
                 )
                THEN ROUND(
                    sale_price_birr::numeric /
                    NULLIF(
                        CASE
                            WHEN builtup_sqm IS NOT NULL AND builtup_sqm > 0 THEN builtup_sqm
                            WHEN plot_sqm IS NOT NULL AND plot_sqm > 0 THEN plot_sqm
                            ELSE NULL
                        END,
                        0
                    ),
                    2
                )
                ELSE NULL
            END AS price_per_sqm,
            raw_text
        FROM processed_listings
        WHERE sale_price_birr IS NOT NULL
          AND sale_price_birr > 0
          AND (
                (builtup_sqm IS NOT NULL AND builtup_sqm > 0)
             OR (plot_sqm IS NOT NULL AND plot_sqm > 0)
          )
        ORDER BY price_per_sqm DESC NULLS LAST
        LIMIT 10;
    """)

    over_500m = text("""
        SELECT
            id,
            source_channel,
            location,
            property_type,
            listing_status,
            sale_price_birr,
            builtup_sqm,
            plot_sqm,
            raw_text
        FROM processed_listings
        WHERE sale_price_birr IS NOT NULL
          AND sale_price_birr > 500000000
        ORDER BY sale_price_birr DESC
        LIMIT 50;
    """)

    with engine.begin() as conn:
        top = conn.execute(top10).mappings().all()
        high = conn.execute(over_500m).mappings().all()

    print("\n" + "=" * 100)
    print("TOP 10 MOST EXPENSIVE (by price_per_sqm)")
    print("=" * 100)
    for i, r in enumerate(top, 1):
        print("\n" + "-" * 100)
        print(f"[{i:02d}] id={r.get('id')} channel={r.get('source_channel')}")
        print(f"  status={r.get('listing_status')} type={r.get('property_type')} loc={r.get('location')} city={r.get('city')}")
        print(f"  sale_price_birr={r.get('sale_price_birr')} sqm_used={r.get('sqm_used')} (builtup={r.get('builtup_sqm')} plot={r.get('plot_sqm')})")
        print(f"  price_per_sqm={r.get('price_per_sqm')}")
        print("  raw_text:", snippet(r.get("raw_text") or ""))

    print("\n" + "=" * 100)
    print("FLAGGED: sale_price_birr > 500,000,000 (top 50)")
    print("=" * 100)
    if not high:
        print("None found.")
    else:
        for i, r in enumerate(high, 1):
            print("\n" + "-" * 100)
            print(f"[{i:02d}] id={r.get('id')} channel={r.get('source_channel')}")
            print(f"  status={r.get('listing_status')} type={r.get('property_type')} loc={r.get('location')}")
            print(f"  sale_price_birr={r.get('sale_price_birr')} builtup={r.get('builtup_sqm')} plot={r.get('plot_sqm')}")
            print("  raw_text:", snippet(r.get("raw_text") or ""))


if __name__ == "__main__":
    main()

