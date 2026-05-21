import re
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"

engine = create_engine(DB_URL)

DEVELOPERS = [
    "ayat",
    "Noah",
    "gift",
    "sunshine",
    "Flintstone",
    "real estate",
    "housing",
    "Temer",
    "Jenboro",
    "Tamer",
    "Properties",
    "Champion",
    "DMC Real",
    "Jambo",
    "Hosea",
    "Bamacon",
    "Phison",
    "Ovid",
    "Akoya",
    "Century",
    "amibara",
    "anchor",
    "reality",
    "prime",
    "star",
    "metro",
    "zaramba"
    "palm",
    "abay",
    "harot",
    "merit",
    "metropolitan",
    "dream_builders"
]

with engine.begin() as conn:
    rows = conn.execute(
        text("SELECT id, text FROM telegram_listings WHERE developer IS NULL")
    ).fetchall()

    for row in rows:
        listing_text = row.text.lower()
        found = None

        for dev in DEVELOPERS:
            if dev in listing_text:
                found = dev.title()
                break

        if found:
            conn.execute(
                text("""
                    UPDATE telegram_listings
                    SET developer = :developer
                    WHERE id = :id
                """),
                {"developer": found, "id": row.id}
            )

print("Developer extraction complete")
