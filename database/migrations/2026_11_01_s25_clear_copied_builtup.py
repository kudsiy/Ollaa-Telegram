r"""
2026_11_01_s25_clear_copied_builtup.py
--------------------------------------
Task S25, approved by the owner on 1 November 2026: release the protected built-up size of the 91
houses in the sale sample whose one stated size was copied into both plot and built-up by a repair
before 26 October 2026. The parser then leaves built-up empty and keeps the size as the plot; no
built-up size is guessed. Run src/reprocess.py afterwards.

Usage:
    venv\Scripts\python.exe database\migrations6_11_01_s25_clear_copied_builtup.py          (dry run)
    venv\Scripts\python.exe database\migrations6_11_01_s25_clear_copied_builtup.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402

IDS = """
    1 11 12 24 29 31 32 34 35 100 1047 1110 1212 1214 1259 1273 1278 1279 1280 1282 1288
    1292 1296 1354 1357 1720 1734 1737 1738 1757 1813 1891 1893 2082 2086 2087 2088 2090
    2093 2094 2104 2106 2319 2321 2322 2323 2326 2335 2336 2338 2388 2825 2831 2832 2834
    2840 2844 2846 2847 2848 2849 2850 2851 2852 2861 2870 2873 2901 3001 3003 3011 3216
    3537 3544 3611 4051 5426 5431 5451 5460 5472 5479 5496 5503 5506 5563 5814 6249 6250
    6254 6255
""".split()


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""DELETE FROM listing_overrides WHERE field = 'builtup_sqm' AND listing_id = ANY(%s)""", (IDS,))
    released = cur.rowcount
    cur.execute("SELECT count(*) FROM listing_overrides")
    print(f"protected built-up sizes released: {released} (expected {len(IDS)}); protected values left: {cur.fetchone()[0]}")
    if apply and released == len(IDS):
        conn.commit()
        print("COMMITTED. Now run src/reprocess.py (report), then src/reprocess.py --apply.")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK: unexpected count")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
