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
    # "ሙሉ ክፍያ" (full payment) is a price word.
    ("ለሽያጭ 2መኝታ አፓርትመንት 81 ካሬ ሙሉ ክፍያ 5.7ሚሊዮን", 5_700_000, None, 81),
    # A monthly income or a down payment is not the sale price.
    ("ለሽያጭ የቀረበ ቪላ ቤት ቦሌ 300 ካሬ 180,000 ብር ገቢ ያለው ይደውሉ", None, None, None),
    ("ለሽያጭ አፓርትመንት 100 ካሬ ቅድመ ክፍያ 2,262,000 ብር ቀሪው በባንክ", None, None, 100),
    # ...but a total stays the total, even when "down payment" follows it.
    ("ለሽያጭ አፓርትመንት 💰 በ ጠቅላላ ክፍያ 6,800,000ብር በ ቅድመ ክፍያ 2,000,000 ብር", 6_800_000, None, None),
    ("ለሽያጭ ባለ 1መኝታ 💸ጠቅላላ = 7,014,000ብር 💸15% ቅድመክፍያ = 1,052,122.5 ብር", 7_014_000, None, None),
    # "ጠቅላላ 1000 ካሬው ነው" (in total 1000 m²) is a size, not a price.
    ("መሬት ለሽያጭ የሚሸጠው ጠቅላላ 1000 ካሬው ነው ዋጋ 50 ሚልዮን ካርታ ያለው", 50_000_000, None, None),
    # When the text gives the total, the total wins.
    ("Apartment for sale. Asking Price: 15,999,000 ብር Total Area: 134 sqm Price per sqm: 119,395 ብር",
     15_999_000, 119_395, 134),
    # Rent per m² is not a sale price.
    ("ሱቅ ለሽያጭ 20 ካሬ ላይ ኢንቨስት ብታደርጉ በወር በካሬ 5,000 ታከራዩታላችሁ", None, None, 20),
    # Sizes like "81 ካሬ" are not "1 ካሬ" (one square metre).
    ("ለሽያጭ 2መኝታ አፓርትመንት 81 ካሬ ዋጋ 5.7 ሚሊዮን ብር", 5_700_000, None, 81),
    # Unchanged: a plain total price.
    ("ለሽያጭ አፓርትመንት 101 ካሬ ዋጋ 12,800,000 ብር", 12_800_000, None, 101),
    # S12: a rent, a rental income or a remaining balance is not the sale price.
    ("የሚሸጥ አፓርትመንት 141 ካሬ ቤቱ አሁን ላይ 120,000 ብር ድረስ ይከራያል የሽያጭ ዋጋ 24,999,000 ብር", 24_999_000, None, 141),
    ("ለሽያጭ ባለ1 መኝታ ኮንዶሚኒየም 🌀52ካሬ 🌀30,000 ብር የሚከራይ 💰..የመሸጫ ዋጋ 🔹በካሽ 5.7 ሚሊየን ብር 🔹በባንክ 6 ሚሊየን ብር",
     5_700_000, None, 52),
    ("የሚሸጥ ሱቅ 70 ካሬ 🌀 ቀሪ 550,000 ብር ክፍያ አለው 💰.. የመሸጫ ዋጋ ለእጁ 4.6 ሚሊየን ብር", 4_600_000, None, 70),
    # ...broker headings give the price after a dash, with no price word:
    ("KAZANCHIES : HILTON – 24,999,000 - 3 Beds | 2 Baths | 1F | 141 sqm - Rented Furnished: 120,000 ብር / months "
     "#አከፋፈል ካሽ (በገዢ በኩል)", 24_999_000, None, 141),
    ("ቦሌ : ጌቱ ጀርባ ° 19,999,000 - 3 Beds / 2 Baths / 6F / 137 sqm - ቤቱ አሁን ላይ 120,000 ብር ተከራይቶ ነው የሚገኘው። "
     "ገዢን", 19_999_000, None, 137),
    ("Figa: Noah Real-Estate ° 9.8 million - 2 beds / 2 baths / 5F / 72 sqm - የመከራየት አቅማቸው ከ40,000 ብር በላይ ነው።",
     9_800_000, None, 72),
    # ...an old price is not the price: "ዋጋው 19 ሚሊዮን ነበር" (the price was 19 million).
    ("ለሽያጭ የቀረበ አፓርትመንት ዋጋው 19 ሚሊዮን ነበር አሁን ለሽያጭ የወጣው 14,560,000 ብር ነው።", 14_560_000, None, None),
    # Other ways of writing the price: "6,400 000", dots, decorative digits, "55,000,000 ሚሊዮን".
    ("የሚሸጥ 40/60 ቤት አያት ሳይት 4 🥢ስፋት 72ካሬ 🥢ደረጃ 9 🥢ዋጋ 6,400 000 ብር ጥሪ", 6_400_000, None, 72),
    ("የሚሸጥ G+2 መኖሪያ ቤት ፋት: 301 m² ዋጋ ....................... 59 ሚልዮን ቀርበው ይደራደሩ", 59_000_000, None, None),
    ("only Fully Finished Apartment Bole Bulbula 3 Beds • 7Floor • 154 sqm 𝟭𝟳,𝟰𝟵𝟵,𝟬𝟬𝟬 𝗘𝗧𝗕 for sale",
     17_499_000, None, 154),
    ("የሚሸጥ G+3 ህንፃ 150 M2 180,000 ብር ገቢ ያለው Mixed used building 55,000,000 ሚሊዮን ብር", 55_000_000, None, None),
    # Cash plus the seller's bank loan that the buyer takes over is the price.
    ("ለሽያጭ ኮንዶሚኒየም 86 ካሬ 👉1,500,000 ብር ካሽ ( ለእጅ ) 👉5,000,000 ብር ባንክ 🔹የወር የባንክ ተመላሽ 38,000 ብር",
     6_500_000, None, 86),
    ("የሚሸጥ አፓርትመንት 175 ካሬ ባንክ 10 ሚሊዮን ብር አለበት ካሽ 5,500,000 ብር 👉160 ሺ ብር በወር የባንክ ተመላሽ",
     15_500_000, None, 175),
    # More ways of giving a price per m²: "እስከ" (to), words before the number, "Price/m²".
    # ("ከ 2.5 ሚልዮን … ጀምሮ", from 2.5 million, is the cheapest unit of all sites, not this one.)
    ("የንግድ ሱቅ ለሽያጭ 80 ካሬ 🏦 ዋጋ በካሬ 95,000 እስከ 115,000 ብር 👉 ቅድመ ክፍያ 10% ጀምሮ + ከ 2.5 ሚልዮን ሙሉ ክፍያ ጀምሮ",
     7_600_000, 95_000, 80),
    # Several buildings in one post: the first price is read, also after "monthly income".
    ("1, Around 22 plot 200 m² Built-up 130 m² G+4 Guesthouse for sale 500,000 birr monthly income price 65 million "
     "negotiable 2, Around Saris 300 m2 G+5 Guesthouse price 270 million", 65_000_000, None, 130),
    ("ለሽያጭ ባለ 1መኝታ አፓርትመንት 60 ካሬ 👉የመሽጫ ዋጋ በካሬ semi finished 95,000ብር በካሬ fully finished 105,000ብር",
     5_700_000, 95_000, 60),
    ("Keraniyo Apartment for sale 2BR: 100 m² – 4th Floor 💰 Price/m²: 140,000 ETB – Fully Finished", 14_000_000,
     140_000, 100),
    # A size is the whole number: "158.72 ካሬ" is 158 m², not 72.
    ("ለሽያጭ አፓርትመንት 158.72 ካሬ ባለ ሁለት መኝታ 17ኛ ፎቅ ጠቅላላ ዋጋ 16,864,000 ብር", 16_864_000, None, 158),
    # ...and the number after "sqm" is not a size.
    ("Apartment for sale Bole 3 Beds / 3 Baths / 189 sqm 29,999,000 Birr", 29_999_000, None, 189),
    # Dollars are not birr: news of a "150 ሚሊዮን ዶላር" (150 million dollar) auction.
    ("ብሔራዊ ባንክ የ150 ሚሊዮን ዶላር ልዩ የውጭ ምንዛሬ ጨረታ ሊያካሂድ ነው ሽያጭ", None, None, None),
]

