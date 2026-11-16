"""
payment_terms.py
----------------
Payment terms of developer (off-plan) adverts, for the owner's thesis on market-implied discount
rates (task S36). Each function reads the advert's text, in Amharic or English, and returns None
when the advert does not say. run_pipeline.py calls extract_terms(); tests/test_payment_terms.py
checks the rules.

  down_payment_pct                 the smallest down payment offered below 100% ("ቅድመ ክፍያ 20%",
                                   "ከ 10% ቅድሚያ ክፍያ ጀምሮ", "10% downpayment")
  discount_schedule                share paid -> discount, as "65:35; 100:20" ("65% ከፍለው 35% ቅናሽ",
                                   "100% ለሚከፍል 20% ቅናሽ", "For 50% Down payment = 3% Discount")
  instalment_count                 "በ16 ዙር ክፍያ", "5 ጊዜ ክፍያ", "12 instalments"
  instalment_months                how long the instalments run ("ቀሪውን ክፍያ እስከ 3 ዓመት" = 36)
  instalments_follow_construction  payments due as the building goes up ("በግንባታ ሂደት",
                                   "payment based on construction progress")
  interest_free                    "ያለምንም ወለድ", "ከወለድ ነፃ", "interest-free"
  handover_months                  months to handover ("መረከቢያ 2 አመት" = 24, "6 ወር የሚረከብ",
                                   "አሁን የሚረከቡት" = 0); dates in the Ethiopian calendar are not read yet
  construction_progress_pct        how far the building is ("97% የደረሱ", a forum topic "85% ቦሌ ደንበል")
"""

from __future__ import annotations

import re

_PCT = r"(\d{1,3}(?:\.\d+)?)\s*%"
_DP_WORD = (r"(?:(?:ቅድመ|ቅድሚያ)\s*-?\s*ክፍያ|የመጀመሪያ\s*(?:ቅድመ\s*)?ክፍያ|down\s*-?\s*payment|downpayment"
            r"|advance\s*payment|initial\s*payment)")
_DOWN_PAYMENT_RES = (
    re.compile(_DP_WORD + r"[^\n%\d]{0,20}?\(?\s*" + _PCT, re.I),        # ቅድመ ክፍያ (20%), Down payment: 20%
    re.compile(_PCT + r"\s*(?:ብቻ\s*)?" + _DP_WORD, re.I),               # 20% ቅድመ ክፍያ, 10% downpayment
)

_PAID_WORD = (r"(?:ከፍለው|ከፍሎ|ከፈሉ|ለከፈለ|ለከፈሉ|ለሚከፍል|ለሚከፍሉ|ለሚከፍሉት|ሲከፍሉ|ሲከፍል|የከፈለ|የከፈሉ|ለከፈላችሁ"
              r"|ቅድመ\s*ክፍያ|ክፍያ|down\s*-?\s*payment|payment|paid|pay\w*)")
_OFF_WORD = r"\s*(?:ሙሉ\s*|ልዩ\s*|ታላቅ\s*|ተጨማሪ\s*)?(?:ቅናሽ|discount|off\b)"
_DISCOUNT_RES = (
    # 65% ከፍለው 35% ቅናሽ; 100%----ለከፈለ---20% ቅናሽ; For 50% Down payment= 3% Discount
    (re.compile(_PCT + r"[\s\-–—=:.]*" + _PAID_WORD + r"[^%\n]{0,30}?" + _PCT + _OFF_WORD, re.I), "paid_first"),
    # ሙሉ ለሚከፍል 35% ቅናሽ; ሙሉ ክፍያ ለሚከፍሉ 30% ቅናሽ; full payment 10% discount
    (re.compile(r"(?:ሙሉ(?:\s*ክፍያ)?|ሙለ|full(?:y)?\s*pa\w*|cash|ካሽ)\s*(?:ለሚከፍል|ለሚከፍሉ|ለከፈለ|ለከፈሉ|ሲከፍሉ|ለሚከፍሉት)"
                r"[^%\n]{0,20}?" + _PCT + _OFF_WORD, re.I), "full"),
    # 6% discount for 100% payment
    (re.compile(_PCT + _OFF_WORD + r"\s*(?:for|ለ)\s*" + _PCT + r"\s*(?:down\s*-?\s*)?(?:payment|ክፍያ|paid)", re.I), "discount_first"),
)

