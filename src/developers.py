"""
developers.py
-------------
One name per developer (task S40). run_pipeline.extract_developer() uses find_developer(); the
developer column holds the names written here. tests/test_developers.py checks the rules.

A developer is found, in this order:
  1. the channel is the developer's own (TemerApartmentShop is Temer);
  2. a forum topic's developer: a known one its title names, else the word before "_" in
     championallsites' "Developer_Project (place)" titles ("Legacy_Green Valley" is Legacy);
  3. the first of the known developers the text names, in any spelling below. A name that is also
     a place or a word ("Ayat", "Metro", "Prime", "Champion", "Sunshine", "ላፍቶ") counts only with
     "real estate" or a project word next to it: "አያት 49" is a place, "አያት ሪል እስቴት" a developer;
  4. else the one or two words before "real estate", "properties" or "homes" ("Eniy Realestate"
     is "Eniy Real Estate"), unless they are ordinary words ("our", "luxury", "the best").
"""

from __future__ import annotations

import re

_RE = r"[\s_\-]*(?:real\s*-?\s*estate|realestate|ሪል\s*እ?ስቴ?ት|ሪልስቴት|properties|property|homes|share|አክሲዮን|አ\.ማ|plc|site|ሳይት)"

# canonical name, spellings (a regular expression), the developer's own channels
DEVELOPERS = [
    ("Temer Real Estate", r"temer|ቴምር|ተመር", ("TemerApartmentShop", "Temerproperties2m")),
    ("Gift Real Estate", r"gift" + _RE + r"|ጊፍት", ("giftrealestateee",)),
    ("Ayat Real Estate", r"ayat" + _RE + r"|አያት" + _RE + r"|አያት\s*(?:አ\.?\s*ማ|ማህበር)", ("ApartmentForYouAyatRealEstate",)),
    ("Noah Real Estate", r"noah|ኖህ", ()),
    ("Jambo Real Estate", r"jambo|janbo|ጃምቦ|ጃንቦ", ("jamborealestate", "jamborealestat")),
    ("Bamacon Real Estate", r"bamacon|ባማኮን", ("Bamaconrealestateplc",)),
    ("DMC Real Estate", r"\bdmc\b|ዲ\s*ኤም\s*ሲ|ዲኤምሲ|ዲምሲ", ("dmcrealestateofficial",)),
    ("Reality Real Estate", r"reality" + _RE + r"|ሪያሊቲ", ()),
    ("Palm Real Estate", r"palm" + _RE + r"|ፓልም", ()),
    ("MetroHomes", r"metro[\s_\-]*homes|metrohomes|ሜትሮ\s*ሆምስ|metro" + _RE + r"|metro\s*(?:ቡልቡላ|bulbula)", ()),
    ("Prime Real Estate", r"prime" + _RE + r"|prime[\s_\-]*mill?inn?e?ium|ፕራይም" + _RE, ()),
    ("Champion Real Estate", r"champion" + _RE + r"|champion[\s_\-]*site|ሻምፒዮን" + _RE, ("championrealestate",)),
    ("Zeramba Real Estate", r"z[ae]ramba|ዘራምባ", ()),
    ("Sunstone Real Estate", r"sunstone|ሰንስቶን", ()),
    ("Nexus Real Estate", r"nexus", ()),
    ("Laphto Life Real Estate", r"laphto|ላፍቶ\s*ላይፍ", ()),
    ("Legacy Real Estate", r"legacy" + _RE, ()),
    ("Hosea Real Estate", r"hosea|ሆሴዕ|ሆስይ", ()),
    ("Ovid Real Estate", r"\bovid\b|ኦቪድ", ()),
    ("Century Real Estate", r"century" + _RE, ()),
    ("Flintstone Homes", r"flintstone|ፍሊንትስቶን", ()),
    ("Sunshine Construction", r"sunshine[\s_\-]*(?:construction|real)|ሰንሻይን" + _RE, ()),
    ("Amibara Properties", r"amibara|አሚባራ", ()),
    ("Akoya Properties", r"akoya", ()),
    ("Phison", r"phison|ፊሶን", ()),
    ("Yared Real Estate", r"yared" + _RE + r"|yarad", ()),
    ("Charisma Real Estate", r"charisma", ()),
    ("Dema Hope Real Estate", r"dema[\s_\-]*hope|ደማ\s*ሆፕ", ()),
    ("Tsehay Real Estate", r"tsehay" + _RE + r"|ፀ[ሀሃ]ይ" + _RE, ()),
    ("Joberg Real Estate", r"joberg", ()),
    ("Abay Homes", r"abay[\s_\-]*homes", ()),
    ("Ghion Homes", r"ghion[\s_\-]*homes", ()),
    ("Merit Real Estate", r"merit" + _RE, ()),
    ("Aman Property", r"aman" + _RE, ()),
    ("Compass Property", r"compass" + _RE, ()),
    ("Eniy Real Estate", r"eniy|እንይ\s*ሪል", ()),
    ("Kavod Commercial", r"kavod", ()),
    ("Tekas Real Estate", r"tekas", ()),
    ("Amifa Real Estate", r"amifa", ()),
    ("Amesco Real Estate", r"amesco", ()),
    ("Estifanos Real Estate", r"estifanos" + _RE + r"|estifanos[_\s]*east", ()),
    ("Star Properties", r"star[\s_\-]*propert", ()),
    ("Nor Sheger Real Estate", r"nor[\s_\-]*sheger", ()),
    ("Visco Real Estate", r"visco", ()),
    ("Wood Land Real Estate", r"wood[\s_\-]*land", ()),
    ("Sunflower Real Estate", r"sunflower" + _RE, ()),
    ("Tewabech Real Estate", r"tewabech", ()),
    ("Jenboro Real Estate", r"jenboro|ጀንቦሮ", ()),
    ("Harot Real Estate", r"harot|ሐሮት", ()),
    ("Alsam Properties", r"al[\s\-]*sam\b", ()),
    ("New Life Real Estate", r"new[\s_\-]*life[\s_\-]*real", ()),
    ("Samuel Real Estate", r"samu[ae]+l[\s_\-]*real", ()),
    ("Damla Real Estate", r"damla", ()),
]
DEVELOPER_NAMES = frozenset(name for name, _, _ in DEVELOPERS)
_PATTERNS = [(name, re.compile(spelling, re.IGNORECASE)) for name, spelling, _ in DEVELOPERS]
_CHANNELS = {channel.lower(): name for name, _, channels in DEVELOPERS for channel in channels}

