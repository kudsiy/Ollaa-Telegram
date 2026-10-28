"""
2026_10_28_s14_release_bet_afri_labels.py
-----------------------------------------
Task S14, approved by the owner on 28 October 2026: release 7 protected
property_type labels on Bet_afri posts that the post itself contradicts
(flats kept as shops or a commercial building, whole villa compounds kept as
shops or a warehouse). After release the refined channel rule applies
(etl_runner.bet_afri_type). The two kept "STUDIO" labels on posts the rule calls
rooms (2048, 2777) stay. Run src/reprocess.py afterwards.

Usage:
    venv\\Scripts\\python.exe database\\migrations\\2026_10_28_s14_release_bet_afri_labels.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_28_s14_release_bet_afri_labels.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402

# listing id -> the kept (wrong) type; the post's own words in brackets.
LABELS = {
    "2040": "COMMERCIAL_BUILDING",   # 1-bedroom flat, 1st/2nd floor of a G+5 building
    "2761": "COMMERCIAL",            # 2-bedroom flat, 1st floor of a G+4 building
    "2773": "COMMERCIAL",            # 3-bedroom duplex, 4th floor, apartment building
    "3845": "COMMERCIAL",            # 3-bedroom flat of 150 m², above the 3rd floor of a G+4
    "3834": "COMMERCIAL",            # 3-bedroom whole compound, villa of 250 m²
    "3851": "COMMERCIAL",            # 3-bedroom whole compound, G+3
    "3862": "WAREHOUSE",             # 4-bedroom whole compound, G+3
}


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    released = 0
    for listing_id, kept in LABELS.items():
        cur.execute("""DELETE FROM listing_overrides
                       WHERE listing_id = %s AND field = 'property_type' AND value = %s""", (listing_id, kept))
        released += cur.rowcount
    cur.execute("SELECT count(*) FROM listing_overrides")
    print(f"protected type labels released: {released} (expected {len(LABELS)}); protected values left: {cur.fetchone()[0]}")
    if apply and released == len(LABELS):
        conn.commit()
        print("COMMITTED. Now run src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK: unexpected count")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
