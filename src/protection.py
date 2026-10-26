"""
protection.py
-------------
Keeps hand repairs and deliberate deletions safe when listings are processed
again (task S4). Two tables in the database do the work:

  listing_overrides       protected values: (listing, field) -> value that always
                          wins over the parser. A database trigger records one
                          automatically whenever a TRACKED_FIELDS column is
                          changed by anything other than the parser (a repair
                          script, pgAdmin, a hand-written UPDATE).
  processing_exclusions   Telegram messages kept out of processed_listings on
                          purpose. Deleting a processed listing records its
                          message here automatically (a second trigger), so it
                          never comes back.

The parser's own writes (etl_runner.py, listener.py, reprocess.py) run
PARSER_WRITE_SQL first in their transaction, so they are not taken for repairs.
"""

from __future__ import annotations

from decimal import Decimal

# Columns the parser fills that a repair may correct. Protected per listing.
# The database trigger receives this same list (see database/migrations).
TRACKED_FIELDS = (
    "listing_status", "intent", "listing_class",
    "valuation_eligible", "sale_analytics_eligible", "developer_analytics_eligible",
    "property_type", "property_subtype", "location", "city",
    "plot_sqm", "builtup_sqm", "bedrooms", "bathrooms",
    "sale_price_birr", "rent_price_birr", "rent_advance_birr",
    "payment_type", "bank_loan_pct", "down_payment_pct",
    "finish_state", "developer",
    "price_currency", "price_usd", "floor_level",
    "contact_phone", "contact_username",
)

# Always recalculated from the final values; never protected.
DERIVED_FIELDS = ("price_per_builtup_sqm", "price_per_plot_sqm", "confidence_json")

PARSER_WRITE_SQL = "SET LOCAL ollaa.writer = 'parser'"

# Reason given to the values frozen when protection was switched on (S4).
LEGACY_REASON = ("legacy: differed from the parser on 2026-10-26 "
                 "(hand or script repair, Gemini label, or older parser)")


def same_value(a, b) -> bool:
    """Compare a database value with a parser value (150 == 150.0 == Decimal('150.00'))."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float, Decimal)) and isinstance(b, (int, float, Decimal)):
        return Decimal(str(a)) == Decimal(str(b))
    return str(a) == str(b)


def from_text(value: str | None, data_type: str):
    """Turn a value stored as text in listing_overrides back into the column's type."""
    if value is None:
        return None
    if data_type == "boolean":
        return value in ("true", "t")
    if data_type in ("integer", "bigint", "smallint"):
        return int(value)
    if data_type == "numeric":
        return Decimal(value)
    return value