_INSTALMENT_COUNT_RES = (
    re.compile(r"(?<![\d.])(\d{1,2})\s*ዙር"),                       # በ16 ዙር ክፍያ ("9ኛ ዙር" has ኛ: an ordinal)
    re.compile(r"(?<![\d.])(\d{1,2})\s*ጊዜ\s*ክፍያ"),                 # 5 ጊዜ ክፍያ
    re.compile(r"(?<![\d.])(\d{1,2})\s*instal+ments?", re.I),       # 12 instalments
)
_UNIT = r"(ወር|months?|አመት|ዓመት|years?)"
_PAYMENT_LEFT = r"(?:ቀሪ\w*|ክፍያ\w*|ዙር|አከፋፈል|ወለድ|instal\w*|pay\w*|balance|remaining|interest)"
_INSTALMENT_MONTHS_RES = (
    re.compile(_PAYMENT_LEFT + r"[^\n]{0,40}?(?:እስከ|በ|ለ|within|over|in|for)[ \t]*(\d{1,2})[ \t]*" + _UNIT, re.I),
    re.compile(r"(?<![\d.])(\d{1,2})[ \t]*" + _UNIT + r"[ \t]*(?:ውስጥ[ \t]*)?[^\n\d]{0,15}?(?:ክፍያ|ዙር|instal|pay)", re.I),
)
_HANDOVER_WORD = (r"(?:መረከ(?:ቢ|ብ)ያ|ማስረከ(?:ቢ|ብ)ያ|ርክክብ\w*|የሚረከቡ\w*|ይረከባሉ|የሚረከብ\w*|ይረከቡ\w*|hand\s*-?\s*over|delivery"
                  r"|ዴሊቨሪ|completion)")
_HANDOVER_RES = (
    re.compile(_HANDOVER_WORD + r"[^\n\d]{0,25}?(?:በ\s*|ከ\s*)?(\d{1,2}(?:\.\d)?)\s*" + _UNIT, re.I),   # መረከቢያ 2 አመት
    re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d)?)\s*" + _UNIT + r"[^\n\d]{0,15}?" + _HANDOVER_WORD, re.I),  # 6 ወር የሚረከብ
)
_HANDOVER_NOW_RE = re.compile(r"(?:አሁን|ወዲያውኑ|immediate(?:ly)?|ready\s*for)\s*" + _HANDOVER_WORD, re.I)
_STAGES_RE = re.compile(
    r"ግንባታ[^\n]{0,40}(?:ደረጃ|ሲደርስ|ሲጠናቀቅ|ሲያልቅ|እያያ|ሂደት|እንደ)|(?:ደረጃ|ሲደርስ|ሲጠናቀቅ)[^\n]{0,30}ግንባታ|በግንባታ\s*(?:ፍጥነት|ሂደት)"
    r"|(?:according|linked|tied|based)\s*(?:to|on)\s*(?:the\s*)?construction|construction\s*(?:milestone|progress|stage)"
    r"|as\s*construction", re.I)
_PAYMENT_NEAR_RE = re.compile(r"ክፍያ|ይከፈ|የሚከፈ|ዙር|pay|instal", re.I)
_INTEREST_FREE_RE = re.compile(
    r"ያለ\s*(?:ምንም\s*)?ወለድ|ከወለድ\s*ነፃ|ወለድ\s*አልባ|ወለድ(?:ም)?\s*(?:ሆነ[^\n]{0,20})?(?:የለውም|የለም|አይታሰብም)"
    r"|interest[\s-]*free|no\s*interest|without\s*interest|0\s*%\s*interest", re.I)
_PROGRESS_RES = (
    re.compile(r"(?<![\d.])(\d{1,3})\s*%\s*(?:የደረሰ|የደረሱ|ተጠናቅ\w*|የተጠናቀቀ|የተጠናቀቁ|ያለቀ|ያለቁ|completed|complete|done|finished)", re.I),
    re.compile(r"ግንባታ\w*\s*(?:ከ\s*)?(\d{1,3})\s*%"),
)
_TOPIC_PROGRESS_RE = re.compile(r"^\s*(\d{1,3})\s*%")


def _number(value: str) -> float:
    return float(value)


def down_payment_pct(text: str) -> int | None:
    """The smallest down payment offered below 100% (an advert may offer several)."""
    found = [_number(m.group(1)) for r in _DOWN_PAYMENT_RES for m in r.finditer(text or "")]
    found = [v for v in found if 0 < v < 100]
    return int(round(min(found))) if found else None


