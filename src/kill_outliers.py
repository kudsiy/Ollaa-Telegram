"""
kill_outliers.py
----------------
Find the rows that are inflating Avg price/sqm by:
  - Selecting the top 10 processed_listings rows ordered by sale_price_birr / builtup_sqm DESC
  - Printing id, sale_price_birr, builtup_sqm, price_per_sqm, and a raw_text preview
  - Counting rows where builtup_sqm is between 0 and 1

Run:
  python src/kill_outliers.py

Env:
  DB_URL (optional) defaults to local ollaa
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text


DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa")
engine = create_engine(DB_URL)


def snippet(value: str | None, length: int = 100) -> str:
    text_value = (value or "").replace("\r", " ").replace("\n", " ").strip()
    return text_value[:length]


def main() -> None:
    top_poison_rows = text(
        """
        SELECT
            id,
            sale_price_birr,
            builtup_sqm,
            ROUND((sale_price_birr::numeric / NULLIF(builtup_sqm, 0)), 2) AS price_per_sqm,
            LEFT(COALESCE(raw_text, ''), 100) AS raw_text_preview
        FROM processed_listings
        WHERE sale_price_birr IS NOT NULL
          AND builtup_sqm IS NOT NULL
          AND builtup_sqm > 0
        ORDER BY (sale_price_birr::numeric / builtup_sqm) DESC
        LIMIT 10
        """
    )

    tiny_area_count = text(
        """
        SELECT COUNT(*) AS tiny_area_rows
        FROM processed_listings
        WHERE builtup_sqm IS NOT NULL
          AND builtup_sqm BETWEEN 0 AND 1
        """
    )

    with engine.begin() as conn:
        rows = conn.execute(top_poison_rows).mappings().all()
        tiny_count = conn.execute(tiny_area_count).scalar_one()

    print("\nTOP 10 ROWS BY sale_price_birr / builtup_sqm")
    print("=" * 80)
    if not rows:
        print("No matching rows found.")
    else:
        for index, row in enumerate(rows, start=1):
            print(f"\n[{index:02d}] id={row['id']}")
            print(f"  sale_price_birr={row['sale_price_birr']}")
            print(f"  builtup_area={row['builtup_sqm']}")
            print(f"  price_per_sqm={row['price_per_sqm']}")
            print(f"  raw_text[0:100]={snippet(row['raw_text_preview'])}")

    print("\nTINY AREA CHECK")
    print("=" * 80)
    print(f"Rows with builtup_sqm between 0 and 1: {tiny_count}")


if __name__ == "__main__":
    main()
