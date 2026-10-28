"""
2026_10_28_s13_release_rental_labels.py
---------------------------------------
Task S13, approved by the owner on 28 October 2026: release the protected
property_type "ADVERTISEMENT" of 14 real rental posts (Bet_afri, Betafrivip,
Bet_afri_Business). S8 kept these old labels because the Bet_afri channel rule
would have forced every post to SINGLE_ROOM; the label kept them out of the
rental listings. After release the parser's type applies (8 single rooms,
3 villas for whole compounds, 1 office, 2 shops). Nothing else of these
listings is released. Run src/reprocess.py afterwards.

Usage:
    venv\\Scripts\\python.exe database\\migrations\\2026_10_28_s13_release_rental_labels.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_28_s13_release_rental_labels.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402

LISTINGS = ["2046", "5957", "5974", "5988", "6015", "6020", "6043", "6087", "6091", "6093", "6098",
            "6158", "6164", "6182"]


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""DELETE FROM listing_overrides
                   WHERE listing_id = ANY(%s) AND field = 'property_type' AND value = 'ADVERTISEMENT'""", (LISTINGS,))
    released = cur.rowcount
    cur.execute("SELECT count(*) FROM listing_overrides")
    print(f"protected type labels released: {released} (expected {len(LISTINGS)}); protected values left: {cur.fetchone()[0]}")
    if apply and released == len(LISTINGS):
        conn.commit()
        print("COMMITTED. Now run src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK: unexpected count")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
