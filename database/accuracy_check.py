r"""
accuracy_check.py
-----------------
The accuracy checks of the sale sample for the owner's thesis, 60 listings drawn at random each time.
Round 1 (task S20): random.seed(20261101) on the 457 listings of the sample, 1 November 2026.
Round 2 (task S26), after the parser fixes: random.seed(20261102) on the 492 listings of the sample,
leaving out round 1's; 2 listings that a later fix took out of the sample were replaced with
random.Random(20261103).

Writes data/accuracy_check/accuracy_check_60.html (round 1) or accuracy_check_60_round2.html, which
show each original advert next to its stored type, place, price, size and bedrooms, with boxes for
the owner's own check. Contacts are masked. Read-only; data/ is never committed.

WRONG and NOTES hold Claude's own reading of the adverts, shown closed in the file so the owner can
check first. Nothing is corrected until the owner confirms.

Usage:
    venv\Scripts\python.exe database\accuracy_check.py              (round 2)
    venv\Scripts\python.exe database\accuracy_check.py --round 1
"""

import html
import re
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "database"))

from sqlalchemy import create_engine, text  # noqa: E402

from data_quality import place_name  # noqa: E402
from settings import DB_URL  # noqa: E402

OUT_DIR = BASE_DIR / "data" / "accuracy_check"
CONTACT_RE = re.compile(r"\(?\+?\(?251\)?[\s-]*\d[\d\s-]{7,12}|(?<!\d)0[79][\d\s-]{7,11}\d|@\w+|https?://\S+|t\.me/\S+"
                        r"|(?<![\d,.])\d{7,}(?![\d,.])|\bwww\.\S+", re.IGNORECASE)

# id: {field: what the advert says}, for values that contradict the advert.
WRONG = {
    "21": {"type": "a Basement+G+4 building under construction, not one flat",
           "size": "160 m² is the land of the building"},
    "37": {"type": "a 2-bedroom condominium, not land"},
    "1019": {"place": "Kazanchis, not Bole"},
    "1036": {"type": "a 2-bedroom apartment, not an office"},
    "1111": {"size": "the 4.5 million shop is 26 m², not 23 m²"},
    "1123": {"type": "apartments, not an office", "bedrooms": "86 m² is the 2-bedroom unit, not 3"},
    "1260": {"type": "a list of land plots and buildings; the first is land", "place": "the first is at Denbel",
             "size": "the first is 1,000 m², not 300 m²"},
    "1283": {"size": "400 m² is one of three warehouses (1,300 m² in all) on 20,000 m² of land"},
    "1312": {"type": "flats at Piassa, not a shop"},
    "1316": {"type": "3-bedroom flats, not a shop", "place": "Ayat, not Piassa", "size": "the price is for 111 m², not 86 m²"},
    "1893": {"price": "reduced from 21 million to 20 million (the advert also says sold)"},
    "2095": {"type": "a G+2 house with 7 bedrooms, not a warehouse"},
    "2341": {"type": "a 1-bedroom home, not a shop"},
    "2426": {"bedrooms": "106 m² is the 2-bedroom unit, not 3"},
    "2444": {"bedrooms": "106 m² is the 2-bedroom unit, not 3"},
    "2519": {"type": "a 3-bedroom apartment, not a shop", "size": "the home is 125 m² (170 m² in all); 20 m² is its shop"},
    "2842": {"type": "a 5-bedroom house, not an office", "size": "72 m² is the land"},
    "6632": {"size": "the 5.3 million flat is 40 m²; 37 m² is the other flat"},
    "7156": {"place": "Ayat Beshale, not Summit (Summit comes from the channel's standing hashtags)"},
    "7333": {"type": "a Basement+G+5 building, not a warehouse", "price": "48 million cash plus a 30 million bank loan: 78 million",
             "size": "180 m² is its footprint; the land is 300 m²"},
}
# Not contradicted, but worth the owner's eye.
NOTES = {
    "1": "one size stated; the same number is stored as built-up and plot",
    "1273": "one size stated; the same number is stored as built-up and plot",
    "1288": "the advert calls 250 m² the land, yet it is also stored as built-up; 4 bedrooms stated, not stored",
    "1737": "one size stated; the same number is stored as built-up and plot",
    "1738": "one size stated; the same number is stored as built-up and plot",
    "1893": "one size stated; the same number is stored as built-up and plot",
    "2086": "1,000 m² in a compound for a G+1 house is surely the land, yet it is also stored as built-up",
    "2088": "500 m² in a compound is surely the land, yet it is also stored as built-up; place is Legetafo",
    "2335": "one size stated; the same number is stored as built-up and plot",
    "2901": "one size stated; the same number is stored as built-up and plot",
    "3216": "the advert calls 250 m² the land, yet it is also stored as built-up",
    "5479": "one size stated; the same number is stored as built-up and plot",
    "6255": "the advert calls 72 m² the land, yet it is also stored as built-up",
    "40": "right area; the advert says Ayat 49",
    "2372": "right area; the advert says Bole 22",
    "2699": "right area; the advert says CMC Figa",
    "1020": "a plot size is stored for a flat, not in the advert",
    "1962": "a plot size of 87 m² is stored for a flat, not in the advert",
    "1210": "3 bedrooms stated, not stored",
    "1582": "2 bedrooms stated, not stored",
    "2504": "2 bedrooms stated, not stored",
    "5841": "3 bedrooms stated, not stored",
    "7042": "4 bedrooms stated, not stored",
    "7062": "3 bedrooms stated, not stored",
    "5552": "158 (145) m²: the net size is stored here, the gross one in similar adverts such as 1809",
}
IDS = ("1 21 37 40 1017 1019 1020 1031 1036 1111 1123 1143 1210 1222 1260 1273 1283 1288 1312 1316 1582 1727 1737 1738 "
       "1809 1893 1962 2086 2088 2095 2236 2335 2341 2370 2372 2405 2426 2444 2504 2505 2519 2699 2842 2901 3216 3325 "
       "4222 5479 5552 5841 6255 6632 6693 7042 7062 7106 7156 7187 7333 7421").split()
