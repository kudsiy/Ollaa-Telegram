"""
data_quality.py
---------------
The numbers behind DATA_QUALITY.md: how many stored listings are usable, where
they are, what they are, how complete each field is, which values are impossible,
and how many listings are fit for a hedonic price model. Read-only; prints
Markdown tables with listing ids and numbers only, never message text or contacts.

Usage:
    venv\\Scripts\\python.exe database\\data_quality.py
"""

import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from locations import NOISE, PLACES, SHEGER, UNKNOWN, coordinates  # noqa: E402
from settings import DB_URL  # noqa: E402

# A usable listing describes a property offered for sale or rent and its text was read.
EXCLUDED_CLASSES = ("ADVERTISEMENT", "INQUIRY", "INVALID", "MEDIA_PENDING")
EXCLUDED_TYPES = ("ADVERTISEMENT", "MEDIA_LINK")
RESIDENTIAL_UNITS = ("APARTMENT", "CONDOMINIUM", "STUDIO", "SINGLE_ROOM")

# "Obvious outlier" rules: values that cannot be right for Addis Ababa in 2025-2026.
SALE_PER_SQM = (20_000, 1_000_000)     # birr per m² (built-up; plot for land)
SALE_TOTAL_MIN = 500_000               # birr
RENT_MONTH = (1_000, 2_000_000)        # birr per month
UNIT_SIZE = (15, 500)                  # m², apartments, condominiums, studios, rooms
SMALL_UNIT_MAX = 100                   # m², studios and single rooms
UNIT_BEDROOMS_MAX = 6                  # apartments, condominiums, studios, rooms

FIELDS = [  # (label, test on one listing)
    ("price (sale or rent)", lambda r: r.sale_price_birr is not None or r.rent_price_birr is not None),
    ("size (built-up or plot)", lambda r: r.builtup_sqm is not None or r.plot_sqm is not None),
    ("built-up size", lambda r: r.builtup_sqm is not None),
    ("bedrooms", lambda r: r.bedrooms is not None),
    ("bathrooms", lambda r: r.bathrooms is not None),
    ("location (a named place)", lambda r: r.location not in (None, UNKNOWN, NOISE)),
    ("sub-city", lambda r: sub_city(r.location) not in NO_SUB_CITY),
    ("map coordinates (place table)", lambda r: coordinates(r.location) is not None),
    ("property type", lambda r: r.property_type != "UNKNOWN"),
    ("floor", lambda r: r.floor_level is not None),
    ("finishing", lambda r: r.finish_state not in (None, "unknown")),
    ("payment terms", lambda r: r.payment_type not in (None, "UNKNOWN")),
    ("building height (G+n)", lambda r: r.property_subtype is not None),
    ("posting date", lambda r: r.posted_at is not None),
]
NO_SUB_CITY = ("no place found", "sub-city not recorded")


def sub_city(code):
    if code in (None, UNKNOWN, NOISE):
        return "no place found"
    place = PLACES.get(code)
    while place and not place.sub_city and place.parent:
        place = PLACES.get(place.parent)
    if place and place.city == SHEGER:
        return "Sheger City (outside Addis Ababa)"
    if place and place.sub_city == "Sheger":
        return "Gelan, Dukem (counted as Addis Ababa)"
    return place.sub_city if place and place.sub_city else "sub-city not recorded"


def place_name(code):
    return PLACES[code].name if code in PLACES else {UNKNOWN: "(no place found)", NOISE: "(noise)"}.get(code, code)


def size_of(r):
    return r.plot_sqm if r.property_type == "LAND" else r.builtup_sqm


