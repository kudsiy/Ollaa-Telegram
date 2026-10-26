# -*- coding: utf-8 -*-
import re
from sqlalchemy import create_engine, text
from settings import DB_URL

# =========================
# DATABASE CONNECTION
# =========================
# Ensure your PostgreSQL service is running and credentials match
engine = create_engine(DB_URL)

# =========================
# AMHARIC & ENGLISH TOKENS
# =========================

PLOT_KEYWORDS = [
    r'plot', r'land',
    r'ይዞታ', r'የመሬት', r'የቦታ ስፋት', r'ግቢ'
]

BUILTUP_KEYWORDS = [
    r'built\s*up', r'net\s*area', r'gross\s*area',
    r'የቤት ስፋት', r'የግንባታ ስፋት', r'ቤቱ ያረፈበት', r'የቤቱ ስፋት', r'ስፋት'
]

DEVELOPER_SUFFIXES = [
    r'real\s*estate', r'properties', r'developers?',
    r'construction', r'development', r'plc', 
    r'ሪል\s*እስቴት', r'ፕሮፐርቲስ', r'ግንባታ', r'ኮንስትራክሽን'
]

FINISH_STATUS_MAP = {
    'fully_furnished': [
        r'fully\s*furnished', r'ፈርኒሽድ', r'የተሟላ የቤት እቃ',r'የቤት እቃ'
    ],
    'fully_finished': [
        r'fully\s*finished', r'ሙሉ\s*የተጠናቀቀ',r'ግንባታው የተጠናቀቀ' 
    ],
    'semi_finished': [
        r'semi\s*finished', r'በከፊል\s*የተጠናቀቀ'
    ],
    'unfinished': [
        r'under\s*construction', r'ግንባታ\s*ላይ'
    ]
}

PROPERTY_TYPES = {
    'villa': [r'villa', r'ቪላ'],
    'apartment': [r'apartment', r'አፓርታማ'],
    'townhouse': [r'town\s*house'],
    'condominium': [r'condominium', r'ኮንዶሚኒየም'],
}

SERVICE_QUARTERS = [
    r'service\s*quarter', r'\bSQ\b', r'ሰርቪስ\s*ክፍል'
]

DOWNPAYMENT = [
    r'down\s*payment', r'advance',
    r'ቅድመ\s*ክፍያ', r'ቅድሚያ'
]

BANK_FINANCING_PATTERNS = [
    r'bank\s*(loan|finance|financing)',
    r'bank\s*option',
    r'ባንክ\s*ብድር',
    r'ባንክ\s*አማራጭ'
]

BANK_COVERAGE_PATTERNS = [
    r'(\d{1,2})\s*%\s*bank',
    r'bank\s*covers\s*(\d{1,2})\s*%',
    r'(\d{1,2})\s*%\s*ባንክ'
]

BEDROOM_PATTERNS = [
    r'(\d+)\s*bed(room)?s?',
    r'(\d+)\s*br\b',
    r'(\d+)\s*ክፍል\s*መኝታ',
    r'(\d+)\s*መኝታ'
]

BATHROOM_PATTERNS = [
    r'(\d+)\s*bath(room)?s?',
    r'(\d+)\s*wc\b',
    r'(\d+)\s*ባኞ',
    r'(\d+)\s*መታጠቢያ'
]

LOCATION_PATTERNS = [
    r'📍\s*([A-Zአ-ዿ][\wአ-ዿ\s\-]{2,50})',
    r'location[:\-]?\s*([A-Zአ-ዿ][\wአ-ዿ\s\-]{2,50})',
    r'ቦታ[:\-]?\s*([አ-ዿ\s]{2,50})',
    r'አካባቢ[:\-]?\s*([አ-ዿ\s]{2,50})',
    r'ሰፈር[:\-]?\s*([አ-ዿ\s]{2,50})'
]

VILLA_FLOORS = [
    r'G\+\d',
    r'ground\s*\+\s*\d',
    r'ግራውንድ\s*\+\s*\d'
]

# =========================
# HELPERS
# =========================

def extract_numbers(text):
    # Regex handles numbers with commas
    return [int(n.replace(',', '')) for n in re.findall(r'\b[\d,]{2,15}\b', text) if n.replace(',', '').isdigit()]

def extract_plot(text):
    for kw in PLOT_KEYWORDS:
        if re.search(kw, text, re.I):
            nums = extract_numbers(text)
            for n in nums:
                if n <= 5000:
                    return n
    return None

def extract_builtup(text):
    for kw in BUILTUP_KEYWORDS:
        if re.search(kw, text, re.I):
            nums = extract_numbers(text)
            for n in nums:
                if 30 <= n <= 1000:
                    return n
    return None

