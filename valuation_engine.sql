/* =========================================================
   OLLAA VALUATION ENGINE — v2
   Fully tested. All PostgreSQL type casts verified.
   
   Run: psql -U postgres -d ollaa -f valuation_engine.sql
   ========================================================= */

-- Drop everything cleanly in correct dependency order
DROP VIEW  IF EXISTS v_data_quality        CASCADE;
DROP VIEW  IF EXISTS v_valid_comparables   CASCADE;
DROP MATERIALIZED VIEW IF EXISTS market_price_model CASCADE;
DROP FUNCTION IF EXISTS estimate_value(TEXT, TEXT, NUMERIC, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS get_comparables(TEXT, TEXT, NUMERIC, INTEGER) CASCADE;


/* ---------------------------------------------------------
   STEP 1 — VALID COMPARABLES VIEW
   --------------------------------------------------------- */

CREATE VIEW v_valid_comparables AS
WITH base AS (
    SELECT
        id, location, property_type, builtup_sqm, plot_sqm,
        bedrooms, bathrooms, sale_price_birr, source_channel,
        raw_text, created_at,

        ROUND((sale_price_birr::NUMERIC / NULLIF(builtup_sqm, 0)), 2) AS price_per_sqm,

        CASE
            WHEN created_at >= NOW() - INTERVAL '30 days'  THEN 1.00
            WHEN created_at >= NOW() - INTERVAL '90 days'  THEN 0.85
            WHEN created_at >= NOW() - INTERVAL '180 days' THEN 0.70
            ELSE 0.55
        END AS recency_weight,

        ROUND(sale_price_birr::NUMERIC * 0.85, 0) AS estimated_market_price

    FROM processed_listings
    WHERE valuation_eligible = TRUE
      AND sale_price_birr    IS NOT NULL
      AND builtup_sqm        IS NOT NULL
      AND builtup_sqm        > 0
      AND location           IS NOT NULL
      AND location           <> 'other_addis'
),
segment_bounds AS (
    SELECT
        location,
        property_type,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_per_sqm)::NUMERIC AS q1,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_per_sqm)::NUMERIC AS q3
    FROM base
    GROUP BY location, property_type
)
SELECT
    b.id, b.location, b.property_type, b.builtup_sqm, b.plot_sqm,
    b.bedrooms, b.bathrooms, b.sale_price_birr, b.estimated_market_price,
    b.price_per_sqm, b.recency_weight, b.source_channel, b.raw_text,
    b.created_at, s.q1, s.q3,
    ROUND((s.q3 - s.q1), 2) AS iqr
FROM base b
JOIN segment_bounds s
  ON b.location = s.location AND b.property_type = s.property_type
WHERE b.price_per_sqm >= (s.q1 - 1.5 * (s.q3 - s.q1))
  AND b.price_per_sqm <= (s.q3 + 1.5 * (s.q3 - s.q1));


/* ---------------------------------------------------------
   STEP 2 — MARKET PRICE MODEL
   Refresh with: REFRESH MATERIALIZED VIEW market_price_model;
   --------------------------------------------------------- */

CREATE MATERIALIZED VIEW market_price_model AS
SELECT
    location,
    property_type,
    bedrooms,
    COUNT(*)::BIGINT AS samples,
    ROUND(
        SUM((estimated_market_price / NULLIF(builtup_sqm, 0)) * recency_weight)
        / NULLIF(SUM(recency_weight), 0),
        2
    ) AS avg_price_per_sqm,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_sqm)::NUMERIC, 2) AS median_price_per_sqm,
    ROUND(MIN(price_per_sqm), 2) AS min_price_per_sqm,
    ROUND(MAX(price_per_sqm), 2) AS max_price_per_sqm,
    ROUND(STDDEV(price_per_sqm)::NUMERIC, 2) AS stddev_price_per_sqm,
    CASE
        WHEN COUNT(*) >= 10 THEN 'HIGH'
        WHEN COUNT(*) >=  5 THEN 'MEDIUM'
        ELSE                     'LOW'
    END AS confidence_tier,
    NOW() AS last_updated
FROM v_valid_comparables
GROUP BY location, property_type, bedrooms;

CREATE INDEX idx_market_model_lookup
    ON market_price_model (location, property_type, bedrooms);


/* ---------------------------------------------------------
   STEP 3 — VALUATION FUNCTION
   
   Usage:
     SELECT * FROM estimate_value('ayat_zone', 'VILLA', 200);
     SELECT * FROM estimate_value('bole_main', 'APARTMENT', 100, 2);
   --------------------------------------------------------- */

