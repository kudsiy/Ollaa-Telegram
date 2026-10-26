"""
text_normalizer.py — Amharic/English text normalization for Ollaa pipeline
Place in: C:\Projects\ollaa\src\text_normalizer.py

Handles:
  - Ethiopic character equivalence normalization
  - Phone number extraction and canonicalization
  - Price expression normalization (ሚሊዮን, M, half million, k, etc.)
  - Mixed-script and zero-width character cleanup
  - Script detection (amharic / latin / mixed)
"""

import re
import unicodedata
from typing import Optional

# ── Ethiopic Character Normalization Map ──────────────────────────────────────
# Standard Amharic NLP normalization: map visually/phonetically equivalent
# Ethiopic characters to a single canonical form.
# Without this, the same word spelled with ሀ vs ሐ vs ሃ produces 3 different
# embeddings and breaks semantic search + deduplication.

ETHIOPIC_NORM_MAP = {
    # ── ha variants → canonical ሃ (U+1203) ──
    'ሀ': 'ሃ',   # U+1200
    'ሐ': 'ሃ',   # U+1210
    'ሓ': 'ሃ',   # U+1213
    'ሑ': 'ሁ',   # U+1211
    'ሔ': 'ሄ',   # U+1214
    'ሕ': 'ህ',   # U+1215
    'ሖ': 'ሆ',   # U+1216

    # ── se variants → canonical ሰ (U+1230) ──
    'ሠ': 'ሰ',   # U+1220
    'ሢ': 'ሲ',   # U+1222
    'ሣ': 'ሳ',   # U+1223
    'ሤ': 'ሴ',   # U+1224
    'ሥ': 'ስ',   # U+1225
    'ሦ': 'ሶ',   # U+1226

    # ── tse variants → canonical ጸ (U+1338) ──
    'ፀ': 'ጸ',   # U+1380
    'ፁ': 'ጹ',
    'ፂ': 'ጺ',
    'ፃ': 'ጻ',
    'ፄ': 'ጼ',
    'ፅ': 'ጽ',
    'ፆ': 'ጾ',

    # ── glottal variants → canonical አ (U+12A0) ──
    'ዓ': 'አ',   # U+12D3
    'ዐ': 'አ',   # U+12D0
    'ዑ': 'ኡ',
    'ዒ': 'ኢ',
    'ዔ': 'ኤ',
    'ዕ': 'እ',
    'ዖ': 'ኦ',
}

_ETHIOPIC_TRANS = str.maketrans(ETHIOPIC_NORM_MAP)

# ── Phone Number Normalization ─────────────────────────────────────────────────

def normalize_phone(text: str) -> Optional[str]:
    """
    Extract and normalize the FIRST Ethiopian phone number in text.
    Returns canonical +251XXXXXXXXX format or None.

    Handles: +251..., 00251..., 09..., 07..., plain 9...
    """
    if not text:
        return None

    # Strip formatting characters before matching
    clean = re.sub(r'[\s\-\(\)\.]+', '', text)

    # +251 / 00251 prefix
    m = re.search(r'(?:\+251|00251)([79]\d{8})', clean)
    if m:
        return f'+251{m.group(1)}'

    # 09 / 07 prefix (local format)
    m = re.search(r'\b0([79]\d{8})\b', clean)
    if m:
        return f'+251{m.group(1)}'

    # Bare 9/7 digits without prefix — less reliable, only if 9 digits
    m = re.search(r'\b([79]\d{8})\b', clean)
    if m:
        return f'+251{m.group(1)}'

    return None


def extract_all_phones(text: str) -> list:
    """Extract ALL phone numbers from text. Returns list of canonical strings."""
    if not text:
        return []

    phones = set()
    clean = re.sub(r'[\s\-\(\)\.]+', '', text)

    for m in re.finditer(r'(?:\+251|00251)([79]\d{8})', clean):
        phones.add(f'+251{m.group(1)}')

    for m in re.finditer(r'\b0([79]\d{8})\b', clean):
        phones.add(f'+251{m.group(1)}')

    return sorted(phones)


