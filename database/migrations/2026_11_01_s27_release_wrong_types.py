r"""
2026_11_01_s27_release_wrong_types.py
-------------------------------------
Task S27, approved by the owner on 1 November 2026: release the protected type of 3 listings in the
sale sample, flats that an older repair called offices or shops (1099, 1744, 2625). Only the type is
released; their other protected values stay. Run src/reprocess.py afterwards.

Usage:
    venv\Scripts\python.exe database\migrations\2026_11_01_s27_release_wrong_types.py          (dry run)
    venv\Scripts\python.exe database\migrations\2026_11_01_s27_release_wrong_types.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402

IDS = ["1099", "1744", "2625"]


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""DELETE FROM listing_overrides WHERE field = 'property_type' AND listing_id = ANY(%s)""", (IDS,))
    released = cur.rowcount
    cur.execute("SELECT count(*) FROM listing_overrides")
    print(f"protected types released: {released} (expected {len(IDS)}); protected values left: {cur.fetchone()[0]}")
    if apply and released == len(IDS):
        conn.commit()
        print("COMMITTED. Now run src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK: unexpected count")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
