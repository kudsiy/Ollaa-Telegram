"""
2026_10_26_s4_protect_repairs.py
--------------------------------
One-time change for task S4: switches on the protection of repairs and deletions
(see src/protection.py for how it works).

Creates the tables listing_overrides and processing_exclusions, and two triggers on
processed_listings that fill them automatically. Then records today's state:
  - every Telegram message without a processed listing -> processing_exclusions
  - every field where a stored listing differs from today's parser -> listing_overrides
    (reason LEGACY_REASON), except the listings in REFRESH_IDS
Nothing in processed_listings or telegram_listings changes.

Usage (take a backup first, see CLAUDE.md):
    venv\\Scripts\\python.exe database\\migrations\\2026_10_26_s4_protect_repairs.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_26_s4_protect_repairs.py --apply
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402
from psycopg2.extras import NamedTupleCursor  # noqa: E402

from etl_runner import build_processed_values  # noqa: E402
from protection import LEGACY_REASON, TRACKED_FIELDS, same_value  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402
from settings import DB_CONFIG  # noqa: E402

# The 3 ads the broker edited (S11): the owner chose their newest text, so their
# listings must be refreshed by re-processing instead of frozen.
REFRESH_IDS = {"1017", "1031", "1041"}

DDL = """
CREATE TABLE public.listing_overrides (
    listing_id text NOT NULL REFERENCES public.processed_listings(id) ON DELETE CASCADE,
    field      text NOT NULL,
    value      text,
    reason     text NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    PRIMARY KEY (listing_id, field)
);
COMMENT ON TABLE public.listing_overrides IS
    'Protected values: always win over the parser when listings are re-processed (src/protection.py).';

