"""
reprocess.py
------------
Brings parser fixes to listings that already exist, without losing repairs.

For every processed listing it runs the parser again on the listing's Telegram
message (the same code as etl_runner.py), then puts the protected values from
listing_overrides on top. Without --apply it only reports what would change.
It never deletes a listing and never processes messages in processing_exclusions
(see protection.py).

Protections recorded when S4 switched protection on ("legacy") are retired
automatically once the parser gives the same value, because then they are no
longer needed. Protections that still hold back a different parser value are
counted in the report, so they can be reviewed.

rental_listings is a copy of the rental listings (for rental_yields). It is
brought in line with the listings as re-processing leaves them: rows are added
for new rentals, updated when their listing changed, and removed when their
listing is no longer a rental or is gone (its message kept out).

Usage:
    python src/reprocess.py                    # dry run: report only
    python src/reprocess.py --show location    # list every change to one field
    python src/reprocess.py --apply            # write the changes
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict

from sqlalchemy import create_engine, text

from etl_runner import INSERT_RENTAL, build_processed_values, is_rental, price_per_sqm_values, rental_row
from locations import city_of
from protection import (DERIVED_FIELDS, LEGACY_REASON, PARSER_WRITE_SQL, TRACKED_FIELDS,
                        from_text, same_value)
from run_pipeline import ValuationPipeline
from settings import DB_URL

engine = create_engine(DB_URL)

WRITE_FIELDS = TRACKED_FIELDS + DERIVED_FIELDS + ("raw_text",)


def check_protection_installed(conn) -> None:
    if conn.execute(text("SELECT to_regclass('public.listing_overrides')")).scalar() is None:
        sys.exit("Protection is not switched on yet. Run "
                 "database/migrations/2026_10_26_s4_protect_repairs.py --apply first.")
    args = conn.execute(text("""
        SELECT tgargs FROM pg_trigger
        WHERE tgname = 'processed_listings_protect_repairs'
          AND tgrelid = 'public.processed_listings'::regclass
    """)).scalar()
    trigger_fields = tuple(bytes(args).decode().split("\x00")[:-1]) if args is not None else ()
    if trigger_fields != TRACKED_FIELDS:
        sys.exit("The database trigger protects different fields than protection.TRACKED_FIELDS. "
                 "Update the trigger before re-processing.")


def plan(conn):
    """Work out every change without writing anything."""
    column_types = dict(conn.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'processed_listings'
    """)).fetchall())

    overrides = defaultdict(dict)
    for listing_id, field, value, reason in conn.execute(text(
            "SELECT listing_id, field, value, reason FROM listing_overrides")):
        overrides[listing_id][field] = (from_text(value, column_types[field]), reason)

    stored = {r.id: r for r in conn.execute(text(
        f"SELECT id, {', '.join(WRITE_FIELDS)} FROM processed_listings"))}
    raw_rows = conn.execute(text("""
        SELECT id, text, channel, posted_at, reply_to_top_id, topic_title
        FROM telegram_listings t
        WHERE NOT EXISTS (SELECT 1 FROM processing_exclusions e WHERE e.raw_id = t.id)
    """)).fetchall()

    pipeline = ValuationPipeline()
    changes = {}                 # listing id -> {field: (old, new)}
    retire = []                  # (listing id, field) legacy protections no longer needed
    holding = Counter()          # field -> protections keeping a value the parser disagrees with
    counts = Counter()
    seen = set()

    for raw in raw_rows:
        if raw.reply_to_top_id is not None:
            counts["forum messages (left to etl_runner.py)"] += 1
            continue
        pid = str(raw.id)
        if pid not in stored:
            counts["new messages not processed yet (run etl_runner.py)"] += 1
            continue
        seen.add(pid)
        try:
            fresh, _, _ = build_processed_values(pipeline, raw)
        except Exception:
            counts["listings the parser fails on (left as they are)"] += 1
            continue

        final = dict(fresh)
        for field, (value, reason) in overrides.get(pid, {}).items():
            if same_value(value, fresh[field]):
                if reason == LEGACY_REASON:
                    retire.append((pid, field))
            else:
                holding[field] += 1
            final[field] = value
        # A protected location brings its own city, unless the city is protected too.
        if "location" in overrides.get(pid, {}) and "city" not in overrides.get(pid, {}):
            final["city"] = city_of(final["location"])
        final["price_per_builtup_sqm"], final["price_per_plot_sqm"] = price_per_sqm_values(final)

        old = stored[pid]
        diff = {f: (getattr(old, f), final[f]) for f in WRITE_FIELDS
                if not same_value(getattr(old, f), final[f])}
        if diff:
            changes[pid] = diff
        counts["listings checked"] += 1

    counts["listings whose message is kept out or missing (left as they are)"] = len(set(stored) - seen)
    return changes, retire, holding, counts


