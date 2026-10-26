import re
from sqlalchemy import create_engine, text
from settings import DB_URL

engine = create_engine(DB_URL)

def extract_beds(text_msg):
    if not text_msg:
        return None
    match = re.search(r'(\d+)\s*(bed|bedroom)', text_msg, re.IGNORECASE)
    return int(match.group(1)) if match else None

def extract_price(text_msg):
    if not text_msg:
        return None
    match = re.search(r'(ETB|\$)?\s?([\d,]{3,})', text_msg)
    if match:
        return int(match.group(2).replace(',', ''))
    return None

with engine.begin() as conn:
    rows = conn.execute(
        text("SELECT id, text FROM telegram_listings")
    ).fetchall()

    for row in rows:
        beds = extract_beds(row.text)
        price = extract_price(row.text)

        conn.execute(
            text("""
                UPDATE telegram_listings
                SET beds = :beds,
                    price = :price
                WHERE id = :id
            """),
            {
                "beds": beds,
                "price": price,
                "id": row.id
            }
        )

print("Parsing complete")
