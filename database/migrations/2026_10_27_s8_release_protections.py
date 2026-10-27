"""
2026_10_27_s8_release_protections.py
------------------------------------
One-time change for task S8: the owner's review of the legacy protections.

After S5-S7 the parser agreed with most values protected when S4 switched
protection on; those retire by themselves in reprocess.py. This script handles
the protected values that still disagree with the parser. Each one gets a
decision by the rules below, which the owner approved on 27 Oct 2026:
'release' (delete the protection, so re-processing writes the parser's value)
or 'keep' (the protected value stays). Nothing in processed_listings changes
here; run reprocess.py afterwards.

Usage (take a backup first, see CLAUDE.md):
    venv\\Scripts\\python.exe database\\migrations\\2026_10_27_s8_release_protections.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_27_s8_release_protections.py --apply
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from etl_runner import build_processed_values  # noqa: E402
from locations import ALIASES, PLACES  # noqa: E402
from protection import LEGACY_REASON, from_text, same_value  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402
from settings import DB_URL  # noqa: E402

# The split the owner approved; --apply refuses to delete anything else.
APPROVED = {"release": 922, "keep": 829}

NONE = {None, "UNKNOWN", "other_addis", "noise"}
RENT_CHANNELS = ("Bet_afri", "Betafrivip")   # rent-only channels (src/channels.py)
NOT_COMPARABLES = ("ADVERTISEMENT", "INQUIRY", "INVALID", "MEDIA_PENDING")
FIGURES = ("sale_price_birr", "builtup_sqm", "plot_sqm", "property_subtype",
           "bedrooms", "floor_level", "rent_price_birr")
# Checked by hand: the protected price was the cash part (2479: cash 40M of a 75M
# total) or the price of another unit in the same post (1143: 13.6M three-bedroom,
# cut by the old decimal bug, on the 48 m² one-bedroom listing).
CHECKED_BY_HAND = {("2479", "sale_price_birr"): "release", ("1143", "sale_price_birr"): "release"}

_names = defaultdict(set)
for _alias, _code in ALIASES:
    _names[_code].add(re.sub(r"\s", "", _alias.lower()))
for _code, _place in PLACES.items():
    _names[_code].add(re.sub(r"\W", "", _place.name.lower()))


def _squeeze(t):
    return re.sub(r"[\s_]", "", (t or "").lower())


def decide(listing_id, field, protected, parser, text_, channel, listing_class):
    """('release' | 'keep', reason). Values are as strings, None when empty."""
    p, q = protected, parser
    if (listing_id, field) in CHECKED_BY_HAND:
        return CHECKED_BY_HAND[(listing_id, field)], "sale price: checked by hand (cash part / other unit)"
    if field == "intent":
        if p == "UNKNOWN" and q == "RENT" and any(r in channel for r in RENT_CHANNELS):
            return "release", "intent: rent-only channels (Bet_afri family) are RENT"
        if p == "ADVERT":
            return "release", 'intent: old "advert" label on photo and link posts'
        if q in ("SALE", "RENT", "MIXED") and p == "UNKNOWN":
            return "release", "intent: parser found sale/rent where none was stored"
        return "keep", "intent: stored sale/rent/unknown is better than the parser's advert/unknown"
    if field == "location":
        if p not in NONE and not any(n in _squeeze(text_) for n in _names.get(p, ())):
            return "release", "location: stored place is named nowhere in the text (old bugs)"
        if p == "noise":
            return "release", 'location: post was "noise", now readable or has a topic place'
        if q in PLACES and PLACES[q].parent == p or (p, q) == ("bole_main", "meskel_flower"):
            return "release", "location: parser names a smaller area inside the stored one"
        if q in NONE:
            return "keep", "location: stored place, parser finds none"
        return "keep", "location: both places are in the text; keep the repaired choice"
    if field == "property_type":
        if q == "SINGLE_ROOM" and any(r in channel for r in RENT_CHANNELS):
            return "keep", "type: Bet_afri channel rule would force SINGLE_ROOM (too blunt)"
        if q in NONE or q in ("ADVERTISEMENT", "MEDIA_LINK") and p not in NONE:
            if p == "UNKNOWN":
                return "release", "type: noise posts typed consistently"
            return "keep", "type: stored type, parser finds none"
        return "release", "type: parser found a better type (e.g. apartment, not villa)"
    if field == "valuation_eligible":
        if listing_class in NOT_COMPARABLES:
            return "release", "valuation flag: adverts and inquiries are not comparables"
        return "keep", "valuation flag: listing with price and size, marked by run_all.py"
    if field in FIGURES:
        if p is None:
            return "release", "figures: parser found a value where none was stored"
        return "keep", "figures: sizes/prices/floors filled by old repair scripts, parser finds none"
    return "keep", f"{field}: keep stored label"


def main(apply: bool) -> None:
    engine = create_engine(DB_URL)
    pipeline = ValuationPipeline()
    with engine.connect() as conn:   # one transaction, committed only when the split is the approved one
        types = dict(conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'processed_listings'")).fetchall())
        classes = dict(conn.execute(text("SELECT id, listing_class FROM processed_listings")).fetchall())
        raws = {str(r.id): r for r in conn.execute(text(
            "SELECT id, text, channel, posted_at, reply_to_top_id, topic_title FROM telegram_listings"))}
        protections = conn.execute(text(
            "SELECT listing_id, field, value FROM listing_overrides WHERE reason = :r"), {"r": LEGACY_REASON}).fetchall()

        fresh, decisions = {}, []
        for listing_id, field, value in protections:
            raw = raws.get(listing_id)
            if raw is None or raw.reply_to_top_id is not None:
                continue
            if listing_id not in fresh:
                fresh[listing_id], _, _ = build_processed_values(pipeline, raw)
            parser_value = fresh[listing_id][field]
            protected_value = from_text(value, types[field])
            if same_value(protected_value, parser_value):
                continue   # retires by itself in reprocess.py
            blob = f"{raw.topic_title} {raw.text or ''}" if raw.topic_title else (raw.text or "")
            d, why = decide(listing_id, field,
                            None if protected_value is None else str(protected_value),
                            None if parser_value is None else str(parser_value),
                            blob, raw.channel or "", classes.get(listing_id))
            decisions.append((listing_id, field, value, d, why))

        totals = Counter(d for *_, d, _ in decisions)
        for d in ("release", "keep"):
            print(f"\n{d.upper()}: {totals[d]}")
            for (dd, why), n in Counter((d_, w) for *_, d_, w in decisions).most_common():
                if dd == d:
                    print(f"  {n:>5}  {why}")

        released = 0
        for listing_id, field, value, d, _ in decisions:
            if d == "release":
                released += conn.execute(text(
                    "DELETE FROM listing_overrides WHERE listing_id = :id AND field = :f "
                    "AND reason = :r AND value IS NOT DISTINCT FROM :v"),
                    {"id": listing_id, "f": field, "r": LEGACY_REASON, "v": value}).rowcount

        if apply and dict(totals) == APPROVED and released == APPROVED["release"]:
            conn.commit()
            print(f"\nCOMMITTED: released {released} protections")
        else:
            conn.rollback()
            if apply:
                print(f"\nROLLED BACK: the split {dict(totals)} is not the approved {APPROVED}")
            else:
                print(f"\nDRY RUN: would release {released} protections (use --apply)")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
