"""
output_validator.py — Pydantic validation for all LLM extraction output
Place in: C:\Projects\ollaa\src\output_validator.py

CRITICAL: This file prevents hallucinated or malformed LLM output
from entering processed_listings or any valuation calculation.

Rule: LLM extracts text fields. Python validates and calculates.
      Never let the LLM do arithmetic unsupervised.

Usage (import in run_pipeline.py or etl_runner.py):
    from output_validator import validate_listing_extraction, ExtractionResult
"""

import re
import json
from typing import Optional, Literal
from enum import Enum

try:
    from pydantic import BaseModel, field_validator, model_validator
    PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic import BaseModel, validator
        PYDANTIC_V2 = False
    except ImportError:
        print("ERROR: pydantic not found. Run: pip install pydantic")
        raise

# ── Enums matching your DB schema ────────────────────────────────────────────

class IntentEnum(str, Enum):
    SALE   = 'SALE'
    RENT   = 'RENT'
    BOTH   = 'BOTH'
    UNKNOWN = 'UNKNOWN'

class PropertyTypeEnum(str, Enum):
    APARTMENT          = 'APARTMENT'
    VILLA              = 'VILLA'
    CONDOMINIUM        = 'CONDOMINIUM'
    COMMERCIAL_BUILDING= 'COMMERCIAL_BUILDING'
    OFFICE             = 'OFFICE'
    SHOP               = 'SHOP'
    WAREHOUSE          = 'WAREHOUSE'
    SINGLE_ROOM        = 'SINGLE_ROOM'
    STUDIO             = 'STUDIO'
    LAND               = 'LAND'
    OTHER              = 'OTHER'
    UNKNOWN            = 'UNKNOWN'

class ConfidenceEnum(str, Enum):
    HIGH   = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW    = 'LOW'

# ── Core Extraction Schema ────────────────────────────────────────────────────

class ListingExtraction(BaseModel):
    """
    Schema for a single listing extraction from LLM output.
    All fields are optional — missing = not found in text.
    price_etb and area_sqm are floats enforced to prevent string hallucinations.
    """
    intent:          Optional[IntentEnum]       = None
    property_type:   Optional[PropertyTypeEnum] = None
    price_etb:       Optional[float]            = None
    price_negotiable:Optional[bool]             = False
    area_sqm:        Optional[float]            = None
    bedrooms:        Optional[int]              = None
    bathrooms:       Optional[int]              = None
    floor_number:    Optional[int]              = None
    total_floors:    Optional[int]              = None
    location:        Optional[str]              = None
    sub_city:        Optional[str]              = None
    contact_phone:   Optional[str]              = None
    contact_username:Optional[str]              = None
    is_furnished:    Optional[bool]             = None
    has_parking:     Optional[bool]             = None
    confidence:      ConfidenceEnum             = ConfidenceEnum.MEDIUM

    if PYDANTIC_V2:
        @field_validator('price_etb', mode='before')
        @classmethod
        def parse_price(cls, v):
            return _coerce_numeric(v, 'price_etb')

        @field_validator('area_sqm', mode='before')
        @classmethod
        def parse_area(cls, v):
            return _coerce_numeric(v, 'area_sqm')

        @field_validator('bedrooms', 'bathrooms', 'floor_number', 'total_floors', mode='before')
        @classmethod
        def parse_int(cls, v):
            if v is None:
                return None
            try:
                return int(float(str(v).replace(',', '').strip()))
            except (ValueError, TypeError):
                return None

        @field_validator('contact_phone', mode='before')
        @classmethod
        def validate_phone(cls, v):
            return _normalize_phone_field(v)

        @field_validator('price_etb')
        @classmethod
        def price_in_range(cls, v):
            if v is not None:
                if v < 0:
                    return None
                if v > 5_000_000_000:   # 5 billion ETB — hard cap
                    return None
            return v

        @field_validator('area_sqm')
        @classmethod
        def area_in_range(cls, v):
            if v is not None:
                if v <= 0 or v > 100_000:  # 100,000 sqm hard cap
                    return None
            return v

        @field_validator('bedrooms')
        @classmethod
        def bedrooms_in_range(cls, v):
            if v is not None and (v < 0 or v > 50):
                return None
            return v

    else:
        # Pydantic v1 fallback validators
        @validator('price_etb', pre=True, always=True)
        def parse_price(cls, v):
            return _coerce_numeric(v, 'price_etb')

        @validator('area_sqm', pre=True, always=True)
        def parse_area(cls, v):
            return _coerce_numeric(v, 'area_sqm')

        @validator('contact_phone', pre=True, always=True)
        def validate_phone(cls, v):
            return _normalize_phone_field(v)


class ExtractionResult(BaseModel):
    """Wrapper for extraction with validation metadata."""
    success:      bool
    data:         Optional[ListingExtraction] = None
    error:        Optional[str]               = None
    raw_output:   Optional[str]               = None
    parse_errors: list                        = []


# ── Helper functions ──────────────────────────────────────────────────────────

