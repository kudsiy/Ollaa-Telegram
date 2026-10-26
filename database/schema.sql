-- ============================================================
-- schema.sql: creates every table, view, materialized view,
-- function, index and constraint of the Ollaa database, empty.
--
-- Made by database/export_schema.py from the live database on 2026-10-26.
-- Do not edit by hand. Change the live database, then run
--     venv\Scripts\python.exe database\export_schema.py
-- and prove the result with
--     venv\Scripts\python.exe database\export_schema.py --check
--
-- Use it on a NEW, empty database, for example:
--     createdb -U postgres ollaa_new
--     psql -U postgres -d ollaa_new -v ON_ERROR_STOP=1 -f database\schema.sql
-- It runs as one transaction: if anything goes wrong, nothing is created.
-- It holds structure only: no data and no passwords.
--
-- Columns that scripts add the first time they run, not yet in the live database:
--   telegram_listings.has_attachment, attachment_type          (src/listener.py)
--   processed_listings.lat, lon, geocode_method,
--     geocode_confidence, geocode_matched_name                 (src/geocoder.py)
--   processed_listings.is_duplicate, duplicate_of              (src/dedup_fast.py)
-- ============================================================

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

BEGIN;

--
-- Name: estimate_value(text, text, numeric, integer); Type: FUNCTION; Schema: public
--

CREATE FUNCTION public.estimate_value(p_location text, p_property_type text, p_builtup_sqm numeric, p_bedrooms integer DEFAULT NULL::integer) RETURNS TABLE(estimated_value bigint, avg_price_per_sqm numeric, samples bigint, confidence_tier text, method text, notes text)
    LANGUAGE plpgsql
    AS $$
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


--
-- Name: get_comparables(text, text, numeric, integer); Type: FUNCTION; Schema: public
--

CREATE FUNCTION public.get_comparables(p_location text, p_property_type text, p_builtup_sqm numeric, p_bedrooms integer DEFAULT NULL::integer) RETURNS TABLE(id text, location text, property_type text, builtup_sqm numeric, bedrooms integer, sale_price_birr bigint, estimated_market_price numeric, price_per_sqm numeric, recency_weight numeric, source_channel text, raw_text_preview text)
    LANGUAGE sql
    AS $$
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: developer_projects; Type: TABLE; Schema: public
--

CREATE TABLE public.developer_projects (
    id integer NOT NULL,
    project_name text,
    developer text,
    location text,
    city text DEFAULT 'ADDIS_ABABA'::text,
    property_type text,
    price_per_sqm numeric,
    min_price numeric,
    max_price numeric,
    total_units integer,
    available_units integer,
    completion_pct integer,
    payment_plan_json jsonb,
    bank_financing_pct integer,
    source_group text,
    source_topic text,
    media_file text,
    scraped_at timestamp with time zone DEFAULT now()
);


--
-- Name: developer_projects_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.developer_projects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: developer_projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.developer_projects_id_seq OWNED BY public.developer_projects.id;


--
-- Name: listings; Type: TABLE; Schema: public
--

