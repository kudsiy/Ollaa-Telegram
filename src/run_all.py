# -*- coding: utf-8 -*-
"""
run_all.py
----------
Single command that runs the complete OLLAA intelligence pipeline
from scraping to final report. One command does everything.

Usage:
    python src\run_all.py              # full run
    python src\run_all.py --skip-scrape  # ETL only (no new scraping)
    python src\run_all.py --reset        # wipe processed tables and rebuild

Steps:
    1. Scrape Telegram channels + forum groups
    2. ETL: process raw listings → processed_listings + rental_listings
    3. Fix extraction: recover missing prices/areas
    4. Mark valuation eligible
    5. Fix locations: reclassify other_addis rows
    6. Semantic deduplication
    7. Refresh materialized views
    8. Print final intelligence report
"""

import argparse
import io
import subprocess
import sys
import time
from pathlib import Path
from sqlalchemy import create_engine, text
from settings import DB_URL

def _force_utf8_stdio() -> None:
    """
    Ensure stdout/stderr use UTF-8 on Windows terminals to avoid UnicodeEncodeError.
    Safe no-op on environments that already support UTF-8.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")  # type: ignore[assignment]
    except Exception:
        pass

    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        else:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")  # type: ignore[assignment]
    except Exception:
        pass


_force_utf8_stdio()

SRC_DIR  = Path(__file__).resolve().parent
engine   = create_engine(DB_URL)

# ── ANSI color codes for terminal output ─────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def header(msg):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def step(n, msg):
    print(f"\n{BOLD}[STEP {n}]{RESET} {msg}")


def ok(msg):
    print(f"  {GREEN}[OK]{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}[ERROR]{RESET} {msg}")


def fail(msg):
    print(f"  {RED}[ERROR]{RESET} {msg}")


def run_script(script_name, extra_args=None, critical=True):
    """
    Run a Python script in the src/ directory.
    Streams output in real time.
    If critical=True and script fails, halts the pipeline.
    Returns True on success, False on failure.
    """
    script_path = SRC_DIR / script_name
    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd.extend(extra_args)

    print()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            print("  " + line, end="")
        proc.wait()

        if proc.returncode != 0:
            fail(f"{script_name} exited with code {proc.returncode}")
            if critical:
                print(f"\n{RED}Pipeline halted at {script_name}. Fix the error above and re-run.{RESET}\n")
                sys.exit(1)
            return False

        return True

    except FileNotFoundError:
        fail(f"{script_name} not found at {script_path}")
        if critical:
            sys.exit(1)
        return False


def run_sql(query, description=""):
    """Execute a SQL statement directly."""
    try:
        with engine.begin() as conn:
            result = conn.execute(text(query))
            rowcount = getattr(result, "rowcount", 0)
        if description:
            ok(f"{description} ({rowcount} rows affected)")
        return rowcount
    except Exception as e:
        warn(f"SQL failed — {description}: {e}")
        return 0


def print_final_report():
    """Print the complete intelligence report after pipeline completes."""
    header("OLLAA INTELLIGENCE REPORT")

    with engine.connect() as conn:

        # ── Database overview ─────────────────────────────────
        print(f"\n{BOLD}DATABASE OVERVIEW{RESET}")
        stats = {
            "Raw Telegram messages":    "SELECT COUNT(*) FROM telegram_listings",
            "Processed listings":       "SELECT COUNT(*) FROM processed_listings",
            "Rental listings":          "SELECT COUNT(*) FROM rental_listings",
            "Media queued":             "SELECT COUNT(*) FROM media_queue WHERE processed = false",
        }
        for label, q in stats.items():
            try:
                val = conn.execute(text(q)).scalar() or 0
                print(f"  {label:<30} {val:>8,}")
            except Exception:
                pass

        # ── Sale market snapshot ──────────────────────────────
        print(f"\n{BOLD}SALE MARKET SNAPSHOT{RESET}")
        sale_stats = {
            "Sale listings":            "SELECT COUNT(*) FROM processed_listings WHERE intent IN ('SALE','MIXED') AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Valuation eligible":       "SELECT COUNT(*) FROM processed_listings WHERE valuation_eligible = true AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Has price":                "SELECT COUNT(*) FROM processed_listings WHERE sale_price_birr IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Has area":                 "SELECT COUNT(*) FROM processed_listings WHERE builtup_sqm IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Has contact phone":        "SELECT COUNT(*) FROM processed_listings WHERE contact_phone IS NOT NULL AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "USD priced listings":      "SELECT COUNT(*) FROM processed_listings WHERE price_currency = 'USD' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Addis Ababa listings":     "SELECT COUNT(*) FROM processed_listings WHERE city = 'ADDIS_ABABA' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
            "Sheger City listings":     "SELECT COUNT(*) FROM processed_listings WHERE city = 'SHEGER_CITY' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)",
        }
        for label, q in sale_stats.items():
            try:
                val = conn.execute(text(q)).scalar() or 0
                print(f"  {label:<30} {val:>8,}")
            except Exception:
                pass

        # ── Property type breakdown ───────────────────────────
        print(f"\n{BOLD}PROPERTY TYPE BREAKDOWN{RESET}")
        try:
            rows = conn.execute(text("""
                SELECT property_type, city, COUNT(*) as n
                FROM processed_listings
                WHERE property_type IS NOT NULL
                AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)
                GROUP BY property_type, city
                ORDER BY n DESC
            """)).fetchall()
            print(f"  {'Type':<15} {'City':<15} {'Count':>6}")
            print(f"  {'-'*15} {'-'*15} {'-'*6}")
            for r in rows:
                print(f"  {(r.property_type or ''):<15} {(r.city or ''):<15} {r.n:>6,}")
        except Exception as e:
            warn(f"Property type breakdown failed: {e}")

        # ── Addis Ababa segment coverage ──────────────────────
        print(f"\n{BOLD}ADDIS ABABA — SEGMENT COVERAGE (Valuation Eligible){RESET}")
        try:
            rows = conn.execute(text("""
                SELECT location, property_type, COUNT(*) as samples
                FROM processed_listings
                WHERE valuation_eligible = true
                AND city = 'ADDIS_ABABA'
                AND sale_price_birr IS NOT NULL
                AND builtup_sqm IS NOT NULL
                AND location NOT IN ('other_addis')
                AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)
                GROUP BY location, property_type
                ORDER BY samples DESC
                LIMIT 25
            """)).fetchall()
            print(f"  {'Location':<25} {'Type':<15} {'Samples':>7}  {'Confidence'}")
            print(f"  {'-'*25} {'-'*15} {'-'*7}  {'-'*10}")
            for r in rows:
                tier = 'HIGH' if r.samples >= 10 else 'MEDIUM' if r.samples >= 5 else 'LOW'
                color = GREEN if tier == 'HIGH' else YELLOW if tier == 'MEDIUM' else ''
                print(f"  {r.location:<25} {r.property_type:<15} {r.samples:>7}  {color}[{tier}]{RESET}")
        except Exception as e:
            warn(f"Segment coverage query failed: {e}")

        # ── Sheger City segment coverage ──────────────────────
        print(f"\n{BOLD}SHEGER CITY — SEGMENT COVERAGE{RESET}")
        try:
            rows = conn.execute(text("""
                SELECT location, property_type, COUNT(*) as samples
                FROM processed_listings
                WHERE city = 'SHEGER_CITY'
                AND sale_price_birr IS NOT NULL
                AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)
                GROUP BY location, property_type
                ORDER BY samples DESC
            """)).fetchall()
            if rows:
                for r in rows:
                    tier = 'HIGH' if r.samples >= 10 else 'MEDIUM' if r.samples >= 5 else 'LOW'
                    print(f"  {r.location:<25} {r.property_type:<15} {r.samples:>7}  [{tier}]")
            else:
                print("  No Sheger City data yet.")
        except Exception as e:
            warn(f"Sheger City query failed: {e}")

        # ── Rental market snapshot ────────────────────────────
        print(f"\n{BOLD}RENTAL MARKET SNAPSHOT{RESET}")
        try:
            rows = conn.execute(text("""
                SELECT location, property_type,
                       COUNT(*) as samples,
                       ROUND(AVG(monthly_rent_birr), 0) as avg_rent,
                       ROUND(AVG(rent_per_sqm), 0) as avg_rent_sqm
                FROM rental_listings
                WHERE monthly_rent_birr IS NOT NULL
                GROUP BY location, property_type
                ORDER BY samples DESC
                LIMIT 15
            """)).fetchall()
            if rows:
                print(f"  {'Location':<20} {'Type':<12} {'Count':>5}  {'Avg Rent':>10}  {'Rent/sqm':>8}")
                print(f"  {'-'*20} {'-'*12} {'-'*5}  {'-'*10}  {'-'*8}")
                for r in rows:
                    avg_rent = f"{int(r.avg_rent):,}" if r.avg_rent else "N/A"
                    avg_sqm  = f"{int(r.avg_rent_sqm):,}" if r.avg_rent_sqm else "N/A"
                    print(f"  {(r.location or ''):<20} {(r.property_type or ''):<12} {r.samples:>5}  {avg_rent:>10}  {avg_sqm:>8}")
            else:
                print("  No rental data yet. Check @Bet_afri scraping.")
        except Exception as e:
            warn(f"Rental snapshot failed: {e}")

        # ── Unresolved locations ──────────────────────────────
        try:
            other = conn.execute(text(
                "SELECT COUNT(*) FROM processed_listings WHERE location = 'other_addis' AND (listing_class NOT IN ('ADVERTISEMENT', 'INVALID', 'MEDIA_PENDING', 'PROMOTIONAL', 'INQUIRY') OR valuation_eligible = true)"
            )).scalar() or 0
            if other > 0:
                warn(f"{other} listings still in 'other_addis' — run dedup_and_fix_locations.py --location-only to investigate")
        except Exception:
            pass

        # ── Media queue ───────────────────────────────────────
        try:
            queued = conn.execute(text(
                "SELECT COUNT(*), file_type FROM media_queue WHERE processed = false GROUP BY file_type"
            )).fetchall()
            if queued:
                print(f"\n{BOLD}MEDIA QUEUE (unprocessed){RESET}")
                for r in queued:
                    print(f"  {r.file_type:<10} {r.count:>5} files waiting")
        except Exception:
            pass

    print(f"\n{BOLD}{GREEN}Pipeline complete.{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="OLLAA master pipeline")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Skip Telegram scraping (ETL only)")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe processed_listings and rental_listings before ETL")
    args = parser.parse_args()

    start = time.time()
    header("OLLAA PIPELINE STARTING")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode: {'ETL only (skip scrape)' if args.skip_scrape else 'Full run'}")
    if args.reset:
        print(f"  Reset: YES — processed tables will be rebuilt from scratch")

    # ── STEP 1: SCRAPE ────────────────────────────────────────
    if not args.skip_scrape:
        step(1, "Scraping Telegram channels + forum groups")
        success = run_script("telegram_scraper.py", critical=True)
        if success:
            ok("Scraping complete")
    else:
        step(1, "Scraping skipped (--skip-scrape)")

    # ── STEP 2: ETL ───────────────────────────────────────────
    step(2, "ETL: processing raw listings → processed_listings + rental_listings")
    etl_args = ["--reset"] if args.reset else []
    run_script("etl_runner.py", extra_args=etl_args, critical=True)

    # ── STEP 3: FIX EXTRACTION ────────────────────────────────
    step(3, "Fix extraction: recovering missing prices and areas")
    run_script("Fix_extraction.py", critical=False)

    # ── STEP 4: MARK VALUATION ELIGIBLE ──────────────────────
    step(4, "Marking valuation eligible listings")
    run_sql("""
        UPDATE processed_listings
        SET valuation_eligible = true
        WHERE intent IN ('SALE','MIXED')
        AND sale_price_birr IS NOT NULL
        AND builtup_sqm IS NOT NULL
        AND valuation_eligible = false
    """, description="valuation_eligible updated")

    # ── STEP 5: FIX LOCATIONS ─────────────────────────────────
    step(5, "Reclassifying other_addis locations (Sheger City + missing neighborhoods)")
    run_script("dedup_and_fix_locations.py",
               extra_args=["--location-only"],
               critical=False)

    # ── STEP 6: SEMANTIC DEDUP ────────────────────────────────
    step(6, "Semantic deduplication (this takes ~10 minutes)")
    run_script("semantic_dedup.py", critical=False)

    # ── STEP 7: REFRESH VIEWS ────────────────────────────────
    step(7, "Refreshing materialized views")
    run_sql("REFRESH MATERIALIZED VIEW market_price_model",
            description="market_price_model refreshed")

    # Refresh rental yields if it exists
    try:
        run_sql("REFRESH MATERIALIZED VIEW rental_yields",
                description="rental_yields refreshed")
    except Exception:
        pass  # view may not exist yet if migration hasn't been run

    # ── STEP 8: FINAL REPORT ──────────────────────────────────
    step(8, "Generating intelligence report")
    elapsed = round(time.time() - start, 1)
    print(f"\n  Total pipeline time: {elapsed}s ({round(elapsed/60, 1)} min)")
    print_final_report()


if __name__ == "__main__":
    main()
