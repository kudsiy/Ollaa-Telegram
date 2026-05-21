import psycopg2

conn = psycopg2.connect(dbname='ollaa', user='postgres', password='REMOVED_OLD_PASSWORD')
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