CREATE TABLE public.processing_exclusions (
    raw_id      integer PRIMARY KEY REFERENCES public.telegram_listings(id) ON DELETE CASCADE,
    reason      text NOT NULL,
    excluded_at timestamp with time zone NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.processing_exclusions IS
    'Telegram messages kept out of processed_listings on purpose, e.g. deleted duplicates (src/protection.py).';

CREATE FUNCTION public.record_listing_override() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    i         integer;
    f         text;
    old_value text;
    new_value text;
BEGIN
    -- The parser's own writes (etl_runner, listener, reprocess) are not repairs.
    IF current_setting('ollaa.writer', true) = 'parser' THEN
        RETURN NEW;
    END IF;
    FOR i IN 0 .. TG_NARGS - 1 LOOP
        f := TG_ARGV[i];
        EXECUTE format('SELECT ($1).%I::text, ($2).%I::text', f, f) INTO old_value, new_value USING OLD, NEW;
        IF old_value IS DISTINCT FROM new_value THEN
            INSERT INTO public.listing_overrides (listing_id, field, value, reason)
            VALUES (NEW.id, f, new_value,
                    'repair on ' || to_char(now(), 'YYYY-MM-DD') || ' by '
                    || COALESCE(NULLIF(current_setting('application_name', true), ''), 'a script or by hand'))
            ON CONFLICT (listing_id, field) DO UPDATE
                SET value = EXCLUDED.value, reason = EXCLUDED.reason, created_at = now();
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE FUNCTION public.record_processing_exclusion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- A deleted listing must not come back when messages are processed again.
    IF OLD.id ~ '^[0-9]{1,9}$' THEN
        INSERT INTO public.processing_exclusions (raw_id, reason)
        SELECT t.id, 'listing deleted on ' || to_char(now(), 'YYYY-MM-DD') || ' by '
                     || COALESCE(NULLIF(current_setting('application_name', true), ''), 'a script or by hand')
        FROM public.telegram_listings t
        WHERE t.id = OLD.id::integer
        ON CONFLICT (raw_id) DO NOTHING;
    END IF;
    RETURN OLD;
END;
$$;

CREATE TRIGGER processed_listings_protect_repairs
    AFTER UPDATE ON public.processed_listings
    FOR EACH ROW EXECUTE FUNCTION public.record_listing_override({fields});

CREATE TRIGGER processed_listings_keep_deleted_out
    AFTER DELETE ON public.processed_listings
    FOR EACH ROW EXECUTE FUNCTION public.record_processing_exclusion();
""".replace("{fields}", ", ".join(f"'{f}'" for f in TRACKED_FIELDS))

RAW_COLUMNS = "t.id, t.text, t.channel, t.posted_at, t.reply_to_top_id, t.topic_title"


def main(apply: bool) -> None:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=NamedTupleCursor)
    cur.execute("SELECT to_regclass('public.listing_overrides')")
    if cur.fetchone()[0]:
        sys.exit("Already applied: listing_overrides exists.")

    cur.execute(DDL)
    print("created tables listing_overrides, processing_exclusions and their two triggers")

    pipeline = ValuationPipeline()

    # ── 1. Messages without a listing -> kept out ─────────────────
    cur.execute(f"""
        SELECT {RAW_COLUMNS},
               EXISTS (SELECT 1 FROM telegram_listings t2 JOIN processed_listings p2 ON p2.id = t2.id::text
                       WHERE t2.text = t.text) AS same_text_kept
        FROM telegram_listings t
        WHERE t.reply_to_top_id IS NULL
          AND NOT EXISTS (SELECT 1 FROM processed_listings p WHERE p.id = t.id::text)
    """)
    orphans = cur.fetchall()
    cur.execute("SELECT sale_price_birr, builtup_sqm, location FROM processed_listings "
                "WHERE sale_price_birr IS NOT NULL OR builtup_sqm IS NOT NULL")
    kept_keys = {tuple(r) for r in cur.fetchall()}
    exclusions = []
    for row in orphans:
        if row.same_text_kept:
            reason = "duplicate: same text as another listing (removed before 2026-10-26)"
        else:
            values, _, _ = build_processed_values(pipeline, row)
            key = (values["sale_price_birr"], values["builtup_sqm"], values["location"])
            reason = ("duplicate: same price, size and location as another listing (removed before 2026-10-26)"
                      if key in kept_keys else
                      "removed before 2026-10-26, most likely as a near-duplicate (semantic_dedup.py)")
        exclusions.append((row.id, reason))
    cur.executemany("INSERT INTO processing_exclusions (raw_id, reason) VALUES (%s, %s)", exclusions)
    print(f"\nkept out {len(exclusions)} messages that have no listing:")
    for reason, n in Counter(r for _, r in exclusions).most_common():
        print(f"  {n:>5}  {reason}")

    # ── 2. Stored values that differ from today's parser -> protected ──
    cur.execute(f"""
        SELECT p.id AS pid, {', '.join('p.' + f for f in TRACKED_FIELDS)}, {RAW_COLUMNS}
        FROM processed_listings p
        LEFT JOIN telegram_listings t ON p.id = t.id::text
    """)
    frozen = {f: [] for f in TRACKED_FIELDS}
    no_message = parser_failed = 0
    for row in cur.fetchall():
        if row.id is None:
            no_message += 1
            continue
        if row.pid in REFRESH_IDS:
            continue
        try:
            values, _, _ = build_processed_values(pipeline, row)
        except Exception:
            parser_failed += 1
            values = {}
        for f in TRACKED_FIELDS:
            if f not in values or not same_value(getattr(row, f), values[f]):
                frozen[f].append(row.pid)
    for f, ids in frozen.items():
        if ids:
            cur.execute(f"""
                INSERT INTO listing_overrides (listing_id, field, value, reason)
                SELECT id, %s, {f}::text, %s FROM processed_listings WHERE id = ANY(%s)
            """, (f, LEGACY_REASON, ids))
    listings = len({i for ids in frozen.values() for i in ids})
    print(f"\nprotected {sum(map(len, frozen.values()))} values in {listings} listings "
          f"(they differ from what today's parser gives):")
    for f, ids in sorted(frozen.items(), key=lambda kv: -len(kv[1])):
        if ids:
            print(f"  {len(ids):>5}  {f}")
    print(f"listings without their Telegram message (left as they are): {no_message}")
    print(f"listings the parser failed on (all fields protected): {parser_failed}")
    print(f"listings left to refresh (edited ads): {len(REFRESH_IDS)}")

    if apply:
        conn.commit()
        print("\nCOMMITTED")
    else:
        conn.rollback()
        print("\nDRY RUN: nothing was changed (use --apply)")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