IDS_2 = (
       "25 45 1021 1040 1099 1102 1106 1124 1240 1271 1294 1295 1446 1456 1724 1730 1744 1745 "
       "1815 2342 2392 2440 2485 2493 2509 2595 2611 2641 2707 2870 2887 2982 2984 3403 3551 "
       "3621 5327 5339 5348 5382 5461 5554 5561 5564 5573 5601 5615 5628 5676 5727 5882 6346 "
       "6651 6662 6831 6833 6866 7152 7161 7537 "
       ).split()
WRONG_2 = {
    "1099": {"type": "flats, not an office; the type is a protected value"},
    "1744": {"type": "flats, not an office; the type is a protected value"},
    "2342": {"price": "no unit is priced: an advert for several sites, 99,935 birr per m² times the 300 m²",
             "size": "300 m² is the top of a range for shops; the flats start at 60 m²"},
    "2887": {"type": "a list of several projects; the first is 2-bedroom flats, not a studio",
             "place": "the first project is at Keraniyo", "size": "the first flat is 100 m², not 44 m²"},
}
NOTES_2 = {
    "1240": "300 m² is the footprint of a G+3 house, stored as its built-up size",
    "2493": "284 m² is the footprint of the house, stored as its built-up size",
    "1271": "G+4 guesthouse: 150 m² in the title and 200 m² as the area",
    "2392": "a plot size is stored for a flat, not in the advert",
    "5564": "a built-up size is stored for land, not in the advert",
    "5601": "3-bedroom stated, not stored; price worked out from the price per m²",
    "5615": "a list of studios and flats; the first is stored; the plot size of 76 m² is a 3-bedroom flat's size",
    "1744": "also nearly the same advert as 1745",
}
ROUNDS = {1: (IDS, WRONG, NOTES, "accuracy_check_60.html"), 2: (IDS_2, WRONG_2, NOTES_2, "accuracy_check_60_round2.html")}
STYLE = """
body{font:15px/1.5 system-ui,sans-serif;margin:16px;color:#1b1b1b;background:#fff}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:8px;vertical-align:top;text-align:left}
th{background:#eee;position:sticky;top:0}.ad{white-space:pre-wrap;min-width:320px;font-family:"Nyala","Noto Sans Ethiopic",system-ui}
.v{white-space:nowrap}label{display:block;white-space:nowrap}details{margin-top:8px;color:#555}
input[type=text]{width:100%;box-sizing:border-box;margin-top:6px}@media print{details{display:none}th{position:static}}
"""


