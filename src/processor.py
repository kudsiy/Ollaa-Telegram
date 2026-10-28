"""
processor.py
------------
Shared extraction helpers for Addis real-estate listings.

This module is meant to be imported by other scripts (e.g. run_pipeline.py)
so the listener/ETL share consistent parsing rules.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional


# --- Phone-like filters -------------------------------------------------------
# We frequently see phone numbers (09xxxxxxxx, +2519xxxxxxxx) in listings.
# These should never be treated as prices.


def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def is_likely_phone(number_str: str) -> bool:
    """
    Reject phone-like strings as prices.
    Rules:
      - starts with 09, 07, or 251 (after stripping non-digits), OR
      - exactly 10 or 12 digits long
    """
    if not number_str:
        return False
    d = _digits_only(number_str)
    if not d:
        return False
    if d.startswith(("09", "07", "251")):
        return True
    if len(d) in (10, 12):
        return True
    return False


MAX_VALID_SALE_PRICE_BIRR = 10_000_000_000
MOBILE_RANGE_BANDS = (
    (700_000_000, 799_999_999),
    (900_000_000, 999_999_999),
)


# --- Labeled field extraction -------------------------------------------------
# Examples:
#   "📍Location: Gerji" / "📍Area: Bole" / "ቦታ: ሳርቤት"
LABELED_LOCATION_RE = re.compile(
    r"(?:📍\s*)?(?:area|location)\s*[:፦]\s*([^\n|]+)|"
    r"(?:ቦታ)\s*[:፦]\s*([^\n|]+)",
    re.IGNORECASE,
)


def extract_labeled_location(text: str) -> Optional[str]:
    if not text:
        return None
    m = LABELED_LOCATION_RE.search(text)
    if not m:
        return None
    val = (m.group(1) or m.group(2) or "").strip()
    return val or None


LABELED_PLOT_SQM_RE = re.compile(
    # "የቦታ ስፋት፦ 930 ካሬ", "የቦታው ስፋት ........ 572 ካሬ" (size of the plot) are plot sizes too.
    r"(?:area|plot|land|compound|total area|ይዞታ|መሬት|ቦታው?\s*ስፋት|ቦታ)\s*[:፦\-\.…]*\s*(\d{2,5})\s*(?:sqm|sq\.?m|m2|m²|ካሬ)?",
    re.IGNORECASE,
)

LABELED_BUILTUP_SQM_RE = re.compile(
    r"(?:built\s*[- ]?up|builtup|built|living area|floor area|constructed|የተገነባ|ተገንብቶ)\s*[:፦-]?\s*(\d{2,5})\s*(?:sqm|sq\.?m|m2|m²|ካሬ)?",
    re.IGNORECASE,
)

# "235.71(199)sqm" is the gross size with the net size in brackets.
GENERIC_AREA_RE = re.compile(r"(?<![\d.,])(\d{2,5})(?:\.\d+)?(?:\s*\(\d+(?:\.\d+)?\))?\s*(?:ካሬ|sqm|sq\.?m|m2|m²)",
                             re.IGNORECASE)


def _clean_area_value(raw: str | None) -> Optional[int]:
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if 20 <= value <= 5000:
        return value
    return None


def extract_area_breakdown(text: str) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None

    plot = None
    built = None

    for match in LABELED_PLOT_SQM_RE.finditer(text):
        plot = _clean_area_value(match.group(1))
        if plot is not None:
            break

    for match in LABELED_BUILTUP_SQM_RE.finditer(text):
        built = _clean_area_value(match.group(1))
        if built is not None:
            break

    values: list[int] = []
    for match in GENERIC_AREA_RE.finditer(text):
        value = _clean_area_value(match.group(1))
        if value is not None and value not in values:
            values.append(value)

    if plot is not None and built is not None:
        return plot, built

    if plot is not None:
        remaining = [v for v in values if v != plot]
        if remaining:
            built = min(remaining)
        return plot, built

    if built is not None:
        remaining = [v for v in values if v != built]
        if remaining:
            plot = max(remaining)
        return plot, built

    if len(values) >= 2:
        ordered = sorted(values)
        return ordered[-1], ordered[0]

    if len(values) == 1:
        return values[0], None

    return None, None


# --- Million amount converter -------------------------------------------------
# Examples:
#   "12 ሚሊዮን" -> 12,000,000
#   "8.5 ሚ"     -> 8,500,000
# Listings spell "million" many ways: ሚልዮን (the most common), ሚሊዮን, ሚሊየን,
# ሚልየን, ሚሊዬን, ሚለን, ሚሊ, or just ሚ. ("ሚሊትር", millilitre, is not one.)
MILLION_WORD = (r"(?:mil(?:lion)?|million|ሚ[ሊል][ዮየዬ]ን|ሚለን"
                r"|ሚሊ(?![ሀ-፿])|ሚ(?![ሀ-፿])|ሚ\.)")
# A whole number, not the end of one ("158.5 ሚሊዮን" is not 5 million); "55,000,000 ሚሊዮን"
# repeats the word and is 55 million.
MILLION_RE = re.compile(r"(?<![\d,.])(?P<num>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*" + MILLION_WORD, re.IGNORECASE)


def million_value(m) -> int:
    """The amount a MILLION_RE match stands for."""
    val = float(m.group("num").replace(",", ""))
    return int(round(val if val >= 1_000_000 else val * 1_000_000))


def parse_million_amount(text: str) -> Optional[int]:
    if not text:
        return None
    m = MILLION_RE.search(text)
    if not m:
        return None
    try:
        return million_value(m)
    except ValueError:
        return None


# --- Bedroom extractor --------------------------------------------------------
# "3 መኝታ" => 3
BEDROOM_RE = re.compile(r"(\d+)\s*መኝታ")


def extract_bedrooms(text: str) -> Optional[int]:
    if not text:
        return None
    m = BEDROOM_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


# --- Price extraction with context --------------------------------------------
AREA_UNIT_RE = re.compile(r"\b\d+(?:[,\d]*)\s*(?:ካሬ|sqm|m2)\b", re.IGNORECASE)
DOWNPAYMENT_RE = re.compile(
    r"(\d{1,3})\s*%\s*=\s*(\d+(?:\.\d+)?)\s*" + MILLION_WORD,
    re.IGNORECASE,
)


THOUSANDS_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")
DECIMAL_RE = re.compile(r"^\d+(?:\.\d+)?$")


def _to_number(raw: str) -> Optional[Decimal]:
    """
    Parse a number safely without "concatenating lists", keeping decimals:
    "5.5" stays 5.5, "12,800,000" is 12800000.
    Rejects spaces inside numbers ('98, 99, 110') and malformed commas.
    """
    if not raw:
        return None
    s = raw.strip().rstrip(".")
    if " " in s:
        return None
    whole = s.split(".", 1)[0]
    if "," in whole and not THOUSANDS_RE.match(whole):
        return None
    s2 = s.replace(",", "")
    if not DECIMAL_RE.match(s2):
        return None
    return Decimal(s2)


def is_invalid_sale_price(price: Optional[int]) -> bool:
    """
    Reject obviously bad extracted prices:
      - anything above 10B
      - 9-digit Ethiopian mobile-number bands that lost a leading zero
    Applies to all property types, including LAND.
    """
    if price is None:
        return False
    if price > MAX_VALID_SALE_PRICE_BIRR:
        return True
    return any(low <= price <= high for low, high in MOBILE_RANGE_BANDS)


def normalize_sale_price(price: Optional[int]) -> Optional[int]:
    if price is None or is_invalid_sale_price(price):
        return None
    return price


# "ስፋት 120", "area: 120", "ካሬ: 120". After a bare unit the next number is something else
# ("189 sqm 29,999,000 Birr"), and a number is never the start of a bigger one.
STRICT_AREA_AFTER_RE = re.compile(
    r"(?:(?:area|ስፋት)\s*[:፦-]?|(?:ካሬ\s*ሜትር|ካሬ|sqm|m2)\s*[:፦-])\s*(\d{2,5})(?![\d,])",
    re.IGNORECASE,
)

STRICT_AREA_BEFORE_RE = re.compile(
    r"(?<![\d.,])(\d{2,5})(?:\.\d+)?(?:\s*\(\d+(?:\.\d+)?\))?\s*(?:ካሬ\s*ሜትር|ካሬ|sqm|m2)",   # "158.72 ካሬ" is 158
    re.IGNORECASE,
)

# "ዋጋ 5.5 ሚሊየን", "ጠቅላላ ዋጋ = 5.3 ሚልዮን", "Price: 12,800,000", "Price: 3.9M",
# "ሙሉ ክፍያ 5.7ሚሊዮን" (full payment), "ጠቅላላ ክፍያ 6,800,000ብር" (total payment).
# Not plain "ጠቅላላ": "ጠቅላላ 1000 ካሬው ነው" is a total size.
# (right after a price word, "M" alone also means million).
# A price word may be followed by a few other characters before its number:
# "ዋጋ ............ 60 ሚልዮን", "#ዋጋው 68 ሚሊዮን", "የመሸጫ ዋጋ 🔹በካሽ 5.7 ሚሊየን" (in cash).
# "6,400 000" (a space between thousands) is 6,400,000.
_ANCHOR_NUM = r"(?P<num>\d[\d,\.]*(?:\s\d{3}(?![\d,]))*)"
STRICT_ANCHORED_PRICE_RE = re.compile(
    r"(?:(?:asking\s*price|መሸጫ\s*ዋጋ|መሽጫ\s*ዋጋ|ጠቅላላ\s*ዋጋ|ጠቅላላ\s*ክፍያ|ሙሉ\s*ክፍያ|full\s*payment|price|ዋጋ)"
    r"[^\d\n]{0,30}?(?<!ከ)(?<!ከ\s)"     # not "ከ 2.5 ሚልዮን" (from 2.5 million: a starting price)
    r"|(?:birr|etb)\s*[:፦=\-]{0,2}\s*)"
    + _ANCHOR_NUM + r"\s*"
    r"(?P<million>" + MILLION_WORD + r"|m(?![\w²]))?",
    re.IGNORECASE,
)

# The scraper and the listener store "[MEDIA ONLY]" (or "[PDF ONLY] <file name>")
# as the text of a post that has a photo or a file but no words.
MEDIA_PLACEHOLDERS = ("[media only]", "[pdf only]")
LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)
# A post with fewer characters than this (links left out) has nothing to read.
MIN_READABLE_CHARS = 30
VEHICLE_ADVERT_RE = re.compile(r"\b(?:toyota|yaris|suzuki|vitz|vehicle|mileage)\b", re.IGNORECASE)
CEREMONY_ADVERT_RE = re.compile(r"(?:expo|ቆይታ|ምስጋና)", re.IGNORECASE)


def extract_labeled_sqm(text: str) -> Optional[int]:
    if not text:
        return None

    m = STRICT_AREA_AFTER_RE.search(text)
    if m:
        value = _clean_area_value(m.group(1))
        if value is not None:
            return value

    m = STRICT_AREA_BEFORE_RE.search(text)
    if m:
        value = _clean_area_value(m.group(1))
        if value is not None:
            return value

    return None


# A rent just before a price word: "የተከራዩበትም ዋጋ 40,000" (the price they rent it at), "የኪራይ ዋጋ".
RENT_BEFORE_PRICE_RE = re.compile(r"ኪራይ|ተከራ|መከራየት|\brent|monthly|በወር", re.IGNORECASE)
SENTENCE_END_RE = re.compile(r"[።\n!?•|]|\.\s")


def same_sentence_before(text: str, pos: int, reach: int) -> str:
    """Up to `reach` characters before pos, not going back past the end of the previous sentence."""
    return SENTENCE_END_RE.split(text[max(0, pos - reach): pos])[-1]


def same_sentence_after(text: str, pos: int, reach: int) -> str:
    """Up to `reach` characters from pos, stopping at the end of the sentence."""
    return SENTENCE_END_RE.split(text[pos: pos + reach])[0]


def _extract_first_anchored_price(text: str, skip_rent: bool = True) -> Optional[int]:
    if not text:
        return None

    for match in STRICT_ANCHORED_PRICE_RE.finditer(text):
        # The word right before the price word ("monthly income price 65 million" is a price).
        word_before = (same_sentence_before(text, match.start(), 15).split() or [""])[-1]
        if skip_rent and RENT_BEFORE_PRICE_RE.search(word_before + text[match.start(): match.start() + 3]):
            continue
        # An old price: "ዋጋው 19 ሚሊዮን ነበር" (was), "የበፊት ዋጋ = 8.1 ሚልዮን" (previous price).
        if (re.match(r"\s*(?:ብር\s*)?(?:ነበር|የነበረ)", text[match.end():])
                or re.search(r"በፊት|previous|old\s*price", text[max(0, match.start() - 12): match.start() + 12], re.I)):
            continue
        raw = match.group("num")
        if " " in raw:   # "6,400 000"
            raw = raw.replace(" ", "").replace(",", "")
        if is_likely_phone(raw):
            continue
        value = _to_number(raw)
        if value is None:
            continue
        # Multiply before rounding, so "5.5 ሚሊየን" is 5,500,000 and not 5,000,000.
        if match.group("million") and value < 1000:
            value *= 1_000_000
        elif value < 1000:
            continue  # "ዋጋ 9.5", "ዋጋ 100%": no property sells for under 1,000 birr
        normalized = normalize_sale_price(int(round(value)))
        if normalized is not None:
            return normalized
    return None


def extract_price_birr(text: str, property_type: Optional[str] = None, for_rent: bool = False) -> Optional[int]:
    """The first price after a price word; a rent's own price word ("የኪራይ ዋጋ") counts only for_rent."""
    if not text:
        return None

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)
    return _extract_first_anchored_price(cleaned, skip_rent=not for_rent)


