import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL)

PRICE_REGEX = re.compile(r'(\$|usd|birr|etb)?\s*([\d,]{4,})', re.I)
BEDS_REGEX = re.compile(r'(\d+)\s*(bed|bdr|bedroom)', re.I)
SQM_REGEX = re.compile(r'(\d+)\s*(sqm|m2)', re.I)

def normalize_row(row):
    text_raw = row["text"].lower()

    price = None
    currency = None
    beds = None
    sqm = None

    price_match = PRICE_REGEX.search(text_raw)
    if price_match:
        currency = price_match.group(1)
        price = int(price_match.group(2).replace(",", ""))

    beds_match = BEDS_REGEX.search(text_raw)
    if beds_match:
        beds = int(beds_match.group(1))

    sqm_match = SQM_REGEX.search(text_raw)
    if sqm_match:
        sqm = int(sqm_match.group(1))

    return price, currency, beds, sqm


with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT id, text
        FROM telegram_listings
        WHERE price IS NULL
        LIMIT 200
    """)).mappings()

    for row in rows:
        price, currency, beds, sqm = normalize_row(row)

        conn.execute(text("""
            UPDATE telegram_listings
            SET price = :price,
                currency = :currency,
                beds = :beds,
                sqm = :sqm
            WHERE id = :id
        """), {
            "id": row["id"],
            "price": price,
            "currency": currency,
            "beds": beds,
            "sqm": sqm
        })

print("Normalization batch complete")