def mask(text_: str) -> str:
    # Twice: two numbers written together ("0911...0922...") leave a part after the first pass.
    return CONTACT_RE.sub("<contact>", CONTACT_RE.sub("<contact> ", text_ or ""))


def main() -> None:
    round_no = int(sys.argv[sys.argv.index("--round") + 1]) if "--round" in sys.argv else 2
    ids, wrong, notes, file_name = ROUNDS[round_no]
    out_file = OUT_DIR / file_name
    with create_engine(DB_URL).connect() as conn:
        rows = conn.execute(text("""
            SELECT p.*, t.text AS advert, t.channel, t.message_id FROM processed_listings p
            JOIN telegram_listings t ON p.id = t.id::text WHERE p.id = ANY(:ids)"""), {"ids": ids}).fetchall()
    rows.sort(key=lambda r: int(r.id))
    missing = set(ids) - {r.id for r in rows}
    if missing:
        sys.exit(f"No longer stored: {sorted(missing)}")
    out = [f"<!doctype html><meta charset=utf-8><title>Accuracy check: 60 listings</title><style>{STYLE}</style>",
           f"<h1>Accuracy check, round {round_no}: 60 random listings from the sale sample</h1>",
           "<p>Read each advert, compare it with the stored values, and tick what is wrong. Contacts are masked. "
           "Then tell Claude the listing numbers and what is wrong; nothing is changed until you confirm. "
           "“My reading” under each advert is Claude's own view: open it only after your own check.</p>",
           "<table><tr><th>#</th><th>Original advert</th><th>Stored values</th><th>Your check</th></tr>"]
    for n, r in enumerate(rows, 1):
        channel = r.channel.rsplit("/", 1)[-1]
        price = f"{r.sale_price_birr:,.0f} birr" if r.sale_price_birr else "—"
        fmt = lambda v: f"{v:g} m²" if v is not None else "—"  # noqa: E731
        stored = (f"<b>Type:</b> {r.property_type}<br><b>Place:</b> {html.escape(place_name(r.location))}<br>"
                  f"<b>Price:</b> {price}<br><b>Built-up:</b> {fmt(r.builtup_sqm)}<br><b>Plot:</b> {fmt(r.plot_sqm)}<br>"
                  f"<b>Bedrooms:</b> {r.bedrooms if r.bedrooms is not None else '—'}")
        boxes = "".join(f"<label><input type=checkbox> {x} wrong</label>" for x in ("Type", "Place", "Price", "Size", "Bedrooms"))
        boxes = "<label><input type=checkbox> All right</label>" + boxes + "<input type=text placeholder='Note'>"
        mine = [f"<b>{k}</b>: {html.escape(v)}" for k, v in wrong.get(r.id, {}).items()]
        if r.id in notes:
            mine.append("note: " + html.escape(notes[r.id]))
        reading = "; ".join(mine) or "no problem found"
        out.append(f"<tr><td>{n}<br><small>listing {r.id}</small></td><td><small>{html.escape(channel)}</small>"
                   f"<div class=ad>{html.escape(mask(r.advert))}</div>"
                   f"<details><summary>My reading</summary>{reading}</details></td>"
                   f"<td class=v>{stored}</td><td>{boxes}</td></tr>")
    out.append("</table>")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(out), encoding="utf-8")
    fields = Counter(f for values in wrong.values() for f in values)
    print(f"Wrote {out_file}")
    print(f"Listings with at least one wrong value: {len(wrong)} of {len(rows)}; by field: {dict(fields.most_common())}")


if __name__ == "__main__":
    main()