def extract_price(text):
    nums = extract_numbers(text)
    for n in nums:
        if n >= 200000:
            return n
    return None

def extract_developer(text):
    for suf in DEVELOPER_SUFFIXES:
        m = re.search(r'([A-Zh-፰][\w\-\s]{2,40})\s+' + suf, text, re.I)
        if m:
            name = m.group(0).strip()
            if name.lower() not in ['real estate', 'developers', 'construction']:
                return name
    return None

def extract_finish_status(text):
    for status, patterns in FINISH_STATUS_MAP.items():
        for p in patterns:
            if re.search(p, text, re.I):
                return status
    return None

def extract_property_type(text):
    for ptype, patterns in PROPERTY_TYPES.items():
        for p in patterns:
            if re.search(p, text, re.I):
                return ptype
    return None

def has_service_quarters(text):
    return any(re.search(p, text, re.I) for p in SERVICE_QUARTERS)

def extract_downpayment(text):
    for p in DOWNPAYMENT:
        if re.search(p, text, re.I):
            perc = re.search(r'(\d{1,2})\s*%', text)
            amt = re.search(r'(\d{6,8})', text)
            return (
                int(perc.group(1)) if perc else None,
                int(amt.group(1)) if amt else None
            )
    return (None, None)

def extract_bank_financing(text):
    return any(re.search(p, text, re.I) for p in BANK_FINANCING_PATTERNS)

def extract_bank_coverage(text):
    for p in BANK_COVERAGE_PATTERNS:
        m = re.search(p, text, re.I)
        if m:
            pct = int(m.group(1))
            if 10 <= pct <= 80:
                return pct
    return None

def extract_bedrooms(text):
    for p in BEDROOM_PATTERNS:
        m = re.search(p, text, re.I)
        if m:
            n = int(m.group(1))
            if 0 < n <= 10:
                return n
    return None

def extract_bathrooms(text):
    for p in BATHROOM_PATTERNS:
        m = re.search(p, text, re.I)
        if m:
            n = int(m.group(1))
            if 0 < n <= 10:
                return n
    return None

def extract_location(text):
    for p in LOCATION_PATTERNS:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip()
    return None

def extract_villa_floors(text):
    m = re.search('|'.join(VILLA_FLOORS), text, re.I)
    return m.group(0) if m else None

# =========================
# MAIN NORMALIZATION
# =========================

with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT id, text FROM telegram_listings
    """)).fetchall()

    for r in rows:
        t = r.text or ""

        plot = extract_plot(t)
        built = extract_builtup(t)
        price = extract_price(t)
        dev = extract_developer(t)
        finish = extract_finish_status(t)
        ptype = extract_property_type(t)
        sq = has_service_quarters(t)
        dp_pct, dp_amt = extract_downpayment(t)
        bank_fin = extract_bank_financing(t)
        bank_pct = extract_bank_coverage(t)
        beds = extract_bedrooms(t)
        baths = extract_bathrooms(t)
        loc = extract_location(t)
        floors = extract_villa_floors(t)

        conn.execute(text("""
            UPDATE telegram_listings SET
                plot_sqm = COALESCE(:plot, plot_sqm),
                builtup_sqm = COALESCE(:built, builtup_sqm),
                price = COALESCE(:price, price),
                developer_name = COALESCE(:dev, developer_name),
                finish_status = COALESCE(:finish, finish_status),
                property_type = COALESCE(:ptype, property_type),
                has_service_quarters = COALESCE(:sq, has_service_quarters),
                down_payment_percent = COALESCE(:dp_pct, down_payment_percent),
                down_payment_amount = COALESCE(:dp_amt, down_payment_amount),
                bank_financing_available = COALESCE(:bank_fin, bank_financing_available),
                bank_coverage_percent = COALESCE(:bank_pct, bank_coverage_percent),
                bedrooms = COALESCE(:beds, bedrooms),
                bathrooms = COALESCE(:baths, bathrooms),
                location_text = COALESCE(:loc, location_text),
                villa_floors = COALESCE(:floors, villa_floors)
            WHERE id = :id
        """), {
            "id": r.id,
            "plot": plot,
            "built": built,
            "price": price,
            "dev": dev,
            "finish": finish,
            "ptype": ptype,
            "sq": sq,
            "dp_pct": dp_pct,
            "dp_amt": dp_amt,
            "bank_fin": bank_fin,
            "bank_pct": bank_pct,
            "beds": beds,
            "baths": baths,
            "loc": loc,
            "floors": floors
        })

print("Semantic normalization complete.")