def extract_price_candidates_birr(text: str) -> list[int]:
    if not text:
        return []

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)
    anchored = _extract_first_anchored_price(cleaned)
    return [anchored] if anchored is not None else []


# --- Price per square metre ---------------------------------------------------
# Developers often give a price per m² instead of a total: "በካሬ 85,000 ብር",
# "Price: 110,000 Birr per sqm", "75,000 Birr/sqm", "በካሬ 110ሺ" (ሺ = thousand).
# Such a number is neither the total price nor a size.
_PSQM_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_PSQM_THOUSAND = r"\s*(?:ሺ|k\b)"
_PSQM_CURRENCY = r"(?:\s*(?:ብር|birr|etb))?"
_PSQM_UNIT = r"(?:sqm|sq\.?\s*m\b|m2|m²|square\s*met(?:er|re)|ካሬ(?:\s*ሜትር)?)"
_PSQM_RANGE = (r"(?:\s*(?:[-–—]+|to|እስከ)\s*(?:" + _PSQM_NUM + r")(?P<RANGE_K>" + _PSQM_THOUSAND + r")?"
               + _PSQM_CURRENCY + r")?")
PRICE_PER_SQM_RE = re.compile(
    # Words first: "በካሬ 85,000 ብር", "ለ1 ካሬ 95,000", "price per sqm: 119,395", "በካሬ ዋጋ ከ115,000",
    # "የካሬ ዋጋ=61,750ብር", "ካሬ ዋጋ Semi 105 - 120ሺ", "በካ.ሜ 150,000", "Price/m²: 140,000",
    # "በካሬ semi finished 95,000ብር", "ዋጋ በካሬ 95,000 እስከ 115,000 ብር" (95,000 to 115,000).
    # "1 ካሬ" must not be the end of a size such as "81 ካሬ", and "74 ካሬ ዋጋ 5.5 ሚሊየን"
    # (74 m², price 5.5 million) is a size followed by a total.
    r"(?:በ\s*ካሬ(?:\s*ሜትር)?|በካ\.\s*ሜ\.?|(?:ለ|በ)\s*(?:1|አንድ)\s*ካሬ|(?<![\d.,])1\s*ካሬ"
    r"|(?<!\d)(?<!\d )(?:የ)?ካሬ\s*(?:ሜ(?:ትር)?\s*)?ዋጋ|kare\s*price|(?:per|price\s*/)\s*" + _PSQM_UNIT + r")"
    r"[^\d\n]{0,20}?(?P<before>" + _PSQM_NUM + r")(?P<before_k>" + _PSQM_THOUSAND + r")?" + _PSQM_CURRENCY
    + _PSQM_RANGE.replace("RANGE_K", "before_range_k")
    # Number first: "75,000 Birr/sqm", "95,000 – 110,000 Birr per sqm" (a range keeps its first number),
    # "120,000 ብር በካሬ", "65,000/በካሬ".
    + r"|(?P<after>" + _PSQM_NUM + r")(?P<after_k>" + _PSQM_THOUSAND + r")?" + _PSQM_CURRENCY
    + _PSQM_RANGE.replace("RANGE_K", "after_range_k")
    + r"\s*(?:(?:/|per)\s*(?:በ\s*)?" + _PSQM_UNIT + r"|በካ\.\s*ሜ\.?|በካሬ|ለ\s*ካሬ\s*ሜ)",   # "91,300 ብር ለካሬሜ"
    re.IGNORECASE,
)
# A rent per m² ("በወር በካሬ 5,000") is not a sale price per m².
RENT_WORDS_RE = re.compile(r"በወር|ወርሃዊ|ኪራይ|ታከራ|per\s*month|monthly|/\s*month|\brent", re.IGNORECASE)
PRICE_PER_SQM_MIN, PRICE_PER_SQM_MAX = 1_000, 1_500_000


