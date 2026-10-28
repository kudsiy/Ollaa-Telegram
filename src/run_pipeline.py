import re
import json
import unicodedata
from datetime import datetime

from locations import NOISE, UNKNOWN, city_of, find_location
from processor import (
    LABELED_BUILTUP_SQM_RE,
    MILLION_RE,
    MILLION_WORD,
    RENT_MARKERS_RE,
    SALE_MARKERS_RE,
    _clean_area_value,
    cash_plus_loan,
    extract_bedrooms,
    extract_area_breakdown,
    extract_labeled_location,
    extract_labeled_sqm,
    extract_price_birr,
    extract_price_candidates_birr,
    find_price_per_sqm,
    MIN_READABLE_CHARS,
    million_value,
    is_media_link_text,
    is_photo_only,
    is_noise_advert,
    parse_forum_topic_title,
    parse_million_amount,
    same_sentence_after,
    same_sentence_before,
    strip_footer,
    strip_links,
    strip_price_per_sqm,
    without_income,
)


RENT_ONLY_CHANNELS = {
    "https://t.me/Bet_afri",
    "https://t.me/Bet_afri_Business",
    "https://t.me/Betafrivip",
}
# No home or shop rents for this much a month: an advert whose price is at least this,
# with no words only a rental advert uses, is a sale ("Price: 21,000,000 ETB").
SALE_ONLY_PRICE = 5_000_000


def is_rent_only_channel(source_channel) -> bool:
    return bool(source_channel) and source_channel.rstrip("/") in {c.rstrip("/") for c in RENT_ONLY_CHANNELS}


