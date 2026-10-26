"""
2026_10_26_s6_location_codes.py
-------------------------------
One-time change for task S6: gives every stored listing today's location code.

Earlier scripts wrote different codes for the same place ("twenty_two",
"22_area", "22_mazoria" for Haya Hulet). This renames them, using
locations.RENAMED_CODES, in processed_listings, in the protected values
(listing_overrides) and in rental_listings, and makes each listing's city match
its place. It is a rename, not a repair: the protected values keep protecting
the same place, and no new protection is recorded.

Usage (take a backup first, see CLAUDE.md):
    venv\\Scripts\\python.exe database\\migrations\\2026_10_26_s6_location_codes.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_26_s6_location_codes.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402

from locations import PLACES, RENAMED_CODES  # noqa: E402
from protection import PARSER_WRITE_SQL  # noqa: E402
from settings import DB_CONFIG  # noqa: E402


def main(apply: bool) -> None:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(PARSER_WRITE_SQL)   # renames are not repairs

    counts = {"listings": 0, "protected values": 0, "rental rows": 0}
    for old, new in RENAMED_CODES.items():
        cur.execute("UPDATE processed_listings SET location = %s WHERE location = %s", (new, old))
        counts["listings"] += cur.rowcount
        cur.execute("UPDATE listing_overrides SET value = %s WHERE field = 'location' AND value = %s", (new, old))
        counts["protected values"] += cur.rowcount
        cur.execute("UPDATE rental_listings SET location = %s WHERE location = %s", (new, old))
        counts["rental rows"] += cur.rowcount
    print("renamed old location codes:", counts)

    # Each listing's city follows its place (protected cities included).
    fixed = 0
    for code, place in PLACES.items():
        cur.execute("UPDATE processed_listings SET city = %s WHERE location = %s AND city IS DISTINCT FROM %s",
                    (place.city, code, place.city))
        fixed += cur.rowcount
        cur.execute("""UPDATE listing_overrides o SET value = %s FROM processed_listings p
                       WHERE o.listing_id = p.id AND o.field = 'city' AND p.location = %s
                         AND o.value IS DISTINCT FROM %s""", (place.city, code, place.city))
        fixed += cur.rowcount
    print("cities made to match their place:", fixed)

    cur.execute("SELECT count(*) FROM processed_listings WHERE location = ANY(%s)", (list(RENAMED_CODES),))
    left = cur.fetchone()[0]
    print("listings still using an old code:", left)

    if apply and left == 0:
        conn.commit()
        print("\nCOMMITTED")
    else:
        conn.rollback()
        print("\nDRY RUN: nothing was changed (use --apply)" if not apply else "\nROLLED BACK")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