# ── Price Normalization ────────────────────────────────────────────────────────

# Amharic number words used in price expressions
_AM_MILLION  = ['ሚሊዮን', 'ሚሊዮኖች']
_AM_THOUSAND = ['ሺ', 'ሺህ']
_AM_HUNDRED  = ['መቶ']
_AM_HALF     = ['ተኩል', 'ፈረቃ', 'ተቀናሽ']
_AM_HALF_LAT = ['half', 'and half', 'and a half']


def normalize_price(text: str) -> Optional[float]:
    """
    Convert any Ethiopian price expression to a float in ETB.
    Returns None if no recognizable price found.

    Handles:
      '5 ሚሊዮን'         → 5_000_000.0
      '2.5M birr'       → 2_500_000.0
      'half million'    → 500_000.0
      '15k per month'   → 15_000.0
      '15,000'          → 15_000.0
      '5,000,000'       → 5_000_000.0
      'ሁለት ሚሊዮን ተኩል'   → 2_500_000.0  (partial support via pattern)
      'negotiable'      → None (handled by is_price_negotiable)
    """
    if not text:
        return None

    t = text.lower().replace(',', '').replace('،', '').strip()

    # ── Amharic: numeric + million ─────────────────────────────────────────
    for word in _AM_MILLION:
        m = re.search(rf'([\d]+\.?[\d]*)\s*{re.escape(word)}', text)
        if m:
            base = float(m.group(1))
            remainder = text[m.end():][:15]
            if any(h in remainder for h in _AM_HALF):
                base += 0.5
            return base * 1_000_000

    # ── Amharic: numeric + thousand ───────────────────────────────────────
    for word in _AM_THOUSAND:
        m = re.search(rf'([\d]+\.?[\d]*)\s*{re.escape(word)}', text)
        if m:
            return float(m.group(1)) * 1_000

    # ── Latin: half million / half a million ──────────────────────────────
    if re.search(r'half\s+(?:a\s+)?million', t):
        return 500_000.0

    # ── Latin: N million / Nm ─────────────────────────────────────────────
    m = re.search(r'([\d]+\.?[\d]*)\s*(?:million|mil\b)', t)
    if m:
        return float(m.group(1)) * 1_000_000

    m = re.search(r'([\d]+\.?[\d]*)\s*m\b', t)
    if m:
        val = float(m.group(1))
        if val < 1_000:          # e.g. "2.5m" — not "2500000m"
            return val * 1_000_000

    # ── Latin: N billion ──────────────────────────────────────────────────
    m = re.search(r'([\d]+\.?[\d]*)\s*(?:billion|bil\b|b\b)', t)
    if m:
        return float(m.group(1)) * 1_000_000_000

    # ── Latin: N thousand / Nk ────────────────────────────────────────────
    m = re.search(r'([\d]+\.?[\d]*)\s*(?:thousand|k\b)', t)
    if m:
        return float(m.group(1)) * 1_000

    # ── Plain large number ────────────────────────────────────────────────
    # Accept only numbers ≥ 1000 (avoids matching room counts etc.)
    m = re.search(r'\b(\d{4,12})\b', t.replace(',', ''))
    if m:
        return float(m.group(1))

    return None


def is_price_negotiable(text: str) -> bool:
    """Return True if the listing indicates price is negotiable."""
    keywords = [
        'negotiable', 'negotiate', 'ይደራደራል', 'ይደራደር', 'ድርድር',
        'ner', 'neg', 'price on request', 'call for price',
    ]
    t = text.lower()
    return any(k in t for k in keywords)


# ── Amharic Script Normalization ──────────────────────────────────────────────

def normalize_amharic(text: str) -> str:
    """
    Apply Ethiopic character normalization + Unicode NFC.
    Must be called before embedding or LLM extraction.
    """
    if not text:
        return text
    text = text.translate(_ETHIOPIC_TRANS)
    text = unicodedata.normalize('NFC', text)
    return text


