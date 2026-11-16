r"""
test_units.py
-------------
Checks src/listing_units.py (task S38): one row per unit of a multi-unit advert, on wordings taken
from real developer adverts. Never touches the database.

Usage:
    venv\Scripts\python.exe tests\test_units.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import listing_units as lu  # noqa: E402

failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got!r}" + ("" if ok else f" (expected {expected!r})"))


def short(units):
    return [(u["unit_no"], u["size_sqm"], u["bedrooms"], u["payment_option"], u["price_birr"]) for u in units]


temer = ("65/35 አከፍፈል\n👉 2መኝታ 81 ካሬ ሙሉ ክፍያ 5.7ሚሊዮን\n👉2መኝታ 1ዐ6ካሬ ሙሉ ክፍያ 7.9ሚሊዮን 👉3መኝታ 139ካሬሙሉ ክፍያ 1ዐ.3ሚሊዮን\n"
         "ቀስ ብሎ ለሚከፍል\n2መኝታ 81 ካሬ\n20%ቅድመ ክፍያ 1.86ሚሊዮን\nሙሉ ክፍያ 9.3ሚሊዮን")
check("each unit and payment option; bedrooms before each size", short(lu.extract_units(temer)), [
    (1, 81, 2, "65", 5700000), (1, 81, 2, "slow", 9300000), (2, 106, 2, "65", 7900000), (3, 139, 3, "65", 10300000)])
check("size = price in millions", short(lu.extract_units("📍1Bed\n67kare=8.0\n77kare=9.2\n📍2bed\n112kare=13.4")),
      [(1, 67, 1, "list", 8000000), (2, 77, 1, "list", 9200000), (3, 112, 2, "list", 13400000)])
check("the old price is not a price", short(lu.extract_units(
    "🏠 ባለ ሁለት መኝታ 86 ካሬ\n👉የበፊት ዋጋ = 8.1 ሚልዮን\n👉አሁን 5.1 ሚልዮን\n🏠 ባለ ሶስት መኝታ 106 ካሬ\n👉የበፊት ዋጋ = 10 ሚልዮን\n👉አሁን 6.7 ሚልዮን")),
      [(1, 86, 2, "list", 5100000), (2, 106, 3, "list", 6700000)])
check("one unit is not a multi-unit advert", lu.extract_units("2 መኝታ 90 ካሬ\nዋጋ 10.8 ሚልዮን"), [])
check("a price per m² times a size is not used", lu.extract_units("📏 69 sqm | 72 sqm | 73 sqm\n💰 Price: 115,000 Birr per sqm"), [])
check("the building's footprint is not a unit", short(lu.extract_units(
    "353 ካሬ ላይ ያረፈ ህንፃ 30 ሚሊዮን\n2 መኝታ 90 ካሬ 10.8 ሚልዮን\n3 መኝታ 121 ካሬ 14.5 ሚልዮን")),
      [(1, 90, 2, "list", 10800000), (2, 121, 3, "list", 14500000)])
check("a down payment is not a unit's price", short(lu.extract_units(
    "ባለ 1 መኝታ 96 ካሬ\n🏷️ ጠቅላላ ዋጋ:- 8,160,000 ብር\n🏷️ ቅድመ ክፍያ(10%):- 816,000 ብር\n🛌ባለ 2 መኝታ 161 ካሬ\n🏷️ ጠቅላላ ዋጋ:- 13,685,000 ብር")),
      [(1, 96, 1, "list", 8160000), (2, 161, 2, "list", 13685000)])

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