CREATE TABLE public.listings (
    id integer NOT NULL,
    source text NOT NULL,
    source_name text,
    post_id text,
    title text,
    description text,
    price_etb bigint,
    size_sqm numeric,
    location text,
    phone text,
    image_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: listings_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.listings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: listings_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.listings_id_seq OWNED BY public.listings.id;


--
-- Name: macro_indicators; Type: TABLE; Schema: public
--

CREATE TABLE public.macro_indicators (
    id integer NOT NULL,
    snapshot_date date NOT NULL,
    usd_etb_rate numeric,
    nbe_rate_pct numeric,
    cement_per_qtl numeric,
    cpi_index numeric,
    source text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: macro_indicators_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.macro_indicators_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: macro_indicators_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.macro_indicators_id_seq OWNED BY public.macro_indicators.id;


--
-- Name: processed_listings; Type: TABLE; Schema: public
--

CREATE TABLE public.processed_listings (
    id text NOT NULL,
    intent text,
    listing_class text,
    valuation_eligible boolean,
    sale_analytics_eligible boolean,
    developer_analytics_eligible boolean,
    property_type text,
    location text,
    plot_sqm numeric,
    builtup_sqm numeric,
    bedrooms integer,
    bathrooms integer,
    sale_price_birr bigint,
    rent_price_birr bigint,
    rent_advance_birr bigint,
    payment_type text,
    bank_loan_pct integer,
    down_payment_pct integer,
    finish_state text,
    developer text,
    price_per_builtup_sqm numeric,
    price_per_plot_sqm numeric,
    confidence_json text,
    source_channel text,
    raw_text text,
    created_at timestamp without time zone DEFAULT now(),
    contact_phone text,
    contact_username text,
    city text DEFAULT 'ADDIS_ABABA'::text,
    property_subtype text,
    price_currency text DEFAULT 'ETB'::text,
    price_usd numeric,
    floor_level integer,
    posted_at timestamp with time zone,
    listing_age_days integer,
    listing_status text
);


--
-- Name: v_valid_comparables; Type: VIEW; Schema: public
--

CREATE VIEW public.v_valid_comparables AS
 WITH base AS (
         SELECT processed_listings.id,
            processed_listings.location,
            processed_listings.property_type,
            processed_listings.builtup_sqm,
            processed_listings.plot_sqm,
            processed_listings.bedrooms,
            processed_listings.bathrooms,
            processed_listings.sale_price_birr,
            processed_listings.source_channel,
            processed_listings.raw_text,
            processed_listings.created_at,
            round(((processed_listings.sale_price_birr)::numeric / NULLIF(processed_listings.builtup_sqm, (0)::numeric)), 2) AS price_per_sqm,
                CASE
                    WHEN (processed_listings.created_at >= (now() - '30 days'::interval)) THEN 1.00
                    WHEN (processed_listings.created_at >= (now() - '90 days'::interval)) THEN 0.85
                    WHEN (processed_listings.created_at >= (now() - '180 days'::interval)) THEN 0.70
                    ELSE 0.55
                END AS recency_weight,
            round(((processed_listings.sale_price_birr)::numeric * 0.85), 0) AS estimated_market_price
           FROM public.processed_listings
          WHERE ((processed_listings.valuation_eligible = true) AND (processed_listings.sale_price_birr IS NOT NULL) AND (processed_listings.builtup_sqm IS NOT NULL) AND (processed_listings.builtup_sqm > (0)::numeric) AND (processed_listings.location IS NOT NULL) AND (processed_listings.location <> 'other_addis'::text))
        ), segment_bounds AS (
         SELECT base.location,
            base.property_type,
            (percentile_cont((0.25)::double precision) WITHIN GROUP (ORDER BY ((base.price_per_sqm)::double precision)))::numeric AS q1,
            (percentile_cont((0.75)::double precision) WITHIN GROUP (ORDER BY ((base.price_per_sqm)::double precision)))::numeric AS q3
           FROM base
          GROUP BY base.location, base.property_type
        )
 SELECT b.id,
    b.location,
    b.property_type,
    b.builtup_sqm,
    b.plot_sqm,
    b.bedrooms,
    b.bathrooms,
    b.sale_price_birr,
    b.estimated_market_price,
    b.price_per_sqm,
    b.recency_weight,
    b.source_channel,
    b.raw_text,
    b.created_at,
    s.q1,
    s.q3,
    round((s.q3 - s.q1), 2) AS iqr
   FROM (base b
     JOIN segment_bounds s ON (((b.location = s.location) AND (b.property_type = s.property_type))))
  WHERE ((b.price_per_sqm >= (s.q1 - (1.5 * (s.q3 - s.q1)))) AND (b.price_per_sqm <= (s.q3 + (1.5 * (s.q3 - s.q1)))));


--
-- Name: market_price_model; Type: MATERIALIZED VIEW; Schema: public
--

CREATE MATERIALIZED VIEW public.market_price_model AS
 SELECT location,
    property_type,
    bedrooms,
    count(*) AS samples,
    round((sum(((estimated_market_price / NULLIF(builtup_sqm, (0)::numeric)) * recency_weight)) / NULLIF(sum(recency_weight), (0)::numeric)), 2) AS avg_price_per_sqm,
    round((percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((price_per_sqm)::double precision)))::numeric, 2) AS median_price_per_sqm,
    round(min(price_per_sqm), 2) AS min_price_per_sqm,
    round(max(price_per_sqm), 2) AS max_price_per_sqm,
    round(stddev(price_per_sqm), 2) AS stddev_price_per_sqm,
        CASE
            WHEN (count(*) >= 10) THEN 'HIGH'::text
            WHEN (count(*) >= 5) THEN 'MEDIUM'::text
            ELSE 'LOW'::text
        END AS confidence_tier,
    now() AS last_updated
   FROM public.v_valid_comparables
  GROUP BY location, property_type, bedrooms
  WITH NO DATA;


--
-- Name: media_queue; Type: TABLE; Schema: public
--

CREATE TABLE public.media_queue (
    id integer NOT NULL,
    channel text NOT NULL,
    message_id bigint NOT NULL,
    topic_title text,
    file_path text NOT NULL,
    file_type text NOT NULL,
    posted_at timestamp with time zone,
    processed boolean DEFAULT false,
    result_json jsonb,
    processed_at timestamp with time zone,
    error_msg text
);


--
-- Name: media_queue_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.media_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: media_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.media_queue_id_seq OWNED BY public.media_queue.id;


--
-- Name: rental_listings; Type: TABLE; Schema: public
--

CREATE TABLE public.rental_listings (
    id text NOT NULL,
    location text,
    city text DEFAULT 'ADDIS_ABABA'::text,
    property_type text,
    property_subtype text,
    bedrooms integer,
    bathrooms integer,
    builtup_sqm numeric,
    plot_sqm numeric,
    monthly_rent_birr bigint,
    rent_advance_birr bigint,
    rent_per_sqm numeric,
    finish_state text,
    floor_level integer,
    contact_phone text,
    contact_username text,
    source_channel text,
    posted_at timestamp with time zone,
    raw_text text,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: rental_yields; Type: MATERIALIZED VIEW; Schema: public
--

CREATE MATERIALIZED VIEW public.rental_yields AS
 SELECT r.location,
    r.city,
    r.property_type,
    count(r.id) AS rental_samples,
    round(avg(r.monthly_rent_birr), 0) AS avg_monthly_rent,
    round(avg(r.rent_per_sqm), 0) AS avg_rent_per_sqm,
    count(s.id) AS sale_samples,
    round(avg(s.sale_price_birr), 0) AS avg_sale_price,
    round((((avg(r.monthly_rent_birr) * 12.0) / NULLIF(avg(s.sale_price_birr), (0)::numeric)) * (100)::numeric), 2) AS gross_yield_pct,
    now() AS calculated_at
   FROM (public.rental_listings r
     LEFT JOIN public.processed_listings s ON (((r.location = s.location) AND (r.property_type = s.property_type) AND (s.valuation_eligible = true) AND (s.sale_price_birr IS NOT NULL))))
  WHERE (r.monthly_rent_birr IS NOT NULL)
  GROUP BY r.location, r.city, r.property_type
 HAVING (count(r.id) >= 3)
  WITH NO DATA;


--
-- Name: telegram_listings; Type: TABLE; Schema: public
--

CREATE TABLE public.telegram_listings (
    id integer NOT NULL,
    channel text,
    message_id bigint,
    text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    beds integer,
    price bigint,
    currency text,
    location text,
    developer text,
    plot_sqm integer,
    builtup_sqm integer,
    developer_name text,
    finish_status text,
    property_type text,
    has_service_quarters boolean,
    down_payment_percent integer,
    down_payment_amount bigint,
    bank_financing_available boolean,
    bank_coverage_percent integer,
    bedrooms integer,
    bathrooms integer,
    location_text text,
    villa_floors text,
    topic_title text,
    posted_at timestamp with time zone,
    has_media boolean DEFAULT false,
    reply_to_top_id bigint
);


--
-- Name: telegram_listings_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.telegram_listings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: telegram_listings_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.telegram_listings_id_seq OWNED BY public.telegram_listings.id;


--
-- Name: v_data_quality; Type: VIEW; Schema: public
--

CREATE VIEW public.v_data_quality AS
 WITH totals AS (
         SELECT count(*) AS total
           FROM public.processed_listings
        ), sale_stats AS (
         SELECT count(*) AS total_sale,
            count(*) FILTER (WHERE (processed_listings.valuation_eligible = true)) AS eligible,
            count(*) FILTER (WHERE (processed_listings.sale_price_birr IS NOT NULL)) AS has_price,
            count(*) FILTER (WHERE (processed_listings.builtup_sqm IS NOT NULL)) AS has_area,
            count(*) FILTER (WHERE ((processed_listings.sale_price_birr IS NOT NULL) AND (processed_listings.builtup_sqm IS NOT NULL))) AS has_both,
            count(*) FILTER (WHERE (processed_listings.location = 'other_addis'::text)) AS unresolved_location
           FROM public.processed_listings
          WHERE (processed_listings.intent = ANY (ARRAY['SALE'::text, 'MIXED'::text]))
        ), segment_stats AS (
         SELECT count(*) FILTER (WHERE (market_price_model.samples >= 10)) AS high_segments,
            count(*) FILTER (WHERE ((market_price_model.samples >= 5) AND (market_price_model.samples < 10))) AS medium_segments,
            count(*) FILTER (WHERE (market_price_model.samples < 5)) AS low_segments,
            COALESCE(sum(market_price_model.samples), (0)::numeric) AS total_comparables
           FROM public.market_price_model
          WHERE (market_price_model.location <> 'other_addis'::text)
        )
 SELECT t.total AS total_listings,
    s.total_sale,
    s.eligible,
    round((((s.eligible)::numeric / (NULLIF(t.total, 0))::numeric) * (100)::numeric), 1) AS eligible_pct,
    s.has_price,
    s.has_area,
    s.has_both,
    round((((s.has_both)::numeric / (NULLIF(s.total_sale, 0))::numeric) * (100)::numeric), 1) AS usable_pct,
    s.unresolved_location,
    seg.total_comparables,
    seg.high_segments,
    seg.medium_segments,
    seg.low_segments
   FROM totals t,
    sale_stats s,
    segment_stats seg;


--
-- Name: web_scraped_listings; Type: TABLE; Schema: public
--

CREATE TABLE public.web_scraped_listings (
    id integer NOT NULL,
    source_url text,
    source_name character varying(100),
    title text NOT NULL,
    description text,
    price numeric(15,2),
    price_currency character varying(10) DEFAULT 'ETB'::character varying,
    property_type character varying(50),
    location character varying(255),
    area_sqm numeric(10,2),
    bedrooms integer,
    bathrooms integer,
    images text[],
    posted_date timestamp without time zone,
    closing_date timestamp without time zone,
    listing_type character varying(20) DEFAULT 'sale'::character varying,
    content_hash character varying(64),
    scraped_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    inserted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    raw_data jsonb
);


--
-- Name: web_scraped_listings_id_seq; Type: SEQUENCE; Schema: public
--

CREATE SEQUENCE public.web_scraped_listings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: web_scraped_listings_id_seq; Type: SEQUENCE OWNED BY; Schema: public
--

ALTER SEQUENCE public.web_scraped_listings_id_seq OWNED BY public.web_scraped_listings.id;


--
-- Name: developer_projects id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.developer_projects ALTER COLUMN id SET DEFAULT nextval('public.developer_projects_id_seq'::regclass);


--
-- Name: listings id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.listings ALTER COLUMN id SET DEFAULT nextval('public.listings_id_seq'::regclass);


--
-- Name: macro_indicators id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.macro_indicators ALTER COLUMN id SET DEFAULT nextval('public.macro_indicators_id_seq'::regclass);


--
-- Name: media_queue id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.media_queue ALTER COLUMN id SET DEFAULT nextval('public.media_queue_id_seq'::regclass);


--
-- Name: telegram_listings id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.telegram_listings ALTER COLUMN id SET DEFAULT nextval('public.telegram_listings_id_seq'::regclass);


--
-- Name: web_scraped_listings id; Type: DEFAULT; Schema: public
--

ALTER TABLE ONLY public.web_scraped_listings ALTER COLUMN id SET DEFAULT nextval('public.web_scraped_listings_id_seq'::regclass);


--
-- Name: developer_projects developer_projects_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.developer_projects
    ADD CONSTRAINT developer_projects_pkey PRIMARY KEY (id);


--
-- Name: listings listings_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.listings
    ADD CONSTRAINT listings_pkey PRIMARY KEY (id);


--
-- Name: macro_indicators macro_indicators_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.macro_indicators
    ADD CONSTRAINT macro_indicators_pkey PRIMARY KEY (id);


--
-- Name: media_queue media_queue_channel_message_id_file_path_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.media_queue
    ADD CONSTRAINT media_queue_channel_message_id_file_path_key UNIQUE (channel, message_id, file_path);


--
-- Name: media_queue media_queue_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.media_queue
    ADD CONSTRAINT media_queue_pkey PRIMARY KEY (id);


--
-- Name: processed_listings processed_listings_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.processed_listings
    ADD CONSTRAINT processed_listings_pkey PRIMARY KEY (id);


--
-- Name: rental_listings rental_listings_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.rental_listings
    ADD CONSTRAINT rental_listings_pkey PRIMARY KEY (id);


--
-- Name: telegram_listings telegram_listings_channel_message_id_key; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.telegram_listings
    ADD CONSTRAINT telegram_listings_channel_message_id_key UNIQUE (channel, message_id);


--
-- Name: telegram_listings telegram_listings_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.telegram_listings
    ADD CONSTRAINT telegram_listings_pkey PRIMARY KEY (id);


--
-- Name: web_scraped_listings unique_content_hash; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.web_scraped_listings
    ADD CONSTRAINT unique_content_hash UNIQUE (content_hash);


--
-- Name: web_scraped_listings web_scraped_listings_pkey; Type: CONSTRAINT; Schema: public
--

ALTER TABLE ONLY public.web_scraped_listings
    ADD CONSTRAINT web_scraped_listings_pkey PRIMARY KEY (id);


--
-- Name: idx_content_hash; Type: INDEX; Schema: public
--

CREATE INDEX idx_content_hash ON public.web_scraped_listings USING btree (content_hash);


--
-- Name: idx_listing_type; Type: INDEX; Schema: public
--

CREATE INDEX idx_listing_type ON public.web_scraped_listings USING btree (listing_type);


--
-- Name: idx_location; Type: INDEX; Schema: public
--

CREATE INDEX idx_location ON public.web_scraped_listings USING btree (location);


--
-- Name: idx_market_model_lookup; Type: INDEX; Schema: public
--

CREATE INDEX idx_market_model_lookup ON public.market_price_model USING btree (location, property_type, bedrooms);


--
-- Name: idx_scraped_at; Type: INDEX; Schema: public
--

CREATE INDEX idx_scraped_at ON public.web_scraped_listings USING btree (scraped_at);


--
-- Name: idx_source_name; Type: INDEX; Schema: public
--

CREATE INDEX idx_source_name ON public.web_scraped_listings USING btree (source_name);


--
-- Fill the materialized views (empty until data is loaded)
--

REFRESH MATERIALIZED VIEW public.market_price_model;
REFRESH MATERIALIZED VIEW public.rental_yields;

COMMIT;
