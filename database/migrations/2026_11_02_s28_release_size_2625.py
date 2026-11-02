r"""
2026_11_02_s28_release_size_2625.py
-----------------------------------
Task S28, approved by the owner on 2 November 2026: release the protected built-up size of listing
2625. The stored 94 m² is not in its advert, which lists 70.85 and 73.94 m². Run src/reprocess.py
afterwards.

Usage:
    venv\Scripts\python.exe database\migrations\2026_11_02_s28_release_size_2625.py          (dry run)
    venv\Scripts\python.exe database\migrations\2026_11_02_s28_release_size_2625.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""DELETE FROM listing_overrides WHERE field = 'builtup_sqm' AND listing_id = '2625'""")
    released = cur.rowcount
    cur.execute("SELECT count(*) FROM listing_overrides")
    print(f"protected sizes released: {released} (expected 1); protected values left: {cur.fetchone()[0]}")
    if apply and released == 1:
        conn.commit()
        print("COMMITTED. Now run src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK: unexpected count")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
