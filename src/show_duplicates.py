"""
show_duplicates.py
------------------
Read-only: lists the 10 groups of listings that share a price, a size and a location.

Usage:
    python src/show_duplicates.py
"""

from sqlalchemy import create_engine, text
from settings import DB_URL

engine = create_engine(DB_URL)

query = """
SELECT
    sale_price_birr,
    builtup_sqm,
    location,
    COUNT(*) AS dup_count,
    STRING_AGG(raw_text, E'\n\n--- DUP ---\n\n') as examples
FROM processed_listings
WHERE sale_price_birr IS NOT NULL
AND builtup_sqm IS NOT NULL
AND location IS NOT NULL
GROUP BY sale_price_birr, builtup_sqm, location
HAVING COUNT(*) > 1
ORDER BY dup_count DESC
LIMIT 10
"""

with engine.connect() as conn:
    rows = conn.execute(text(query)).fetchall()

with open("duplicate_examples.txt", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"\n{'='*60}\n")
        f.write(f"PRICE: {r.sale_price_birr}\n")
        f.write(f"AREA: {r.builtup_sqm}\n")
        f.write(f"LOCATION: {r.location}\n")
        f.write(f"DUP COUNT: {r.dup_count}\n")
        f.write(f"{'-'*60}\n")
        f.write(r.examples)
        f.write("\n")

print("Saved to duplicate_examples.txt")