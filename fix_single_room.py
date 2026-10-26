import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from settings import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

cur.execute("""
    UPDATE processed_listings 
    SET property_type = 'SINGLE_ROOM'
    WHERE property_type = 'UNKNOWN'
    AND source_channel IN (
        'https://t.me/Bet_afri',
        'https://t.me/Bet_afri_Business',
        'https://t.me/Betafrivip'
    )
""")

print(f"Updated {cur.rowcount} rows to SINGLE_ROOM")
conn.commit()
cur.close()
conn.close()