r"""
2026_11_16_s36_payment_terms.py
-------------------------------
Task S36 (owner's go-ahead, 16 November 2026): new processed_listings columns for the payment terms
of developer adverts (src/payment_terms.py), and the protection trigger widened to the new
protection.TRACKED_FIELDS, so a hand correction of a payment term is kept like any other repair.
The columns start empty; run src/reprocess.py afterwards to fill them.

Usage:
    venv\Scripts\python.exe database\migrations\2026_11_16_s36_payment_terms.py          (dry run)
    venv\Scripts\python.exe database\migrations\2026_11_16_s36_payment_terms.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402
from protection import TRACKED_FIELDS  # noqa: E402

COLUMNS = {
    "discount_schedule":               "text",       # share paid -> discount, "65:35; 100:20"
    "instalment_count":                "integer",
    "instalment_months":               "integer",
    "instalments_follow_construction": "boolean",
    "interest_free":                   "boolean",
    "handover_months":                 "integer",
    "construction_progress_pct":       "integer",
    "price_per_sqm_stated":            "numeric",    # the price per m² written in the advert
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
