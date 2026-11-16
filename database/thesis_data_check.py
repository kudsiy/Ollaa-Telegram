r"""
thesis_data_check.py
--------------------
Read-only counts for the owner's thesis, "Market-implied discount rates and cash-equivalent
prices of off-plan apartments in Bole Sub-City" (task S35, 16 November 2026). It uses the
stored listings only and never contacts Telegram.

It finds the off-plan apartment adverts (still being built, sold by a developer), counts which
payment terms their text states, compares them with ready Bole apartments, ranks the channels
and forum topics, and lists every place named in them with the sub-city of src/locations.py.
The rules are word patterns, so the counts are estimates; THESIS_DATA_CHECK.md explains them.
Examples are short and masked (no phone numbers or usernames).

Usage:
    venv\Scripts\python.exe database\thesis_data_check.py > scratch.md
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE_DIR / "src"), str(BASE_DIR / "database")]

from sqlalchemy import create_engine, text  # noqa: E402

import data_quality as dq  # noqa: E402
import locations  # noqa: E402
from accuracy_check import mask  # noqa: E402
from settings import DB_URL  # noqa: E402

APARTMENT_TYPES = ("APARTMENT", "STUDIO")
HOME_WORDS = re.compile(r"apartment|አፓርት?መንት|አፓርታማ|መኝታ|\bbed(?:room)?s?\b|\d\s*bed|studio|ስቱዲዮ", re.I)

# Off-plan: the building is not finished, or the advert sells on a developer's payment plan.
UNDER_CONSTRUCTION = re.compile(
    r"under\s*construction|off[\s-]?plan|በግንባታ\s*ላይ|ግንባታ\s*ላይ\s*ያለ|እየተገነባ|እየገነባ|ግንባታ(?:ው|ቸው|ቸዉ)?\s*(?:ከ\s*)?\d{1,3}\s*%"
    r"|\d{1,3}\s*%\s*(?:የደረሰ|የደረሱ|ተጠናቅቋል|completed|complete|done|construction)|construction\s*(?:progress|stage|status)", re.I)
HANDOVER = re.compile(r"መረከቢ?ያ|ርክክብ|የሚረከቡ|ይረከባሉ|ይረከባሉ|የሚረከብ|ማስረከቢያ|hand\s*-?\s*over|delivery|ዴሊቨሪ|completion\s*date|ቁልፍ\s*የሚረከቡ", re.I)
DOWN_PAYMENT = re.compile(r"(?:ቅድመ|ቅድሚያ)\s*-?\s*ክፍያ|down\s*-?\s*payment|advance\s*payment|initial\s*payment|first\s*payment", re.I)
DOWN_PAYMENT_PCT = re.compile(
    r"(?:(?:ቅድመ|ቅድሚያ)\s*-?\s*ክፍያ|down\s*-?\s*payment|advance\s*payment|initial\s*payment)[^\n\d%]{0,25}\(?\s*(\d{1,2}(?:\.\d)?)\s*%"
    r"|(\d{1,2}(?:\.\d)?)\s*%\s*(?:ቅድመ|ቅድሚያ)?\s*-?\s*(?:ክፍያ\s*)?(?:ቅድመ|ቅድሚያ)\s*-?\s*ክፍያ"
    r"|(\d{1,2}(?:\.\d)?)\s*%\s*(?:down\s*-?\s*payment|advance)", re.I)
INSTALMENT = re.compile(
    r"\d+\s*ዙር|ዙር\s*ክፍያ|በ\s*\d+\s*ዙር|instal+ments?|payment\s*plan|monthly|በየወሩ|በየ\s*\d+\s*ወር|quarterly|ቀሪ(?:ው)?\s*(?:\d+\s*%\s*)?ክፍያ"
    r"|remaining\s*(?:\d+\s*%\s*)?(?:payment|balance)|balance\s*(?:payment|of)|ሁለተኛ\s*ክፍያ|second\s*payment|አከፋፈል|ክፍያ\s*(?:በ|እስከ)\s*\d+\s*(?:ወር|አመት|ዓመት)"
    r"|ቀስ\s*(?:እያለ|እያሉ|ብሎ|በቀስ)", re.I)
INSTALMENT_STAGES = re.compile(
    r"ግንባታ[^\n]{0,40}(?:ደረጃ|ሲደርስ|ሲጠናቀቅ|ሲያልቅ|እያያ|ሂደት|እንደ)|(?:ደረጃ|ሲደርስ|ሲጠናቀቅ)[^\n]{0,30}ግንባታ|በግንባታ\s*(?:ፍጥነት|ሂደት)"
    r"|(?:foundation|ፋውንዴሽን|structure|ስትራክቸር|superstructure|roof|ጣሪያ|finishing\s*stage|ፊኒሺንግ\s*ሲ)"
    r"|(?:according|linked|tied|based)\s*(?:to|on)\s*(?:the\s*)?construction|construction\s*(?:milestone|progress|stage)|as\s*construction", re.I)
DISCOUNT = re.compile(r"(\d{1,2}(?:\.\d)?)\s*%\s*(?:ሙሉ\s*|ልዩ\s*|ታላቅ\s*|ተጨማሪ\s*)?(?:ቅናሽ|discount|off\b)|(?:ቅናሽ|discount)[^\n\d]{0,15}(\d{1,2}(?:\.\d)?)\s*%", re.I)
CASH_EARLY = re.compile(r"100\s*%|ሙሉ\s*ክፍያ|full\s*payment|fully\s*pa|cash|ካሽ|በአንድ\s*ጊዜ|\b[3-9]0\s*%\s*(?:ለ|ለከ|ከፍለ|ለሚከ|pay)|ለከፈለ|ለሚከፍሉ|ለከፈሉ|early", re.I)
PER_SQM = re.compile(r"በካ(?:ሬ|\.ሜ)|(?:per|/)\s*(?:sq\.?\s*m|sqm|m2|m²|square)|price\s*/\s*m|ካሬ\s*ሜትር\s*(?:ዋጋ|በ)|የካሬ\s*ዋጋ|ዋጋ\s*በካሬ", re.I)
TOTAL_PRICE = re.compile(r"ጠቅላላ\s*(?:ዋጋ|ክፍያ)|ሙሉ\s*ክፍያ|total\s*price|full\s*price|total\s*=", re.I)
DEVELOPER_NAME = re.compile(r"[\w'’.-]+(?:\s+[\w'’.-]+)?\s+(?:real\s*-?\s*estate|realestate|ሪል\s*እ?ስቴ?ት|ሪልስቴት|ሪል\s*ስቴት|properties|homes|developers?)", re.I)
PROJECT_NAME = re.compile(r"ፕሮጀክት|project|ሳይት|\bsite\b|ቪሌጅ|village|tower|ታወር|residence|apartments?\s+[A-Z]", re.I)
# A finished building: the advert says so, the flat has its own title deed, or people live in it.
READY = re.compile(
    r"ግንባታ(?:ው|ቸው)?\s*(?:ሙሉ\s*ለሙሉ\s*)?(?:የተጠናቀቀ|ተጠናቅቋል|ያለቀ|አልቋል)|የተጠናቀቁ|ዛሬውኑ\s*የሚገቡበት|ready\s*to\s*move|move[\s-]*in\s*ready"
    r"|ready\s*(?:apartment|house|flat)|ሰዎች\s*እየኖሩበት|እየኖሩበት\s*ያለ|ተከራይቶ|የተናጠል\s*ካርታ|ካርታ\s*(?:ያለው|ያላቸው|የያዘ|አለው|አለ)|ዲ[ጅጂ]ታል\s*ካርታ|digital\s*map|title\s*deed|resale", re.I)
PAYMENT_TERMS = (DOWN_PAYMENT, INSTALMENT, DISCOUNT)
# Claude's notes on the sub-city of each place, from general knowledge of Addis Ababa, not an official map:
# for the owner to check and correct. Places without a note and with a sub-city are marked "likely".
BORDER = "check: near a sub-city border"
PLACE_NOTES = {
    "ayat_zone": "check: a large area at the Bole–Yeka border", "ayat_49": "check: Ayat, at the Bole–Yeka border",
    "bole_main": "check: may mean the whole sub-city or Bole Road", "cmc_michael": BORDER + " (Yeka–Bole)",
    "megenagna": BORDER + " (Yeka–Bole)", "haya_hulet": BORDER + " (Bole–Yeka)", "gerji": BORDER + " (Bole–Yeka)",
    "imperial": BORDER + " (Bole–Yeka)", "meskel_flower": BORDER + " (Kirkos–Bole)", "bambis": BORDER + " (Kirkos–Bole)",
    "mexico": BORDER + " (Kirkos–Lideta)", "sarbet_old_airport": BORDER + " (Nifas Silk–Kolfe–Kirkos)",
    "mekanisa_abo": BORDER + " (Nifas Silk–Kolfe)", "gotera": BORDER + " (Kirkos–Nifas Silk)", "sholla": BORDER + " (Yeka–Bole)",
    "lebu": BORDER + " (Nifas Silk–Kolfe)", "saris": BORDER + " (Nifas Silk–Akaki)", "6kilo": BORDER + " (Gulele–Arada)",
    "stadium": BORDER + " (Kirkos–Arada)", "tafo": "check: at the city edge (Yeka–Lemi Kura–Sheger)",
    "yeka": "check: may be a false match inside a longer word", "bole_atlas": "check: Atlas is near the Bole–Kirkos border",
}


def place_note(code) -> str:
    place = locations.PLACES.get(code)
    if not place or not place.sub_city:
        return "**no sub-city in the place table**"
    return PLACE_NOTES.get(code, "likely")
PAYMENT_WORDS = re.compile(r"ክፍያ|ይከፈ|የሚከፈ|ዙር|pay|instal", re.I)
# Forum topic titles in luxury_freelancers start with how far the building is: "97% ካዛንቺስ Joberg", "100% ያለቀ ሰሚት Golden".
TOPIC_BUILDING = re.compile(r"^\s*([1-9]\d?)\s*%")
TOPIC_FINISHED = re.compile(r"^\s*100\s*%|ያለቀ|ተጠናቀቀ", re.I)


def stages_linked(raw: str) -> bool:
    """Payments tied to construction: a construction-stage phrase with payment words close to it."""
    for m in INSTALMENT_STAGES.finditer(raw or ""):
        if PAYMENT_WORDS.search(raw[max(0, m.start() - 80):m.end() + 80]):
            return True
    return False


def classify(r) -> str:
    """OFF_PLAN, READY or UNCLEAR, for an apartment advert for sale."""
    t = r.raw_text or ""
    topic = r.topic_title or ""
    developer = bool(r.developer) or bool(DEVELOPER_NAME.search(t)) or bool(topic)
    off_plan = bool(UNDER_CONSTRUCTION.search(t) or HANDOVER.search(t) or TOPIC_BUILDING.search(topic)
                    or (developer and (DOWN_PAYMENT.search(t) or INSTALMENT.search(t))))
    ready = bool(READY.search(t) or TOPIC_FINISHED.search(topic))
    if off_plan and not ready:
        return "OFF_PLAN"
    if off_plan and ready:
        return "UNCLEAR"
    return "READY"


def is_apartment_for_sale(r) -> bool:
    if r.listing_class == "MEDIA_PENDING" or r.intent == "RENT" or r.location == locations.NOISE:
        return False
    return r.property_type in APARTMENT_TYPES or (r.property_type in (None, "UNKNOWN") and bool(HOME_WORDS.search(r.raw_text or "")))


def sub_city(code):
    place = locations.PLACES.get(locations.canonical(code)) if code else None
    return place.sub_city if place else None


def places_named(raw: str):
    """Every place of src/locations.py named in the text: {code: the words as written}."""
    t = locations._prepare(raw or "")
    found = {}
    for pattern, code in locations._COMPILED:
        m = pattern.search(t)
        if m and code not in found:
            found[code] = m.group(0).strip()
    return found


def snippet(raw: str, m, width=70) -> str:
    t = raw or ""
    a, b = max(0, m.start() - width), min(len(t), m.end() + width)
    s = mask(t[a:b])
    return " ".join(s.split()).replace("|", "/")


def channel_name(r) -> str:
    return (r.channel or r.source_channel or "?").rsplit("/", 1)[-1]


def pct(n, total):
    return f"{n:,} ({100 * n / total:.0f}%)" if total else "0"


def table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        print("| " + " | ".join(str(c) for c in row) + " |")
    print()


def main() -> None:
    with create_engine(DB_URL).connect() as conn:
        rows = [SimpleNamespace(**r) for r in conn.execute(text("""
            SELECT p.*, t.channel, t.topic_title FROM processed_listings p
            JOIN telegram_listings t ON p.id = t.id::text""")).mappings()]
    usable = {r.id for r in rows if dq.is_usable(r)}
    sample = {r.id for r in dq.sale_sample(rows)}
    apartments = [r for r in rows if is_apartment_for_sale(r)]
    kind = {r.id: classify(r) for r in apartments}
    off = [r for r in apartments if kind[r.id] == "OFF_PLAN"]
    unclear = [r for r in apartments if kind[r.id] == "UNCLEAR"]
    ready = [r for r in apartments if kind[r.id] == "READY"]
    in_bole = lambda r: sub_city(r.location) == "Bole"
    names_bole = lambda r: any(sub_city(c) == "Bole" for c in places_named(r.raw_text))
    off_bole = [r for r in off if in_bole(r)]

    print("## Off-plan apartment adverts\n")
    table(["", "All stored adverts with text", "of them usable listings", "in the sale sample"], [
        ["Apartment adverts for sale (text read)", f"{len(apartments):,}", sum(r.id in usable for r in apartments), sum(r.id in sample for r in apartments)],
        ["**Off-plan** (being built or sold on a developer's plan)", f"**{len(off):,}**", sum(r.id in usable for r in off), sum(r.id in sample for r in off)],
        ["Unclear (off-plan words and finished-building words)", len(unclear), sum(r.id in usable for r in unclear), sum(r.id in sample for r in unclear)],
        ["Ready (no off-plan words)", f"{len(ready):,}", sum(r.id in usable for r in ready), sum(r.id in sample for r in ready)],
    ])
    table(["Off-plan adverts", "Count"], [
        ["Stored place in Bole sub-city", f"**{len(off_bole)}**"],
        ["Naming a Bole place anywhere in the text (a developer often lists several sites)", sum(names_bole(r) for r in off)],
        ["Stored place in another sub-city", sum(sub_city(r.location) not in (None, "Bole") for r in off)],
        ["Stored place without a sub-city in the place table", sum(r.location not in (None, locations.UNKNOWN) and sub_city(r.location) is None for r in off)],
        ["No place found", sum(r.location in (None, locations.UNKNOWN) for r in off)],
    ])
    in_bole_places = Counter(r.location for r in off_bole)
    print(f"Of the {len(off_bole)} off-plan adverts placed in Bole, {in_bole_places['ayat_zone'] + in_bole_places['ayat_49']} are at Ayat "
          f"(Ayat or Ayat 49), whose sub-city should be checked (see the last table); the others: "
          + ", ".join(f"{k} {v}" for k, v in in_bole_places.most_common() if k not in ("ayat_zone", "ayat_49")) + ".\n")
    by_sub = Counter(sub_city(r.location) or "(none)" for r in off)
    print("Off-plan adverts by the sub-city of their stored place: "
          + ", ".join(f"{k} {v}" for k, v in by_sub.most_common()) + ".\n")
    photo_dev = [r for r in rows if r.listing_class == "MEDIA_PENDING" and (r.topic_title or (r.developer))]
    photo_champ = [r for r in rows if r.listing_class == "MEDIA_PENDING" and "championallsites" in (r.channel or "")]
    print(f"Not counted above: {len([r for r in rows if r.listing_class == 'MEDIA_PENDING']):,} photo-only posts, whose words are in the "
          f"picture; {len(photo_champ):,} of them are in championallsites and {len(photo_dev):,} are in a forum topic or name a developer.\n")

    fields = [
        ("Developer or project name", lambda r: r.developer and re.search(re.escape(r.developer.split()[0]), r.raw_text or "", re.I)
         or DEVELOPER_NAME.search(r.raw_text or "") or PROJECT_NAME.search(r.raw_text or "")),
        ("Unit size and total price (both stored)", lambda r: r.builtup_sqm is not None and r.sale_price_birr is not None and (
            TOTAL_PRICE.search(r.raw_text or "") or re.search(r"\d", r.raw_text or ""))),
        ("…of which the total price is written as a total", lambda r: r.builtup_sqm is not None and r.sale_price_birr is not None and TOTAL_PRICE.search(r.raw_text or "")),
        ("Down payment as a %", lambda r: DOWN_PAYMENT_PCT.search(r.raw_text or "")),
        ("Down payment, any form (% or amount)", lambda r: DOWN_PAYMENT.search(r.raw_text or "")),
        ("Instalment plan", lambda r: INSTALMENT.search(r.raw_text or "")),
        ("Instalments linked to construction stages", lambda r: stages_linked(r.raw_text)),
        ("Handover date or period", lambda r: HANDOVER.search(r.raw_text or "")),
        ("Cash or early-payment discount", lambda r: DISCOUNT.search(r.raw_text or "") and CASH_EARLY.search(r.raw_text or "")),
        ("Discount schedule (2 or more discount rates)", lambda r: len({(m.group(1) or m.group(2)) for m in DISCOUNT.finditer(r.raw_text or "")}) >= 2
         and CASH_EARLY.search(r.raw_text or "")),
        ("Price per m² written in the advert", lambda r: PER_SQM.search(r.raw_text or "")),
    ]
    print("## What the off-plan adverts state\n")
    results = []
    for name, test in fields:
        hits = [r for r in off if test(r)]
        results.append((name, hits))
    table(["Field", f"All off-plan ({len(off)})", f"Off-plan in Bole ({len(off_bole)})", "Usable off-plan"],
          [[n, pct(len(h), len(off)), pct(sum(in_bole(r) for r in h), len(off_bole)), sum(r.id in usable for r in h)] for n, h in results])

    print("### Stored by the parser (task S36)\n")
    print("The same terms as fields of `processed_listings`, filled by `src/payment_terms.py` (stricter than the word counts above, "
          "which only show that a term is mentioned):\n")
    stored_fields = [
        ("Down payment %", "down_payment_pct"), ("Discount schedule (share paid : discount)", "discount_schedule"),
        ("Number of instalments", "instalment_count"), ("Instalment period, months", "instalment_months"),
        ("Instalments follow construction", "instalments_follow_construction"), ("Interest-free", "interest_free"),
        ("Months to handover", "handover_months"), ("Construction progress %", "construction_progress_pct"),
        ("Price per m² as written", "price_per_sqm_stated"),
    ]
    has = lambda r, f: getattr(r, f, None) not in (None, False)
    table(["Field", "Column", f"All off-plan ({len(off)})", f"Off-plan in Bole ({len(off_bole)})"],
          [[n, f"`{f}`", pct(sum(has(r, f) for r in off), len(off)), pct(sum(has(r, f) for r in off_bole), len(off_bole))]
           for n, f in stored_fields])
    usable_for_rate = [r for r in off_bole if r.discount_schedule and r.sale_price_birr is not None and r.builtup_sqm is not None]
    print(f"Off-plan Bole adverts with a discount schedule and a stored size and total price: {len(usable_for_rate)}.\n")

    print("### Five real examples of each (masked; the listing number is the stored id)\n")
    pattern_of = {
        "Developer or project name": DEVELOPER_NAME, "Unit size and total price (both stored)": TOTAL_PRICE,
        "…of which the total price is written as a total": TOTAL_PRICE,
        "Down payment as a %": DOWN_PAYMENT_PCT, "Down payment, any form (% or amount)": DOWN_PAYMENT, "Instalment plan": INSTALMENT,
        "Instalments linked to construction stages": INSTALMENT_STAGES, "Handover date or period": HANDOVER,
        "Cash or early-payment discount": DISCOUNT, "Discount schedule (2 or more discount rates)": DISCOUNT, "Price per m² written in the advert": PER_SQM,
    }
    for name, hits in results:
        if name.startswith("…"):
            continue
        print(f"**{name}**\n")
        bole_first = sorted(hits, key=lambda r: (not in_bole(r), int(r.id) if r.id.isdigit() else 0))
        shown, channels = 0, set()
        for r in bole_first:
            m = pattern_of[name].search(r.raw_text or "") or re.search(r"\d", r.raw_text or "")
            if not m or (channel_name(r) in channels and len(hits) > 15):
                continue
            channels.add(channel_name(r))
            extra = f"; stored {int(r.builtup_sqm)} m², {int(r.sale_price_birr):,} birr" if name.startswith("Unit size") else ""
            print(f"- {r.id} ({channel_name(r)}, {r.location}{extra}): “{snippet(r.raw_text, m)}”")
            shown += 1
            if shown == 5:
                break
        print()

    print("## Ready Bole apartments, for comparison\n")
    ready_bole = [r for r in ready if in_bole(r)]
    priced = [r for r in ready_bole if r.sale_price_birr is not None and r.builtup_sqm is not None]
    off_bole_priced = [r for r in off_bole if r.sale_price_birr is not None and r.builtup_sqm is not None]
    condos = [r for r in rows if r.property_type == "CONDOMINIUM" and r.intent != "RENT" and r.listing_class != "MEDIA_PENDING"
              and in_bole(r) and r.sale_price_birr is not None and r.builtup_sqm is not None]
    table(["Bole apartments for sale", "Count", "usable", "in the sale sample"], [
        ["Ready, any", len(ready_bole), sum(r.id in usable for r in ready_bole), sum(r.id in sample for r in ready_bole)],
        ["**Ready, with price and size**", f"**{len(priced)}**", sum(r.id in usable for r in priced), sum(r.id in sample for r in priced)],
        ["Off-plan, with price and size", len(off_bole_priced), sum(r.id in usable for r in off_bole_priced), sum(r.id in sample for r in off_bole_priced)],
        ["Unclear, in Bole", sum(in_bole(r) for r in unclear), sum(in_bole(r) and r.id in usable for r in unclear), sum(in_bole(r) and r.id in sample for r in unclear)],
        ["Government condominiums with price and size (kept apart)", len(condos), sum(r.id in usable for r in condos), sum(r.id in sample for r in condos)],
    ])

    def median(values):
        v = sorted(values)
        return v[len(v) // 2] if v else None
    for label, group in (("Ready", priced), ("Off-plan", off_bole_priced)):
        per = [float(r.sale_price_birr) / float(r.builtup_sqm) for r in group if float(r.builtup_sqm) > 0]
        if per:
            print(f"- {label} Bole apartments: median asking price {median(per):,.0f} birr per m² over {len(per)} listings "
                  f"(stored total price ÷ stored size; not cleaned for outliers).")
    print()

    print("## Channels and forum topics with the most off-plan adverts with payment terms\n")
    terms = [r for r in off if any(p.search(r.raw_text or "") for p in PAYMENT_TERMS)]
    print(f"{len(terms)} of the {len(off)} off-plan adverts state a down payment, an instalment plan or a discount; "
          f"{sum(in_bole(r) for r in terms)} of them have their stored place in Bole.\n")
    by_channel = Counter(channel_name(r) for r in terms)
    bole_channel = Counter(channel_name(r) for r in terms if in_bole(r))
    table(["Channel or group", "Off-plan with payment terms", "of them in Bole"],
          [[c, n, bole_channel[c]] for c, n in by_channel.most_common(15)])
    topics = Counter((channel_name(r), r.topic_title) for r in terms if r.topic_title)
    bole_topic = Counter((channel_name(r), r.topic_title) for r in terms if r.topic_title and in_bole(r))
    all_topics = Counter((channel_name(r), r.topic_title) for r in rows if r.topic_title)
    print("Forum topics (each topic is usually one developer project):\n")
    table(["Group", "Topic", "Off-plan with payment terms", "of them in Bole", "All stored posts in the topic"],
          [[g, t.replace("|", "/"), n, bole_topic[(g, t)], all_topics[(g, t)]] for (g, t), n in topics.most_common(25)])
    champ = [r for r in rows if "championallsites" in (r.channel or "")]
    progress = re.compile(r"progress|slab|column|floor\s*(?:slab|casting)|ግንባታ|ሂደት|stage", re.I)
    print(f"**championallsites** (a forum group, one topic per developer project): {len(champ):,} stored posts in "
          f"{len({r.topic_title for r in champ})} topics; {sum(r.listing_class == 'MEDIA_PENDING' for r in champ):,} are photo-only, "
          f"so their prices and payment terms are in the pictures, which the text parser cannot read. Of the "
          f"{sum(r.listing_class != 'MEDIA_PENDING' for r in champ)} with text, "
          f"{sum(r.listing_class != 'MEDIA_PENDING' and bool(progress.search(r.raw_text or '')) for r in champ)} are construction-progress "
          f"updates, and {sum(kind.get(r.id) == 'OFF_PLAN' for r in champ)} is read as an off-plan apartment advert. Its busiest topics:\n")
    ct = Counter(r.topic_title for r in champ)
    table(["Topic (project)", "Stored posts", "Photo-only", "With text"],
          [[t.replace("|", "/"), n, sum(r.listing_class == "MEDIA_PENDING" for r in champ if r.topic_title == t),
            sum(r.listing_class != "MEDIA_PENDING" for r in champ if r.topic_title == t)] for t, n in ct.most_common(15)])

    print("## Places named in the off-plan adverts\n")
    named = defaultdict(lambda: {"adverts": 0, "stored": 0, "written": Counter()})
    for r in off + unclear:
        for code, words in places_named(r.raw_text).items():
            named[code]["adverts"] += 1
            named[code]["written"][words] += 1
        if r.location not in (None, locations.UNKNOWN):
            named[r.location]["stored"] += 1
    rows_out = []
    for code, v in sorted(named.items(), key=lambda kv: -kv[1]["adverts"]):
        place = locations.PLACES.get(code)
        rows_out.append([code, place.name if place else "?", ", ".join(w for w, _ in v["written"].most_common(3)).replace("|", "/") or "(from the topic title)",
                         (place.sub_city if place else None) or "—", place_note(code), v["adverts"], v["stored"]])
    table(["Code", "Place", "Written in the adverts as", "Sub-city now", "Sure?", "Adverts naming it", "Stored as the listing's place"], rows_out)


if __name__ == "__main__":
    main()
