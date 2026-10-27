"""
recount_findings.py
-------------------
Counts, in the stored data, the listings still showing the bugs found in the
audit (STATUS.md findings 3 to 12). Read-only; prints counts, no message text.

Usage:
    venv\\Scripts\\python.exe database\\recount_findings.py
"""

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from locations import ALIASES, NOISE, PLACES, UNKNOWN  # noqa: E402
from processor import MILLION_WORD, find_price_per_sqm, is_photo_only, strip_links  # noqa: E402
from settings import DB_URL  # noqa: E402

DECIMAL_MILLION_RE = re.compile(r"(\d+)\.(\d+)\s*" + MILLION_WORD, re.IGNORECASE)

names = defaultdict(set)
for alias, code in ALIASES:
    names[code].add(re.sub(r"\s", "", alias.lower()))
for code, place in PLACES.items():
    names[code].add(re.sub(r"\W", "", place.name.lower()))


def named_in(code, text_):
    # NFKC turns decorative letters ("𝗞𝗮𝘇𝗮𝗻𝗰𝗵𝗶𝘀") into plain ones, as the parser does.
    squeezed = re.sub(r"[\s_]", "", unicodedata.normalize("NFKC", text_).lower())
    return any(n in squeezed for n in names.get(code, ()))


def main():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.location, p.listing_class, p.sale_price_birr,
                   coalesce(t.topic_title || ' ', '') || coalesce(t.text, '') AS blob, t.text
            FROM processed_listings p JOIN telegram_listings t ON p.id = t.id::text
        """)).fetchall()
        protected_location = {r[0] for r in conn.execute(text(
            "SELECT listing_id FROM listing_overrides WHERE field = 'location'"))}
        codes = [r[0] for r in conn.execute(text("SELECT DISTINCT location FROM processed_listings"))]
        excluded_back = conn.execute(text("""
            SELECT count(*) FROM processing_exclusions e JOIN processed_listings p ON p.id = e.raw_id::text
        """)).scalar()
        kept_out = conn.execute(text("SELECT count(*) FROM processing_exclusions")).scalar()
        holding = conn.execute(text("SELECT count(*) FROM listing_overrides")).scalar()

    f = defaultdict(int)
    for lid, loc, cls, sale, blob, raw in rows:
        if sale is not None:
            for m in DECIMAL_MILLION_RE.finditer(blob):
                if int(m.group(1)) * 1_000_000 == sale and int(m.group(2)) > 0:
                    f["3"] += 1
                    break
            per = find_price_per_sqm(blob)
            if per is not None and per == sale:
                f["4"] += 1
        if loc == "yeka" and not re.search(r"(?<![^\W\d_])(?:በ|ከ|ለ|የ)?(?:የካ|yeka)(?![^\W\d_])", blob, re.I):
            f["5"] += 1
        if loc == "haya_hulet" and not named_in("haya_hulet", blob):
            f["6"] += 1
        if loc not in (NOISE, UNKNOWN) and loc in PLACES and not named_in(loc, blob):
            f["7"] += 1
            if lid in protected_location:
                f["7 protected"] += 1
        if loc == NOISE and cls == "ADVERTISEMENT" and not is_photo_only(raw) and re.search(r"https?://", raw or "", re.I) \
                and len(strip_links(raw).strip()) >= 30:
            f["9"] += 1
        if is_photo_only(raw) and cls == "ADVERTISEMENT":
            f["10"] += 1

    unknown_codes = [c for c in codes if c not in PLACES and c not in (NOISE, UNKNOWN)]
    print(f"listings checked: {len(rows)}")
    print(f" 3 decimals cut off (5.5 million stored as 5,000,000):          {f['3']}")
    print(f" 4 a price per m² stored as the total price:                    {f['4']}")
    print(f" 5 'yeka' where the text never names Yeka:                       {f['5']}")
    print(f" 6 22 area where the text only has the number 22:               {f['6']}")
    print(f" 7 a place named nowhere in the text (e.g. #Bole as Bulbula):   {f['7']}  (of which protected: {f['7 protected']})")
    print(f" 8 location codes in use: {len(codes)}; codes not in locations.py: {len(unknown_codes)} {unknown_codes}")
    print(f" 9 posts with a web link thrown away as noise:                  {f['9']}")
    print(f"10 photo-only posts labelled ADVERTISEMENT:                      {f['10']}")
    print(f"12 messages kept out: {kept_out}; of them back as listings: {excluded_back}")
    print(f"   protected values (listing_overrides): {holding}")
    print("11 run src\\reprocess.py: 'Listings that would change' must be 0")


if __name__ == "__main__":
    main()