def outlier_reasons(r):
    reasons = []
    if r.intent in ("SALE", "MIXED") and r.sale_price_birr is not None:
        if r.sale_price_birr < SALE_TOTAL_MIN:
            reasons.append("sale price under 500,000 birr")
        size = size_of(r)
        if size:
            per_sqm = r.sale_price_birr / size
            if not SALE_PER_SQM[0] <= per_sqm <= SALE_PER_SQM[1]:
                reasons.append(f"{per_sqm:,.0f} birr per m²")
    if r.intent == "RENT" and r.rent_price_birr is not None:
        if not RENT_MONTH[0] <= r.rent_price_birr <= RENT_MONTH[1]:
            reasons.append(f"rent {r.rent_price_birr:,.0f} birr a month")
    if r.property_type in RESIDENTIAL_UNITS:
        if r.builtup_sqm is not None and not UNIT_SIZE[0] <= r.builtup_sqm <= UNIT_SIZE[1]:
            reasons.append(f"{r.property_type.lower()} of {r.builtup_sqm:g} m²")
        elif (r.property_type in ("STUDIO", "SINGLE_ROOM") and r.builtup_sqm is not None
              and r.builtup_sqm > SMALL_UNIT_MAX):
            reasons.append(f"{r.property_type.lower()} of {r.builtup_sqm:g} m²")
        if r.bedrooms is not None and r.bedrooms > UNIT_BEDROOMS_MAX:
            reasons.append(f"{r.property_type.lower()} with {r.bedrooms} bedrooms")
    return reasons


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    print("\n".join(out) + "\n")


def pct(n, total):
    return f"{n:,} ({100 * n / total:.0f}%)" if total else "0"