class ValuationPipeline:
    def __init__(self):

        # ==========================================================
        # INTENT VOCABULARY
        # ==========================================================
        # ("furnished" and "guest house" are not rent signals: houses for sale are furnished
        # guest houses too.)
        self.RENT_SIGNALS = [
            "ኪራይ", "rent", "for rent", "monthly", "per month",
            "deposit", "advance",
            "በወር", "ወርሃዊ", "ቅድሚያ", "አጋር",
            # @Bet_afri specific patterns
            "የሚከራይ",    # for rent (house)
            "ለሚከራዩ",    # for those renting
            "ሚከራይ",     # partial match
            "ይከራያል",    # is available for rent
        ]

        self.SALE_SIGNALS = [
            "ሽያጭ", "for sale", "sale", "selling",
            "ownership", "title deed", "ካርታ",
            "million", "ሚሊዮን", "በሽያጭ", "በሺያጭ", "ሺያጭ", "ሚሊየን",
        ]

        # ==========================================================
        # KNOWN DEVELOPERS
        # ==========================================================
        self.KNOWN_DEVELOPERS = {
            "noah": "Noah Real Estate",
            "gift": "Gift Real Estate",
            "ayat": "Ayat Real Estate",
            "flintstone": "Flintstone Homes",
            "sunshine": "Sunshine Construction",
            "yarad": "Yared Real Estate",
            "amibara": "Amibara Properties",
            "metro": "MetroHomes",
            "prime": "Prime Real Estate",
            "zaramba": "Zaramba Real Estate",
            "sunstone": "Sunstone",
            "nexus": "Nexus",
            "legacy": "Legacy Real Estate",
            "laphto": "Laphto Life Real Estate",
            "champion": "Champion",
            "jambo": "Jambo Real Estate",
            "temer": "Temer",
            "hosea": "Hosea",
            "bamacon": "Bamacon",
            "phison": "Phison",
            "ovid": "Ovid",
            "akoya": "Akoya Properties",
            "century": "Century",
            # Amharic
            "ኖህ": "Noah Real Estate",
            "ጊፍት": "Gift Real Estate",
            "አያት": "Ayat Real Estate",
            "ፍሊንትስቶን": "Flintstone Homes",
            "ሀውሲንግ": "housing",
            "ጀንቦሮ": "Jenboro",
            "ቴምር": "Temer",
            "ሻምፒዮን": "Champion",
            "ዲምሲ": "DMC Real",
            "ጃንቦ": "Jambo",
            "ሆስይ": "Hosea",
            "ባማኮን": "Bamacon",
            "ፊሶን": "Phison",
            "ኦቪድ": "Ovid",
            "ሐሮት": "Harot",
            "አሚባራ": "Amibara Properties",
            "ሜትሮ": "MetroHomes",
        }
        self.DEVELOPER_NAMES = set(self.KNOWN_DEVELOPERS.values())

        # ==========================================================
        # PROPERTY TYPES — RESIDENTIAL
        # ==========================================================
        self.TYPE_CONDOMINIUM = [
            "condominium", "condo", "ኮንዶሚኒየም", "ኮንደሚኒየም", "ኮንዶ",
            "40/60", "20/80",
        ]

        self.TYPE_APARTMENT = [
            "apartment", "flat", "አፓርታማ", "አፖርትመንት",
            "ፔንትሃውስ", "penthouse",
        ]

        self.TYPE_VILLA = [
            "villa", "ቪላ", "house", "detached",
            "g+0", "g+1", "g+2", "g+3", "g+4", "ቤት",
        ]

        self.TYPE_TOWNHOUSE = ["townhouse", "row house", "duplex"]

        # ==========================================================
        # PROPERTY TYPES — COMMERCIAL & INDUSTRIAL
        # ==========================================================
        # ("store" and "storage" are not: houses list "laundry / store" among their rooms.)
        self.TYPE_WAREHOUSE = [
            "warehouse", "መጋዘን",
            "ware house", "ware-house", "logistics",
        ]

        self.TYPE_COMMERCIAL = [
            "shop", "ሱቅ", "showroom", "retail", "commercial",
            "supermarket", "ሱፐርማርኬት", "ሱቃ", "ሱቆ",
        ]

        self.TYPE_OFFICE = [
            "office", "ቢሮ", "office space", "ፅህፈት ቤት",
            "ፅ/ቤት", "coworking", "workspace",
        ]

        # ==========================================================
        # PROPERTY TYPES — LAND
        # ==========================================================
        self.TYPE_LAND = [
            "land", "plot", "መሬት", "ይዞታ", "ቦታ",
            "vacant", "ባዶ መሬት",
        ]

        # ==========================================================
        # PROPERTY SUBTYPES
        # (more granular classification after primary type)
        # ==========================================================
        self.SUBTYPE_STUDIO   = ["studio", "ስቱዲዮ"]
        self.SUBTYPE_G0       = [r'\bg\+?0\b', r'ground\s*floor\s*only']
        self.SUBTYPE_G1       = [r'\bg\+1\b']
        self.SUBTYPE_G2       = [r'\bg\+2\b']
        self.SUBTYPE_G3       = [r'\bg\+3\b']
        self.SUBTYPE_G4       = [r'\bg\+4\b']
        self.SUBTYPE_G5_PLUS  = [r'\bg\+(?:[5-9]|\d{2,})\b']

        # ==========================================================
        # FINISH STATES
        # ==========================================================
        self.FINISH_STATES = {
            "unfinished":    ["unfinished", "bare", "ያልተጠናቀቀ", "under construction", "ግንባታ ላይ"],
            "semi_finished": ["semi finished", "semi-finished", "ግማሽ"],
            "finished":      ["finished", "ready", "ተጠናቋል", "fully finished"],
            "furnished":     ["furnished", "fully furnished", "እቃ ቤት", "የቤት እቃ"],
        }

        # ==========================================================
        # LOCATIONS: the place table, its aliases and the Sheger City
        # list now live in locations.py, shared with topic_resolver.py,
        # dedup_and_fix_locations.py and geocoder.py (task S6).
        # ==========================================================

    # ==========================================================
    # NORMALIZATION HELPER
    # ==========================================================
    def _norm(self, text: str) -> str:
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", text).lower()
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    # ==========================================================
    # STEP 1 — INTENT
    # ==========================================================
    def has_rent_marker(self, text) -> bool:
        """Words only a rental advert uses, outside the footer and the property's income
        ("estimated rent price" in a sale advert is not one)."""
        return bool(RENT_MARKERS_RE.search(without_income(self._norm(strip_footer(text)))))

    def classify_intent(self, text, source_channel=None):
        # Channel-level override: these channels exclusively list rentals.
        if is_rent_only_channel(source_channel):
            return "RENT", 0.95

        t = self._norm(strip_footer(text))

        # Words only a sale advert or only a rental advert uses decide on their own; when
        # both occur, the advert says what it is first ("ለሽያጭ የቀረበ … the neighbourhood's
        # rent is 25,000"). A sale price per m² ("በካሬ 110,000 ብር") is a sale word too.
        sale_marker = SALE_MARKERS_RE.search(t)
        rent_marker = RENT_MARKERS_RE.search(without_income(t))
        sale_at = sale_marker.start() if sale_marker else None
        rent_at = rent_marker.start() if rent_marker else None
        if sale_at is None and find_price_per_sqm(unicodedata.normalize("NFKC", strip_footer(text))):
            sale_at = len(t)   # no position of its own: rent words, if any, come first
        if sale_at is not None and (rent_at is None or sale_at < rent_at):
            return "SALE", 0.9 if rent_at is None else 0.7
        if rent_at is not None:
            return "RENT", 0.9 if sale_at is None else 0.7

        # A rent or income that a property earns ("በወር 300,000 ብር ገቢ", "Monthly income")
        # does not make its advert a rental.
        t = without_income(t)
        sale_score = sum(1 for w in self.SALE_SIGNALS if w in t)
        rent_score = sum(1 for w in self.RENT_SIGNALS if w in t)

        if any(w in t for w in ["advance", "monthly", "per month", "ኪራይ", "በወር"]):
            sale_score -= 2

        rent_context  = any(x in t for x in ["ኪራይ", "በወር", "rent", "for rent", "monthly", "per month", "ወርሃዊ"])
        core_sale     = ["ሽያጭ", "for sale", "sale", "selling", "ownership", "title deed", "ካርታ", "በሽያጭ", "በሺያጭ", "ሺያጭ"]
        monetary_sale = ["million", "ሚሊዮን", "ሚሊየን"]

        if rent_context and not any(c in t for c in core_sale) and any(m in t for m in monetary_sale):
            sale_score = 0

        if sale_score > rent_score and sale_score > 0:
            return "SALE", min(0.9, 0.6 + 0.1 * sale_score)
        if rent_score > sale_score and rent_score > 0:
            return "RENT", min(0.9, 0.6 + 0.1 * rent_score)
        if sale_score > 0 and rent_score > 0:
            return "MIXED", 0.4
        return "UNKNOWN", 0.0

    # ==========================================================
    # STEP 2 — LISTING CLASS
    # ==========================================================
    def classify_listing_class(self, text, intent=None):
        t = self._norm(text)

        if any(x in t for x in ["looking for", "እፈልጋለሁ"]):
            return "INQUIRY"

        # Media-only placeholders (used by listener for attachment-only posts)
        if is_media_link_text(text) or any(x in t for x in ["[media only]", "[pdf only]"]):
            return "MEDIA_PENDING"

        if is_noise_advert(text):
            return "ADVERTISEMENT"

        # Advertisement / promo posts without a specific unit price.
        if (("አዘጋጅተናል" in t) or ("discount" in t)) and extract_price_birr(t) is None:
            return "ADVERTISEMENT"

        # Strict advertisement tagging for developer brands when no unit-specific details exist.
        if any(x in t for x in ["gift", "jambo", "alsam", "ጊፍት", "ጃንቦ"]):
            if extract_price_birr(t) is None and extract_area_from_text(t) is None:
                return "ADVERTISEMENT"

        # Addis-specific source signals:
        # - Payment-plan / yearly terms are typical for developer presales.
        # - "Owner" language is typical for direct listings.
        if any(x in t for x in ["ክፍያ", "በአመት"]):
            return "DEVELOPER"
        if "ባለቤት" in t:
            return "DIRECT_LISTING"

        # As in classify_intent: the footer and the property's income do not count, and an
        # intent decided by words only a sale (or rental) advert uses is the listing's.
        body = without_income(self._norm(strip_footer(text)))
        rent_present = any(w in body for w in self.RENT_SIGNALS) or intent == "RENT"
        sale_present = (any(w in body for w in self.SALE_SIGNALS) or intent == "SALE") and intent != "RENT"

        dev_name, dev_conf = self.extract_developer(text)
        is_known_developer = dev_name in self.DEVELOPER_NAMES and dev_conf >= 0.9

        project_signals = [
            "እያስገነባ", "መንደር", "የካሬ አማራጮች", "የካሬ አማራጭ",
            "options", "unit types",
        ]

        if sale_present and is_known_developer and any(p in t for p in project_signals):
            return "PROMOTIONAL"

        if any(x in t for x in ["call", "dm", "inbox"]) and sale_present:
            return "PURE_SALE"

        if rent_present and sale_present:
            if intent == "SALE":
                return "PURE_SALE"
            if intent == "RENT":
                return "PURE_RENT"
            return "MIXED"

        if rent_present and not sale_present:
            return "PURE_RENT"

        if sale_present and not rent_present:
            return "PURE_SALE"

        return "INVALID"

    def is_strictly_noise(self, text):
        text_lower = text.lower().strip()
        # Kill Articles (No price/size, just bank/inflation talk) [cite: 1]
        if 'inflation' in text_lower and 'bank' in text_lower: return True
        if '1 million homes' in text_lower: return True
        # Kill Holiday Greetings [cite: 1]
        if 'እንኳን አደረሳችሁ' in text_lower and 'apartment' not in text_lower: return True
        # Kill short garbage, including posts that are only a link [cite: 1].
        # A link inside a real listing does not make it noise (photo-only posts
        # are handled before this, see process()).
        if len(strip_links(text_lower).strip()) < MIN_READABLE_CHARS: return True
        return False
    def extract_g_plus_level(self, text):
        t = self._norm(text)
        m = re.search(r'(?:\bg|ጂ)\s*\+\s*(\d{1,2})\b', t)   # "G+8", "B2 + G + 8", "ጂ+2"
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    # An apartment word, also in hashtags ("#AddisAbabaApartments"). Not "ለአፓርታማ"
    # (suitable for apartments, said of land).
    APARTMENT_WORD_RE = re.compile(r"apartment|\bflats?\b|penthouse|(?<!ለ)(?:አፓርታማ|አፖርትመንት|አፓርትመንት|ፔንትሃውስ)")
    HASHTAG_RE = re.compile(r"#\S+")
    # The floor a flat is on: "6F", "4ኛ ፎቅ", "ደረጃ=4ኛ", "5th floor", "Floor: 3".
    UNIT_FLOOR_RE = re.compile(
        r"\b\d{1,2}f\b|\d\s*ኛ\s*(?:ፎቅ|ፍሎር|ወለል)|ደረጃ\s*[=:፦-]?\s*\d|\b\d{1,2}(?:st|nd|rd|th)\s*floor"
        r"|\bfloor\s*[:፦]\s*\d")
    # One flat in a tall building: its floor, "3 Beds | 2 Baths", or "በወለል 4 ቤቶች" (4 flats a floor).
    UNIT_IN_BUILDING_RE = re.compile(UNIT_FLOOR_RE.pattern + r"|\b\d\s*beds?\b|በ\s*(?:ወለል|ፍሎር|floor)\s*\d+\s*(?:ቤት|አባወራ)")
    # A whole building for sale: "ህንፃ ለሽያጭ", "ለሽያጭ የቀረበው ህንፃ" (the building offered for sale),
    # "the building owner", "building for sale", "ከ1ኛ እስከ 3ኛ ፎቅ" (from the 1st to the 3rd floor).
    WHOLE_BUILDING_RE = re.compile(
        r"ህንፃ\s*ለሽያጭ|(?:የሚሸጥ|ለሽያጭ)[^\n]{0,15}?ህንፃ|ሙሉ\s*ህንፃ|የህንፃ\s*ባለቤት|ህንፃው\s*(?:ይሸጣል|ለሽያጭ)"
        r"|ከ\s*\d+\s*ኛ\s*እስከ\s*\d+\s*ኛ"
        r"|building\s*for\s*sale|whole\s*building|mixed[\s-]*used?\s*building")

    def classify_type(self, text):
        text = strip_footer(text)
        t = self._norm(text)
        g_plus_level = self.extract_g_plus_level(t)

        has_bedroom = "መኝታ" in t or "bed" in t
        has_floor_context = g_plus_level is not None or "ፎቅ" in t or "floor" in t
        apartment_word = bool(self.APARTMENT_WORD_RE.search(t))

        if is_media_link_text(text):
            return "MEDIA_LINK", 0.99

        if is_noise_advert(text):
            return "ADVERTISEMENT", 0.99

        if any(x in t for x in ["studio", "ስቱዲዮ"]):
            return "STUDIO", 0.95

        # One flat, shop or office in a G+12 building is not the building.
        unit_in_tall_building = False
        if g_plus_level is not None and g_plus_level >= 5:
            if (apartment_word or self.UNIT_IN_BUILDING_RE.search(t)) and not self.WHOLE_BUILDING_RE.search(t):
                # A flat, unless the text clearly offers an office, shop or warehouse ("ቢሮ" and
                # "ሱቅ" alone are often just the building's other floors).
                clearly_other = (any(w in t for w in self.TYPE_WAREHOUSE)
                                 or any(w in t for w in self.TYPE_OFFICE if w != "ቢሮ")
                                 or any(w in t for w in self.TYPE_COMMERCIAL if w not in ("ሱቅ", "ሱቃ", "ሱቆ")))
                if apartment_word and not clearly_other:
                    return "APARTMENT", 0.9
                unit_in_tall_building = True   # a shop or office if the text says so, else a flat
            else:
                return "COMMERCIAL_BUILDING", 0.95

        # Commercial / Industrial first (before residential checks)
        if any(w in t for w in self.TYPE_WAREHOUSE) or "መጋዘን" in t:
            return "WAREHOUSE", 0.95

        # "ቢሮ" (office) appears in channel footers; only treat it as a signal
        # when it occurs in the first 300 characters of the message.
        _office_no_biro = [w for w in self.TYPE_OFFICE if w != "ቢሮ"]
        _biro_in_prefix = "ቢሮ" in t[:300]
        if any(w in t for w in _office_no_biro) or _biro_in_prefix:
            return "OFFICE", 0.9

        # "ሱቅ" / "ሱቃ" / "ሱቆ" (shop) appear in footers; same 300-char rule.
        _suq_words = {"ሱቅ", "ሱቃ", "ሱቆ"}
        _commercial_no_suq = [w for w in self.TYPE_COMMERCIAL if w not in _suq_words]
        _suq_in_prefix = any(w in t[:300] for w in _suq_words)
        if any(w in t for w in _commercial_no_suq) or _suq_in_prefix:
            return "COMMERCIAL", 0.9

        # Residential
        if any(w in t for w in self.TYPE_CONDOMINIUM) or any(w in t for w in ["ኮንዶሚኒየም", "ኮንዶ"]):
            return "CONDOMINIUM", 0.97

        if unit_in_tall_building:
            return "APARTMENT", 0.9

        # A G+1 to G+4 house with its bedrooms is a villa, unless one of its floors is
        # what is offered ("4ኛ ፎቅ", "5th floor") or its text, not just a hashtag
        # ("#rohaapartment" is a brand), calls it an apartment.
        if (g_plus_level is not None and not self.UNIT_FLOOR_RE.search(t)
                and not self.APARTMENT_WORD_RE.search(self.HASHTAG_RE.sub(" ", t))):
            return "VILLA", 0.9

        if apartment_word or re.search(r"(?<!ለ)አፓርት", t) or "ፎቅ ቤት" in t:
            return "APARTMENT", 0.95

        if re.search(r"villa|ቪላ", t):
            return "VILLA", 0.9

        # A home on a given floor ("ደረጃ=4ኛ", "3rd floor") of a building is a flat.
        if ("መኝታ ቤት" in t and has_floor_context) or (g_plus_level is None and self.UNIT_FLOOR_RE.search(t)):
            return "APARTMENT", 0.95

        if any(w in t for w in self.TYPE_TOWNHOUSE):
            return "TOWNHOUSE", 0.9

        if any(w in t for w in self.TYPE_VILLA) or any(w in t for w in ["ቪላ", "የመኖሪያ ቤት"]):
            return "VILLA", 0.9
            
        if "ቤት" in t and not has_floor_context:
            return "VILLA", 0.85

        if any(w in t for w in self.TYPE_LAND) or any(w in t for w in ["ዲጂታል ካርታ", "ካርታ", "መሬት", "ቦታ"]):
            if not has_bedroom and not has_floor_context:
                return "LAND", 0.9

        # Fallback rules
        if "መኝታ" in t and re.search(r'\b[gb]\+\d+\b', t):
            return "APARTMENT", 0.85

        if "ዲጂታል ካርታ" in t or "ካርታ አለው" in t:
            beds, _ = self.extract_rooms(text)
            area = extract_area_from_text(text)
            if area is not None and area > 200 and beds is None:
                return "LAND", 0.85

        # Single-room listings
        if any(x in t for x in ["አንድ ክፍል", "1 ክፍል", "one room"]):
            return "SINGLE_ROOM", 0.9

        return "UNKNOWN", 0.0

    # ==========================================================
    # STEP 3b — PROPERTY SUBTYPE
    # More granular classification within the primary type.
    # e.g. VILLA → G+1, G+2; APARTMENT → STUDIO
    # ==========================================================
    def classify_subtype(self, text, p_type):
        t = self._norm(text)

        if p_type in ("APARTMENT", "CONDOMINIUM"):
            if any(re.search(p, t) for p in self.SUBTYPE_STUDIO):
                return "STUDIO"

        if p_type in ("VILLA", "TOWNHOUSE", "COMMERCIAL", "COMMERCIAL_BUILDING", "WAREHOUSE"):
            if any(re.search(p, t) for p in self.SUBTYPE_G5_PLUS):
                return "G+5+"
            if any(re.search(p, t) for p in self.SUBTYPE_G4):
                return "G+4"
            if any(re.search(p, t) for p in self.SUBTYPE_G3):
                return "G+3"
            if any(re.search(p, t) for p in self.SUBTYPE_G2):
                return "G+2"
            if any(re.search(p, t) for p in self.SUBTYPE_G1):
                return "G+1"
            if any(re.search(p, t) for p in self.SUBTYPE_G0):
                return "G+0"

        return None

    # ==========================================================
    # STEP 4 — ROOMS
    # ==========================================================
    def extract_rooms(self, text):
        t = self._norm(text)

        bed = None
        # Prefer Amharic "X መኝታ" pattern.
        bed = extract_bedrooms(t)
        if bed is None:
            m_bed = re.search(r'(?:ባለ\s*|)\s*(\d+)\s*(?:bedroom|bed)', t)
            if m_bed:
                bed = int(m_bed.group(1))

        bath = None
        m_bath = re.search(r'(\d+)\s*(?:መታጠቢያ|bath)', t)
        if m_bath:
            bath = int(m_bath.group(1))

        return bed, bath

    # ==========================================================
    # STEP 5 — AREA RESOLUTION
    # ==========================================================
    def resolve_area(self, intent, p_type, raw_area, text):
        if not raw_area:
            return None, None, 0.0, 0.0

        inferred_plot, inferred_built = extract_area_breakdown(text)

        # A whole building's area is its land or the ground it stands on, not its floor
        # area, unless the text calls a size built-up or floor area.
        if p_type == "COMMERCIAL_BUILDING":
            built = next((v for v in (_clean_area_value(m.group(1)) for m in LABELED_BUILTUP_SQM_RE.finditer(text))
                          if v is not None), None)
            return inferred_plot or raw_area, built, 0.9, 0.9 if built else 0.0

        # Offices, shops and warehouses: the floor area: a size called built-up, else the
        # "Total ....... 1500 m2" of several listed spaces.
        if p_type in ("WAREHOUSE", "OFFICE", "COMMERCIAL"):
            labelled = next((v for v in (_clean_area_value(m.group(1)) for m in LABELED_BUILTUP_SQM_RE.finditer(text))
                             if v is not None), None)
            total = TOTAL_AREA_RE.search(text)
            total = _clean_area_value(total.group(1)) if total else None
            return None, labelled or total or inferred_built or raw_area, 0.0, 0.9

        if intent not in ["SALE", "MIXED", "RENT"]:
            return None, None, 0.0, 0.0

        t = self._norm(text)

        built_keywords = ["built", "built-up", "living area", "floor area", "constructed", "ተገንብቶ", "የተገነባ"]
        plot_keywords  = ["plot", "land", "compound", "total area", "ይዞታ", "መሬት", "ቦታ"]

        if p_type in ("APARTMENT", "CONDOMINIUM"):
            built = inferred_built or raw_area
            # Over 1,000 m² is the site or the building ("Apartment 3B+G+14 4000 ካሬ"), not one flat.
            return None, built if built and built <= 1000 else None, 0.0, 0.95

        if inferred_plot is not None or inferred_built is not None:
            return inferred_plot, inferred_built, 0.95 if inferred_plot is not None else 0.0, 0.95 if inferred_built is not None else 0.0

        if any(w in t for w in plot_keywords):
            plot = raw_area
            other = find_additional_area_diff(raw_area, text)
            if other is not None:
                return plot, other, 0.95, 0.7
            return plot, None, 0.95, 0.0

        if any(w in t for w in built_keywords):
            built = raw_area
            other = find_additional_area_diff(raw_area, text)
            if other is not None:
                return other, built, 0.7, 0.95
            return None, built, 0.0, 0.95

        if p_type in ("VILLA", "TOWNHOUSE"):
            return raw_area, None, 0.7, 0.0

        if p_type == "LAND":
            return raw_area, None, 0.95, 0.0

        return None, None, 0.0, 0.0

    # ==========================================================
    # STEP 6 — PAYMENT SEMANTICS
    # ==========================================================
    def extract_payment(self, text):
        t = self._norm(text)
        if "cash only" in t or "no bank" in t:
            return "CASH_ONLY"
        if "bank" in t or "loan" in t or "ባንክ" in t:
            return "BANK_POSSIBLE"
        return "UNKNOWN"

    # ==========================================================
    # STEP 6b — FINANCING DETAILS
    # ==========================================================
    def extract_financing_details(self, text):
        t = self._norm(text)
        bank_loan_pct = None
        down_payment_pct = None

        if "20/80" in t:
            down_payment_pct = 20
            bank_loan_pct = 80
        if "40/60" in t:
            down_payment_pct = 40
            bank_loan_pct = 60

        m_loan = re.search(r'(\d{1,3})\s*%\s*(?:የባንክ\s*ብድር|bank loan|loan|ብድር)', t)
        if m_loan:
            try:
                bank_loan_pct = int(m_loan.group(1))
            except ValueError:
                pass

        m_dp = re.search(r'(\d{1,3})\s*%\s*(?:down ?payment|የመጀመሪያ\s*ክፍያ|ቅድሚያ|advance)', t)
        if m_dp:
            try:
                down_payment_pct = int(m_dp.group(1))
            except ValueError:
                pass

        if bank_loan_pct is not None and down_payment_pct is None and 0 < bank_loan_pct < 100:
            down_payment_pct = 100 - bank_loan_pct
        if down_payment_pct is not None and bank_loan_pct is None and 0 < down_payment_pct < 100:
            bank_loan_pct = 100 - down_payment_pct

        return bank_loan_pct, down_payment_pct

    # ==========================================================
    # STEP 7 — FINISH STATE
    # ==========================================================
    def extract_finish(self, text):
        t = self._norm(text)
        for k, words in self.FINISH_STATES.items():
            if any(w in t for w in words):
                return k, 0.9
        return "unknown", 0.0

    # ==========================================================
    # STEP 8 — DEVELOPER
    # ==========================================================
    def extract_developer(self, text):
        t = self._norm(text)
        for key, name in self.KNOWN_DEVELOPERS.items():
            if key.lower() in t:
                return name, 0.95
        m = re.search(r'([\u1200-\u137F a-zA-Z]{3,40})\s+(ሪል\s*እስቴት|real estate|development)', t)
        if m:
            return m.group(1).strip(), 0.85
        return None, 0.0

    # ==========================================================
    # STEP 9 — LOCATION & CITY
    # ==========================================================
    def normalize_location(self, text):
        # Label ("Location: Bole") first, then hashtags (@Bet_afri and others end
        # listings with #ጦርሃይሎች #ልደታ), then the whole text. See locations.py.
        return find_location(text, label=extract_labeled_location(text))

    def classify_city(self, location_code):
        """Returns 'SHEGER_CITY' or 'ADDIS_ABABA' for a location code (locations.PLACES)."""
        return city_of(location_code)

    # ==========================================================
    # STEP 10 — CONTACT EXTRACTION
    # Extracts agent phone number and/or Telegram username.
    # Critical for Estate IQ supplier feed integration.
    # ==========================================================
    def extract_contact(self, text):
        """
        Returns (phone, username).
        Phone: Ethiopian number in international or local format.
        Username: @handle (excludes known channel names and short tokens).
        """
        if not text:
            return None, None

        phone = None
        username = None

        # Ethiopian phone patterns
        # International: +251911234567 or +251 91 123 4567
        # Local: 0911234567 or 0711234567
        phone_patterns = [
            r'\+251\s*[\d\s\-]{9,13}',       # +251 format
            r'0[79]\d[\s\-]?\d{3}[\s\-]?\d{3,4}',  # 09X or 07X format
            r'0[79]\d{8}',                    # 09XXXXXXXX compact
        ]

        for pat in phone_patterns:
            m = re.search(pat, text)
            if m:
                raw = m.group(0)
                # Clean to digits only for storage
                cleaned = re.sub(r'[\s\-]', '', raw)
                # Normalize to +251 format
                if cleaned.startswith('0') and len(cleaned) >= 10:
                    cleaned = '+251' + cleaned[1:]
                if len(cleaned) >= 10:
                    phone = cleaned
                    break

        # Telegram username: @handle (5-32 chars, alphanumeric + underscore)
        # Skip if it's a known channel handle we already track
        KNOWN_CHANNELS = {
            "mygojo1", "roya_king4102", "temerproperties2m",
            "brokercom11", "condoaddis", "bet_afri", "realityaddisababa",
            "luxury_freelancers", "championallsites", "addisababagebeya",
            "etbhouseagents", "smartdealers", "ethiodelala2",
            "apartmentsaleboleayatcmckazanchi", "addisBrokerageNetworking",
        }

        username_matches = re.findall(r'@([a-zA-Z][a-zA-Z0-9_]{4,31})', text)
        for u in username_matches:
            if u.lower() not in KNOWN_CHANNELS:
                username = '@' + u
                break

        return phone, username

    # ==========================================================
    # STEP 11 — CURRENCY DETECTION
    # Detects if price is posted in USD vs ETB.
    # USD pricing is common in Bole/Summit luxury segment.
    # ==========================================================
    def detect_currency(self, text):
        """Returns ('USD', usd_amount) or ('ETB', None)."""
        t = self._norm(text)

        usd_patterns = [
            r'\$\s*[\d,]+',
            r'[\d,]+\s*(?:usd|dollar|dollars)',
            r'(?:usd|dollar)\s*[\d,]+',
        ]

        for pat in usd_patterns:
            m = re.search(pat, t)
            if m:
                raw = re.sub(r'[^\d]', '', m.group(0))
                try:
                    amount = int(raw)
                    if amount > 1000:
                        return "USD", amount
                except ValueError:
                    pass

        return "ETB", None

    # ==========================================================
    # STEP 12 — FLOOR LEVEL
    # Extracts apartment/commercial floor level.
    # ==========================================================
    def extract_floor_level(self, text):
        t = self._norm(text)

        patterns = [
            r'(\d+)(?:st|nd|rd|th)\s*floor',
            r'floor\s*(\d+)',
            r'(\d+)\s*(?:ኛ|ኛው)\s*(?:ፍሎር|ወለል|ፎቅ)',
            r'(?:ፍሎር|ወለል|ፎቅ)\s*(\d+)',
        ]

        for pat in patterns:
            m = re.search(pat, t)
            if m:
                try:
                    level = int(m.group(1))
                    if 0 < level <= 50:
                        return level
                except ValueError:
                    pass

        return None

    # ==========================================================
    # MAIN PIPELINE
    # ==========================================================
    def process(self, record):
        text = record["text"]
        # A photo or file without words is not noise: it waits for the image to be
        # read (media_queue). Its forum topic title, if any, can still name the place.
        photo_only   = is_photo_only(text)
        strict_noise = not photo_only and self.is_strictly_noise(text)

        listing_status = "ACTIVE"
        t0 = (text or "").strip().lower()
        if "(sold out)" in t0 or "(not active)" in t0 or t0.startswith("sold out") or t0.startswith("not active"):
            listing_status = "INACTIVE"

        if photo_only:
            intent, intent_conf = "UNKNOWN", 0.0
            listing_class = "MEDIA_PENDING"
            p_type, type_conf = "MEDIA_LINK", 0.99
        elif strict_noise:
            intent, intent_conf = "ADVERT", 0.99
            listing_class = "ADVERTISEMENT"
            p_type, type_conf = ("MEDIA_LINK", 0.99) if is_media_link_text(text) else ("ADVERTISEMENT", 0.99)
        else:
            intent, intent_conf = self.classify_intent(text, source_channel=record.get("source_channel"))
            listing_class = self.classify_listing_class(text, intent)
            p_type, type_conf = self.classify_type(text)
        p_subtype                   = self.classify_subtype(text, p_type)
        beds, baths                 = self.extract_rooms(text)

        # A price per m² is neither a total nor a size: read those from the text without it.
        # NFKC turns decorative digits and letters ("𝟭𝟮,𝟵𝟵𝟵,𝟬𝟬𝟬 𝗘𝗧𝗕") into plain ones.
        number_source  = unicodedata.normalize("NFKC", text or "")
        asking_per_sqm = find_price_per_sqm(number_source)
        number_text    = strip_price_per_sqm(number_source)

        area = record.get("extracted_area") or extract_area_from_text(number_text)

        plot, built, plot_c, built_c = self.resolve_area(intent, p_type, area, number_text)
        if built is not None and built < 1:
            built = None

        payment                     = self.extract_payment(text)
        finish, finish_c            = self.extract_finish(text)
        dev, dev_c                  = self.extract_developer(text)
        bank_loan_pct, down_pct     = self.extract_financing_details(text)
        sale_price, rent_price, rent_advance = extract_prices(number_text, property_type=p_type, intent=intent)
        biggest = max((p for p in (sale_price, rent_price) if p is not None), default=0)
        if (intent in ("RENT", "UNKNOWN", "MIXED") and not photo_only and biggest >= SALE_ONLY_PRICE
                and not self.has_rent_marker(text)
                and not is_rent_only_channel(record.get("source_channel"))):
            intent = "SALE"
            listing_class = self.classify_listing_class(text, intent)
            plot, built, plot_c, built_c = self.resolve_area(intent, p_type, area, number_text)
            if built is not None and built < 1:
                built = None
            sale_price, rent_price, rent_advance = extract_prices(number_text, property_type=p_type, intent=intent)
        # Only a price per m² was given: the total is that price times the size. A total
        # that does not fit the price per m² (it would mean a home of 837 m²) is some other
        # sum ("100 ሚሊዮን" of company capital), and the price per m² times the size wins.
        if asking_per_sqm and intent != "RENT":
            size = plot if p_type == "LAND" else (built or plot)
            fits = sale_price is not None and (p_type == "LAND" or 15 <= sale_price / asking_per_sqm <= 600)
            if size and not fits:
                sale_price = int(round(asking_per_sqm * size))
        contact_phone, contact_user = self.extract_contact(text)
        currency, price_usd         = self.detect_currency(text)
        floor_level                 = self.extract_floor_level(text)
        location                    = NOISE if strict_noise else self.normalize_location(text)
        if photo_only and location == UNKNOWN:
            location = NOISE   # no words and no topic title naming a place
        city                        = self.classify_city(location)

        is_known_dev = dev in self.DEVELOPER_NAMES and dev_c >= 0.9

        valuation_eligible = (
            intent in ["SALE", "MIXED"]
            and listing_class in ["PURE_SALE", "MIXED"]
            and (plot is not None or built is not None)
            and p_type not in ("UNKNOWN",)
        )

        sale_analytics_eligible = (
            intent in ["SALE", "MIXED"]
            and listing_class in ["PURE_SALE", "PROMOTIONAL", "MIXED"]
            and sale_price is not None
            and (plot is not None or built is not None)
        )

        developer_analytics_eligible = (
            is_known_dev
            and intent in ["SALE", "MIXED"]
            and (
                sale_price is not None or rent_price is not None
                or rent_advance is not None or bank_loan_pct is not None
                or built is not None or plot is not None
            )
        )

        return {
            "id":                            record["id"],
            "listing_status":                listing_status,
            "intent":                        intent,
            "listing_class":                 listing_class,
            "property_type":                 p_type,
            "property_subtype":              p_subtype,
            "bedrooms":                      beds,
            "bathrooms":                     baths,
            "plot_sqm":                      plot,
            "builtup_sqm":                   built,
            "sale_price_birr":               sale_price,
            "price_per_sqm_birr":            asking_per_sqm,
            "rent_price_birr":               rent_price,
            "rent_advance_birr":             rent_advance,
            "payment_type":                  payment,
            "bank_loan_pct":                 bank_loan_pct,
            "down_payment_pct":              down_pct,
            "finish_state":                  finish,
            "developer":                     dev,
            "location":                      location,
            "city":                          city,
            "contact_phone":                 contact_phone,
            "contact_username":              contact_user,
            "price_currency":                currency,
            "price_usd":                     price_usd,
            "floor_level":                   floor_level,
            "valuation_eligible":            valuation_eligible,
            "sale_analytics_eligible":       sale_analytics_eligible,
            "developer_analytics_eligible":  developer_analytics_eligible,
            "confidence": {
                "intent":    intent_conf,
                "type":      type_conf,
                "plot":      plot_c,
                "builtup":   built_c,
                "finish":    finish_c,
                "developer": dev_c,
            }
        }