def discount_schedule(text: str) -> str | None:
    """Share paid -> discount, as "65:35; 100:20", sorted by the share paid."""
    pairs = set()
    for pattern, kind in _DISCOUNT_RES:
        for m in pattern.finditer(text or ""):
            if kind == "paid_first":
                paid, off = _number(m.group(1)), _number(m.group(2))
            elif kind == "full":
                paid, off = 100.0, _number(m.group(1))
            else:
                off, paid = _number(m.group(1)), _number(m.group(2))
            if 0 < paid <= 100 and 0 < off <= 50 and off < paid:
                pairs.add((paid, off))
    if not pairs:
        return None
    fmt = lambda v: f"{v:g}"
    return "; ".join(f"{fmt(p)}:{fmt(o)}" for p, o in sorted(pairs))


def instalment_count(text: str) -> int | None:
    for pattern in _INSTALMENT_COUNT_RES:
        for m in pattern.finditer(text or ""):
            n = int(m.group(1))
            if 2 <= n <= 60:
                return n
    return None


def _months(value: str, unit: str) -> float:
    return _number(value) * (12 if unit.lower().startswith(("አ", "ዓ", "y")) else 1)


_YEARS_AND_MONTHS_RE = re.compile(r"(\d{1,2})[ \t]*(?:አመት|ዓመት|years?)[ \t]*(?:ከ|እና|and)?[ \t]*(\d{1,2})[ \t]*(?:ወር|months?)", re.I)


def _whole_months(text: str) -> str:
    """"2አመት ከ4ወር" -> "28 ወር", so it is read as one period."""
    return _YEARS_AND_MONTHS_RE.sub(lambda m: f"{int(m.group(1)) * 12 + int(m.group(2))} ወር", text or "")


def instalment_months(text: str) -> int | None:
    text = _whole_months(text)
    for pattern in _INSTALMENT_MONTHS_RES:
        for m in pattern.finditer(text or ""):
            # Not a handover period: "መረከቢያ 2 አመት" right before the number.
            if re.search(_HANDOVER_WORD + r"[^\n\d]{0,10}$", text[max(0, m.start(1) - 25):m.start(1)], re.I):
                continue
            months = _months(m.group(1), m.group(2))
            if 1 <= months <= 120:
                return int(round(months))
    return None


def instalments_follow_construction(text: str) -> bool:
    """A construction-stage phrase with payment words close to it."""
    t = text or ""
    return any(_PAYMENT_NEAR_RE.search(t[max(0, m.start() - 80):m.end() + 80]) for m in _STAGES_RE.finditer(t))


def interest_free(text: str) -> bool:
    return bool(_INTEREST_FREE_RE.search(text or ""))


def handover_months(text: str) -> int | None:
    """The longest handover period stated ("ከ 1 አመት እስከ 2 አመት ... የሚረከቡ" = 24); 0 for "now"."""
    t = _whole_months(text)
    found = [_months(m.group(1), m.group(2)) for r in _HANDOVER_RES for m in r.finditer(t)]
    found = [v for v in found if 0 < v <= 120]
    if found:
        return int(round(max(found)))
    return 0 if _HANDOVER_NOW_RE.search(t) else None


def construction_progress_pct(text: str, topic_title: str | None = None) -> int | None:
    """How far the building is, from the text or from a forum topic titled "97% ካዛንቺስ"."""
    values = [int(m.group(1)) for r in _PROGRESS_RES for m in r.finditer(text or "")]
    if topic_title:
        m = _TOPIC_PROGRESS_RE.match(topic_title)
        if m:
            values.append(int(m.group(1)))
    values = [v for v in values if 1 <= v <= 100]
    return max(values) if values else None


def extract_terms(text: str, topic_title: str | None = None) -> dict:
    """All payment terms of one advert; None (or False) where the advert does not say."""
    return {
        "discount_schedule":               discount_schedule(text),
        "instalment_count":                instalment_count(text),
        "instalment_months":               instalment_months(text),
        "instalments_follow_construction": instalments_follow_construction(text),
        "interest_free":                   interest_free(text),
        "handover_months":                 handover_months(text),
        "construction_progress_pct":       construction_progress_pct(text, topic_title),
    }
