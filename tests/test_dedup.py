r"""
test_dedup.py
-------------
Checks the rules of src/dedup_strict.py with made-up listings: repeats are found, and
different properties on one broker's template, or a changed price, never are. Never
touches the database.

Usage:
    venv\Scripts\python.exe tests\test_dedup.py
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import dedup_strict as ds  # noqa: E402

failures = 0


def row(id_, text, **values):
    base = dict(id=id_, raw_text=text, intent="SALE", listing_class="PURE_SALE", property_type="APARTMENT",
                location="jemo", sale_price_birr=None, rent_price_birr=None, builtup_sqm=None, plot_sqm=None,
                bedrooms=None, bathrooms=None, floor_level=None, posted_at=None, price_currency="ETB", topic_title=None)
    return SimpleNamespace(**{**base, **values})


def check(label, rows, removed, protected=(), kept=None):
    global failures
    plan, _ = ds.plan(rows, set(protected))
    got = sorted(i for i, _, _ in plan)
    ok = got == sorted(removed) and (kept is None or {k for _, k, _ in plan} == {kept})
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: removes {got}" + ("" if ok else f" (expected {sorted(removed)})"))


FLAT = "የሚሸጥ ዘመናዊ ቤት ቦታ ጀሞ {place} የቤቱ ስፋት {size} ካሬ ባለ 2 መኝታ ሙሉ ሴራሚክ ዋጋ {price} ሚ ብር"
one = dict(sale_price_birr=6_500_000, builtup_sqm=72, bedrooms=2)

check("same words, different phone and hashtags",
      [row("1", "ቦሌ አፓርታማ ለሽያጭ 120 ካሬ ዋጋ 9 ሚሊዮን ብር 0911000000 #Bole"),
       row("2", "ቦሌ አፓርታማ ለሽያጭ 120 ካሬ, ዋጋ 9 ሚሊዮን ብር! 0922000000 #Sale")], ["1"])
check("same facts in two channels with other words",
      [row("1", "አፓርታማ ጀሞ አንደኛ ምርጥ ቤት", **one), row("2", "Modern flat for sale at Jemo with parking", **one)], ["1"])
check("the Jemo pair the old script would have merged: different size and price",
      [row("1", FLAT.format(place=3, size=47, price=4), sale_price_birr=4_000_000, builtup_sqm=47),
       row("2", FLAT.format(place=1, size=40, price=4.1), sale_price_birr=4_100_000, builtup_sqm=40)], [])
check("a changed price is not removed",
      [row("1", FLAT.format(place=1, size=72, price=6.5), sale_price_birr=6_500_000, builtup_sqm=72),
       row("2", FLAT.format(place=1, size=72, price=8.5), sale_price_birr=8_500_000, builtup_sqm=72)], [])
check("same facts but different bedrooms",
      [row("1", "ምርጥ ቤት አንድ", **one), row("2", "ሌላ ቤት ሁለት", **{**one, "bedrooms": 3})], [])
check("same facts but different floors",
      [row("1", "ምርጥ ቤት አንድ", floor_level=2, **one), row("2", "ሌላ ቤት ሁለት", floor_level=5, **one)], [])
check("same facts, the floor only in the words: 3floor and 5floor",
      [row("1", "Bole Denbel 3 Beds 3floor 165sqm", **one), row("2", "Bole Denbel 3 Beds 5floor 165sqm", **one)], [])
check("same facts, ground floor and 3rd floor",
      [row("1", "ጀሞ1 ደረጃ=00/ ግራውንድ ላይ", **one), row("2", "ጀሞ1 ሌላ ቤት 3ኛ ፎቅ ላይ", **one)], [])
check("ground parking is not the ground floor",
      [row("1", "ግራውንድ የመኪና ማቆሚያ 3ኛ ፎቅ አለው", **one), row("2", "ሌላ ቤት 3ኛ ፎቅ ላይ ነው", **one)], ["1"])
check("a broker's template with another code and room size",
      [row("1", "የሚከራይ ቤት CODE BT 1222 ኪራይ 10,000 ብር አንድ ክፍል 3.5X3.5 ሊሾ ወለል ብሎኬት ግቢ ውስጥ ሰፈሩ ሲኤምሲ ሚካኤል ከመገናኛ አንድ ታክሲ",
           intent="RENT", property_type="SINGLE_ROOM", rent_price_birr=10_000),
       row("2", "የሚከራይ ቤት CODE BT 1307 ኪራይ 10,000 ብር አንድ ክፍል 4X4 ሊሾ ወለል ብሎኬት ግቢ ውስጥ ሰፈሩ ሲኤምሲ ሚካኤል ከመገናኛ አንድ ታክሲ",
           intent="RENT", property_type="SINGLE_ROOM", rent_price_birr=10_000)], [])
check("same facts but no named place",
      [row("1", "ምርጥ ቤት አንድ", **one), row("2", "ሌላ ቤት ሁለት", **{**one, "location": "other_addis"})], [])
check("same facts, place unknown for both",
      [row("1", "ምርጥ ቤት አንድ", **{**one, "location": "other_addis"}),
       row("2", "ሌላ ቤት ሁለት", **{**one, "location": "other_addis"})], [])
check("photo-only posts are never repeats",
      [row("1", "[MEDIA ONLY]", listing_class="MEDIA_PENDING"), row("2", "[MEDIA ONLY]", listing_class="MEDIA_PENDING")], [])
check("same words in different forum topics are different projects",
      [row("1", "3bed 148ካሬ 15,5Mill ለሽያጭ", topic_title="A"), row("2", "3bed 148ካሬ 15,5Mill ለሽያጭ", topic_title="B")], [])
check("a protected listing is the one kept",
      [row("1", "ምርጥ ቤት አንድ", **one), row("2", "ሌላ ቤት ሁለት", **one)], ["2"], protected=["1"], kept="1")
check("two protected listings both stay",
      [row("1", "ምርጥ ቤት አንድ", **one), row("2", "ሌላ ቤት ሁለት", **one)], [], protected=["1", "2"])
check("the listing with more details is the one kept",
      [row("1", "ምርጥ ቤት አንድ", bathrooms=2, **one), row("2", "ሌላ ቤት ሁለት", **one)], ["2"], kept="1")

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