def _price_per_sqm_value(m) -> Optional[int]:
    value = _to_number(m.group("before") or m.group("after"))
    if value is None:
        return None
    # "110ሺ", or a range whose last number carries the ሺ: "105 - 120ሺ".
    if any(m.group(g) for g in ("before_k", "after_k", "before_range_k", "after_range_k")):
        value *= 1000
    return int(round(value)) if PRICE_PER_SQM_MIN <= value <= PRICE_PER_SQM_MAX else None


def find_price_per_sqm(text: str) -> Optional[int]:
    """The first sale price per m² in the text (birr), or None."""
    if not text:
        return None
    for m in PRICE_PER_SQM_RE.finditer(text):
        if RENT_WORDS_RE.search(text[max(0, m.start() - 40): m.end() + 40]):
            continue
        value = _price_per_sqm_value(m)
        if value is not None:
            return value
    return None


def strip_price_per_sqm(text: str) -> str:
    """The text without its prices per m² (sale or rent), so they are not read as totals or sizes."""
    if not text:
        return text
    return PRICE_PER_SQM_RE.sub(lambda m: " " if _price_per_sqm_value(m) is not None else m.group(0), text)


def is_photo_only(text: str) -> bool:
    """A post with a photo or file and no words (see MEDIA_PLACEHOLDERS)."""
    t = (text or "").lower()
    return any(p in t for p in MEDIA_PLACEHOLDERS)


