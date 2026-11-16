r"""
2026_11_16_s37_price_options.py
-------------------------------
Task S37 (owner's go-ahead, 16 November 2026): new processed_listings columns for the prices of developer
adverts by payment option and finish (src/payment_terms.py, price_options), and the protection trigger
widened to the new protection.TRACKED_FIELDS. The columns start empty; run src/reprocess.py afterwards.

Usage:
    venv\Scripts\python.exe database\migrations\2026_11_16_s37_price_options.py          (dry run)
    venv\Scripts\python.exe database\migrations\2026_11_16_s37_price_options.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402
from protection import TRACKED_FIELDS  # noqa: E402

COLUMNS = {
    "price_options":            "text",       # "100: 75,000/m²; slow: 115,000/m²; 65: 5,700,000 (81 m²)"
    "cash_price_per_sqm":       "numeric",
    "instalment_price_per_sqm": "numeric",
    "cash_price_birr":          "numeric",
    "instalment_price_birr":    "numeric",
}

TRIGGER = """
DROP TRIGGER processed_listings_protect_repairs ON public.processed_listings;
CREATE TRIGGER processed_listings_protect_repairs
    AFTER UPDATE ON public.processed_listings
    FOR EACH ROW EXECUTE FUNCTION public.record_listing_override({fields});
""".replace("{fields}", ", ".join(f"'{f}'" for f in TRACKED_FIELDS))


def main(apply: bool) -> None:
    assert set(COLUMNS) <= set(TRACKED_FIELDS), "protection.TRACKED_FIELDS must list the new columns"
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    for name, kind in COLUMNS.items():
        cur.execute(f"ALTER TABLE public.processed_listings ADD COLUMN IF NOT EXISTS {name} {kind}")
    cur.execute(TRIGGER)
    cur.execute("""SELECT count(*) FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'processed_listings' AND column_name = ANY(%s)""",
                (list(COLUMNS),))
    print(f"columns present: {cur.fetchone()[0]} of {len(COLUMNS)}; trigger protects {len(TRACKED_FIELDS)} fields")
    if apply:
        conn.commit()
        print("COMMITTED. Now run database/export_schema.py, src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