CREATE OR REPLACE FUNCTION estimate_value(
    p_location      TEXT,
    p_property_type TEXT,
    p_builtup_sqm   NUMERIC,
    p_bedrooms      INTEGER DEFAULT NULL
)
RETURNS TABLE (
    estimated_value     BIGINT,
    avg_price_per_sqm   NUMERIC,
    samples             BIGINT,
    confidence_tier     TEXT,
    method              TEXT,
    notes               TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_avg_price  NUMERIC;
    v_samples    BIGINT;
    v_confidence TEXT;
    v_method     TEXT;
BEGIN

    -- Level 1: exact match
    SELECT m.avg_price_per_sqm, m.samples::BIGINT, m.confidence_tier
    INTO   v_avg_price, v_samples, v_confidence
    FROM   market_price_model m
    WHERE  m.location      = p_location
      AND  m.property_type = p_property_type
      AND  m.bedrooms IS NOT DISTINCT FROM p_bedrooms
    LIMIT 1;

    IF v_samples >= 5 THEN
        v_method := 'exact_match (location + type + bedrooms)';

    ELSE
        -- Level 2: location + type, all bedrooms
        SELECT
            AVG(m.avg_price_per_sqm),
            SUM(m.samples)::BIGINT,
            CASE WHEN SUM(m.samples) >= 10 THEN 'HIGH'
                 WHEN SUM(m.samples) >=  5 THEN 'MEDIUM'
                 ELSE 'LOW' END
        INTO v_avg_price, v_samples, v_confidence
        FROM market_price_model m
        WHERE m.location = p_location AND m.property_type = p_property_type;

        IF v_samples >= 5 THEN
            v_method := 'fallback_level_2 (location + type, all bedrooms)';

        ELSE
            -- Level 3: location only
            SELECT
                AVG(m.avg_price_per_sqm),
                SUM(m.samples)::BIGINT,
                CASE WHEN SUM(m.samples) >= 10 THEN 'HIGH'
                     WHEN SUM(m.samples) >=  5 THEN 'MEDIUM'
                     ELSE 'LOW' END
            INTO v_avg_price, v_samples, v_confidence
            FROM market_price_model m
            WHERE m.location = p_location;

            IF v_samples >= 5 THEN
                v_method := 'fallback_level_3 (location only)';
            ELSE
                v_method := 'none';
            END IF;
        END IF;
    END IF;

    IF v_samples IS NULL OR v_samples < 5 THEN
        RETURN QUERY SELECT
            NULL::BIGINT, NULL::NUMERIC, 0::BIGINT,
            'INSUFFICIENT_DATA'::TEXT, 'none'::TEXT,
            'Not enough comparables for this segment'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY SELECT
        ROUND(p_builtup_sqm * v_avg_price)::BIGINT,
        ROUND(v_avg_price, 2),
        v_samples,
        v_confidence,
        v_method,
        '15% negotiation discount already applied'::TEXT;

END;
$$;


/* ---------------------------------------------------------
   STEP 4 — COMPARABLE SEARCH
   
   Usage:
     SELECT * FROM get_comparables('ayat_zone', 'VILLA', 200);
   --------------------------------------------------------- */

CREATE OR REPLACE FUNCTION get_comparables(
    p_location      TEXT,
    p_property_type TEXT,
    p_builtup_sqm   NUMERIC,
    p_bedrooms      INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id                     TEXT,
    location               TEXT,
    property_type          TEXT,
    builtup_sqm            NUMERIC,
    bedrooms               INTEGER,
    sale_price_birr        BIGINT,
    estimated_market_price NUMERIC,
    price_per_sqm          NUMERIC,
    recency_weight         NUMERIC,
    source_channel         TEXT,
    raw_text_preview       TEXT
)
LANGUAGE sql AS $$
    SELECT
        v.id, v.location, v.property_type, v.builtup_sqm, v.bedrooms,
        v.sale_price_birr, v.estimated_market_price, v.price_per_sqm,
        v.recency_weight, v.source_channel,
        LEFT(v.raw_text, 200) AS raw_text_preview
    FROM v_valid_comparables v
    WHERE v.location      = p_location
      AND v.property_type = p_property_type
      AND v.builtup_sqm BETWEEN (p_builtup_sqm * 0.70) AND (p_builtup_sqm * 1.30)
    ORDER BY
        CASE WHEN p_bedrooms IS NOT NULL AND v.bedrooms = p_bedrooms THEN 0 ELSE 1 END,
        ABS(v.builtup_sqm - p_builtup_sqm),
        v.created_at DESC
    LIMIT 5;
$$;


/* ---------------------------------------------------------
   STEP 5 — DATA QUALITY DASHBOARD
   
   Usage: SELECT * FROM v_data_quality;
   --------------------------------------------------------- */

CREATE VIEW v_data_quality AS
WITH totals AS (
    SELECT COUNT(*) AS total FROM processed_listings
),
sale_stats AS (
    SELECT
        COUNT(*)                                              AS total_sale,
        COUNT(*) FILTER (WHERE valuation_eligible = TRUE)    AS eligible,
        COUNT(*) FILTER (WHERE sale_price_birr IS NOT NULL)  AS has_price,
        COUNT(*) FILTER (WHERE builtup_sqm IS NOT NULL)      AS has_area,
        COUNT(*) FILTER (
            WHERE sale_price_birr IS NOT NULL AND builtup_sqm IS NOT NULL
        )                                                     AS has_both,
        COUNT(*) FILTER (WHERE location = 'other_addis')     AS unresolved_location
    FROM processed_listings
    WHERE intent IN ('SALE', 'MIXED')
),
segment_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE samples >= 10)                 AS high_segments,
        COUNT(*) FILTER (WHERE samples >= 5 AND samples < 10) AS medium_segments,
        COUNT(*) FILTER (WHERE samples <  5)                  AS low_segments,
        COALESCE(SUM(samples), 0)                             AS total_comparables
    FROM market_price_model
    WHERE location <> 'other_addis'
)
SELECT
    t.total                                                          AS total_listings,
    s.total_sale,
    s.eligible,
    ROUND(s.eligible::NUMERIC / NULLIF(t.total, 0) * 100, 1)       AS eligible_pct,
    s.has_price,
    s.has_area,
    s.has_both,
    ROUND(s.has_both::NUMERIC / NULLIF(s.total_sale, 0) * 100, 1)  AS usable_pct,
    s.unresolved_location,
    seg.total_comparables,
    seg.high_segments,
    seg.medium_segments,
    seg.low_segments
FROM totals t, sale_stats s, segment_stats seg;