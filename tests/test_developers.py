r"""
test_developers.py
------------------
Checks src/developers.py (task S40): one name per developer, and places or ordinary words are not
developers. Never touches the database.

Usage:
    venv\Scripts\python.exe tests\test_developers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from developers import find_developer  # noqa: E402

failures = 0


def check(label, text, expected, channel=None, topic=None):
    global failures
    got = find_developer(text, channel, topic)[0]
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got!r}" + ("" if ok else f" (expected {expected!r})"))


# One name for every spelling.
check("ቴምር", "ከ #ቴምር ሪልስቴት ይግዙ", "Temer Real Estate")
check("Temer properties", "Miki at Temer Properties", "Temer Real Estate")
check("ሪያሊቲ ሪልእስቴት", "ሪያሊቲ ፓላስ ቪው ፕሮጀክት ሪያሊቲ ሪልእስቴት reality", "Reality Real Estate")
check("ዲ ኤም ሲ", "መጭውን የገና በዓል ምክንያት በማድረግ ዲ ኤም ሲ ሪል እስቴት", "DMC Real Estate")
check("DMC", "DMC Real Estate - Joy Start", "DMC Real Estate")
check("ጃምቦ and Janbo", "ስለ ጃምቦ ሪል እስቴት", "Jambo Real Estate")
check("a forum topic", "Janbo Realestate\nባለ 3 መኝታ", "Jambo Real Estate")
check("ፓልም", "ከፓልም ሪል እስቴት(Palm Real Estate)", "Palm Real Estate")
check("Zeramba spelled two ways", "#Zeramba_City Breeze", "Zeramba Real Estate")
check("ደማ ሆፕ", "አንዱ የሆነው ደማ ሆፕ", "Dema Hope Real Estate")
check("the developer's own channel", "ባለ 3 መኝታ 121 ካሬ", "Temer Real Estate", channel="https://t.me/TemerApartmentShop")
check("Ayat's own channel", "ዘመናዊ ህይወት በዘመናዊ ቤት", "Ayat Real Estate", channel="https://t.me/ApartmentForYouAyatRealEstate")

# A place or a word is not a developer.
check("Ayat the place", "የሚሸጥ ቦታ አያት 49 አካባቢ 150 ካሬ", None)
check("Ayat the place, in English", "Apartment for sale at Ayat, 3 bedrooms", None)
check("Ayat the developer", "አንጋፋውና ስመ ገናናዉ አያት አክሲዮን ማህበር", "Ayat Real Estate")
check("Ayat Real Estate", "ከአያት ሪል እስቴት ትልቅ አጋጣሚ", "Ayat Real Estate")
check("Gerji Sunshine, a compound", "ቤቱ የሚገኘው ገርጂ ሰንሻይን", None)
check("Lafto, a place", "ላፍቶ 120 ካሬ ቦታ", None)
check("a gift", "🎁 a special gift for our customers", None)
check("prime location", "prime location in Bole", None)
check("a sentence before real estate", "everyone has an opinion about real estate", None)
check("our real estate", "join our real estate family", None)

# A developer not in the list: the words before "real estate".
check("Eniy Realestate", "Eniy realestate ቡልቡላ compund", "Eniy Real Estate")
check("an unknown developer", "Habesha Gate Real Estate presents", "Habesha Gate Real Estate")
check("the first developer named", "Temer and Gift real estate", "Temer Real Estate")

# Forum topics: championallsites names them "Developer_Project (place)".
check("a known developer in the topic", "[MEDIA ONLY]", "Legacy Real Estate", topic="Legacy_Green Valley (ጦርሀይሎች)")
check("Prime in a topic", "[MEDIA ONLY]", "Prime Real Estate", topic="Prime_Bole Japan Apartment (ቦሌ ጃፓን)")
check("an unknown developer's topic", "[MEDIA ONLY]", "Mansion Real Estate", topic="Mansion_PalaceOne(ጌቱ ኮሜርሻል ጀርባ)")
check("sold-out marks are left out", "[MEDIA ONLY]", "HD Real Estate", topic="(Sold Out) HD_CityCenter(ጌቱ ጀርባ)")
check("the topic's developer before one the post names", "Temer also sells nearby", "Nexus Real Estate", topic="Nexus_Sunset (ለቡ ቫርኔሮ)")
check("a topic without a developer", "[MEDIA ONLY]", None, topic="Resale")
check("Metro's Bulbula compound", "ባለ 3 መኝታ", "MetroHomes", topic="Metro ቡልቡላ compund")
check("AL-SAM PROPERTIES", "why alsam? 1–3 bedroom apartments AL-SAM PROPERTIES", "Alsam Properties")
check("Prime Hotel is not Prime Real Estate", "🏨 Prime Hotel for Sale in Bole", None)

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