# ==============================================================
# HELPER: AREA EXTRACTION FROM TEXT
# ==============================================================

AREA_PATTERNS = [
    r'(?<![\d.,])(\d{2,5})(?:\.\d+)?(?:\s*\(\d+(?:\.\d+)?\))?\s*(?:ካሬ|sqm|sq\.?m|m2|m²)',   # "158.72 ካሬ" is 158
]
TOTAL_AREA_RE = re.compile(r"(?:total|ጠቅላላ\s*ስፋት)[\s.\-:፦…]*(\d{2,5})\s*(?:m2|m²|sqm|ካሬ)", re.IGNORECASE)


def extract_area_from_text(text: str):
    labeled = extract_labeled_sqm(text)
    if labeled:
        if 20 <= labeled <= 5000:
            return labeled
    for pat in AREA_PATTERNS:
        for m in re.finditer(pat, text):
            try:
                val = int(m.group(1))
                if 20 <= val <= 5000:
                    return val
            except ValueError:
                continue
    return None


def find_additional_area_diff(primary, text: str):
    try:
        primary = int(primary)
    except (TypeError, ValueError):
        return None

    values = []
    for pat in AREA_PATTERNS:
        for m in re.finditer(pat, text):
            try:
                val = int(m.group(1))
            except ValueError:
                continue
            if val not in values:
                values.append(val)

    others = [v for v in values if v != primary]
    return others[0] if others else None


