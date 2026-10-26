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
PHONE_PREFIX_RE = re.compile(r"(?:\+251\s*|0)\s*9\d{1,}", re.IGNORECASE)


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


# Backwards compatibility for older call sites.
_is_phone_like = is_likely_phone


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

# Examples:
#   "Size: 150" / "🟩 Size: 150sqm" / "ካሬ: 150"
LABELED_SQM_RE = re.compile(
    r"(?:🟩\s*)?size\s*[:፦]\s*(\d{2,5})|"
    r"(?:🟩\s*)?size\s*[:፦]\s*(\d{2,5})\s*(?:sqm|m2|m²|ካሬ)?|"
    r"(?:ካሬ)\s*[:፦]\s*(\d{2,5})",
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


def extract_labeled_sqm(text: str) -> Optional[int]:
    if not text:
        return None
    m = LABELED_SQM_RE.search(text)
    if not m:
        return None
    raw = next((g for g in m.groups() if g), None)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


LABELED_PLOT_SQM_RE = re.compile(
    r"(?:area|plot|land|compound|total area|ይዞታ|መሬት|ቦታ)\s*[:፦-]?\s*(\d{2,5})\s*(?:sqm|sq\.?m|m2|m²|ካሬ)?",
    re.IGNORECASE,
)

LABELED_BUILTUP_SQM_RE = re.compile(
    r"(?:built\s*[- ]?up|builtup|built|living area|floor area|constructed|የተገነባ|ተገንብቶ)\s*[:፦-]?\s*(\d{2,5})\s*(?:sqm|sq\.?m|m2|m²|ካሬ)?",
    re.IGNORECASE,
)

GENERIC_AREA_RE = re.compile(r"(\d{2,5})\s*(?:ካሬ|sqm|sq\.?m|m2|m²)", re.IGNORECASE)


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
MILLION_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*" + MILLION_WORD, re.IGNORECASE)


def parse_million_amount(text: str) -> Optional[int]:
    if not text:
        return None
    m = MILLION_RE.search(text)
    if not m:
        return None
    try:
        val = float(m.group("num"))
    except ValueError:
        return None
    return int(val * 1_000_000)


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
PRICE_TAG_RE = re.compile(r"(?:ዋጋ)\s*[:፦]?\s*(\d[\d,\.]*)", re.UNICODE)
BIRR_TAG_RE = re.compile(r"(\d[\d,\.]*)\s*(?:ብር|birr|etb)\b", re.IGNORECASE)
PLAIN_BIG_NUMBER_RE = re.compile(r"\b(\d{7,12})\b")  # 1,000,000+ without commas
PLAIN_BIG_NUMBER_COMMA_RE = re.compile(r"\b(\d{1,3}(?:,\d{3}){2,})\b")  # 1,000,000+
DOWNPAYMENT_RE = re.compile(
    r"(\d{1,3})\s*%\s*=\s*(\d+(?:\.\d+)?)\s*" + MILLION_WORD,
    re.IGNORECASE,
)


THOUSANDS_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")
DECIMAL_RE = re.compile(r"^\d+(?:\.\d+)?$")


def _to_int_num(raw: str) -> Optional[int]:
    """
    Parse a number safely without "concatenating lists".
    Accepts:
      - plain digits (optionally with a single decimal point)
      - comma thousands separators in the correct grouping (e.g. 1,200,000)
    Rejects:
      - spaces inside numbers (e.g. '98, 99, 110')
      - malformed commas
    """
    if not raw:
        return None
    s = raw.strip()
    if " " in s:
        return None
    if "," in s and not THOUSANDS_RE.match(s):
        return None
    s2 = s.replace(",", "")
    if not DECIMAL_RE.match(s2):
        return None
    try:
        return int(float(s2))
    except ValueError:
        return None


def _to_number(raw: str) -> Optional[Decimal]:
    """Like _to_int_num, but keeps decimals: "5.5" stays 5.5, "12,800,000" is 12800000."""
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


PRICE_ANCHOR_RE = re.compile(
    r"(?:ብር|birr|etb|ዋጋ|price|" + MILLION_WORD + ")",
    re.IGNORECASE,
)


def _anchored_number_candidates(text: str) -> list[str]:
    """
    Keyword anchoring:
    Only consider a number as a price if within 3 tokens of a price anchor.
    Also captures combined tokens like '11.6mil' or '2.8m'.
    """
    if not text:
        return []
    tokens = re.findall(r"\S+", text)
    out: list[str] = []
    for i, tok in enumerate(tokens):
        if not re.search(r"\d", tok):
            continue
        window = " ".join(tokens[max(0, i - 3): min(len(tokens), i + 4)])
        if PRICE_ANCHOR_RE.search(window):
            out.append(tok)
    return out


def _anchored_price_values(text: str) -> list[int]:
    if not text:
        return []

    tokens = re.findall(r"\S+", text)
    values: list[int] = []
    for i, tok in enumerate(tokens):
        if not re.search(r"\d", tok):
            continue
        window_tokens = tokens[max(0, i - 3): min(len(tokens), i + 4)]
        window = " ".join(window_tokens)
        if not PRICE_ANCHOR_RE.search(window):
            continue
        if is_likely_phone(tok):
            continue
        m_mil = MILLION_RE.search(tok)
        if m_mil:
            try:
                normalized = normalize_sale_price(int(float(m_mil.group("num")) * 1_000_000))
                if normalized is not None:
                    values.append(normalized)
            except ValueError:
                pass
            continue

        m_num = re.search(r"\d[\d,\.]*", tok)
        if not m_num:
            continue
        raw_value = _to_int_num(m_num.group(0))
        if raw_value is None:
            continue
        if raw_value < 1000:
            if re.search(r"\bmil(?:lion)?\b|million|ሚሊዮን|ሚሊየን", window, re.IGNORECASE):
                raw_value *= 1_000_000
            else:
                continue
        normalized = normalize_sale_price(raw_value)
        if normalized is not None:
            values.append(normalized)
    return values


def extract_price_birr(text: str, property_type: Optional[str] = None) -> Optional[int]:
    """
    Price Context rules:
    - A number followed by ካሬ / SQM / M2 is area, never price.
    - Treat a number as a price if:
        - preceded by 'ዋጋ' OR
        - followed by 'ብር' OR
        - it's a very large number (> 1,000,000)
    Also supports million expressions ("8.5 ሚ", "12 ሚሊዮን").
    """
    if not text:
        return None

    # Remove obvious area mentions so they don't get misread as "big numbers"
    cleaned = AREA_UNIT_RE.sub(" ", text)
    # Phone shield (must happen before any price math)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)

    # Down-payment math: "25% = 2.8m" => total = 2.8M / 0.25
    m = DOWNPAYMENT_RE.search(cleaned)
    if m:
        pct_raw, amt_raw = m.group(1), m.group(2)
        if not is_likely_phone(amt_raw):
            try:
                pct = float(pct_raw)
                amt_m = float(amt_raw)
            except ValueError:
                pct = 0.0
                amt_m = 0.0
            if 1 <= pct <= 99 and amt_m > 0:
                total = int((amt_m * 1_000_000) / (pct / 100.0))
                if total >= 1_000_000:
                    return normalize_sale_price(total)

    # Prefer explicit "million" mentions (anchored)
    million = parse_million_amount(cleaned)
    if million:
        return normalize_sale_price(million)

    # Explicit "ዋጋ"
    m = PRICE_TAG_RE.search(cleaned)
    if m:
        if is_likely_phone(m.group(1)):
            return None
        v = _to_int_num(m.group(1))
        if v is not None:
            # If the tagged number is small (e.g. "12"), it's likely million shorthand missed above.
            return normalize_sale_price(v)

    # Explicit birr suffix
    m = BIRR_TAG_RE.search(cleaned)
    if m:
        if is_likely_phone(m.group(1)):
            return None
        v = _to_int_num(m.group(1))
        if v is not None:
            return normalize_sale_price(v)

    # Keyword-anchored fallback: scan nearby anchors and parse the best candidate.
    candidates = _anchored_price_values(cleaned)
    if candidates:
        best = max(candidates)
        return normalize_sale_price(best)

    return None


def extract_price_candidates_birr(text: str) -> list[int]:
    """
    Returns all plausible birr-denominated price candidates found in text,
    with phone shields and area guards applied.
    Used to implement the "price priority" rule when multiple prices exist.
    """
    if not text:
        return []

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)

    out: list[int] = []

    # Downpayment math yields a derived "total value" candidate
    m = DOWNPAYMENT_RE.search(cleaned)
    if m:
        pct_raw, amt_raw = m.group(1), m.group(2)
        if not is_likely_phone(amt_raw):
            try:
                pct = float(pct_raw)
                amt_m = float(amt_raw)
                if 1 <= pct <= 99 and amt_m > 0:
                    total = int((amt_m * 1_000_000) / (pct / 100.0))
                    normalized = normalize_sale_price(total)
                    if normalized is not None and normalized >= 1_000_000:
                        out.append(normalized)
            except ValueError:
                pass

    for value in _anchored_price_values(cleaned):
        out.append(value)

    # de-dupe while preserving order
    seen: set[int] = set()
    deduped: list[int] = []
    for v in out:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


