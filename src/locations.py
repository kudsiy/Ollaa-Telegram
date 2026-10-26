"""
locations.py
------------
The one table of places (task S6). Every script that names a location uses it:
run_pipeline.py (listing text), topic_resolver.py (forum topic titles),
dedup_and_fix_locations.py (re-checking 'other_addis') and geocoder.py (map
coordinates). A location code written to processed_listings.location always
comes from PLACES.

PLACES   location code -> Place (display name, city, sub-city, coordinates)
ALIASES  (words, code) in priority order: more specific places first, so
         "bole bulbula" is tried before "bole". The first alias found wins.

Matching rules:
  - Whole words only: "የካ" (Yeka) is not found inside "የካሬ" (per square
    metre), "22 mazoria" not inside a phone number, "bole" not inside "bolemi".
  - Amharic prepositions written onto a name still match: "በቦሌ", "ከአያት".
  - Spaces in an alias are optional: "bole michael" also matches "BoleMichael".
  - A label ("Location: Bole") or a hashtag ("#Bole") only matches aliases
    found inside it, never a longer alias that merely contains it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

ADDIS = "ADDIS_ABABA"
SHEGER = "SHEGER_CITY"

# Not places, but codes the parser also writes.
NOISE = "noise"              # adverts, articles, empty posts
UNKNOWN = "other_addis"      # no place found in the text


@dataclass(frozen=True)
class Place:
    name: str
    city: str = ADDIS
    sub_city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    parent: Optional[str] = None   # wider area, used for coordinates when a place has none


def _p(name, city=ADDIS, sub_city=None, at=None, parent=None) -> Place:
    lat, lon = at if at else (None, None)
    return Place(name, city, sub_city, lat, lon, parent)


# Coordinates come from the landmark table geocoder.py used before S6.
PLACES: dict[str, Place] = {
    # ── Bole ──────────────────────────────────────────────────────────
    "bole_main":            _p("Bole", sub_city="Bole", at=(9.0050, 38.7800)),
    "bole_bulbula":         _p("Bole Bulbula", sub_city="Bole", at=(8.9800, 38.8100)),
    "bole_michael":         _p("Bole Michael", sub_city="Bole", parent="bole_main"),
    "bole_arabsa":          _p("Bole Arabsa", sub_city="Bole", at=(8.9650, 38.8250)),
    "bole_rwanda":          _p("Bole Rwanda", sub_city="Bole", parent="bole_main"),
    "bole_japan":           _p("Bole Japan", sub_city="Bole", parent="bole_main"),
    "bole_brass":           _p("Bole Brass", sub_city="Bole", parent="bole_main"),
    "bole_lemi":            _p("Bole Lemi", sub_city="Bole", parent="bole_main"),
    "bole_lemi_industrial": _p("Bole Lemi Industrial Park", sub_city="Bole", parent="bole_lemi"),
    "bole_medhanialem":     _p("Bole Medhanialem", sub_city="Bole", at=(9.0007, 38.7864)),
    "bole_adeyabeba":       _p("Bole Adey Abeba", sub_city="Bole", parent="bole_main"),
    "bole_atlas":           _p("Atlas", sub_city="Bole", at=(9.0132, 38.7824)),
    "bole_airport_road":    _p("Bole Airport Road", sub_city="Bole", at=(8.9950, 38.7900)),
    "urael":                _p("Urael", sub_city="Bole", at=(9.0128, 38.7750)),
    "haya_hulet":           _p("Haya Hulet (22)", sub_city="Bole", at=(9.0068, 38.7680)),
    "wello_sefer":          _p("Wello Sefer", parent="bole_main"),
    "bulgaria":             _p("Bulgaria"),
    "awere":                _p("Awere"),
    # ── Ayat / CMC / Summit / Yeka ────────────────────────────────────
    "ayat_zone":            _p("Ayat", sub_city="Bole", at=(8.9992, 38.8611)),
    "ayat_49":              _p("Ayat 49", sub_city="Bole", at=(8.9992, 38.8611)),
    "ayat_mekdonia":        _p("Ayat Mekdonia", sub_city="Bole", parent="ayat_zone"),
    "cmc_michael":          _p("CMC", sub_city="Yeka", at=(9.0470, 38.7690)),
    "summit":               _p("Summit", at=(8.9490, 38.8090)),
    "summit_72":            _p("Summit 72", parent="summit"),
    "summit_figa":          _p("Summit Figa", parent="summit"),
    "figa":                 _p("Figa", parent="summit"),
    "figa_mebrat":          _p("Figa Mebrat", parent="summit"),
    "german":               _p("German Square"),
    "signal":               _p("Signal"),
    "megenagna":            _p("Megenagna", sub_city="Yeka", at=(9.0226, 38.7901)),
    "imperial":             _p("Imperial", sub_city="Yeka", at=(9.0226, 38.7901)),
    "gerji":                _p("Gerji", sub_city="Yeka", at=(9.0350, 38.8090)),
    "yeka":                 _p("Yeka", sub_city="Yeka", at=(9.0400, 38.8000)),
    "kotebe":               _p("Kotebe", sub_city="Yeka", at=(9.0500, 38.7900)),
    "sholla":               _p("Shola", sub_city="Yeka", at=(9.0360, 38.7910)),
    "gurd_shola":           _p("Gurd Shola", sub_city="Yeka", parent="sholla"),
    "sefere_selam":         _p("Sefere Selam", sub_city="Yeka", at=(9.0200, 38.8100)),
    "lemi_kura":            _p("Lemi Kura", sub_city="Lemi Kura", at=(9.0600, 38.8200)),
    "tafo":                 _p("Tafo", sub_city="Lemi Kura", at=(9.0500, 38.8100)),
    "tulu_dimtu":           _p("Tulu Dimtu"),
    "bethel":               _p("Bethel"),
    "kebena":               _p("Kebena"),
    "lamberet":             _p("Lamberet"),
    "awareness":            _p("Awareness"),
    "jacros":               _p("Jacros"),
    "goro":                 _p("Goro", sub_city="Kolfe", at=(9.0300, 38.7200)),
    "wesen":                _p("Wesen"),
    "hiya":                 _p("Hiya"),
    "enkulal_fabrica":      _p("Enkulal Fabrica"),
    "ambassador":           _p("Ambassador"),
    "alem_bank":            _p("Alem Bank"),
    "atena_tera":           _p("Atena Tera"),
    # ── Kirkos / Arada / centre ───────────────────────────────────────
    "kazanchis":            _p("Kazanchis", sub_city="Kirkos", at=(9.0100, 38.7700)),
    "meskel_flower":        _p("Meskel Flower", sub_city="Kirkos"),
    "meskel_square":        _p("Meskel Square", sub_city="Kirkos", at=(9.0082, 38.7576)),
    "mexico":               _p("Mexico", sub_city="Kirkos", at=(9.0082, 38.7576)),
    "sengatera":            _p("Sengatera", sub_city="Kirkos", parent="mexico"),
    "bambis":               _p("Bambis", sub_city="Kirkos", at=(9.0082, 38.7700)),
    "kirkos":               _p("Kirkos", sub_city="Kirkos", at=(9.0082, 38.7576)),
    "la_gare":              _p("La Gare", sub_city="Kirkos"),
    "dembel":               _p("Dembel"),
    "stadium":              _p("Stadium", sub_city="Arada", at=(9.0174, 38.7575)),
    "piassa":               _p("Piassa", sub_city="Arada", at=(9.0260, 38.7572)),
    "arada":                _p("Arada", sub_city="Arada"),
    "4kilo":                _p("Arat Kilo", sub_city="Arada", at=(9.0278, 38.7621)),
    "6kilo":                _p("Sidist Kilo", sub_city="Gulele", at=(9.0348, 38.7650)),
    "7kilo":                _p("Sebategna"),
    "teklehaimanot":        _p("Teklehaimanot"),
    "merkato":              _p("Merkato", sub_city="Addis Ketema", at=(9.0360, 38.7430)),
    "addis_ketema":         _p("Addis Ketema", sub_city="Addis Ketema", at=(9.0260, 38.7400)),
    "addisu_gebeya":        _p("Addisu Gebeya"),
    "salite_mehret":        _p("Salite Mehret"),
    "mikililand":           _p("Mikililand"),
    "addis_sefer":          _p("Addis Sefer"),
    "gulele":               _p("Gulele", sub_city="Gulele", at=(9.0500, 38.7500)),
    "entoto":               _p("Entoto", sub_city="Gulele", at=(9.0700, 38.7600)),
    "ferensay":             _p("Ferensay", sub_city="Gulele", at=(9.0400, 38.7550)),
    # ── Nifas Silk / Lideta / Kolfe / Akaki ───────────────────────────
    "sarbet_old_airport":   _p("Sarbet / Old Airport", sub_city="Nifas Silk", at=(8.9968, 38.7480)),
    "gotera":               _p("Gotera", sub_city="Nifas Silk", at=(8.9912, 38.7576)),
    "saris":                _p("Saris", sub_city="Nifas Silk", at=(8.9790, 38.7250)),
    "lafto":                _p("Lafto", sub_city="Nifas Silk", at=(8.9600, 38.7400)),
    "nifas_silk":           _p("Nifas Silk", sub_city="Nifas Silk", at=(8.9800, 38.7900)),
    "mekanisa_abo":         _p("Mekanisa / Abo Mazoria", sub_city="Nifas Silk", at=(8.9700, 38.7500)),
    "haile_garment":        _p("Haile Garment"),
    "garment":              _p("Garment"),
    "pastor_medhanialem":   _p("Pastor Medhanialem"),
    "medhanialem":          _p("Medhanialem"),
    "bisrate_gabriel":      _p("Bisrate Gabriel"),
    "lideta":               _p("Lideta", sub_city="Lideta", at=(9.0082, 38.7400)),
    "tor_hayloch":          _p("Tor Hayloch", sub_city="Kolfe", at=(9.0100, 38.7200)),
    "ayer_tena":            _p("Ayer Tena", sub_city="Kolfe"),
    "kolfe":                _p("Kolfe", sub_city="Kolfe", at=(9.0100, 38.7200)),
    "wingate":              _p("Wingate", sub_city="Kolfe"),
    "alem_gena":            _p("Alem Gena"),
    "jemo":                 _p("Jemo", sub_city="Kolfe", at=(8.9450, 38.7350)),
    "lebu":                 _p("Lebu", sub_city="Kolfe", at=(8.9528, 38.7196)),
    "lebu_varnero":         _p("Lebu Varnero", sub_city="Kolfe", parent="lebu"),
    "jarsso":               _p("Jarso"),
    "gofa":                 _p("Gofa"),
    "kality":               _p("Kality", sub_city="Akaki", at=(8.9128, 38.7451)),
    "akaki":                _p("Akaki", sub_city="Akaki", at=(8.9128, 38.7451)),
    "kilinto_industrial":   _p("Kilinto Industrial Park", sub_city="Akaki"),
    "addis_industrial":     _p("Industrial Zone"),
    # ── Outside Addis Ababa ───────────────────────────────────────────
    "sheger_city":          _p("Sheger City", SHEGER, "Sheger", at=(8.8800, 38.8100)),
    "legetafo":             _p("Legetafo", SHEGER, "Sheger", at=(9.0700, 38.8300)),
    "burayu":               _p("Burayu", SHEGER, "Sheger", at=(9.0600, 38.6500)),
    "sebeta":               _p("Sebeta", SHEGER, "Sheger"),
    "sululta":              _p("Sululta", SHEGER, "Sheger", at=(9.1700, 38.7500)),
    "chancho":              _p("Chancho", SHEGER, "Sheger"),
    "holeta":               _p("Holeta", SHEGER, "Sheger"),
    "sendafa":              _p("Sendafa", SHEGER, "Sheger"),
    # The parser has always counted these as Addis Ababa (Gelan condominiums are
    # run by Addis); Dukem and Chacha lie outside both (see STATUS.md).
    "gelan":                _p("Gelan", sub_city="Sheger", at=(8.8800, 38.8100)),
    "dukem":                _p("Dukem", sub_city="Sheger", at=(8.8500, 38.8300)),
    "chacha":               _p("Chacha"),
}

# Old codes written by earlier versions of the scripts, and the code each became.
RENAMED_CODES = {
    "piyasa": "piassa", "friendship": "piassa",
    "twenty_two": "haya_hulet", "22_area": "haya_hulet", "22_mazoria": "haya_hulet",
    "4_kilo": "4kilo", "6_kilo": "6kilo", "7_kilo": "7kilo",
    "wollo_sefer": "wello_sefer",
    "arabsa": "bole_arabsa", "bulbula": "bole_bulbula", "lemi_bole": "bole_lemi",
    "ayat": "ayat_zone", "cmc": "cmc_michael",
    "sarbet": "sarbet_old_airport", "old_airport": "sarbet_old_airport",
    "kaliti": "kality", "akaki_kality": "akaki",
    "german_square": "german", "tuludimtu": "tulu_dimtu",
    "bole_meskel_flower": "meskel_flower", "mexico_sengatera": "sengatera",
    "winget": "wingate", "debre_berhan": "chacha",
    "tafo_adebabay": "tafo", "tafo_condominium": "tafo",
    "sheger_burayu": "burayu", "sheger_sululta": "sululta", "sheger_sebeta": "sebeta",
}

# Priority order: a more specific place before the wider one that contains it.
# The order follows the parser's LOCATION_MAP before S6, with the names known only
# to topic_resolver.py, dedup_and_fix_locations.py and geocoder.py added in place.
ALIASES: list[tuple[str, str]] = [
    # ── Places rescued from listings without a location ──────────────
    ("bisrate gabriel", "bisrate_gabriel"), ("ቢስራተ ገብርኤል", "bisrate_gabriel"),
    ("ብስራተ ገብርኤል", "bisrate_gabriel"), ("ብስራተ ገብሬል", "bisrate_gabriel"),
    ("awere", "awere"), ("አዋሬ", "awere"),
    ("mebratu", "bulgaria"), ("መብራቱ", "bulgaria"),
    ("gotera", "gotera"), ("ጎተራ", "gotera"),
    # "mex" used to match inside "mexico", which gave Mexico this early place.
    ("mex", "mexico"), ("mexico", "mexico"), ("ሜክስ", "mexico"), ("ሜክሲኮ", "mexico"),
    ("tulu dimtu", "tulu_dimtu"), ("tuludimtu", "tulu_dimtu"),
    ("ጡሉ ዲምቱ", "tulu_dimtu"), ("ቱሉ ዲምቱ", "tulu_dimtu"), ("ቱሉዱምቱ", "tulu_dimtu"),
    ("summit safari", "summit"), ("ሰሚት ሳፋሪ", "summit"),
    ("kotebe 02", "kotebe"), ("ኮተቤ 02", "kotebe"),
    ("adanech park", "kazanchis"), ("አዳነች ፓርክ", "kazanchis"),
    ("friendship square", "piassa"), ("ፍሬንድሺፕ", "piassa"),
    ("sheraton", "kazanchis"), ("ሸራተን", "kazanchis"),
    ("chacha", "chacha"), ("ቻቻ", "chacha"),
    ("tafo ccd", "sheger_city"), ("ccd tafo", "sheger_city"), ("ጣፎ ccd", "sheger_city"),
    ("legetafo ccd", "legetafo"), ("ለገጣፎ ccd", "legetafo"),
    ("ccd", "ayat_zone"), ("ሲሲዲ", "ayat_zone"),
    ("abo mazoriya", "mekanisa_abo"), ("አቦ ማዞሪያ", "mekanisa_abo"),
    ("mekanisa", "mekanisa_abo"), ("mekanissa", "mekanisa_abo"), ("መካኒሳ", "mekanisa_abo"),
    ("haya hulet", "haya_hulet"), ("hayahulet", "haya_hulet"), ("ሀያ ሁለት", "haya_hulet"),
    ("ሃያ ሁለት", "haya_hulet"), ("22 mazoria", "haya_hulet"), ("22 mazoriya", "haya_hulet"),
    ("22 ማዞሪያ", "haya_hulet"), ("lem hotel", "haya_hulet"), ("ለም ሆቴል", "haya_hulet"),
    ("golagol", "haya_hulet"), ("ጎላጎል", "haya_hulet"),

    # ── Bole sub-areas (before plain "bole") ─────────────────────────
    ("bole bulbula", "bole_bulbula"), ("ቦሌ ቡልቡላ", "bole_bulbula"),
    ("bole michael", "bole_michael"), ("bole mikael", "bole_michael"), ("bole mikiel", "bole_michael"),
    ("bolemic", "bole_michael"), ("bole harmony", "bole_michael"), ("ቦሌ ሚካኤል", "bole_michael"),
    ("bole arabsa", "bole_arabsa"), ("ቦሌ አራብሳ", "bole_arabsa"),
    ("rwanda kuter", "bole_rwanda"), ("rwanda", "bole_rwanda"),
    ("bole rwanda", "bole_rwanda"), ("bole ruwanda", "bole_rwanda"), ("ቦሌ ርዋንዳ", "bole_rwanda"),
    ("bole japan", "bole_japan"), ("ቦሌ ጃፓን", "bole_japan"),
    ("bole brass", "bole_brass"), ("ቦሌ ብራስ", "bole_brass"),
    ("bole lemi industrial", "bole_lemi_industrial"), ("boli lemi", "bole_lemi_industrial"),
    ("bole lemi", "bole_lemi"), ("ቦሌ ለሚ", "bole_lemi"), ("lemi bole", "bole_lemi"),
    ("bole medhanialem", "bole_medhanialem"),
    ("bole adeyabeba", "bole_adeyabeba"), ("ቦሌ አደይ አበባ", "bole_adeyabeba"),
    ("bole gerji", "gerji"),
    ("bole meskel flower", "meskel_flower"), ("bole meskel", "meskel_flower"), ("bole mesqel", "meskel_flower"),
    ("bole airport road", "bole_airport_road"),

    # ── Ayat sub-areas ───────────────────────────────────────────────
    ("ayat 49", "ayat_49"), ("አያት 49", "ayat_49"),
    ("ayat mekdonia", "ayat_mekdonia"), ("ayat meqdonia", "ayat_mekdonia"), ("አያት መቅዶንያ", "ayat_mekdonia"),
    ("ayat tafo", "ayat_zone"),

    # ── Summit sub-areas ─────────────────────────────────────────────
    ("summit 72", "summit_72"), ("ሰሚት 72", "summit_72"),
    ("summit figa", "summit_figa"), ("ሰሚት ፊጋ", "summit_figa"),
    ("figa mebrat", "figa_mebrat"), ("ፊጋ መብራት", "figa_mebrat"),
    ("figa", "figa"), ("ፊጋ", "figa"),
    ("german", "german"), ("ጀርመን", "german"),

    # ── CMC / Michael ────────────────────────────────────────────────
    ("cmc", "cmc_michael"), ("ሲኤምሲ", "cmc_michael"),
    ("signal", "signal"), ("ሲግናል", "signal"),

    # ── Kazanchis / Meskel Flower ────────────────────────────────────
    ("kazanchis", "kazanchis"), ("kazanches", "kazanchis"), ("ካዛንቺስ", "kazanchis"), ("ካሳንቺስ", "kazanchis"),
    ("meskel flower", "meskel_flower"), ("meskel flore", "meskel_flower"), ("mesqel flower", "meskel_flower"),
    ("መስቀል ፍሎወር", "meskel_flower"), ("መስቀል ፍላወር", "meskel_flower"),
    ("meskel square", "meskel_square"),

    # ── Piassa / old town ────────────────────────────────────────────
    ("piassa", "piassa"), ("piaza", "piassa"), ("piyasa", "piassa"), ("ፒያሳ", "piassa"),
    ("sarem", "piassa"), ("ሳሬም", "piassa"),
    ("arada", "arada"), ("አራዳ", "arada"),
    ("teklehaimanot", "teklehaimanot"), ("tekle haimanot", "teklehaimanot"), ("ጥቅለ ሃይማኖት", "teklehaimanot"),
    ("merkato", "merkato"), ("መርካቶ", "merkato"),

    # ── 4 / 6 / 7 kilo ───────────────────────────────────────────────
    ("4 kilo", "4kilo"), ("arat kilo", "4kilo"), ("4ኪሎ", "4kilo"), ("አራት ኪሎ", "4kilo"),
    ("6 kilo", "6kilo"), ("siddist kilo", "6kilo"), ("6ኪሎ", "6kilo"), ("ስድስት ኪሎ", "6kilo"),
    ("7 kilo", "7kilo"), ("sebategna", "7kilo"), ("ሰባት ኪሎ", "7kilo"),

    # ── Gerji / Haile Garment ────────────────────────────────────────
    ("gerji", "gerji"), ("ገርጂ", "gerji"),
    ("haile garment", "haile_garment"), ("ሃይሌ ጋርመንት", "haile_garment"),
    ("ሀይሌ ጋርመንት", "haile_garment"), ("ኃይሌ ጋርመንት", "haile_garment"),
    ("garment", "garment"), ("ጋርመንት", "garment"),

    # ── Megenagna / Wello Sefer ──────────────────────────────────────
    ("megenagna", "megenagna"), ("megna", "megenagna"), ("መገናኛ", "megenagna"),
    ("egziabher ab", "megenagna"), ("እግዚያራብ", "megenagna"),
    ("wello sefer", "wello_sefer"), ("welo sefer", "wello_sefer"), ("wollo sefer", "wello_sefer"),
    ("wolo sefer", "wello_sefer"), ("ወሎ ሰፈር", "wello_sefer"),

    # ── Sarbet / old airport ─────────────────────────────────────────
    ("sarbet", "sarbet_old_airport"), ("sar bet", "sarbet_old_airport"), ("ሳርቤት", "sarbet_old_airport"),
    ("ሳር ቤት", "sarbet_old_airport"),
    ("old airport", "sarbet_old_airport"), ("ድሮ አውሮፕላን ማረፊያ", "sarbet_old_airport"),
    ("ድሮ አየር ማረፊያ", "sarbet_old_airport"), ("ድሮ አየር", "sarbet_old_airport"),

    # ── Jemo / Kality ────────────────────────────────────────────────
    ("jemo", "jemo"), ("ጀሞ", "jemo"),
    ("kality", "kality"), ("kaliti", "kality"), ("ቃሊቲ", "kality"),
    ("akaki", "akaki"), ("አቃቂ", "akaki"),

    # ── Lebu / Lafto / Nifas Silk ────────────────────────────────────
    ("lebu varnero", "lebu_varnero"), ("varnero", "lebu_varnero"), ("ቫርኔሮ", "lebu_varnero"),
    ("lebu", "lebu"), ("ለቡ", "lebu"),
    ("lafto", "lafto"), ("ላፍቶ", "lafto"), ("laphto", "lafto"),
    ("nifas silk", "nifas_silk"), ("ንፋስ ስልክ", "nifas_silk"),

    # ── Kolfe / Gofa / Saris ─────────────────────────────────────────
    ("kolfe", "kolfe"), ("ኮልፌ", "kolfe"), ("ቆልፌ", "kolfe"),
    ("gofa", "gofa"), ("ጎፋ", "gofa"),
    ("saris", "saris"), ("ሳሪስ", "saris"),

    # ── Lideta / Kirkos / Yeka ───────────────────────────────────────
    ("lideta", "lideta"), ("ልደታ", "lideta"),
    ("kirkos", "kirkos"), ("ቂርቆስ", "kirkos"),
    ("yeka", "yeka"), ("የካ", "yeka"),

    # ── Sengatera / Urael / Bambis ───────────────────────────────────
    ("sengatera", "sengatera"), ("ሰንጋትራ", "sengatera"), ("ሰንጋተራ", "sengatera"),
    ("urael", "urael"), ("ኡራኤል", "urael"),
    ("bambis", "bambis"), ("ባምቢስ", "bambis"),

    # ── Gurd Shola / Alem Bank ───────────────────────────────────────
    ("gurd shola", "gurd_shola"), ("ጉርድ ሾላ", "gurd_shola"),
    ("alem bank", "alem_bank"), ("አለም ባንክ", "alem_bank"),

    # ── Bethel / Kebena ──────────────────────────────────────────────
    ("bethel", "bethel"), ("ቤተለ", "bethel"), ("ቤተል", "bethel"),
    ("kebena", "kebena"), ("ቀበና", "kebena"),

    # ── Bulgaria / Atlas / Lemi Kura ─────────────────────────────────
    ("bulgaria", "bulgaria"), ("ቡልጋሪያ", "bulgaria"),
    ("atlas", "bole_atlas"),
    ("lemi kura", "lemi_kura"), ("ለሚ ኩራ", "lemi_kura"),

    # ── Plain Bole / Ayat / Summit (after their sub-areas) ───────────
    ("bulbula", "bole_bulbula"), ("ቡልቡላ", "bole_bulbula"),
    ("arabsa", "bole_arabsa"), ("አራብሳ", "bole_arabsa"),
    ("bole", "bole_main"), ("ቦሌ", "bole_main"),
    ("ayat", "ayat_zone"), ("ayate", "ayat_zone"), ("አያት", "ayat_zone"),
    ("summit", "summit"), ("ሰሚት", "summit"), ("ሳሚት", "summit"),

    # ── Tor Hayloch ──────────────────────────────────────────────────
    ("tor hayloch", "tor_hayloch"), ("tor hailoch", "tor_hayloch"), ("thorhailoch", "tor_hayloch"),
    ("ጦር ኃይሎች", "tor_hayloch"), ("ጦር ሃይሎች", "tor_hayloch"), ("ጦር ሀይሎች", "tor_hayloch"), ("ጦርሃይሎች", "tor_hayloch"),

    # ── Shola / Ayer Tena / Wesen ────────────────────────────────────
    ("sholla", "sholla"), ("shola", "sholla"), ("ሾላ", "sholla"),
    ("ayer tena", "ayer_tena"), ("ayertena", "ayer_tena"), ("አየር ጤና", "ayer_tena"),
    ("wesen", "wesen"), ("ወሰን", "wesen"),

    # ── Pastor / Medhanialem / Hiya / Enkulal Fabrica ────────────────
    ("pastor", "pastor_medhanialem"), ("ፓስተር", "pastor_medhanialem"),
    ("medhanialem", "medhanialem"), ("መድሃኒዓለም", "medhanialem"),
    ("hiya", "hiya"), ("ሂያ", "hiya"),
    ("enkulal fabrica", "enkulal_fabrica"), ("enkolal fabrica", "enkulal_fabrica"), ("እንቁላል ፋብሪካ", "enkulal_fabrica"),

    # ── Outside Addis (Sheger before Tafo: "Tafo, Sheger" is Sheger) ─
    ("sheger", "sheger_city"), ("ሸገር", "sheger_city"),
    ("legetafo", "legetafo"), ("legetaffo", "legetafo"), ("ለገጣፎ", "legetafo"), ("ለጌጣፎ", "legetafo"),
    ("burayu", "burayu"), ("ቡራዩ", "burayu"),
    ("sebeta", "sebeta"), ("ሰበታ", "sebeta"),
    ("sululta", "sululta"), ("ሱሉልታ", "sululta"),
    ("chancho", "chancho"), ("ጫንቾ", "chancho"), ("ጫንጮ", "chancho"),
    ("holeta", "holeta"), ("ሆለታ", "holeta"),
    ("sendafa", "sendafa"), ("ሰንዳፋ", "sendafa"),
    ("gelan", "gelan"), ("ገላን", "gelan"),
    ("dukem", "dukem"), ("ዱከም", "dukem"),

    # ── Other neighbourhoods ─────────────────────────────────────────
    ("jacros", "jacros"), ("ጃክሮስ", "jacros"),
    ("la gare", "la_gare"), ("ለገሃር", "la_gare"),
    ("dembel", "dembel"), ("ደንበል", "dembel"),
    ("goro", "goro"), ("ጎሮ", "goro"),
    ("addisu gebeya", "addisu_gebeya"), ("አዲሱ ገበያ", "addisu_gebeya"),
    ("alem gena", "alem_gena"), ("አለም ገና", "alem_gena"),
    ("atena tera", "atena_tera"), ("አጠና ተራ", "atena_tera"),
    ("ambassador", "ambassador"), ("አምባሳደር", "ambassador"),
    ("kotebe", "kotebe"), ("ኮተቤ", "kotebe"), ("ቆጠቤ", "kotebe"), ("ቆተቤ", "kotebe"),
    ("ferensay", "ferensay"), ("ferensai", "ferensay"), ("ፈረንሳይ", "ferensay"),
    ("jarsso", "jarsso"), ("jarso", "jarsso"), ("ጃርሶ", "jarsso"),
    ("stadium", "stadium"), ("ስታድዬም", "stadium"),
    ("lamberet", "lamberet"), ("ላምበረት", "lamberet"),
    ("wingate", "wingate"), ("winget", "wingate"), ("ዊንጌት", "wingate"),
    ("awareness", "awareness"), ("አዌርነስ", "awareness"),
    ("imperial", "imperial"), ("ኢምፔሪያል", "imperial"),
    ("salite mehret", "salite_mehret"), ("salete mihret", "salite_mehret"), ("ሳልቴ ምህረት", "salite_mehret"),
    ("addis ketema", "addis_ketema"), ("አዲስ ከተማ", "addis_ketema"),
    ("mikililand", "mikililand"), ("ሚኪሊላንድ", "mikililand"),
    ("industry zone", "addis_industrial"), ("industrial zone", "addis_industrial"), ("ኢንዱስትሪ ዞን", "addis_industrial"),
    ("kilinto", "kilinto_industrial"), ("ቂሊንጦ", "kilinto_industrial"),
    ("addis sefer", "addis_sefer"), ("አዲስ ሰፈር", "addis_sefer"),
    ("sefere selam", "sefere_selam"),
    ("gulele", "gulele"), ("entoto", "entoto"),
    ("tafo", "tafo"), ("ጣፎ", "tafo"),
    ("airport road", "bole_airport_road"), ("bole airport", "bole_airport_road"),
]

_ETHIOPIC = "ሀ-፿"
# Amharic prepositions are written onto the next word: በቦሌ "in Bole", ከአያት "from Ayat".
_AMHARIC_PREFIX = r"(?:በ|ከ|ለ|የ|ወደ\s?)?"
_CAMEL_RE = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"           # "BoleBulbula", "CMCApartment"
    rf"|(?<=[{_ETHIOPIC}])(?=[A-Za-z])|(?<=[A-Za-z])(?=[{_ETHIOPIC}])"   # "ቦሌMeskel"
)
_SEPARATORS_RE = re.compile(r"[_./\\|\-]+")


def _alias_pattern(alias: str) -> re.Pattern:
    body = r"\s*".join(re.escape(word) for word in alias.split())
    starts_ethiopic = bool(re.match(f"[{_ETHIOPIC}]", alias))
    left = r"(?<![^\W\d_])" + (_AMHARIC_PREFIX if starts_ethiopic else "")
    if alias[0].isdigit():
        left = r"(?<![\d.,])"
    right = r"(?!\d)" if alias[-1].isdigit() else r"(?![^\W\d_])"
    return re.compile(left + body + right, re.IGNORECASE)


_COMPILED = [(_alias_pattern(alias), code) for alias, code in ALIASES]


def _prepare(text: str) -> str:
    """Split CamelCase ("BoleBulbula") and separators ("Legacy_Green", "6.kilo") into words."""
    text = unicodedata.normalize("NFKC", text or "")
    text = _CAMEL_RE.sub(" ", text)
    return _SEPARATORS_RE.sub(" ", text)


def match_text(text: str) -> Optional[str]:
    """The code of the first place (in ALIASES order) named anywhere in the text, or None."""
    prepared = _prepare(text)
    if not prepared.strip():
        return None
    for pattern, code in _COMPILED:
        if pattern.search(prepared):
            return code
    return None


def _match_inside_hashtag(tag: str) -> Optional[str]:
    """
    Hashtags often run words together in lower case ("#summithouse",
    "#ቦሌቡልጋሪያ"). A place name counts at the start of the tag if it has 3+
    letters, anywhere in it if it has 4+: so "#teamexcellence" is not Mexico
    ("mex") and "#የካሬ…" is not Yeka ("የካ").
    """
    squeezed = re.sub(r"[\W_]", "", _prepare(tag)).lower()
    for alias, code in ALIASES:
        name = alias.replace(" ", "").lower()
        if (len(name) >= 3 and squeezed.startswith(name)) or (len(name) >= 4 and name in squeezed):
            return code
    return None


def find_location(text: str, label: Optional[str] = None) -> str:
    """
    The location code for a listing: from its location label if it has one
    ("Location: Bole"), else its hashtags ("#ቦሌ"), else the whole text.
    """
    if label:
        code = match_text(label)
        if code:
            return code
    for tag in re.findall(r"#([^\s#]+)", text or ""):
        if tag == "22":   # "#22" on its own is the 22 area
            return "haya_hulet"
        code = match_text(tag) or _match_inside_hashtag(tag)
        if code:
            return code
    return match_text(text) or UNKNOWN


def city_of(code: Optional[str]) -> str:
    place = PLACES.get(code or "")
    return place.city if place else ADDIS


def coordinates(code: Optional[str]) -> Optional[tuple[float, float, Optional[str]]]:
    """(lat, lon, sub_city) of a place, or of its wider area; None if unknown."""
    seen = set()
    while code and code in PLACES and code not in seen:
        seen.add(code)
        place = PLACES[code]
        if place.lat is not None:
            return place.lat, place.lon, place.sub_city
        code = place.parent
    return None


def canonical(code: Optional[str]) -> Optional[str]:
    """Today's code for a code written by an older script."""
    return RENAMED_CODES.get(code, code)