def strip_links(text: str) -> str:
    return LINK_RE.sub(" ", text or "")


def is_media_link_text(text: str) -> bool:
    """A photo-only post, or a post that is nothing but a link (a link inside a listing is fine)."""
    if not text:
        return False
    if is_photo_only(text):
        return True
    return bool(LINK_RE.search(text)) and len(strip_links(text).strip()) < MIN_READABLE_CHARS


# Adverts for shares in a real-estate company ("አክሲዮን"), not for a property.
SHARE_WORD_RE = re.compile(r"አክሲዮን|አክስዮን|shareholder", re.IGNORECASE)


def is_noise_advert(text: str) -> bool:
    if not text:
        return False
    return bool(VEHICLE_ADVERT_RE.search(text) or CEREMONY_ADVERT_RE.search(text)
                or len(SHARE_WORD_RE.findall(text)) >= 2)


# --- Sale or rent ---------------------------------------------------------------
# Channel footers that list the broker's services ("ኪራይ / ሽያጭ" of houses and cars,
# "the buildings, villas and apartments we post") say nothing about the listing.
FOOTER_RE = re.compile(
    r"ለ\s*ክቡራን\s*ደንበኞቻችን"
    r"|(?:የሚሸጥ|የሚከራይ)[^\n]{0,30}?ቤት\s*ም?\s*(?:ሆነ|ወይም)?\s*መኪና[^\n]{0,30}?(?:ካሎት|ካለዎት|ከልወ|ከለወ|ይላኩ)"
    r"|የህንፃ\s*[፣,]?\s*የቪላ\s*እና\s*አፓርታማ",
)


