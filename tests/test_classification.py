"""
test_classification.py
----------------------
Checks how posts are classified (task S7): a web link does not make a listing
noise, and a photo-only post waits as MEDIA_PENDING instead of being called an
advert.

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
row = type("Row", (), {"id": 1, "text": "[MEDIA ONLY]", "channel": "https://t.me/Bet_afri", "posted_at": None,
                       "reply_to_top_id": None, "topic_title": None})()
values, _, _ = build_processed_values(P, row)
ok = (values["listing_class"], values["intent"]) == ("MEDIA_PENDING", "RENT")
failures += not ok
print(f"{'ok  ' if ok else 'FAIL'} Bet_afri photo post: {values['listing_class']}, {values['intent']}")

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
