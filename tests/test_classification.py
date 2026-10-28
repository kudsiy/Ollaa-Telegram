"""
test_classification.py
----------------------
Checks how posts are classified (task S7): a web link does not make a listing
noise, and a photo-only post waits as MEDIA_PENDING instead of being called an
advert. Task S12: a sale advert that mentions rent or income stays a sale, a
channel footer decides nothing, and houses, flats, buildings and land get their
own type. The texts are shortened versions of real listings.

Usage:
    venv\\Scripts\\python.exe tests\\test_classification.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from etl_runner import build_processed_values  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402

P = ValuationPipeline()
FIELDS = ("listing_class", "intent", "property_type", "location", "sale_price_birr")

# (text, expected listing_class, intent, property_type, location, sale price)
CASES = [
    # Photo-only posts (the scraper stores "[MEDIA ONLY]" when a post has no words).
    ("[MEDIA ONLY]", ("MEDIA_PENDING", "UNKNOWN", "MEDIA_LINK", "noise", None)),
    ("[PDF ONLY] brochure.pdf", ("MEDIA_PENDING", "UNKNOWN", "MEDIA_LINK", "noise", None)),
    # ...in a forum topic whose title names the place.
    ("Janbo Realestate Summit Villa\n[MEDIA ONLY]", ("MEDIA_PENDING", "UNKNOWN", "MEDIA_LINK", "summit", None)),
    # A real listing with a link is read like any other listing.
    ("ለሽያጭ አፓርትመንት ቦሌ 120 ካሬ ዋጋ 12,800,000 ብር ለበለጠ መረጃ https://t.me/somechannel",
     ("PURE_SALE", "SALE", "APARTMENT", "bole_main", 12_800_000)),
    ("https://t.me/somechannel\nለሽያጭ አፓርትመንት ሰሚት 3 መኝታ 150 ካሬ ዋጋ 9.5 ሚሊዮን ብር",
     ("PURE_SALE", "SALE", "APARTMENT", "summit", 9_500_000)),
    # A post that is only a link, or a few words and a link, is still noise.
    ("https://www.youtube.com/watch?v=abcdefghijk", ("ADVERTISEMENT", "ADVERT", "MEDIA_LINK", "noise", None)),
    ("Join us https://t.me/xyz", ("ADVERTISEMENT", "ADVERT", "MEDIA_LINK", "noise", None)),
    # Unchanged: a short greeting is noise, a normal listing is a listing.
    ("እንኳን አደረሳችሁ", ("ADVERTISEMENT", "ADVERT", "ADVERTISEMENT", "noise", None)),
    ("ለሽያጭ አፓርትመንት 101 ካሬ ዋጋ 12,800,000 ብር ቦሌ አካባቢ", ("PURE_SALE", "SALE", "APARTMENT", "bole_main", 12_800_000)),
    # S12: a sale advert that mentions rent or income is a sale.
    # ...the channel footer lists "ኪራይ / ሽያጭ" (rent / sale) services:
    ("የሚሸጥ ዘመናዊ ቤት 🔷 ቦታ= ጀሞ1 🔷የቤቱ ስፋት=72 ካሬ 🔷ደረጃ=4ኛ ላይ 🔷 ባለ 2 መኝታ 🔷 ዋጋ=6.5 ሚ ብር 🌏 ለ ክቡራን "
     "ደንበኞቻችን ከዚህ በታች የተዘረዘሩትን አገልግሎቶች እንሰጣለን 1-ኮንዶሚየም ቤት ኪራይ / ሽያጭ 2- G++ መኖሪያ ቤት ኪራይ/ሽያጭ",
     ("PURE_SALE", "SALE", "APARTMENT", "jemo", 6_500_000)),
    # ...the building's income ("በወር … ገቢ", income per month):
    ("ልዩ የኢንቨስትመንት ዕድል - በላፍቶ ዋና አስፓልት ላይ የሚገኝ G+6 ህንፃ! ከፍተኛ ገቢ፦ በወር ከ 500,000 ብር በላይ ገቢ "
     "ያስገኝልዎታል 💰 ዋጋ፦ 150,000,000 (150 ሚሊየን) ብር — ድርድር አለው",
     ("PURE_SALE", "SALE", "COMMERCIAL_BUILDING", "lafto", 150_000_000)),
    # ...the estimated rent in an investment analysis:
    ("Commercial Space for Sale – High Income Potential Bole : Rwanda – 65,600,000 ብር - 328 sqm [1st Floor ] "
     "የተገመተ የኪራይ ዋጋ በካሬ: 2,500 – 3,500 ብር / sqm",
     ("PURE_SALE", "SALE", "COMMERCIAL", "bole_rwanda", 65_600_000)),
    # ...a rent level, after the advert said it is for sale:
    ("ለሽያጭ የቀረበ ባለ2 መኝታ ኮንደሚኒየም ቤት በዊንጌት 71ካሬ ባንክ 3 ሚሊዮን ብር አለበት ካሽ 4,700,000 ብር አጠቃላይ ዋጋ "
     "7,700,000 ብር ነው ወርሃዊ ተመላሽ 30,000 ብር ነው የሰፈሩ የኪራይ ዋጋ አሁን ላይ ከ 25ሺ እስከ 28ሺ ነው",
     ("PURE_SALE", "SALE", "CONDOMINIUM", "wingate", 7_700_000)),
    # ...no sale or rent words at all, but no home rents for 21 million birr a month:
    ("MOVE-IN READY LUXURY IN MEXICO! 124 SQM of pure elegance Fully Furnished 16th Floor Views "
     "Price: 21,000,000 ETB (Furniture included!)",
     ("PURE_SALE", "SALE", "APARTMENT", "mexico", 21_000_000)),
    # A rental is still a rental, and its price is the rent, never a sale price.
    ("Apartment for rent Location: Kazanchis Bedroom:3 Price:100,000 birr",
     ("PURE_RENT", "RENT", "APARTMENT", "kazanchis", None)),
    ("#ኮድ_3251 ለኪራይ የቀረበ ባለ1 መኝታ 40/60 በቦሌ ቡልቡላ 🔹58 ካሬ 🔹8ኛ ፍሎር 👉👉..የኪራይ ዋጋ 30,000 ብር ✅ ሲከራዩ 10% "
     "ኮሚሽን ይከፍሉናል የሚሸጥ ቤት መኪና🏠🚙 ካሎት በቴሌግራም ይላኩልን",
     ("PURE_RENT", "RENT", "CONDOMINIUM", "bole_bulbula", None)),
    # Types. A G+2 house with 8 bedrooms is a villa (the footer's "አፓርታማ" says nothing):
    ("ኮድ*** 175 የሚሸጥ g+2 ፎቅ 170 ካሬ ሜትር መገናኛ ሴንቼሪ ሞል አካባቢ 8 መኝታ እና 6 ባኞ ቤት ያለው ዋጋ 50 million "
     "========= የህንፃ ፣ የቪላ እና አፓርታማ ቤቶችን ብቻ ለማየት",
     ("PURE_SALE", "SALE", "VILLA", "megenagna", 50_000_000)),
    ("#ኮድ_3250 ለሽያጭ የቀረበ ዘመናዊ ጂ+2 በአያት 🔹330ካሬ 🔹6 መኝታ ቤቶች 💰..የመሸጫ ዋጋ 55 ሚሊየን ብር",
     ("PURE_SALE", "SALE", "VILLA", "ayat_zone", 55_000_000)),
    # ...a flat in a G+12 building is a flat, not a commercial building:
    ("KAZANCHIES : HILTON – 24,999,000 - 3 Beds | 2 Baths | 1F | 141 sqm - #አፓርመንቱ የሚገኘው ካሳንቺስ ሂልተን "
     "አካባቢ B+G+12 ሆኖ በተገነባ ህንፃ ነው። Rented Furnished: 120,000 ብር / months #አከፋፈል ካሽ (በገዢ በኩል)",
     ("PURE_SALE", "SALE", "APARTMENT", "kazanchis", 24_999_000)),
    # ...a whole building for sale is a commercial building ("B2 + G + 8"):
    ("በፒያሳ ለኢንቨስትመንት ተመራጭ የሆነ ድንቅ ህንፃ ለሽያጭ አቅርበናል። የወለል ብዛት፦ B2 + G + 8 የቦታ ስፋት፦ 450 ካሬ "
     "ያሉ አማራጮች (ባለ 3 መኝታ)፦ ሰፊ ቤቶች፦ 165 እና 167 ካሬ 💰ዋጋ 250 ሚልየን ብር ድርድር አለው",
     ("PURE_SALE", "SALE", "COMMERCIAL_BUILDING", "piassa", 250_000_000)),
    # ...land "for apartment builders" is land:
    ("ለአፓርታማ ገንቢዎች በጣም ምርጥ ቦታ 460 ካሬ ቦታ/ዲጂታል ካርታ 22 አክሱም ሆቴል አካባቢ ዋጋ 47 ሚሊዮን ብር",
     ("PURE_SALE", "SALE", "LAND", "other_addis", 47_000_000)),
    # ...a house whose rooms include a "store" is not a warehouse:
    ("Bole: Mega Area 3 Beds / 3 Baths / 2 kitchens / laundry / store / 5 Floors / 189 sqm 29,999,000 Birr "
     "It is a well-constructed house.",
     ("PURE_SALE", "SALE", "VILLA", "bole_main", 29_999_000)),
    # Adverts for shares in a real-estate company are adverts, not listings.
    ("አያት አክሲዮን ማህበር እጅግ ከፍተኛ ትርፍ የሚያስገኘዉን የአክሲዮን ሽያጭ መጀመሩን ሰምተዋል? የአንድ አክሲዮን ዋጋ 100 ብር",
     ("ADVERTISEMENT", "SALE", "ADVERTISEMENT", "ayat_zone", None)),
]

failures = 0
for text, expected in CASES:
    r = P.process({"id": "t", "text": text})
    got = tuple(r[f] for f in FIELDS)
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {got} | {text[:50]!r}")
    if not ok:
        print(f"      expected {expected}")

# The ETL's channel rule still applies: Bet_afri photo posts are rentals.
def channel_row(text, channel):
    return type("Row", (), {"id": 1, "text": text, "channel": f"https://t.me/{channel}", "posted_at": None,
                            "reply_to_top_id": None, "topic_title": None})()


values, _, _ = build_processed_values(P, channel_row("[MEDIA ONLY]", "Bet_afri"))
ok = (values["listing_class"], values["intent"]) == ("MEDIA_PENDING", "RENT")
failures += not ok
print(f"{'ok  ' if ok else 'FAIL'} Bet_afri photo post: {values['listing_class']}, {values['intent']}")

# Bet_afri lists single rooms; Bet_afri_Business lists offices and shops.
room = "የሚከራይ ክፍል ሳርቤት አካባቢ ኪራይ 6,000 ብር ውሃ መብራት ያለው"
office = "ቢሮ ለኪራይ ቦሌ አካባቢ 120 ካሬ ኪራይ 60,000 ብር በወር"
for text, channel, expected in [(room, "Bet_afri", ("RENT", "SINGLE_ROOM")),
                                (office, "Bet_afri_Business", ("RENT", "OFFICE"))]:
    values, _, _ = build_processed_values(P, channel_row(text, channel))
    got = (values["intent"], values["property_type"])
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {channel} post: {got}" + ("" if ok else f"  (expected {expected})"))

# S12: a whole compound on Bet_afri is a house; "ንግድ ክፍል … አንድ ሚሊዮን" (commercial part ... one
# million) is a building, not a single room ("አንድ ክፍል").
compound = "🔥የሚከራይ ሙሉ ግቢ🔥 ▫️CODE BT 1323 🟢 ኪራይ፡ 25,000 ብር 🟢 ባለሁለት መኝታ (200 ካሬ፣ ሴራሚክ)"
building = ("መርካቶ ላይ የገቢ ምንጭ የሚሆን የህንፃ ባለቤት ይሁኑ! በወር 1,000,000 (አንድ ሚሊዮን) ብር ገቢ ያስገኝልዎታል! ዘመናዊ G+7 "
            "ህንፃ። የቦታው ስፋት፦ 287 ካሬ ሜትር ንግድ ክፍል (G-3)፦ ለሱቆች የተከራየ። የሽያጭ ዋጋ፦ 250 ሚሊዮን ብር")
for text, channel, expected in [(compound, "Bet_afri", ("RENT", "VILLA", None)),
                                (building, "smartdealers", ("SALE", "COMMERCIAL_BUILDING", 250_000_000))]:
    values, _, _ = build_processed_values(P, channel_row(text, channel))
    got = (values["intent"], values["property_type"], values["sale_price_birr"])
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {channel} post: {got}" + ("" if ok else f"  (expected {expected})"))

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
