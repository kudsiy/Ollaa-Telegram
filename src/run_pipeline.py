import re
import json
import unicodedata
from datetime import datetime

from processor import (
    extract_bedrooms,
    extract_area_breakdown,
    extract_labeled_location,
    extract_labeled_sqm,
    extract_price_birr,
    extract_price_candidates_birr,
    find_price_per_sqm,
    is_media_link_text,
    is_noise_advert,
    parse_forum_topic_title,
    parse_million_amount,
    strip_price_per_sqm,
)


class ValuationPipeline:
    def __init__(self):

        # ==========================================================
        # INTENT VOCABULARY
        # ==========================================================
        self.RENT_SIGNALS = [
            "ኪራይ", "rent", "for rent", "monthly", "per month",
            "deposit", "advance", "furnished", "guest house",
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
            "condominium", "condo", "ኮንዶሚኒየም", "ኮንዶ",
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
        self.TYPE_WAREHOUSE = [
            "warehouse", "መጋዘን", "store", "storage",
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
        # SHEGER CITY LOCATIONS
        # These are unambiguously outside Addis Ababa admin boundary.
        # city = 'SHEGER_CITY' for these.
        # ==========================================================
        self.SHEGER_LOCATIONS = {
            "legetafo", "burayu", "sebeta", "sululta",
            "chancho", "holeta", "sendafa", "sheger_city",
            "sheger_burayu", "sheger_sululta", "sheger_sebeta",
        }

        # ==========================================================
        # LOCATION MAP
        # Key = text fragment to match (lowercase)
        # Value = normalized location code
        # ORDER MATTERS — more specific matches first
        # ==========================================================
        self.LOCATION_MAP = {
            # ── NEW LOCATIONS RESCUED FROM MISSING LISTINGS ───────
            "bisrate gabriel":      "bisrate_gabriel",
            "ቢስራተ ገብርኤል":         "bisrate_gabriel",
            "awere":                "awere",
            "አዋሬ":                 "awere",
            "mebratu":              "bulgaria", # Landmark mapping for Bulgaria
            "መብራቱ":                "bulgaria",
            "gotera":               "gotera",
            "ጎተራ":                 "gotera",
            "mex":                  "mexico",
            "ሜክስ":                  "mexico",
            "tulu dimtu":           "tulu_dimtu",
            "ጡሉ ዲምቱ":              "tulu_dimtu",
            "summit safari":        "summit",
            "ሰሚት ሳፋሪ":             "summit",
            "kotebe 02":            "kotebe",
            "ኮተቤ 02":               "kotebe",
            "adanech park":         "kazanchis", # Amibara project
            "አዳነች ፓርክ":            "kazanchis",
            "friendship square":    "piassa",
            "ፍሬንድሺፕ":              "piassa",
            "sheraton":             "kazanchis", 
            "ሸራተን":                "kazanchis",
            "chacha":               "debre_berhan",
            "ccd":                  "ayat_zone",
            "ሲሲዲ":                 "ayat_zone",
            "ቻቻ":                  "chacha",
            "abo mazoriya":         "mekanisa_abo",
            "አቦ ማዞሪያ":             "mekanisa_abo",
            "haya hulet":           "haya_hulet",
            "ሀያ ሁለት":              "haya_hulet",
            "22 mazoria":           "haya_hulet",
            "lem hotel":            "22_mazoria",
            "ለም ሆቴል":              "22_mazoria",
            "22ማዞሪያ":              "haya_hulet",
            "ሃያ ሁለት":              "haya_hulet",

            # ── BOLE sub-areas (check before plain "bole") ────────
            "bole bulbula":         "bole_bulbula",
            "ቦሌ ቡልቡላ":            "bole_bulbula",
            "bole michael":         "bole_michael",
            "bole mikael":          "bole_michael",
            "ቦሌ ሚካኤል":            "bole_michael",
            "bole arabsa":          "bole_arabsa",
            "rwanda kuter":         "bole_rwanda",
            "rwanda":               "bole_rwanda",
            "ቦሌ አራብሳ":            "bole_arabsa",
            "bole rwanda":          "bole_rwanda",
            "bole ruwanda":         "bole_rwanda",
            "ቦሌ ርዋንዳ":            "bole_rwanda",
            "bole japan":           "bole_japan",
            "ቦሌ ጃፓን":             "bole_japan",
            "bole brass":           "bole_brass",
            "ቦሌ ብራስ":             "bole_brass",
            "bole lemi":            "bole_lemi",
            "ቦሌ ለሚ":              "bole_lemi",
            "bole medhanialem":     "bole_medhanialem",
            "bole adeyabeba":       "bole_adeyabeba",
            "ቦሌ አደይ አበባ":         "bole_adeyabeba",

            # ── AYAT sub-areas ────────────────────────────────────
            "ayat 49":              "ayat_49",
            "አያት 49":              "ayat_49",
            "ayat mekdonia":        "ayat_mekdonia",
            "ayat meqdonia":        "ayat_mekdonia",
            "አያት መቅዶንያ":          "ayat_mekdonia",

            # ── SUMMIT sub-areas ──────────────────────────────────
            "summit 72":            "summit_72",
            "ሰሚት 72":              "summit_72",
            "summit figa":          "summit_figa",
            "ሰሚት ፊጋ":             "summit_figa",
            "figa mebrat":          "figa_mebrat",
            "ፊጋ መብራት":            "figa_mebrat",
            "german":               "german",
            "ጀርመን":               "german",

            # ── CMC / MICHAEL ─────────────────────────────────────
            "cmc":                  "cmc_michael",
            "ሲኤምሲ":               "cmc_michael",
            "signal":               "signal",
            "ሲግናል":               "signal",

            # ── KAZANCHIS / MESKEL FLOWER ─────────────────────────
            "kazanchis":            "kazanchis",
            "ካዛንቺስ":              "kazanchis",
            "meskel flower":        "meskel_flower",
            "meskel flore":         "meskel_flower",
            "mesqel flower":        "meskel_flower",
            "መስቀል ፍሎወር":          "meskel_flower",
            "መስቀልፍሎወር":          "meskel_flower",

            # ── PIASSA / OLD TOWN ─────────────────────────────────
            "piassa":               "piassa",
            "ፒያሳ":                "piassa",
            "arada":                "arada",
            "አራዳ":                "arada",
            "teklehaimanot":        "teklehaimanot",
            "ጥቅለ ሃይማኖት":          "teklehaimanot",
            "merkato":              "merkato",
            "መርካቶ":               "merkato",

            # ── 4 KILO / 6 KILO ──────────────────────────────────
            "4 kilo":               "4kilo",
            "4kilo":                "4kilo",
            "4ኪሎ":                "4kilo",
            "አራት ኪሎ":             "4kilo",
            "6 kilo":               "6kilo",
            "6ኪሎ":                "6kilo",
            "ስድስት ኪሎ":            "6kilo",

            # ── MEXICO / MEXICO AREA ──────────────────────────────
            "mexico":               "mexico",
            "ሜክሲኮ":               "mexico",

            # ── GERJI / HAILE GARMENT ─────────────────────────────
            "gerji":                "gerji",
            "ገርጂ":                "gerji",
            "haile garment":        "haile_garment",
            "ሃይሌ ጋርመንት":          "haile_garment",
            "garment":              "garment",
            "ጋርመንት":              "garment",

            # ── MEGENAGNA / WELLO SEFER ───────────────────────────
            "megenagna":            "megenagna",
            "መገናኛ":               "megenagna",
            "wello sefer":          "wello_sefer",
            "welo sefer":           "wello_sefer",
            "ወሎ ሰፈር":              "wello_sefer",

            # ── SARBET / OLD AIRPORT ──────────────────────────────
            "sarbet":               "sarbet_old_airport",
            "ሳርቤት":               "sarbet_old_airport",
            "old airport":          "sarbet_old_airport",
            "ድሮ አውሮፕላን ማረፊያ":    "sarbet_old_airport",

            # ── JEMO / KALITY ─────────────────────────────────────
            "jemo":                 "jemo",
            "ጀሞ":                 "jemo",
            "kality":               "kality",
            "ቃሊቲ":                "kality",
            "akaki":                "akaki",
            "አቃቂ":                "akaki",

            # ── LEBU / LAFTO / NIFAS SILK ────────────────────────
            "lebu":                 "lebu",
            "ለቡ":                 "lebu",
            "lafto":                "lafto",
            "ላፍቶ":                "lafto",
            "laphto":               "lafto",
            "nifas silk":           "nifas_silk",
            "ንፋስ ስልክ":            "nifas_silk",

            # ── KOLFE / GOFA / SARIS ─────────────────────────────
            "kolfe":                "kolfe",
            "ኮልፌ":                "kolfe",
            "gofa":                 "gofa",
            "ጎፋ":                 "gofa",
            "saris":                "saris",
            "ሳሪስ":                "saris",

            # ── LIDETA / KIRKOS / YEKA ───────────────────────────
            "lideta":               "lideta",
            "ልደታ":                "lideta",
            "kirkos":               "kirkos",
            "ቂርቆስ":               "kirkos",
            "yeka":                 "yeka",
            "የካ":                 "yeka",

            # ── SENGATERA / URAEL / BAMBIS ───────────────────────
            "sengatera":            "sengatera",
            "ሰንጋትራ":              "sengatera",
            "urael":                "urael",
            "ኡራኤል":               "urael",
            "bambis":               "bambis",
            "ባምቢስ":               "bambis",

            # ── GURD SHOLA / ALEM BANK ───────────────────────────
            "gurd shola":           "gurd_shola",
            "ጉርድ ሾላ":             "gurd_shola",
            "alem bank":            "alem_bank",
            "አለም ባንክ":            "alem_bank",

            # ── BETHEL / KEBENA ───────────────────────────────────
            "bethel":               "bethel",
            "ቤተለ":                "bethel",
            "kebena":               "kebena",
            "ቀበና":                "kebena",

            # ── BULGARIA ──────────────────────────────────────────
            "bulgaria":             "bulgaria",
            "ቡልጋሪያ":              "bulgaria",

            # ── ATLAS ─────────────────────────────────────────────
            "atlas":                "bole_atlas",

            # ── LEMI KURA ─────────────────────────────────────────
            "lemi kura":            "lemi_kura",

            # ── PLAIN BOLE / AYAT / SUMMIT (after sub-areas) ─────
            "bole":                 "bole_main",
            "ቦሌ":                 "bole_main",
            "ayat":                 "ayat_zone",
            "አያት":                "ayat_zone",
            "summit":               "summit",
            "ሰሚት":                "summit",

            # ── TOR HAYLOCH / MILITARY AREA ───────────────────────
            "tor hayloch":          "tor_hayloch",
            "ጦር ኃይሎች":             "tor_hayloch",
            "tor hailoch":          "tor_hayloch",
            "torhailoch":           "tor_hayloch",
            "torhayloch":           "tor_hayloch",
            "ጦር ሃይሎች":            "tor_hayloch",
            "ጦርሃይሎች":             "tor_hayloch",
            "ጦር ሀይሎች":            "tor_hayloch",

            # ── SHOLLA ────────────────────────────────────────────
            "sholla":               "sholla",
            "shola":                "sholla",
            "ሾላ":                 "sholla",

            # ── AYER TENA ─────────────────────────────────────────
            "ayer tena":            "ayer_tena",
            "ayertena":             "ayer_tena",
            "አየር ጤና":             "ayer_tena",

            # ── WESEN ─────────────────────────────────────────────
            "wesen":                "wesen",
            "ወሰን":                "wesen",

            # ── PASTOR MEDHANIALEM ────────────────────────────────
            "pastor":               "pastor_medhanialem",
            "ፓስተር":               "pastor_medhanialem",
            "medhanialem":          "medhanialem",
            "መድሃኒዓለም":            "medhanialem",

            # ── HIYA ──────────────────────────────────────────────
            "hiya":                 "hiya",
            "ሂያ":                 "hiya",

            # ── ARENGUADE / ENKULAL FABRICA ───────────────────────
            "enkulal fabrica":      "enkulal_fabrica",
            "እንቁላል ፋብሪካ":         "enkulal_fabrica",

            # ── SHEGER CITY ───────────────────────────────────────
            "sheger":               "sheger_city",
            "ሸገር":                "sheger_city",
            "legetafo":             "legetafo",
            "ለገጣፎ":               "legetafo",
            "burayu":               "burayu",
            "ቡራዩ":               "burayu",
            "sebeta":               "sebeta",
            "ሰበታ":                "sebeta",
            "sululta":              "sululta",
            "ሱሉልታ":               "sululta",
            "chancho":              "chancho",
            "ጫንቾ":                "chancho",
            "holeta":               "holeta",
            "ሆለታ":                "holeta",
            "sendafa":              "sendafa",
            "ሰንዳፋ":               "sendafa",
            "gelan":                "gelan",
            "ገላን":                "gelan",
            # ── MISSING HUBS & SPELLING VARIATIONS ────────────────
            "jacros":               "jacros",
            "22":                   "22_area",
            "wollo sefer":          "wollo_sefer",
            "6 kilo":               "6_kilo",
            "bulgaria":             "bulgaria",
            "ጃክሮስ":                "jacros",
            "ጃክሮስ ሜታ":             "jacros",
            "la gare":              "la_gare",
            "ለገሃር":                "la_gare",
            "dembel":               "dembel",
            "ደንበል":                "dembel",
            "goro":                 "goro",
            "ጎሮ":                  "goro",
            "addisu gebeya":        "addisu_gebeya",
            "አዲሱ ገበያ":             "addisu_gebeya",
            "golagol":              "22_mazoria", # Landmark for 22
            "ጎላጎል":                "22_mazoria",
            "alem gena":            "alem_gena",
            "አለም ገና":              "alem_gena",
            "atena tera":           "atena_tera",
            "አጠና ተራ":              "atena_tera",
            "ambassador":           "ambassador",
            "አምባሳደር":             "ambassador",
            "kotebe":               "kotebe",
            "ኮተቤ":                 "kotebe",
            "dukem":                "dukem",
            "ዱከም":                 "dukem",
            "thorhailoch":          "tor_hayloch", # English spelling var
            "ብስራተ ገብርኤል":         "bisrate_gabriel", # Amharic spelling var
            "ቱሉዱምቱ":              "tulu_dimtu", # Amharic spelling var
         }

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
    def classify_intent(self, text, source_channel=None):
        # Channel-level override: these channels exclusively list rentals.
        RENT_ONLY_CHANNELS = {
            "https://t.me/Bet_afri",
            "https://t.me/Bet_afri_Business",
            "https://t.me/Betafrivip",
        }
        if source_channel and source_channel.rstrip("/") in {c.rstrip("/") for c in RENT_ONLY_CHANNELS}:
            return "RENT", 0.95

        t = self._norm(text)

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

        rent_present = any(w in t for w in self.RENT_SIGNALS)
        sale_present = any(w in t for w in self.SALE_SIGNALS)

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
        # Kill short garbage and links [cite: 1]
        if '[media only]' in text_lower or 'https://' in text_lower or len(text_lower) < 30: return True
        return False
    def extract_g_plus_level(self, text):
        t = self._norm(text)
        m = re.search(r'\bg\+(\d{1,2})\b', t)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    def classify_type(self, text):
        t = self._norm(text)
        g_plus_level = self.extract_g_plus_level(t)
        
        has_bedroom = "መኝታ" in t or "bed" in t
        has_floor_context = g_plus_level is not None or "ፎቅ" in t or "floor" in t

        if is_media_link_text(text):
            return "MEDIA_LINK", 0.99

        if is_noise_advert(text):
            return "ADVERTISEMENT", 0.99

        if any(x in t for x in ["studio", "ስቱዲዮ"]):
            return "STUDIO", 0.95

        if g_plus_level is not None and g_plus_level >= 5:
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

        if any(w in t for w in self.TYPE_APARTMENT) or any(w in t for w in ["አፓርትመንት", "አፓርታማ", "አፓርት", "ፎቅ ቤት"]):
            return "APARTMENT", 0.95
            
        if "መኝታ ቤት" in t and has_floor_context:
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

        # For commercial/industrial always treat area as builtup
        if p_type in ("WAREHOUSE", "OFFICE", "COMMERCIAL", "COMMERCIAL_BUILDING"):
            return None, inferred_built or raw_area, 0.0, 0.9

        if intent not in ["SALE", "MIXED", "RENT"]:
            return None, None, 0.0, 0.0

        t = self._norm(text)

        built_keywords = ["built", "built-up", "living area", "floor area", "constructed", "ተገንብቶ", "የተገነባ"]
        plot_keywords  = ["plot", "land", "compound", "total area", "ይዞታ", "መሬት", "ቦታ"]

        if p_type in ("APARTMENT", "CONDOMINIUM"):
            return None, inferred_built or raw_area, 0.0, 0.95

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
        t = self._norm(text)

        labeled = extract_labeled_location(text)
        if labeled:
            labeled_norm = self._norm(labeled)
            for k, v in self.LOCATION_MAP.items():
                if k in labeled_norm or labeled_norm in k:
                    return v

        # Check hashtag locations first — @Bet_afri and others use
        # structured hashtags like #ጦርሃይሎች #ልደታ at end of listings.
        # These are explicit and reliable so check before free-text scan.
        hashtag_matches = re.findall(r'#([^\s#]+)', text)
        for tag in hashtag_matches:
            tag_lower = tag.lower().strip()
            for k, v in self.LOCATION_MAP.items():
                if k in tag_lower or tag_lower in k:
                    return v

        # Free-text location scan
        for k, v in self.LOCATION_MAP.items():
            if k in t:
                return v
        return "other_addis"

    def classify_city(self, location_code):
        """
        Returns 'SHEGER_CITY' or 'ADDIS_ABABA' based on location code.
        Gelan is treated as Addis (Gelan condos are within Addis admin).
        Explicitly Sheger-only locations are classified accordingly.
        """
        if location_code in self.SHEGER_LOCATIONS:
            return "SHEGER_CITY"
        return "ADDIS_ABABA"

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
        strict_noise = self.is_strictly_noise(text)

        listing_status = "ACTIVE"
        t0 = (text or "").strip().lower()
        if "(sold out)" in t0 or "(not active)" in t0 or t0.startswith("sold out") or t0.startswith("not active"):
            listing_status = "INACTIVE"

        if strict_noise:
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
        asking_per_sqm = find_price_per_sqm(text)
        number_text    = strip_price_per_sqm(text)

        area = record.get("extracted_area") or extract_area_from_text(number_text)

        plot, built, plot_c, built_c = self.resolve_area(intent, p_type, area, number_text)
        if built is not None and built < 1:
            built = None

        payment                     = self.extract_payment(text)
        finish, finish_c            = self.extract_finish(text)
        dev, dev_c                  = self.extract_developer(text)
        bank_loan_pct, down_pct     = self.extract_financing_details(text)
        sale_price, rent_price, rent_advance = extract_prices(number_text, property_type=p_type)
        # Only a price per m² was given: the total is that price times the size.
        if sale_price is None and asking_per_sqm:
            size = plot if p_type == "LAND" else (built or plot)
            if size:
                sale_price = int(round(asking_per_sqm * size))
        contact_phone, contact_user = self.extract_contact(text)
        currency, price_usd         = self.detect_currency(text)
        floor_level                 = self.extract_floor_level(text)
        location                    = "noise" if strict_noise else self.normalize_location(text)
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
    r'(\d{2,5})\s*(?:ካሬ|sqm|sq\.?m|m2|m²)',
]


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


def extract_prices(text: str, property_type: str | None = None):
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

    # Price priority rule:
    # - If multiple prices exist, larger is sale_price, smaller likely rent.
    # - Never pick <1M as sale price if a larger number exists.
    candidates = extract_price_candidates_birr(t)
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

    # Birr amounts — rental prices like 23,000 ብር or sale prices
    for pat in PRICE_BIRR_PATTERNS:
        m = re.search(pat, t)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                val = int(raw)
            except ValueError:
                continue

            # Validate range — ignore codes, IDs, and extraction noise
            if val < PRICE_BIRR_MIN or val > PRICE_BIRR_MAX:
                continue

            if rent_context and not sale_context:
                if rent_price is None:
                    rent_price = val
            else:
                if sale_price is None:
                    sale_price = val
            break

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
