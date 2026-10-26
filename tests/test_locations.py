"""
test_locations.py
-----------------
Checks the shared place table (task S6): whole-word matching (Yeka, "22"),
one-way label and hashtag matching (Bole Bulbula), and that the parser, the
topic resolver, the location fixer and the geocoder all give the same codes.

Usage:
    venv\\Scripts\\python.exe tests\\test_locations.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dedup_and_fix_locations import classify_location  # noqa: E402
from geocoder import geocode_location_text  # noqa: E402
from locations import ALIASES, PLACES, RENAMED_CODES, SHEGER, ADDIS, city_of  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402
from topic_resolver import resolve_location  # noqa: E402

P = ValuationPipeline()
failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got!r}" + ("" if ok else f"  (expected {expected!r})"))


# Listing text -> location code, through the parser.
LISTINGS = [
    # Yeka: the word for "per square metre" (የካሬ) contains the letters of Yeka (የካ).
    ("ለሽያጭ አፓርትመንት ቦሌ አካባቢ 120 ካሬ የካሬ ዋጋ 85,000 ብር", "bole_main"),
    ("የካ ክፍለ ከተማ ውስጥ አፓርትመንት ለሽያጭ", "yeka"),
    ("በየካ ክፍለ ከተማ ቪላ ቤት ለሽያጭ", "yeka"),
    # "22" inside a phone number or a size is not the 22 area.
    ("ሰሚት አካባቢ ቤት ለሽያጭ ይደውሉ 0911223344", "summit"),
    ("22 ካሬ ሱቅ ለኪራይ ዋጋ ድርድር አለው", "other_addis"),
    ("ለሽያጭ ቤት 22 ማዞሪያ አካባቢ", "haya_hulet"),
    ("Apartment for sale at Haya Hulet, 3 bedrooms", "haya_hulet"),
    # Labels and hashtags only match names found inside them.
    ("📍Location: Bole\nApartment for sale 3 bedrooms", "bole_main"),
    ("📍Location: Bole Bulbula\nApartment for sale", "bole_bulbula"),
    ("Apartment for sale 3 bedrooms #Bole #RealEstate", "bole_main"),
    ("ቤት ለኪራይ ባለ 2 መኝታ #ቦሌ #ኪራይ", "bole_main"),
    ("Apartment for sale 3 bedrooms #BoleBulbula", "bole_bulbula"),
    ("Apartment for sale 3 bedrooms #Ayat", "ayat_zone"),
    ("Apartment for sale 3 bedrooms #AyatRealEstate", "ayat_zone"),
    # Hashtags that run words together.
    ("Apartment for sale #kazanchisapartmentforsale", "kazanchis"),
    ("ዲጂታል ካርታ አለው #ያለቀአፓርትመንት #ቦሌቡልጋሪያ #ደንበል", "bulgaria"),
    ("ዲጂታል ካርታ አለው #ያለቀአፓርትመንት#22 #ደንበል", "haya_hulet"),
    ("Apartment in Bole #TeamExcellence #MidYearReview", "bole_main"),
    # Holidays are not places: Buhe (ለቡሄ is not ለቡ, Lebu) and Meskel (not Meskel Flower).
    ("እንኳን ለቡሄ በዓል በሰላም አደረሳችሁ", "other_addis"),
    ("Happy holiday #Meskel #Ethiopian", "other_addis"),
    # Amharic prepositions written onto a name.
    ("በቦሌ ቡልቡላ አካባቢ ቪላ ቤት ለሽያጭ", "bole_bulbula"),
    ("ከአያት 49 አጠገብ አፓርትመንት ለሽያጭ", "ayat_49"),
    # Whole words: "Germany" is not German Square.
    ("Villa for sale in Summit, fittings imported from Germany", "summit"),
    # Names the parser did not know before S6 (from the other tables).
    ("ቤት ለሽያጭ ሳልቴ ምህረት አካባቢ", "salite_mehret"),
    ("Apartment for sale Lebu Varnero 2 bedrooms", "lebu_varnero"),
]
for text, expected in LISTINGS:
    check(f"listing  {text[:45]}", P.normalize_location(text), expected)

# Forum topic titles, through the topic resolver.
TOPICS = [
    ("Visco_BoleMeskelFlower(መስቀልፍላወር)", ("meskel_flower", ADDIS)),
    ("MetroHomes_Bole_Harmony Loft", ("bole_michael", ADDIS)),
    ("Damla Realestate ፒያሳ ሱቅ", ("piassa", ADDIS)),
    ("Janbo Realestate Summit Villa", ("summit", ADDIS)),
    ("Champion CMC Apartment", ("cmc_michael", ADDIS)),
    ("Legacy_Green Valley (ጦርሀይሎች)", ("tor_hayloch", ADDIS)),
    ("Sunshine Legetafo Site Villas", ("legetafo", SHEGER)),
]
for title, expected in TOPICS:
    check(f"topic    {title}", resolve_location(title), expected)

# The location fixer uses the same table.
check("fixer    ካሳንቺስ አካባቢ", classify_location("ካሳንቺስ አካባቢ ቢሮ ለኪራይ"), "kazanchis")
check("fixer    የካሬ ዋጋ", classify_location("የካሬ ዋጋ 85,000 ብር ብቻ"), None)

# Cities.
check("city     legetafo", city_of("legetafo"), SHEGER)
check("city     sheger_city", city_of("sheger_city"), SHEGER)
check("city     gelan (counted as Addis, as before)", city_of("gelan"), ADDIS)

# Geocoder: coordinates by code, the wider area's when a place has none, old codes renamed.
g = geocode_location_text("bole_bulbula", use_nominatim=False)
check("geocode  bole_bulbula", (g["lat"], g["lon"], g["confidence"]), (8.98, 38.81, "HIGH"))
g = geocode_location_text("bole_japan", use_nominatim=False)
check("geocode  bole_japan (uses Bole)", (g["lat"], g["lon"], g["confidence"]), (9.005, 38.78, "MEDIUM"))
g = geocode_location_text("22_mazoria", use_nominatim=False)
check("geocode  22_mazoria (old code)", g["matched_name"], "haya_hulet")
check("geocode  other_addis", geocode_location_text("other_addis", use_nominatim=False), None)

# Every code used anywhere is a known place.
check("every alias points to a known place", sorted({c for _, c in ALIASES} - set(PLACES)), [])
check("every renamed code points to a known place", sorted(set(RENAMED_CODES.values()) - set(PLACES)), [])

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