# Override price extraction with strict anchor-first behavior.
STRICT_ANCHORED_PRICE_RE = re.compile(
    r"(?:price|ዋጋ|birr|etb)\s*[:፦-]?\s*(?P<num>\d[\d,\.]*)\s*(?P<million>mil(?:lion)?|million|ሚ\b|ሚ\.|ሚሊዮን|ሚሊየን)?",
    re.IGNORECASE,
)


def _extract_first_anchored_price(text: str) -> Optional[int]:
    if not text:
        return None

    for match in STRICT_ANCHORED_PRICE_RE.finditer(text):
        raw = match.group("num")
        if is_likely_phone(raw):
            continue
        value = _to_int_num(raw)
        if value is None:
            continue
        if match.group("million") and value < 1000:
            value *= 1_000_000
        normalized = normalize_sale_price(value)
        if normalized is not None:
            return normalized
    return None


def extract_price_birr(text: str, property_type: Optional[str] = None) -> Optional[int]:
    if not text:
        return None

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)
    return _extract_first_anchored_price(cleaned)


def extract_price_candidates_birr(text: str) -> list[int]:
    if not text:
        return []

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)
    anchored = _extract_first_anchored_price(cleaned)
    return [anchored] if anchored is not None else []


STRICT_AREA_AFTER_RE = re.compile(
    r"(?:area|ስፋት|ካሬ|sqm|m2|ካሬ\s*ሜትር)\s*[:፦-]?\s*(\d{2,5})",
    re.IGNORECASE,
)

