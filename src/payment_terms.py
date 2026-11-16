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

Prices by payment option and finish (task S37), see price_options():
  price_options                    every price the advert ties to a way of paying or a finish, as
                                   "100: 75,000/m²; slow: 115,000/m²; 65: 5,700,000 (81 m²)"; the option is the
                                   share paid at once (100 = cash), "slow" (paid over time, share not said) or
                                   "list" (no option given, shown only beside labelled prices)
  cash_price_per_sqm, instalment_price_per_sqm, cash_price_birr, instalment_price_birr
                                   the price per m² and the total of one unit when paid at once (100%) and when
                                   paid over time (the smallest share paid at once); totals are of one unit size
"""

from __future__ import annotations

import re
import unicodedata

from processor import MILLION_RE, PRICE_PER_SQM_RE, _price_per_sqm_value, million_value, normalize_numbers

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


# ── Prices by payment option and finish (S37) ──────────────────────────────────
# A way of paying, on the same line as a price or as a heading over the lines below it.
# "ሙሉ ክፍያ" alone is not one: under "ቀስ ብሎ ለሚከፍል" it means the total ("ሙሉ ክፍያ 9.3ሚሊዮን").
_PAYER = r"(?:ለሚከፍ\w*|ለከፈ\w*|ሲከፍ\w*|ከፍለ\w*|የሚከፍ\w*|pay\w*|cash)"
_SHARE_RE = re.compile(r"(?<![\d.])(\d{1,3})\s*%\s*(?:" + _PAYER + r"|በካሬ)", re.I)          # 100% ለሚከፍል, 50% በካሬ
_FOR_SHARE_RE = re.compile(r"for\s*(\d{1,3})\s*%\s*(?:cash|pay)", re.I)                    # for 100% cash payers
_RATIO_RE = re.compile(r"(?<![\d/])(\d{2})\s*/\s*(\d{2})(?![\d/])\s*(?:የክፍያ\s*)?(?:አማራጭ|አከፋፈል|አከፍፈል|payment|option)", re.I)
# Not "in cash": "5 million in cash" beside a bank loan is the buyer's own part of a resale.
_FULL_RE = re.compile(r"ሙሉ\s*(?:ክፍያ\s*)?(?:ለሚከፍ|ለከፈ)|ሙለ\s*ለሚከፍ|በአንዴ\s*(?:ለሚከፍ|ለከፈ|ሲከፍ)|full\s*payment|cash\s*pay"
                      r"|for\s*cash|at\s*once", re.I)
_SLOW_RE = re.compile(r"ቀስ\s*(?:እያለ|እያሉ|ብሎ|በቀስ)|በረጅም\s*ጊዜ|long[\s-]*term\s*pay|instal", re.I)   # not "long-term hold"
_SEMI_RE = re.compile(r"semi[\s-]*finish|ከፊል\s*ፊኒሺንግ|በከፊል\s*ግንባታ|ሰሚ\s*ፊኒሺንግ", re.I)
_FULL_FINISH_RE = re.compile(r"full(?:y)?[\s-]*finish|ሙሉ\s*ፊኒሺንግ|በሙሉ\s*ግንባታ|ፊኒሺንግን?\s*ጨምሮ", re.I)
# An amount on these lines is not the unit's price: a down payment, a discount, a bank's part, an income.
_NOT_A_PRICE_RE = re.compile(r"ቅድመ\s*-?\s*ክፍያ|ቅድሚያ|down\s*-?\s*payment|advance|ቅናሽ|discount|ባንክ|bank|ብድር|loan|ዕዳ|እዳ"
                             r"|ገቢ|income|ኪራይ|rent|በወር|monthly|ኮሚሽን|commission"
                             r"|የበፊት|old\s*price|previous\s*price|\(\s*from\b", re.I)   # the old price: "👉የበፊት ዋጋ = 8.1 ሚልዮን"
_TOTAL_WORD_RE = re.compile(r"ጠቅላላ|total", re.I)
_DISCOUNT_WORD_RE = re.compile(r"ቅናሽ|discount", re.I)
_DISCOUNT_AMOUNT_RE = re.compile(r"\s*(?:ብር|birr|etb)?\s*(?:ቅናሽ|discount)", re.I)
_SIZE_RE = re.compile(r"(?<![\d.,])(\d{2,4})(?:\.\d+)?\s*(?:ካሬ|kare|sqm|sq\.?\s*m\b|m2|m²)", re.I)
_SIZE_EQUALS_RE = re.compile(r"(?<![\d.,])(\d{2,4})(?:\.\d+)?\s*(?:ካሬ|kare|sqm|m2|m²)\s*=\s*(\d{1,3}(?:\.\d+)?)(?![\d,%.])", re.I)
_COMMA_TOTAL_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:,\d{3}){2,})(?![\d,])")
_TOTAL_MIN, _TOTAL_MAX = 300_000, 1_000_000_000


def _labels(line: str):
    """(position, option) for each way of paying a line names: a share paid at once ("100", "65") or "slow"."""
    found = [(m.start(), m.group(1)) for r in (_FOR_SHARE_RE, _SHARE_RE) for m in r.finditer(line) if 0 < int(m.group(1)) <= 100]
    found += [(m.start(), m.group(1)) for m in _RATIO_RE.finditer(line)]
    found += [(m.start(), "100") for m in _FULL_RE.finditer(line)]
    found += [(m.start(), "slow") for m in _SLOW_RE.finditer(line)]
    return sorted(found)


def _line_option(line: str):
    labels = _labels(line)
    return labels[0][1] if labels else None


def _option_at(labels, pos):
    """The way of paying written nearest before a price on its line, else the first one after it."""
    before = [o for p, o in labels if p <= pos]
    return before[-1] if before else (labels[0][1] if labels else None)


def _finish(line: str):
    return "semi-finished" if _SEMI_RE.search(line) else "fully finished" if _FULL_FINISH_RE.search(line) else None


def _totals(line: str):
    """(position, size or None, total) for each total price on a line without its prices per m²."""
    found = [(m.start(), int(m.group(1)), int(round(float(m.group(2)) * 1_000_000))) for m in _SIZE_EQUALS_RE.finditer(line)]
    rest = _SIZE_EQUALS_RE.sub(lambda m: " " * len(m.group(0)), line)          # blanks keep the positions
    found += [(m.start(), None, million_value(m)) for m in MILLION_RE.finditer(rest)]
    rest = MILLION_RE.sub(lambda m: " " * len(m.group(0)), rest)
    found += [(m.start(), None, int(m.group(1).replace(",", ""))) for m in _COMMA_TOTAL_RE.finditer(rest)]
    # "100% ሲከፍሉ = 2.3 ሚልዮን ብር ቅናሽ ያገኛሉ": the size of a discount, not a price.
    return [(p, s, v) for p, s, v in found if _TOTAL_MIN <= v <= _TOTAL_MAX
            and not _DISCOUNT_AMOUNT_RE.match(line, p + len(re.match(r"[\d.,]+\s*\S*", line[p:]).group(0)))]


def price_entries(text: str):
    """Every price tied to a way of paying or a finish: (option, finish, value, per_sqm, size)."""
    t = normalize_numbers(unicodedata.normalize("NFKC", text or ""))
    t = re.sub(r"(?<=\d)ዐ|ዐ(?=\d)", "0", t)          # "1ዐ6ካሬ" is 106 m²
    entries, section, finish_section, size = [], None, None, None
    for line in t.split("\n"):
        if not line.strip():
            continue
        labels, finish = _labels(line), _finish(line)
        option = labels[0][1] if labels else None
        plain = PRICE_PER_SQM_RE.sub(lambda m: " " * len(m.group(0)), line)
        sizes = [(m.start(), int(m.group(1))) for m in _SIZE_RE.finditer(plain)]
        per_sqm = [(m.start(), v) for m, v in ((m, _price_per_sqm_value(m)) for m in PRICE_PER_SQM_RE.finditer(line)) if v]
        # "100% ለከፈለ 35% ቅናሽ = 7ሚልዮን": the price after a cash discount is a price.
        discounted_cash = option == "100" and not _NOT_A_PRICE_RE.search(re.sub(r"ቅናሽ|discount", " ", line, flags=re.I))
        skip_totals = bool(_NOT_A_PRICE_RE.search(line)) and not _TOTAL_WORD_RE.search(line) and not discounted_cash
        totals = [] if skip_totals else _totals(plain)
        if not per_sqm and not totals:
            # A heading: "ቀስ ብሎ ለሚከፍል", "65/35 አከፋፈል"; not a discount ("100% ለሚከፍል 35% ቅናሽ").
            if option and not _DISCOUNT_WORD_RE.search(line):
                section = option
            finish_section = finish or finish_section   # "🔰Fully finished price"
            if sizes:
                size = sizes[0][1]
            continue
        finish = finish or finish_section
        use = lambda pos: _option_at(labels, pos) or section or "list"
        entries += [(use(pos), finish, v, True, None) for pos, v in per_sqm]
        for pos, s, v in totals:
            # The size written before the price on this line ("2መኝታ 106ካሬ … 7.9ሚሊዮን 👉3መኝታ 139ካሬ … 10.3ሚሊዮን").
            before = [z for p, z in sizes if p < pos]
            entries.append((use(pos), finish, v, False, s or (before[-1] if before else size)))
        if sizes:
            size = sizes[-1][1]
    return entries


def _share(option: str) -> float:
    """How much is paid at once: "slow" counts as the least."""
    return -1 if option == "slow" else float(option)


def price_options(text: str, size=None) -> dict:
    """The prices by payment option and finish, and the cash and instalment prices of one unit."""
    entries = price_entries(text)
    keys = ("price_options", "cash_price_per_sqm", "instalment_price_per_sqm", "cash_price_birr", "instalment_price_birr")
    # Only prices tied to a way of paying, or to two finish levels ("only Fully Finished Apartment" in a broker's
    # heading says nothing about price; finish_state already holds it).
    if not any(o != "list" for o, *_ in entries) and len({f for _, f, *_ in entries if f}) < 2:
        return dict.fromkeys(keys)
    shown, seen = [], set()
    for o, f, v, per_sqm, s in entries:
        label = f"{o}{' ' + f if f else ''}: {v:,}" + ("/m²" if per_sqm else f" ({s} m²)" if s else "")
        if label not in seen:
            seen.add(label)
            shown.append(label)
    def first(option, per_sqm, unit=None):
        for o, _, v, p, s in entries:
            if o == option and p == per_sqm and (unit is None or s == unit):
                return v
        return None

    def over_time(per_sqm, unit=None):
        """The price paid over time: the option with the smallest share paid at once ("slow" first)."""
        options = sorted({o for o, _, _, p, s in entries if o not in ("list", "100") and p == per_sqm
                          and (unit is None or s == unit)}, key=_share)
        return first(options[0], per_sqm, unit) if options else None
    # Totals of one unit: the stored size if the advert prices it, else the first unit priced both ways.
    sizes = [s for o, _, _, p, s in entries if not p and s]
    unit = size if size in sizes else next((s for s in sizes if first("100", False, s) and over_time(False, s)),
                                           sizes[0] if sizes else None)
    return {
        "price_options":            "; ".join(shown),
        "cash_price_per_sqm":       first("100", True),
        "instalment_price_per_sqm": over_time(True),
        "cash_price_birr":          first("100", False, unit),
        "instalment_price_birr":    over_time(False, unit),
    }


def extract_terms(text: str, topic_title: str | None = None, size=None) -> dict:
    """All payment terms of one advert; None (or False) where the advert does not say."""
    return {
        **price_options(text, size),
        "discount_schedule":               discount_schedule(text),
        "instalment_count":                instalment_count(text),
        "instalment_months":               instalment_months(text),
        "instalments_follow_construction": instalments_follow_construction(text),
        "interest_free":                   interest_free(text),
        "handover_months":                 handover_months(text),
        "construction_progress_pct":       construction_progress_pct(text, topic_title),
    }