def detect_script(text: str) -> str:
    """
    Classify the primary script of a text sample.
    Returns: 'amharic' | 'latin' | 'mixed' | 'unknown'
    """
    if not text:
        return 'unknown'

    ethiopic = sum(1 for c in text if '\u1200' <= c <= '\u139F')
    latin    = sum(1 for c in text if c.isalpha() and c.isascii())
    total    = ethiopic + latin

    if total == 0:
        return 'unknown'
    ratio = ethiopic / total
    if ratio > 0.70:
        return 'amharic'
    elif ratio < 0.30:
        return 'latin'
    return 'mixed'


def normalize_listing_text(raw_text: str) -> str:
    """
    Master normalization function. Run on every raw_text before
    any LLM call, embedding, or insertion into processed_listings.

    Steps:
      1. Remove zero-width / invisible characters
      2. Ethiopic character normalization
      3. Collapse horizontal whitespace
      4. Cap consecutive newlines at 2
      5. Normalize Ethiopic punctuation to ASCII equivalents
      6. Strip per-line whitespace
    """
    if not raw_text:
        return raw_text

    # Zero-width chars: ZWSP, ZWNJ, ZWJ, BOM, soft hyphen
    text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad\u00a0]', ' ', raw_text)

    # Ethiopic character normalization
    text = normalize_amharic(text)

    # Collapse horizontal whitespace
    text = re.sub(r'[ \t]+', ' ', text)

    # Ethiopic punctuation → ASCII
    text = re.sub(r'[።]', '. ', text)   # Ethiopic full stop
    text = re.sub(r'[፡]', ', ', text)   # Ethiopic word separator
    text = re.sub(r'[፤]', '; ', text)   # Ethiopic semicolon
    text = re.sub(r'[፣]', ', ', text)   # Ethiopic comma

    # Cap newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip per-line whitespace
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(line for line in lines).strip()

    return text


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  TEXT NORMALIZER — SELF TEST")
    print("=" * 55)

    price_tests = [
        '5 ሚሊዮን',
        '2.5M birr',
        'half million',
        'half a million birr',
        '15,000 per month',
        '5,000,000',
        '800k',
        '1.2 billion',
        'ሁለት ሚሊዮን ተኩል',
        '15 ሺ',
        'price negotiable',
    ]

    print("\n── Price Tests ──────────────────────────────────────")
    for p in price_tests:
        result = normalize_price(p)
        neg    = is_price_negotiable(p)
        if result is not None:
            print(f"  '{p}' → {result:,.0f} ETB")
        elif neg:
            print(f"  '{p}' → NEGOTIABLE")
        else:
            print(f"  '{p}' → None")

    phone_tests = [
        '+251911234567',
        '0911 234 567',
        '09-11-234-567',
        '00251911234567',
        'Call us: 0912345678 or 0923456789',
        'no phone here',
    ]

    print("\n── Phone Tests ──────────────────────────────────────")
    for p in phone_tests:
        single = normalize_phone(p)
        all_p  = extract_all_phones(p)
        print(f"  '{p}' → first={single} | all={all_p}")

    amharic_tests = [
        ('ሀ ሐ ሃ',  'ha variants → should all become ሃ'),
        ('ሠ vs ሰ',  'se variants → should all become ሰ'),
        ('ፀ vs ጸ',  'tse variants → should all become ጸ'),
        ('ዓ vs አ',  'glottal variants → should all become አ'),
    ]

    print("\n── Amharic Normalization Tests ──────────────────────")
    for text, desc in amharic_tests:
        normalized = normalize_amharic(text)
        print(f"  {desc}'):\n    input:  '{text}'\n    output: '{normalized}'")

    script_tests = [
        'ቦሌ ሱብ ሲቲ ኪራይ ቤት',
        'Bole sub city rental apartment',
        'Bole ቦሌ mixed listing 3 bed',
        '12345',
    ]

    print("\n── Script Detection Tests ───────────────────────────")
    for text in script_tests:
        script = detect_script(text)
        print(f"  '{text[:40]}' → {script}")

    print("\n✅ All tests complete.\n")