STRICT_AREA_BEFORE_RE = re.compile(
    r"(\d{2,5})\s*(?:ካሬ\s*ሜትር|ካሬ|sqm|m2)",
    re.IGNORECASE,
)

# "ዋጋ 5.5 ሚሊየን", "ጠቅላላ ዋጋ = 5.3 ሚልዮን", "Price: 12,800,000", "Price: 3.9M"
# (right after a price word, "M" alone also means million).
STRICT_ANCHORED_PRICE_RE = re.compile(
    r"(?:asking\s*price|መሸጫ\s*ዋጋ|ጠቅላላ\s*ዋጋ|price|ዋጋ|birr|etb)\s*[:፦=\-]{0,2}\s*(?P<num>\d[\d,\.]*)\s*"
    r"(?P<million>" + MILLION_WORD + r"|m(?![\w²]))?",
    re.IGNORECASE,
)

# The scraper and the listener store "[MEDIA ONLY]" (or "[PDF ONLY] <file name>")
# as the text of a post that has a photo or a file but no words.
MEDIA_PLACEHOLDERS = ("[media only]", "[pdf only]")
LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)
# A post with fewer characters than this (links left out) has nothing to read.
MIN_READABLE_CHARS = 30
VEHICLE_ADVERT_RE = re.compile(r"\b(?:toyota|yaris|suzuki|vitz)\b", re.IGNORECASE)
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


def _extract_first_anchored_price(text: str) -> Optional[int]:
    if not text:
        return None

    for match in STRICT_ANCHORED_PRICE_RE.finditer(text):
        raw = match.group("num")
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


def extract_price_birr(text: str, property_type: Optional[str] = None) -> Optional[int]:
    if not text:
        return None

    cleaned = AREA_UNIT_RE.sub(" ", text)
    cleaned = re.sub(r"\+251\s*\d{9,12}", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b0[79]\d{8}\b", " ", cleaned)
    return _extract_first_anchored_price(cleaned)


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
_PSQM_RANGE = r"(?:\s*(?:[-–—]+|to)\s*(?:" + _PSQM_NUM + r")(?P<RANGE_K>" + _PSQM_THOUSAND + r")?" + _PSQM_CURRENCY + r")?"
PRICE_PER_SQM_RE = re.compile(
    # Words first: "በካሬ 85,000 ብር", "ለ1 ካሬ 95,000", "price per sqm: 119,395", "በካሬ ዋጋ ከ115,000",
    # "የካሬ ዋጋ=61,750ብር", "ካሬ ዋጋ Semi 105 - 120ሺ", "በካ.ሜ 150,000".
    # "1 ካሬ" must not be the end of a size such as "81 ካሬ", and "74 ካሬ ዋጋ 5.5 ሚሊየን"
    # (74 m², price 5.5 million) is a size followed by a total.
    r"(?:በ\s*ካሬ(?:\s*ሜትር)?|በካ\.\s*ሜ\.?|(?:ለ|በ)\s*(?:1|አንድ)\s*ካሬ|(?<![\d.,])1\s*ካሬ"
    r"|(?<!\d)(?<!\d )(?:የ)?ካሬ\s*(?:ሜ(?:ትር)?\s*)?ዋጋ|per\s*" + _PSQM_UNIT + r")"
    r"[^\d\n]{0,12}?(?P<before>" + _PSQM_NUM + r")(?P<before_k>" + _PSQM_THOUSAND + r")?" + _PSQM_CURRENCY
    + _PSQM_RANGE.replace("RANGE_K", "before_range_k")
    # Number first: "75,000 Birr/sqm", "95,000 – 110,000 Birr per sqm" (a range keeps its first number),
    # "120,000 ብር በካሬ".
    + r"|(?P<after>" + _PSQM_NUM + r")(?P<after_k>" + _PSQM_THOUSAND + r")?" + _PSQM_CURRENCY
    + _PSQM_RANGE.replace("RANGE_K", "after_range_k")
    + r"\s*(?:(?:/|per)\s*" + _PSQM_UNIT + r"|በካ\.\s*ሜ\.?|በካሬ)",
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


def is_noise_advert(text: str) -> bool:
    if not text:
        return False
    return bool(VEHICLE_ADVERT_RE.search(text) or CEREMONY_ADVERT_RE.search(text))


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

