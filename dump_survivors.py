import psycopg2
import os

DB_CONFIG = {
    "dbname": "ollaa",
    "user": "postgres",
    "password": "REMOVED_OLD_PASSWORD",
    "host": "localhost",
    "port": "5432"
}

def extract_survivors():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        query = """
        SELECT id, sale_price_birr, raw_text 
        FROM processed_listings 
        WHERE location = 'other_addis' 
          AND intent IN ('SALE', 'MIXED')
        ORDER BY id DESC;
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        with open("other_addis_survivors.txt", "w", encoding="utf-8") as f:
            f.write(f"SURVIVOR ANALYSIS - {len(rows)} ROWS FOUND\n")
            f.write("="*60 + "\n\n")
            for row in rows:
                f.write(f"ID: {row[0]}\n")
                f.write(f"PRICE: {row[1]:,}\n" if row[1] else "PRICE: None\n")
                f.write(f"CONTENT:\n{row[2]}\n")
                f.write("-" * 40 + "\n\n")
        print(f"DONE: Created other_addis_survivors.txt with {len(rows)} rows.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_survivors()