def plan_rentals(conn, changes):
    """rental_listings as the listings will be after `changes`: (rows to add, {id: {column: (old, new)}}, ids to remove)."""
    listings = {r.id: dict(r._mapping) for r in conn.execute(text("SELECT * FROM processed_listings"))}
    for pid, diff in changes.items():
        listings[pid].update({field: new for field, (_, new) in diff.items()})
    wanted = {row["id"]: row for row in (rental_row(v, v["raw_text"]) for v in listings.values() if is_rental(v))}
    existing = {r.id: dict(r._mapping) for r in conn.execute(text("SELECT * FROM rental_listings"))}

    add = [row for rid, row in wanted.items() if rid not in existing]
    update = {}
    for rid, row in wanted.items():
        if rid in existing:
            diff = {c: (existing[rid][c], v) for c, v in row.items() if c != "id" and not same_value(existing[rid][c], v)}
            if diff:
                update[rid] = diff
    remove = sorted(rid for rid in existing if rid not in wanted)
    return add, update, remove


def report(changes, retire, holding, counts, conn) -> None:
    print("\nRE-PROCESSING REPORT")
    for label, n in counts.items():
        print(f"  {label:<62} {n:>6}")
    total_protected = conn.execute(text("SELECT count(*) FROM listing_overrides")).scalar()
    kept_out = conn.execute(text("SELECT count(*) FROM processing_exclusions")).scalar()
    print(f"  {'protected values (listing_overrides)':<62} {total_protected:>6}")
    print(f"  {'messages kept out (processing_exclusions)':<62} {kept_out:>6}")

    by_field = Counter(f for diff in changes.values() for f in diff)
    print(f"\n  Listings that would change: {len(changes)}")
    for group, fields in (("parser fields", TRACKED_FIELDS), ("recalculated fields", DERIVED_FIELDS),
                          ("message text copy", ("raw_text",))):
        rows = [(f, by_field[f]) for f in fields if by_field[f]]
        if rows:
            print(f"    {group}:")
            for f, n in sorted(rows, key=lambda r: -r[1]):
                print(f"      {f:<30} {n:>6}")
    print(f"\n  Legacy protections no longer needed (parser now agrees), retired on --apply: {len(retire)}")
    print(f"  Protections still holding a value the parser disagrees with: {sum(holding.values())}")
    for f, n in holding.most_common(8):
        print(f"      {f:<30} {n:>6}")


def report_rentals(add, update, remove, conn) -> None:
    total = conn.execute(text("SELECT count(*) FROM rental_listings")).scalar()
    by_column = Counter(c for diff in update.values() for c in diff)
    print(f"\n  Rental rows (rental_listings, now {total}) that would change: "
          f"{len(add)} added, {len(update)} updated, {len(remove)} removed -> {total + len(add) - len(remove)}")
    for c, n in by_column.most_common():
        print(f"      {c:<30} {n:>6}")


def apply(conn, changes, retire, rentals=None) -> None:
    conn.execute(text(PARSER_WRITE_SQL))
    for pid, diff in changes.items():
        fields = list(diff)
        conn.execute(
            text(f"UPDATE processed_listings SET {', '.join(f'{f} = :{f}' for f in fields)} WHERE id = :id"),
            {"id": pid, **{f: diff[f][1] for f in fields}},
        )
    for pid, field in retire:
        conn.execute(text("DELETE FROM listing_overrides WHERE listing_id = :id AND field = :field AND reason = :reason"),
                     {"id": pid, "field": field, "reason": LEGACY_REASON})
    add, update, remove = rentals or ([], {}, [])
    for row in add:
        conn.execute(text(INSERT_RENTAL), row)
    for rid, diff in update.items():
        conn.execute(text(f"UPDATE rental_listings SET {', '.join(f'{c} = :{c}' for c in diff)} WHERE id = :id"),
                     {"id": rid, **{c: new for c, (_, new) in diff.items()}})
    for rid in remove:
        conn.execute(text("DELETE FROM rental_listings WHERE id = :id"), {"id": rid})
    conn.execute(text("REFRESH MATERIALIZED VIEW market_price_model"))
    conn.execute(text("REFRESH MATERIALIZED VIEW rental_yields"))
    print(f"\nAPPLIED: updated {len(changes)} listings, retired {len(retire)} legacy protections; "
          f"rental rows: {len(add)} added, {len(update)} updated, {len(remove)} removed; "
          "refreshed the materialized views.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bring parser fixes to existing listings safely.")
    parser.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    parser.add_argument("--show", metavar="FIELD", help="list every change to this field")
    args = parser.parse_args()

    with engine.begin() as conn:
        check_protection_installed(conn)
        changes, retire, holding, counts = plan(conn)
        rentals = plan_rentals(conn, changes)
        report(changes, retire, holding, counts, conn)
        report_rentals(*rentals, conn)
        if args.show:
            print(f"\n  Changes to {args.show} (listing id: stored -> new):")
            for pid, diff in sorted(changes.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
                if args.show in diff:
                    print(f"    {pid}: {diff[args.show][0]!r} -> {diff[args.show][1]!r}")
        if args.apply:
            apply(conn, changes, retire, rentals)
        else:
            print("\nDRY RUN: nothing was changed (use --apply).")


if __name__ == "__main__":
    main()