def strip_footer(text: str) -> str:
    """The text before the channel's footer, if it has one."""
    m = FOOTER_RE.search(text or "")
    return text[:m.start()] if m else (text or "")


# Words only a sale advert uses: "for sale", "selling price", "buyer", "become the owner".
# A rent or an income such an advert mentions is the property's income, not its price.
SALE_MARKERS_RE = re.compile(
    r"የሚሸጥ|ይሸጣል|እየሸጥን|ለሽያጭ|የሽያጭ\s*#?\s*ዋጋ|የ?መሸጫ\s*ዋጋ|የመሽጫ\s*ዋጋ|አጠቃላይ\s*ዋጋ|ጠቅላላ\s*ዋጋ"
    r"|ገዢ|ገዥ|ሲገዙ|ይግዙ|ባለቤት\s*ይሁኑ"
    r"|for\s*sale|asking\s*price|selling\s*price|total\s*price|\bresale\b|\bbuyer",
    re.IGNORECASE,
)
# Words only a rental advert uses: "for rent", "offered for rent", "rent price", "when you rent".
RENT_MARKERS_RE = re.compile(
    r"for\s+rent\b|ለኪራይ\s*የቀረበ|የኪራይ\s*ዋጋ|ሲከራዩ|\brent\s*price|#ለኪራይ"
    r"|የሚከራይ\s*(?:ቤት|አፓርታማ|ኮንዶሚኒየም|ክፍል|ሙሉ\s*ግቢ|ቢሮ|ሱቅ|መጋዘን)",
    re.IGNORECASE,
)
# A rent, income or repayment that a property earns or costs, not one it is offered for.
INCOME_RE = re.compile(
    r"ገቢ|income|yield|\broi\b|ተከራይ(?:ቶ|ቷል)|የተከራየ|ተከራዩበት|rented|የኪራይ_አቅም|rental\s*(?:capacity|status|potential)"
    r"|ተመላሽ|installment|repayment|tenant|የተገመተ|estimated|ቢያከራዩ|ሊያከራዩ|ለማከራየት",
    re.IGNORECASE,
)


