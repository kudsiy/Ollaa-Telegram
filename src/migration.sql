-- =============================================================
-- OLLAA PHASE 1 MIGRATION
-- Run once: psql -U postgres -d ollaa -f src\migration.sql
-- =============================================================

-- ── processed_listings new columns ───────────────────────────
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS contact_phone    TEXT;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS contact_username TEXT;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS city             TEXT DEFAULT 'ADDIS_ABABA';
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS property_subtype TEXT;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS price_currency   TEXT DEFAULT 'ETB';
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS price_usd        NUMERIC;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS floor_level      INTEGER;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS posted_at        TIMESTAMP WITH TIME ZONE;
ALTER TABLE processed_listings ADD COLUMN IF NOT EXISTS listing_age_days INTEGER;

-- ── rental_listings table ─────────────────────────────────────
-- Stores all RENT intent listings separately from sale comparables.
-- Critical for income approach valuation and yield calculation.
CREATE TABLE IF NOT EXISTS rental_listings (
    id                  TEXT PRIMARY KEY,
    location            TEXT,
    city                TEXT DEFAULT 'ADDIS_ABABA',
    property_type       TEXT,
    property_subtype    TEXT,
    bedrooms            INTEGER,
    bathrooms           INTEGER,
    builtup_sqm         NUMERIC,
    plot_sqm            NUMERIC,
    monthly_rent_birr   BIGINT,
    rent_advance_birr   BIGINT,
    rent_per_sqm        NUMERIC,
    finish_state        TEXT,
    floor_level         INTEGER,
    contact_phone       TEXT,
    contact_username    TEXT,
    source_channel      TEXT,
    posted_at           TIMESTAMP WITH TIME ZONE,
    raw_text            TEXT,
    created_at          TIMESTAMP DEFAULT now()
);

-- ── developer_projects table ──────────────────────────────────
-- Price history per developer project. Never overwrite — always INSERT.
-- Populated by media_processor.py (Phase 2).
CREATE TABLE IF NOT EXISTS developer_projects (
    id                  SERIAL PRIMARY KEY,
    project_name        TEXT,
    developer           TEXT,
    location            TEXT,
    city                TEXT DEFAULT 'ADDIS_ABABA',
    property_type       TEXT,
    price_per_sqm       NUMERIC,
    min_price           NUMERIC,
    max_price           NUMERIC,
    total_units         INTEGER,
    available_units     INTEGER,
    completion_pct      INTEGER,
    payment_plan_json   JSONB,
    bank_financing_pct  INTEGER,
    source_group        TEXT,
    source_topic        TEXT,
    media_file          TEXT,
    scraped_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── macro_indicators table ────────────────────────────────────
-- Monthly snapshots of macro factors affecting property values.
-- Populated manually or by future NBE scraper.
CREATE TABLE IF NOT EXISTS macro_indicators (
    id              SERIAL PRIMARY KEY,
    snapshot_date   DATE NOT NULL,
    usd_etb_rate    NUMERIC,
    nbe_rate_pct    NUMERIC,
    cement_per_qtl  NUMERIC,
    cpi_index       NUMERIC,
    source          TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ── rental yield view ─────────────────────────────────────────
-- Calculates gross rental yield per segment.
-- Refreshed automatically after each pipeline run.
CREATE MATERIALIZED VIEW IF NOT EXISTS rental_yields AS
SELECT
    r.location,
    r.city,
    r.property_type,
    COUNT(r.id)                                         AS rental_samples,
    ROUND(AVG(r.monthly_rent_birr), 0)                  AS avg_monthly_rent,
    ROUND(AVG(r.rent_per_sqm), 0)                       AS avg_rent_per_sqm,
    COUNT(s.id)                                         AS sale_samples,
    ROUND(AVG(s.sale_price_birr), 0)                    AS avg_sale_price,
    ROUND(
        (AVG(r.monthly_rent_birr) * 12.0 / NULLIF(AVG(s.sale_price_birr), 0)) * 100,
        2
    )                                                   AS gross_yield_pct,
    NOW()                                               AS calculated_at
FROM rental_listings r
LEFT JOIN processed_listings s
    ON r.location = s.location
    AND r.property_type = s.property_type
    AND s.valuation_eligible = true
    AND s.sale_price_birr IS NOT NULL
WHERE r.monthly_rent_birr IS NOT NULL
GROUP BY r.location, r.city, r.property_type
HAVING COUNT(r.id) >= 3
WITH DATA;

SELECT 'Migration complete.' AS status;