# ==============================================================
# HELPER: PRICE EXTRACTION (SALE VS RENT + ADVANCE)
# ==============================================================

PRICE_MILLION_PATTERNS = [r'(\d+(?:\.\d+)?)\s*(?:ሚሊዮን|ሚሊየን|million)']

# Fixed: was \d{4,9} which missed prices like 23,000 or 8,500 ብር
# Ethiopian rental prices range from ~3,000–500,000 ብር
# Pattern now matches any digit group before comma-thousands separator
PRICE_BIRR_PATTERNS = [
    r'(\d{1,9}(?:,\d{3})*)\s*(?:ብር|birr|etb)',   # 23,000 ብር or 3,500,000 ብር
    r'ኪራይ\s*[:፦]?\s*(\d{1,9}(?:,\d{3})*)',       # ኪራይ: 23,000 (no ብር suffix)
    r'ዋጋ\s*[:፦]?\s*(\d{1,9}(?:,\d{3})*)',         # ዋጋ: 15,000
]
PRICE_BIRR_MIN = 2_000       # below this = not a real price (room number, code, etc.)
PRICE_BIRR_MAX = 500_000_000 # above this = extraction error
# Words that mark a number as a part of the price or another sum, not the sale price:
# down payment, advance, loan, repayment, income, commission, a rent (paid now or
# expected), a profit, the remaining balance, a bank loan.
NOT_A_TOTAL_RE = re.compile(
    r"ቅድመ\s*ክፍያ|ቅድሚያ|ብድር|ተመላሽ|ገቢ|ኮሚሽን|down\s*payment|advance|loan|income|commission"
    r"|ተከራ|መከራየት|ይከራያል|ኪራይ|\brent|per\s*month|/\s*months?|monthly|በወር|ወርሃዊ|ወርሀዊ"
    r"|ትርፍ|ቀሪ|(?<!በ)ባንክ|annual|yearly",
    re.IGNORECASE,
)
TOTAL_WORDS_RE = re.compile(r"ጠቅላላ|አጠቃላይ|ሙሉ|total|full", re.IGNORECASE)
# Broker headings give the asking price after a dash and no price word:
# "KAZANCHIES : HILTON – 24,999,000 - 3 Beds", "ቦሌ : ጌቱ ጀርባ ° 19,999,000 - 3 Beds",
# "Figa: Noah Real-Estate ° 9.8 million - 2 beds". (Not the end of a range "8,000,000 – 9,000,000".)
HEADING_PRICE_RE = re.compile(
    r"(?<![\d,])(?<![\d,]\s)[–—\-°]\s*"
    r"(?:(?P<num>\d{1,3}(?:,\d{3}){2,})|(?P<mil>\d+(?:\.\d+)?)\s*" + MILLION_WORD + r")"
    r"\s*(?:ብር|birr|etb)?\s*(?=[\-–—|(\n]|$)",
    re.IGNORECASE,
)