def _coerce_numeric(v, field_name: str) -> Optional[float]:
    """Convert LLM numeric output to float, handling string formats."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        # Remove currency symbols, commas, ETB label
        cleaned = re.sub(r'[^\d\.]', '', v.replace(',', ''))
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_phone_field(v) -> Optional[str]:
    """Normalize a phone number string from LLM output."""
    if not v:
        return None
    phone_str = str(v).strip()
    # Clean formatting
    clean = re.sub(r'[\s\-\(\)\.]+', '', phone_str)
    # Match Ethiopian patterns
    m = re.search(r'(?:\+251|00251)([79]\d{8})', clean)
    if m:
        return f'+251{m.group(1)}'
    m = re.search(r'\b0([79]\d{8})\b', clean)
    if m:
        return f'+251{m.group(1)}'
    return None


def parse_llm_json(raw_output: str) -> Optional[dict]:
    """
    Safely parse JSON from LLM output.
    Handles: JSON in ```json blocks, leading/trailing text, single quotes.
    """
    if not raw_output:
        return None

    text = raw_output.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract from ```json ... ``` block
    m = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Find first { ... } block
    m = re.search(r'\{[\s\S]+\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            # Replace single quotes with double quotes (common LLM mistake)
            try:
                fixed = m.group(0).replace("'", '"')
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    return None


def validate_listing_extraction(raw_output: str) -> ExtractionResult:
    """
    Main entry point. Parse and validate LLM extraction output.

    Returns ExtractionResult with:
      .success = True/False
      .data    = ListingExtraction if valid
      .error   = error message if failed
      .raw_output = original LLM response for debugging

    Usage:
        result = validate_listing_extraction(llm_response_text)
        if result.success:
            price = result.data.price_etb
        else:
            # flag for manual review
            log_extraction_failure(result.error, result.raw_output)
    """
    result = ExtractionResult(success=False, raw_output=raw_output)

    parsed = parse_llm_json(raw_output)
    if parsed is None:
        result.error = "Could not parse JSON from LLM output"
        return result

    try:
        extraction = ListingExtraction(**parsed)
        result.success = True
        result.data    = extraction

        # Downgrade confidence if critical fields are missing
        if extraction.price_etb is None and extraction.area_sqm is None:
            result.data.confidence = ConfidenceEnum.LOW
        if extraction.location is None and extraction.sub_city is None:
            result.data.confidence = ConfidenceEnum.LOW

    except Exception as e:
        result.error       = str(e)
        result.parse_errors = [str(e)]

    return result


def safe_extract_with_retry(
    raw_text: str,
    extractor_fn,
    max_retries: int = 2
) -> ExtractionResult:
    """
    Call extractor_fn(raw_text) → LLM response string.
    Validate the result. Retry up to max_retries on failure.

    extractor_fn signature: (text: str) -> str

    Usage:
        def my_extractor(text):
            return call_ollama_or_llamacpp(text)

        result = safe_extract_with_retry(listing_text, my_extractor)
    """
    for attempt in range(max_retries + 1):
        try:
            llm_response = extractor_fn(raw_text)
            result = validate_listing_extraction(llm_response)
            if result.success:
                return result
            if attempt < max_retries:
                print(f"    ⚠️  Validation failed (attempt {attempt+1}): {result.error}. Retrying...")
        except Exception as e:
            if attempt < max_retries:
                print(f"    ⚠️  Extractor error (attempt {attempt+1}): {e}. Retrying...")
            else:
                return ExtractionResult(
                    success=False,
                    error=f"Extractor raised exception: {e}",
                    raw_output=str(e)
                )

    return ExtractionResult(
        success=False,
        error=f"Validation failed after {max_retries+1} attempts",
        raw_output=llm_response if 'llm_response' in dir() else None
    )


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 55)
    print("  OUTPUT VALIDATOR — SELF TEST")
    print("=" * 55)

    test_cases = [
        # Valid JSON
        ('{"intent":"SALE","property_type":"APARTMENT","price_etb":5000000,"bedrooms":3,"location":"Bole","confidence":"HIGH"}',
         "Valid extraction"),

        # JSON in markdown block
        ('Here is the extracted data:\n```json\n{"intent":"RENT","price_etb":"15,000","bedrooms":2}\n```',
         "JSON in markdown block"),

        # Price as string with currency
        ('{"intent":"SALE","price_etb":"5 million ETB","area_sqm":"120 sqm"}',
         "String price with text"),

        # Hallucinated impossible values
        ('{"price_etb":-1000,"bedrooms":200,"area_sqm":9999999}',
         "Out-of-range values"),

        # Missing JSON entirely
        ('The property is a 3 bedroom apartment in Bole for 5 million birr.',
         "No JSON at all"),

        # Partial JSON
        ('{"intent":"SALE","bedrooms":3}',
         "Minimal valid fields — should be LOW confidence"),
    ]

    for raw, description in test_cases:
        print(f"\n  Test: {description}")
        result = validate_listing_extraction(raw)
        print(f"    success: {result.success}")
        if result.success:
            d = result.data
            print(f"    intent: {d.intent} | type: {d.property_type}")
            print(f"    price: {d.price_etb} | area: {d.area_sqm} | beds: {d.bedrooms}")
            print(f"    location: {d.location} | phone: {d.contact_phone}")
            print(f"    confidence: {d.confidence}")
        else:
            print(f"    error: {result.error}")

    print("\n✅ Validator test complete.\n")