# Rentals: the rent is the rent, and a rental has no sale price.
# (text, expected intent, rent)
RENTALS = [
    ("Apartment for rent Location: Kazanchis Bedroom:3 Price:100,000 birr", "RENT", 100_000),
    ("Furnished Apartment for rent Location:Shola Bedrooom:2 Price:100,000 per month", "RENT", 100_000),
    ("🏡 RENT🏡 💰Price (USD): 1780 📍Area:Bole 🏠Type: Office for rent", "RENT", None),
    ("ለኪራይ የቀረበ ባለ1 መኝታ 40/60 🔹58 ካሬ 👉👉..የኪራይ ዋጋ 30,000 ብር ✅ ሲከራዩ 10% ኮሚሽን ይከፍሉናል", "RENT", 30_000),
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

    # A rent next to its advance is still the rent.
    r = P.process({"id": "t", "text": "ቤት ለኪራይ ባለ 2 መኝታ ኪራይ 25,000 ብር 3 ወር ቅድሚያ ይጠየቃል"})
    ok = r["rent_price_birr"] == 25_000
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} rent next to its advance: rent={r['rent_price_birr']}")

    for text, intent, rent in RENTALS:
        r = P.process({"id": "t", "text": text})
        got = (r["intent"], r["rent_price_birr"], r["sale_price_birr"])
        ok = got == (intent, rent, None)
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} rental: intent={got[0]} rent={got[1]} sale={got[2]} | {text[:50]}")

    # A labelled plot size is the plot ("የቦታ ስፋት" = size of the plot), also for a G+3 house.
    r = P.process({"id": "t", "text": "ልዩ የመኖሪያ ዕድል በመገናኛ 📐 የቦታ ስፋት፦ 930 ካሬ ሜትር 🏢 የቤቱ ሁኔታ፦ G+3 የሆነ ቤት "
                                      "የሽያጭ ዋጋ፦ 💰 400 ሚሊዮን ብር #rohaapartment"})
    ok = (r["property_type"], r["plot_sqm"], r["builtup_sqm"]) == ("VILLA", 930, None)
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} plot size: type={r['property_type']} plot={r['plot_sqm']} built={r['builtup_sqm']}")

    checks = len(CASES) + 7 + len(RENTALS)
    print(f"\n{'PASS' if not failures else 'FAILED'}: {checks - failures} of {checks} checks passed.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