def _not_a_total(t: str, start: int, end: int) -> bool:
    """A down payment, rent, income, … next to this number in the same sentence, and no
    "total" just before it."""
    near = same_sentence_before(t, start, 25) + t[start:end] + same_sentence_after(t, end, 12)
    return bool(NOT_A_TOTAL_RE.search(near) and not TOTAL_WORDS_RE.search(t[max(0, start - 15): start]))


def extract_prices(text: str, property_type: str | None = None, intent: str | None = None):
    t = text.lower()

    sale_price   = None
    rent_price   = None
    rent_advance = None

    rent_context = any(x in t for x in [
        "በወር", "per month", "monthly", "ኪራይ", "rent", "ወርሃዊ",
        "የሚከራይ", "ሚከራይ", "ይከራያል", "ለሚከራዩ",
    ])
    sale_context = any(x in t for x in [
        "ሽያጭ", "for sale", "sale", "selling", "ownership",
        "title deed", "ካርታ", "በሽያጭ", "በሺያጭ", "ሺያጭ",
    ])
    # A known intent decides what kind of price a number is: a rental has no sale price,
    # and the rent or income a property for sale earns is not its price.
    if intent == "SALE":
        rent_context, sale_context = False, True
    elif intent == "RENT":
        rent_context, sale_context = True, False

    # Price priority rule:
    # - If multiple prices exist, larger is sale_price, smaller likely rent.
    # - Never pick <1M as sale price if a larger number exists.
    candidates = extract_price_candidates_birr(t) if intent != "RENT" else []
    if candidates:
        max_p = max(candidates)
        min_p = min(candidates)
        if max_p >= 1_000_000:
            sale_price = max_p
            if min_p < 1_000_000:
                rent_price = rent_price or min_p
        else:
            birr = extract_price_birr(t, property_type=property_type)
            if birr:
                sale_price = birr

    # (Also when the intent is not known: a price of millions makes the listing a sale, see process().)
    if sale_price is None and intent != "RENT":
        m = HEADING_PRICE_RE.search(t)
        if m:
            sale_price = (int(m.group("num").replace(",", "")) if m.group("num")
                          else int(round(float(m.group("mil")) * 1_000_000)))

    # Birr amounts — rental prices like 23,000 ብር or sale prices
    found = False
    for pat in PRICE_BIRR_PATTERNS:
        for m in re.finditer(pat, t):
            raw = m.group(1).replace(",", "")
            try:
                val = int(raw)
            except ValueError:
                break

            # Validate range — ignore codes, IDs, and extraction noise
            if val < PRICE_BIRR_MIN or val > PRICE_BIRR_MAX:
                break

            if rent_context and not sale_context:
                if rent_price is None:
                    rent_price = val
            else:
                # A down payment, loan, income or commission is not the price: try the next
                # number. "ጠቅላላ"/"ሙሉ" (total/full) just before it makes it the price anyway.
                if _not_a_total(t, m.start(), m.end()):
                    continue
                if sale_price is None:
                    sale_price = val
            found = True
            break
        if found:
            break

    # A rent given as "Price: 100,000 per month", without "ብር" (not "Price (USD): 1780").
    if intent == "RENT" and rent_price is None and not re.search(r"\busd\b|\$|dollar|ዶላር", t):
        rent_price = extract_price_birr(t, property_type=property_type, for_rent=True)

    if intent != "RENT":
        # "ዋጋ" and "ብር" both missing: "9.8 million", "61 ሚሊየን".
        if sale_price is None and rent_price is None:
            for m in MILLION_RE.finditer(t):
                value = million_value(m)
                if re.search(r"ዶላር|dollar|usd|\$", t[m.end(): m.end() + 20]):   # "150 ሚሊዮን (የአሜሪካ) ዶላር"
                    continue
                if re.search(r"ከ\s*$", t[max(0, m.start() - 3): m.start()]):   # "ከ 2.5 ሚልዮን ጀምሮ": a starting price
                    continue
                if PRICE_BIRR_MIN <= value <= PRICE_BIRR_MAX and not _not_a_total(t, m.start(), m.end()):
                    sale_price = value
                    break
        # The cash part of a sale whose buyer also takes over the seller's bank loan.
        parts = cash_plus_loan(t)
        if parts and (sale_price is None or sale_price == parts[0]):
            sale_price = parts[0] + parts[1]

    return sale_price, rent_price, rent_advance