_GENERIC_RE = re.compile(r"(?<![\w'’])([a-z][a-z'’]{2,15}(?:\s+[a-z][a-z'’]{2,15})?)\s*(real\s*-?\s*estate|realestate|properties|homes)\b",
                         re.IGNORECASE)
_ORDINARY = {
    "our", "the", "your", "best", "luxury", "modern", "new", "addis", "ababa", "ethiopia", "ethiopian", "top", "trusted",
    "leading", "premium", "quality", "with", "from", "for", "and", "a", "an", "of", "in", "at", "by", "this", "that", "all",
    "great", "good", "affordable", "smart", "dream", "your", "own", "local", "commercial", "residential", "dealers",
    "buy", "sell", "sale", "rent", "find", "about", "more", "most", "other", "many", "any", "invest", "investment", "is",
    "are", "to", "on", "as", "my", "his", "her", "their", "its", "we", "us", "you", "real", "estate", "broker", "brokers",
    "agent", "agents", "free", "best", "online", "group", "ethio", "home", "house", "apartments", "apartment", "property",
}
_SUFFIX = {"properties": "Properties", "homes": "Homes"}


def _known(t: str):
    """The known developer named first in the text, or None."""
    first = None
    for name, pattern in _PATTERNS:
        m = pattern.search(t or "")
        if m and (first is None or m.start() < first[0]):
            first = (m.start(), name)
    return first[1] if first else None


_TOPIC_MARKS_RE = re.compile(r"\((?:sold\s*out|not\s*active)\)|#", re.IGNORECASE)


def _topic_developer(topic: str):
    """A forum topic named "Developer_Project (place)": championallsites' "Legacy_Green Valley (ጦርሀይሎች)" is Legacy."""
    t = _TOPIC_MARKS_RE.sub(" ", topic).strip()
    m = re.match(r"([A-Za-z][A-Za-z0-9' ]{1,25}?)\s*[_\-]", t)
    if not m:
        return None
    prefix = " ".join(w if w.isupper() and len(w) <= 3 else w.capitalize() for w in m.group(1).split())
    name = prefix if re.search(r"(?:real estate|properties|homes)$", prefix, re.I) else f"{prefix} Real Estate"
    return next((n for n in DEVELOPER_NAMES if n.lower() == name.lower()), name)


def find_developer(text: str, channel: str | None = None, topic: str | None = None) -> tuple[str | None, float]:
    """(developer, confidence): 0.95 for a known developer or a forum topic's, 0.85 for a name before "real estate".
    A forum topic's own developer comes before one the post's words name."""
    if channel:
        own = _CHANNELS.get(channel.rstrip("/").rsplit("/", 1)[-1].lstrip("@").lower())
        if own:
            return own, 0.95
    if topic:
        named = _known(topic) or _topic_developer(topic)
        if named:
            return named, 0.95
    t = text or ""
    named = _known(t)
    if named:
        return named, 0.95
    for m in _GENERIC_RE.finditer(t):
        words = [w for w in m.group(1).lower().split() if w not in _ORDINARY]
        if words and len(words) == len(m.group(1).split()):
            suffix = _SUFFIX.get(m.group(2).lower(), "Real Estate")
            return " ".join(w.capitalize() for w in words) + " " + suffix, 0.85
    return None, 0.0
