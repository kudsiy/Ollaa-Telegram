import psycopg2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from settings import DB_CONFIG

def run_fix():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 1. MOVE ARTICLES & HOLIDAY ADS TO NOISE
        # Patterns found in your file: Inflation, 1 Million Homes, ROI, Holiday Greetings [cite: 6, 7, 16, 17, 28, 44]
        noise_query = """
        UPDATE processed_listings 
        SET location = 'noise', intent = 'ADVERT' 
        WHERE location = 'other_addis' 
        AND (
            raw_text ILIKE '%inflation%' OR 
            raw_text ILIKE '%1 million homes%' OR 
            raw_text ILIKE '%እንኳን አደረሳችሁ%' OR 
            raw_text ILIKE '%ROI%' OR
            raw_text ILIKE '%Invest in Real Estate%'
        );
        """
        cur.execute(noise_query)
        print(f"Cleaned up {cur.rowcount} articles and holiday ads.")

        # 2. MAP SPECIFIC LANDMARKS TO NEIGHBORHOODS
        # Mapping 22, Wollo Sefer, 6 Kilo, and Bulgaria/AU [cite: 1, 2, 26, 45, 46]
        mapping = {
            "wello_sefer": ["wollo sefer", "ወሎ ሰፈር"],
            "haya_hulet": ["22 mazoria", "ሀያ ሁለት", "አዲስ ሕይወት"],
            "6kilo": ["6 kilo", "ስድስት ኪሎ"],
            "bulgaria": ["bulgaria", "ብልጋሪያ", "africa union", "አፍሪካ ህብረት"]
        }
        
        for loc, keys in mapping.items():
            for key in keys:
                cur.execute("""
                    UPDATE processed_listings 
                    SET location = %s 
                    WHERE location = 'other_addis' AND raw_text ILIKE %s
                """, (loc, f'%{key}%'))
                if cur.rowcount > 0:
                    print(f"Moved {cur.rowcount} rows to {loc} using keyword '{key}'.")

        conn.commit()
        print("SUCCESS: Database updated.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

if __name__ == "__main__":
    run_fix()