def without_income(text: str, reach: int = 40) -> str:
    """The text with everything within `reach` characters of an income word blanked out."""
    if not text:
        return ""
    keep = list(text)
    for m in INCOME_RE.finditer(text):
        for i in range(max(0, m.start() - reach), min(len(text), m.end() + reach)):
            keep[i] = " "
    return "".join(keep)


# --- Cash plus a bank loan -----------------------------------------------------
# "ባንክ 10 ሚሊዮን ብር አለበት ካሽ 5,500,000 ብር" or "1,500,000 ብር ካሽ ... 5,000,000 ብር ባንክ ... የባንክ
# ተመላሽ": the buyer pays the cash part and takes over the bank loan, so the price is both.
# ("በካሽ 5.7 ሚሊየን፣ በባንክ 6 ሚሊየን" are two ways to pay, not two parts.)
_LOAN_AMOUNT = r"(?P<amount>\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?\s*" + MILLION_WORD + r")"
LOAN_RE = re.compile(
    r"(?<!በ)ባንክ\s*[:፦]?\s*" + _LOAN_AMOUNT + r"\s*(?:ብር)?\s*(?=አለበት|[\s\S]{0,30}?(?:ተመላሽ|እዳ))"
    r"|" + _LOAN_AMOUNT.replace("amount", "amount2") + r"\s*(?:ብር)?\s*ባንክ(?=[\s\S]{0,30}?(?:ተመላሽ|እዳ|አለበት))",
    re.IGNORECASE,
)
CASH_RE = re.compile(
    r"(?<!በ)ካሽ\s*[:፦]?\s*" + _LOAN_AMOUNT
    + r"|" + _LOAN_AMOUNT.replace("amount", "amount2") + r"\s*(?:ብር)?\s*(?:ካሽ|ለእጅ)",
    re.IGNORECASE,
)