# ==============================================================
# HELPER: BUILD RECORD FROM TELEGRAM POST
# ==============================================================

def build_record_from_telegram(msg):
    parts = [msg.get("caption", "")]
    for ocr in msg.get("ocr_texts", []):
        if ocr:
            parts.append(ocr)
    full_text = "\n".join(parts).strip()
    return {
        "id":             msg["id"],
        "text":           full_text,
        "extracted_area": msg.get("extracted_area")
    }


# ==============================================================
# DEMO
# ==============================================================

if __name__ == "__main__":
    pipeline = ValuationPipeline()

    tests = [
        {
            "label": "Condominium resale",
            "text": """ለሽያጭ የቀረበ ባለ2 መኝታ ኮንዶሚኒየም
74ካሬ | 2ኛ ፍሎር | አያት መብራት
ሙሉ ሴራሚክ | ዲጂታል ካርታ | ለካሽ ለባንክ ይሆናል
ዋጋ 5.5 ሚሊየን ብር | ለተጨማሪ መረጃ 0911234567"""
        },
        {
            "label": "Rental apartment",
            "text": """For rent 3 bedroom apartment in Bole
150sqm | 3rd floor | fully furnished
Monthly rent: 45,000 ብር | 3 months advance
Contact: @agentmike or call 0944556677"""
        },
        {
            "label": "Warehouse for sale",
            "text": """መጋዘን ለሽያጭ በቃሊቲ ኢንደስትሪ ዞን
G+1 warehouse | 600 sqm | For sale
15 million birr | Bank possible 50%
Call +251911223344"""
        },
        {
            "label": "Sheger City villa",
            "text": """ቪላ ቤት ለሽያጭ ሰበታ ሸገር ከተማ
G+2 | 300 sqm compound | 200 sqm builtup
ዋጋ 8 ሚሊዮን ብር | @seller_2024"""
        },
    ]

    for t in tests:
        result = pipeline.process({"id": "TEST", "text": t["text"]})
        print(f"\n=== {t['label']} ===")
        for k in ["intent", "property_type", "property_subtype", "location", "city",
                  "contact_phone", "contact_username", "price_currency", "floor_level",
                  "sale_price_birr", "rent_price_birr"]:
            print(f"  {k}: {result.get(k)}")