def main():
    with create_engine(DB_URL).connect() as conn:
        rows = conn.execute(text("SELECT * FROM processed_listings")).fetchall()
        raw = conn.execute(text("SELECT count(*) FROM telegram_listings")).scalar()
        kept_out = conn.execute(text("SELECT count(*) FROM processing_exclusions")).scalar()
        protected = dict(conn.execute(text(
            "SELECT listing_id, count(*) FROM listing_overrides GROUP BY 1")).fetchall())
        photos_waiting = conn.execute(text("SELECT count(*) FROM media_queue WHERE NOT processed")).scalar()
        scraped = dict(conn.execute(text("SELECT id::text, created_at FROM telegram_listings")).fetchall())

    print(f"# Data quality numbers ({date.today().isoformat()})\n")
    print(f"Raw messages {raw:,}; stored listings {len(rows):,}; messages kept out "
          f"(deleted duplicates and junk) {kept_out:,}.\n")

    # ── From stored listings to usable listings ──────────────────────────
    media = [r for r in rows if r.listing_class == "MEDIA_PENDING"]
    rest = [r for r in rows if r.listing_class != "MEDIA_PENDING"]
    noise = [r for r in rest if r.listing_class in EXCLUDED_CLASSES or r.property_type in EXCLUDED_TYPES]
    rest = [r for r in rest if not (r.listing_class in EXCLUDED_CLASSES or r.property_type in EXCLUDED_TYPES)]
    no_intent = [r for r in rest if r.intent not in ("SALE", "RENT", "MIXED")]
    usable = [r for r in rest if r.intent in ("SALE", "RENT", "MIXED")]
    print("## From stored listings to usable listings\n")
    table(["Step", "Listings"], [
        ["Stored listings", f"{len(rows):,}"],
        ["Photo or file only, text not read yet (MEDIA_PENDING)", f"-{len(media):,}"],
        ["Adverts for services, inquiries (\"looking for\"), junk", f"-{len(noise):,}"],
        ["Property post, but neither sale nor rent could be told", f"-{len(no_intent):,}"],
        ["**Usable listings**", f"**{len(usable):,}**"],
    ])
    with_protection = sum(1 for r in usable if r.id in protected)
    print(f"{with_protection:,} usable listings hold at least one value set by an earlier hand "
          f"repair (protected in listing_overrides); all other values come from the parser.\n")

    # ── Sale vs rent, property types ────────────────────────────────────
    print("## Sale and rent\n")
    by_intent = Counter(r.intent for r in usable)
    table(["Intent", "Listings"], [[k, pct(v, len(usable))] for k, v in by_intent.most_common()])
    print("## Property types\n")
    types = Counter(r.property_type for r in usable)
    table(["Type", "Sale", "Rent", "Both (MIXED)", "Total"],
          [[t, *(sum(1 for r in usable if r.property_type == t and r.intent == i)
                 for i in ("SALE", "RENT", "MIXED")), n] for t, n in types.most_common()])

    # ── Where ────────────────────────────────────────────────────────────
    print("## Sub-cities\n")
    subs = Counter(sub_city(r.location) for r in usable)
    table(["Sub-city", "Sale", "Rent", "Both", "Total"],
          [[s, *(sum(1 for r in usable if sub_city(r.location) == s and r.intent == i)
                 for i in ("SALE", "RENT", "MIXED")), n] for s, n in subs.most_common()])
    print("## Neighbourhoods (25 most frequent)\n")
    places = Counter(r.location for r in usable)
    print(f"{len([p for p in places if p not in (UNKNOWN, NOISE)])} different places are named.\n")
    table(["Place", "Sub-city", "Sale", "Rent", "Both", "Total"],
          [[place_name(p), sub_city(p), *(sum(1 for r in usable if r.location == p and r.intent == i)
                                         for i in ("SALE", "RENT", "MIXED")), n]
           for p, n in places.most_common(25)])

    # ── Completeness ─────────────────────────────────────────────────────
    print("## How complete each field is (usable listings)\n")
    groups = [("Sale", [r for r in usable if r.intent == "SALE"]),
              ("Rent", [r for r in usable if r.intent == "RENT"]),
              ("Both", [r for r in usable if r.intent == "MIXED"]),
              ("All usable", usable)]
    table(["Field", *(f"{g} (n={len(rs)})" for g, rs in groups)],
          [[label, *(pct(sum(1 for r in rs if test(r)), len(rs)) for _, rs in groups)]
           for label, test in FIELDS])
    core = [r for r in usable if all(test(r) for label, test in FIELDS
                                     if label in ("price (sale or rent)", "size (built-up or plot)",
                                                  "bedrooms", "location (a named place)"))]
    print(f"Price, size, bedrooms and a named place all known: {pct(len(core), len(usable))} usable "
          f"listings (sale {sum(1 for r in core if r.intent == 'SALE')}, "
          f"rent {sum(1 for r in core if r.intent == 'RENT')}, "
          f"both {sum(1 for r in core if r.intent == 'MIXED')}).\n")
    sale_with_rent = sum(1 for r in usable if r.intent == "SALE" and r.rent_price_birr is not None)
    rent_with_sale = [r for r in usable if r.intent == "RENT" and r.sale_price_birr is not None]
    print(f"Prices in the wrong field: {len(rent_with_sale)} rent listings carry a sale price "
          f"({sum(1 for r in rent_with_sale if r.rent_price_birr is None)} of them no rent); "
          f"{sale_with_rent} sale listings carry a rent.\n")
    usd = [r for r in usable if r.price_currency == "USD"]
    print(f"Prices quoted in US dollars: {len(usd)} usable listings (often a price per m² or a "
          f"monthly rent; not converted).\n")

    dated = [r for r in usable if r.posted_at is not None]
    undated = [scraped[r.id] for r in usable if r.posted_at is None and r.id in scraped]
    years = Counter(r.posted_at.year for r in dated)
    print(f"Posting date known for {pct(len(dated), len(usable))} usable listings "
          f"({', '.join(f'{y}: {n}' for y, n in sorted(years.items()))}); the other "
          f"{len(undated)} only have the date they were collected "
          f"({min(undated):%d %b %Y} to {max(undated):%d %b %Y}).\n")

    # ── Photo-only posts ─────────────────────────────────────────────────
    print("## Photo-only posts (MEDIA_PENDING)\n")
    media_place = sum(1 for r in media if r.location not in (UNKNOWN, NOISE))
    print(f"{len(media):,} listings ({100 * len(media) / len(rows):.0f}% of all stored listings) are "
          f"photos or files without readable text; {media_place:,} of them have a place from their "
          f"forum topic. {photos_waiting:,} images wait in media_queue, none read yet.\n")

    # ── Outliers ─────────────────────────────────────────────────────────
    print("## Obvious outliers (usable listings)\n")
    flagged = [(r, outlier_reasons(r)) for r in usable]
    flagged = [(r, why) for r, why in flagged if why]
    print(f"{len(flagged)} usable listings break at least one rule.\n")
    table(["Listing", "Intent", "Type", "Place", "Why"],
          [[r.id, r.intent, r.property_type, place_name(r.location), "; ".join(why)]
           for r, why in sorted(flagged, key=lambda x: int(x[0].id))])

    # ── Hedonic model sample ─────────────────────────────────────────────
    def model_ready(r, price_field):
        return (getattr(r, price_field) is not None and size_of(r) is not None
                and r.location not in (None, UNKNOWN, NOISE) and r.property_type != "UNKNOWN"
                and r.price_currency == "ETB" and not outlier_reasons(r))

    sale = [r for r in usable if r.intent in ("SALE", "MIXED") and model_ready(r, "sale_price_birr")]
    rent = [r for r in usable if r.intent == "RENT" and model_ready(r, "rent_price_birr")]
    print("## Listings fit for a hedonic model\n")
    print("Price, size (plot for land), a named place and a known type; priced in birr; "
          "no obvious outlier.\n")
    for label, sample in (("Sale", sale), ("Rent", rent)):
        places_n = Counter(r.location for r in sample)
        cells = Counter((r.location, r.property_type) for r in sample)
        print(f"**{label}: {len(sample)} listings** — types: "
              f"{', '.join(f'{t} {n}' for t, n in Counter(r.property_type for r in sample).most_common())}; "
              f"{len(places_n)} places, of which {sum(1 for n in places_n.values() if n >= 10)} have 10 or more "
              f"listings and {sum(1 for n in places_n.values() if n >= 5)} have 5 or more; "
              f"place-and-type cells with 5 or more listings: {sum(1 for n in cells.values() if n >= 5)}.\n")
        table(["Field", f"{label} sample (n={len(sample)})"],
              [[label_, pct(sum(1 for r in sample if test(r)), len(sample))]
               for label_, test in FIELDS if label_ not in ("price (sale or rent)", "size (built-up or plot)",
                                                             "built-up size", "location (a named place)",
                                                             "property type")])
    rent_no_size = [r for r in usable if r.intent == "RENT" and r.rent_price_birr is not None
                    and r.location not in (None, UNKNOWN, NOISE) and r.property_type != "UNKNOWN"
                    and r.price_currency == "ETB" and not outlier_reasons(r)]
    rent_types = Counter(r.property_type for r in rent_no_size).most_common()
    print(f"Rent listings with a rent, a named place and a known type when size is not required: "
          f"{len(rent_no_size)} ({', '.join(f'{t} {n}' for t, n in rent_types)}).\n")
    homes = [r for r in sale if r.property_type in ("APARTMENT", "CONDOMINIUM", "VILLA", "STUDIO", "TOWNHOUSE")]
    print(f"Homes only (apartments, condominiums, villas, studios, townhouses) in the sale sample: "
          f"{len(homes)}; bedrooms known for {pct(sum(1 for r in homes if r.bedrooms is not None), len(homes))}, "
          f"bathrooms for {pct(sum(1 for r in homes if r.bathrooms is not None), len(homes))}.\n")
    reposts = Counter((r.property_type, r.location, r.sale_price_birr, size_of(r)) for r in sale)
    print(f"Possible reposts in the sale sample (same type, place, price and size): "
          f"{sum(n - 1 for n in reposts.values() if n > 1)} extra copies in "
          f"{sum(1 for n in reposts.values() if n > 1)} groups.\n")


if __name__ == "__main__":
    main()