def _amount_value(m) -> Optional[int]:
    raw = m.group("amount") or m.group("amount2")
    million = re.search(MILLION_WORD, raw, re.IGNORECASE)
    value = _to_number(re.sub(MILLION_WORD + r".*", "", raw, flags=re.IGNORECASE).strip())
    if value is None:
        return None
    return int(round(value * 1_000_000)) if million else int(value)


def cash_plus_loan(text: str) -> Optional[tuple[int, int]]:
    """(cash part, bank loan the buyer takes over), when the text gives both."""
    loan, cash = LOAN_RE.search(text or ""), CASH_RE.search(text or "")
    if not loan or not cash:
        return None
    loan_v, cash_v = _amount_value(loan), _amount_value(cash)
    return (cash_v, loan_v) if loan_v and cash_v else None


# --- Forum title metadata -----------------------------------------------------
FORUM_TITLE_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%\b")


def parse_forum_topic_title(title: str):
    """
    Parses titles like:
      Legacy_Green Valley (ጦርሀይሎች)
    Returns:
      developer_name, project_name, location, completion_pct
    """
    if not title:
        return {
            "developer_name": None,
            "project_name": None,
            "location": None,
            "completion_pct": None,
        }

    raw = title.strip()
    base = raw
    loc_part = None
    if "(" in raw and ")" in raw:
        base = raw.split("(", 1)[0].strip()
        loc_part = raw.split("(", 1)[1].rsplit(")", 1)[0].strip()

    parts = [p for p in re.split(r"[_\-]+", base) if p]
    developer = parts[0].strip() if parts else None
    project = " ".join(p.strip() for p in parts[1:]) if len(parts) > 1 else None

    pct = None
    m_pct = FORUM_TITLE_PERCENT_RE.search(raw)
    if m_pct:
        try:
            pct = int(m_pct.group(1))
        except ValueError:
            pct = None

    location = None
    if loc_part:
        try:
            from topic_resolver import resolve_location  # local import to avoid cycles

            slug, _city = resolve_location(loc_part)
            if slug:
                location = slug.replace("_", " ").title()
            else:
                location = loc_part
        except Exception:
            location = loc_part

    return {
        "developer_name": developer,
        "project_name": project,
        "location": location,
        "completion_pct": pct,
    }

