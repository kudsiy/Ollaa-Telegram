import re
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa"

engine = create_engine(DB_URL)

DEV_REGEX = re.compile(
    r'(ayat|flintstone|gift|noah|jemo|sunshine|real\s?estate|developers?)',
    re.I
)

PLOT_REGEX = re.compile(
    r'(\d{2,5})\s*(sqm|m2|meter|land)',
    re.I
)

def extract_developer(text_raw):
    match = DEV_REGEX.search(text_raw)
    return match.group(1).title() if match else None

def extract_plot(text_raw):
    match = PLOT_REGEX.search(text_raw)
    return int(match.group(1)) if match else None


with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT id, text
        FROM telegram_listings
        WHERE developer IS NULL
        LIMIT 300
    """)).mappings()

    for row in rows:
        raw = row["text"].lower()

        developer = extract_developer(raw)
        plot_sqm = extract_plot(raw)

        conn.execute(text("""
            UPDATE telegram_listings
            SET developer = :developer,
                plot_sqm = :plot_sqm
            WHERE id = :id
        """), {
            "id": row["id"],
            "developer": developer,
            "plot_sqm": plot_sqm
        })

print("Valuation normalization complete")