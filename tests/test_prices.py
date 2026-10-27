"""
test_prices.py
--------------
Checks how the parser reads prices (task S5): decimals, the different spellings
of "million", "ዋጋ =", and prices per square metre. The texts are shortened
versions of real listings.

Usage:
    venv\\Scripts\\python.exe tests\\test_prices.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from etl_runner import build_processed_values  # noqa: E402
from processor import find_price_per_sqm  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402

P = ValuationPipeline()

# (text, expected sale price, expected price per m² read from the text, expected built-up size)
CASES = [
    # Decimals are kept.
    ("ለሽያጭ ባለ 2 መኝታ አፓርታማ 74 ካሬ ዋጋ 5.5 ሚሊየን ብር ለመረጃ", 5_500_000, None, 74),
    ("አፓርትመንት ሰሚት 65 ካሬ ዋጋ 8.5 ሚሊዮን ብር ለሽያጭ", 8_500_000, None, 65),
    # Other spellings of "million", and "ዋጋ =".
    ("ለሽያጭ የቀረበ አፓርትመንት 71 ካሬ ጠቅላላ ዋጋ = 5.3 ሚልዮን ብር", 5_300_000, None, 71),
    ("አስቸኳይ ሽያጭ ሰሚት አፓርትመንት 65 ካሬ ባለ 2 መኝታ ዋጋ 7 ሚለን 2nd floor", 7_000_000, None, 65),
    ("ለሽያጭ አፓርትመንት 88 ካሬ ዋጋ 9.25 ሚልየን ብር ድርድር አለው", 9_250_000, None, 88),
    # A price per m² is not the total: total = price per m² x size when the size is known.
    ("ለሽያጭ የቀረበ አፓርትመንት 120 ካሬ በካሬ 85,000 ብር ብቻ", 10_200_000, 85_000, 120),
    ("Apartment for sale 139 sqm 75,000 Birr/sqm for cash payers", 10_425_000, 75_000, 139),
    ("Apartment for sale, 3 Bedrooms. Price: 110,000 Birr per sqm", None, 110_000, None),
    ("ለሽያጭ የቀረበ አፓርትመንት በካሬ 110ሺ ብር ቅድመ ክፍያ 20%", None, 110_000, None),
    ("Apartment for sale 2 Bedroom apartments 95,000 – 110,000 Birr per sqm", None, 95_000, None),
    ("ለሽያጭ አፓርትመንት 3 መኝታ ዋጋ (price ) በካሬ = 110ሺ ሁሉም ባለ 3 መኝታ ናቸው", None, 110_000, None),
    ("ለሽያጭ አፓርትመንት G+10 ቅንጡ መኖሪያ 🔰ካሬ ዋጋ =100,000(Fully finished) 🔰በወለል 5 ቤት", None, 100_000, None),
    # Here the 86 m² is stored as plot size (the post says "houses"); the total still uses it.
    ("ለሽያጭ ቤቶች ፒያሳ ✍️የካሬ ዋጋ=61,750ብር ✍️ከ86ካሬ ጀምሮ", 5_310_500, 61_750, None),
    ("ለሽያጭ አፓርትመንት 👉ካሬ ዋጋ Semi 105 - 120ሺ 👉50% ባንክ የተመቻቸለት", None, 105_000, None),
    ("ለሽያጭ አፓርትመንቶች ባለ 3 መኝታ 120,000 ብር በካሬ ቅድመ ክፍያ 20%", None, 120_000, None),
    ("በአያት 49 ባለ 2 መኝታ ለሽያጭ 💥ዋጋ: 65,000/በካሬ 💥 ቅድመ ክፍያ 30%", None, 65_000, None),
    # "M" right after a price word means million.
    ("Shops for sale in front of Adwa Museum. 💰 Price: 3.9M–10M birr 📌 Down Payment: 900K", 3_900_000, None, None),
    # A number under 1,000 after "ዋጋ" is not a sale price.
    ("ለሽያጭ የቀረበ ቪላ ቤት ሰሚት አካባቢ ዋጋ 9.5 ድርድር አለው ይደውሉ", None, None, None),
    ("ለሽያጭ አፓርትመንት ቅናሽ ይህ ዋጋ 100% ለሚከፍሉ ደንበኞች ብቻ ነው", None, None, None),
    # A size followed by a total ("74 m², price 850,000") is not a price per m².
    ("ለሽያጭ ኮንዶሚኒየም 74 ካሬ ዋጋ 850,000 ብር ብቻ ይደውሉ", 850_000, None, 74),
    # When the text gives the total, the total wins.
    ("Apartment for sale. Asking Price: 15,999,000 ብር Total Area: 134 sqm Price per sqm: 119,395 ብር",
     15_999_000, 119_395, 134),
    # Rent per m² is not a sale price.
    ("ሱቅ ለሽያጭ 20 ካሬ ላይ ኢንቨስት ብታደርጉ በወር በካሬ 5,000 ታከራዩታላችሁ", None, None, 20),
    # Sizes like "81 ካሬ" are not "1 ካሬ" (one square metre).
    ("ለሽያጭ 2መኝታ አፓርትመንት 81 ካሬ ዋጋ 5.7 ሚሊዮን ብር", 5_700_000, None, 81),
    # Unchanged: a plain total price.
    ("ለሽያጭ አፓርትመንት 101 ካሬ ዋጋ 12,800,000 ብር", 12_800_000, None, 101),
]


def raw_row(text):
    return type("Row", (), {"id": 1, "text": text, "channel": "https://t.me/test", "posted_at": None,
                            "reply_to_top_id": None, "topic_title": None})()


def main():
    failures = 0
    for text, sale, per_sqm, built in CASES:
        r = P.process({"id": "t", "text": text})
        got = (r["sale_price_birr"], find_price_per_sqm(text), r["builtup_sqm"])
        ok = got == (sale, per_sqm, built)
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} sale={got[0]!s:>10} per_m2={got[1]!s:>7} size={got[2]!s:>4} | {text[:60]}")
        if not ok:
            print(f"      expected sale={sale} per_m2={per_sqm} size={built}")

    # Land: the price per m² applies to the plot.
    land = "ለሽያጭ የቀረበ መሬት ቦታ 300 ካሬ በካሬ 60,000 ብር ካርታ ያለው"
    r = P.process({"id": "t", "text": land})
    ok = (r["property_type"], r["plot_sqm"], r["sale_price_birr"]) == ("LAND", 300, 18_000_000)
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} land: type={r['property_type']} plot={r['plot_sqm']} sale={r['sale_price_birr']}")

    # The stored price per m²: from the total when there is one, else the asking price per m².
    for text, expected in [(CASES[5][0], 85_000), (CASES[7][0], 110_000), (land, None)]:
        values, _, _ = build_processed_values(P, raw_row(text))
        ok = values["price_per_builtup_sqm"] == expected
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} stored price_per_builtup_sqm={values['price_per_builtup_sqm']} | {text[:50]}")
    values, _, _ = build_processed_values(P, raw_row(land))
    ok = values["price_per_plot_sqm"] == 60_000
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} stored price_per_plot_sqm={values['price_per_plot_sqm']} | land")

    print(f"\n{'PASS' if not failures else 'FAILED'}: {len(CASES) + 5 - failures} of {len(CASES) + 5} checks passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
