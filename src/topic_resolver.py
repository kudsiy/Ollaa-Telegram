"""
topic_resolver.py
-----------------
Resolves location and property_type for processed_listings rows
stuck in 'other_addis' by reading topic_title from telegram_listings.

Forum group messages have no location in their text body.
Their topic_title contains the location + property context.

Examples:
  Visco_BoleMeskelFlower(መስቀልፍላወር)  → bole_meskel_flower / APARTMENT
  MetroHomes_Bole_Harmony Loft       → bole_michael / APARTMENT
  Damla Realestate ፒያሳ ሱቅ           → piassa / COMMERCIAL
  Janbo Realestate Summit Villa      → summit / VILLA
  Champion CMC Apartment             → cmc / APARTMENT

Run:
  python src/topic_resolver.py            # dry run - shows what will change
  python src/topic_resolver.py --apply    # writes changes to database
  python src/topic_resolver.py --stats    # show resolution stats only
"""

import re
import sys
import psycopg2
from psycopg2.extras import execute_values

# ── Database ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "dbname": "ollaa",
    "user": "postgres",
    "password": "REMOVED_OLD_PASSWORD",
    "host": "localhost",
    "port": 5432,
}

# ── Location Patterns ─────────────────────────────────────────────────────────
# Order matters — more specific patterns first
LOCATION_PATTERNS = [
    # Bole sub-areas first (before generic Bole match)
    (r"bole\s*mes[kq]el|meskel\s*flower|meskel.?flower|meskelflower|መስቀል\s*ፍላወር|መስቀልፍላወር|meskel", "bole_meskel_flower"),
    (r"bole\s*michael|bolemic|bole\s*mika[ei]l|ቦሌሚካኤል|bole_harmony", "bole_michael"),
    (r"bole\s*arabsa|arabsa", "bole_arabsa"),
    (r"bole\s*atlas|atlas", "bole_atlas"),
    (r"bole\s*bulbula|bulbula", "bole_bulbula"),
    (r"bole\s*japan|bolejapan", "bole_japan"),
    (r"bole\s*gerji|bolegerji", "gerji"),
    # Main areas
    (r"ayat|አያት", "ayat"),
    (r"summit|ሰሚት", "summit"),
    (r"cmc|ሲኤምሲ", "cmc"),
    (r"bethel|ቤተል", "bethel"),
    (r"wollo\s*sefer|wolo\s*sefer|ወሎ\s*ሰፈር", "wollo_sefer"),
    (r"figa|ፊጋ", "figa"),
    (r"piassa|piaza|ፒያሳ", "piassa"),
    (r"sarem|ሳሬም", "piassa"),
    (r"kazanch[ie]s|ካዛንቺስ|kazanch", "kazanchis"),
    (r"egziabher\s*ab|እግዚያራብ", "megenagna"),
    (r"megenagna|megna|መገናኛ", "megenagna"),
    (r"german|ጀርመን", "german_square"),
    (r"gerji|ገርጂ", "gerji"),
    (r"jemo|ጀሞ", "jemo"),
    (r"\bbulbula\b|ቡልቡላ", "bulbula"),
    (r"lebu|ለቡ", "lebu"),
    (r"varnero|ቫርኔሮ", "lebu_varnero"),
    (r"jarsso|jarso|ጃርሶ", "jarsso"),
    (r"tuludimtu|tulu.?dimtu|ቱሉ\s*ዲምቱ", "tuludimtu"),
    (r"kotebe|ቆጠቤ|ቆተቤ", "kotebe"),
    (r"ferensay|ferensai|ፈረንሳይ", "ferensay"),
    (r"lideta|ልደታ", "lideta"),
    (r"mexico|ሜክሲኮ", "mexico"),
    (r"sengatera|ሰንጋተራ", "mexico_sengatera"),
    (r"sarbet|ሳርቤት", "sarbet"),
    (r"tor.?hayloch|torha[yi]|ጦርሃይሎች|ጦር\s*ሃይሎች", "tor_hayloch"),
    (r"old.?airport|oldairport|ድሮ\s*አየር", "old_airport"),
    (r"4.?kilo|4ኪሎ|አራት\s*ኪሎ", "4_kilo"),
    (r"6.?kilo|ስድስት\s*ኪሎ", "6_kilo"),
    (r"stadium|ስታድዬም", "stadium"),
    (r"gotera|ጎተራ", "gotera"),
    (r"saris|ሳሪስ", "saris"),
    (r"kolfe|ቆልፌ", "kolfe"),
    (r"shola|ሾላ", "sholla"),
    (r"ayer.?tena|ayertena|አየር\s*ጤና", "ayer_tena"),
    (r"wesen|ወሰን", "wesen"),
    (r"haya.?hulet|hayahulet|22|ሃያ\s*ሁለት", "haya_hulet"),
    (r"sebategna|7.?kilo|ሰባት\s*ኪሎ", "7_kilo"),
    (r"lafto|laphto|ላፍቶ", "lafto"),
    (r"nifas.?silk|nifassilk|ንፋስ\s*ስልክ", "nifas_silk"),
    (r"akaki|አቃቂ", "akaki"),
    (r"kaliti|ቃሊቲ", "kaliti"),
    (r"lamberet|ላምበረት", "lamberet"),
    (r"winget|ዊንጌት", "winget"),
    (r"bambis|ባምቢስ", "bambis"),
    (r"friend.?ship|friendship", "friendship"),
    (r"pastor|ፓስተር", "pastor_medhanialem"),
    (r"enk[uo]lal.?fabrica|enkuklal", "enkulal_fabrica"),
    (r"awareness|አዌርነስ", "awareness"),
    (r"lem[ei].?bole|lemibole", "lemi_bole"),
    (r"imperial|ኢምፔሪያል", "imperial"),
    # Generic Bole last (after all sub-areas)
    (r"bole|ቦሌ", "bole_main"),
    # Sheger City locations
    (r"legetafo|legetaffo|ለጌጣፎ", "legetafo"),
    (r"burayu|ቡራዩ", "burayu"),
    (r"sebeta|ሰበታ", "sebeta"),
    (r"sululta|ሱሉልታ", "sululta"),
    (r"gelan|ገላን", "gelan"),
    (r"holeta|ሆለታ", "holeta"),
    (r"chancho|ጫንጮ", "chancho"),
]

SHEGER_LOCATIONS = {"legetafo", "burayu", "sebeta", "sululta", "gelan", "holeta", "chancho"}

# ── Property Type Patterns ────────────────────────────────────────────────────
PROPERTY_TYPE_PATTERNS = [
    # Amharic first
    (r"ሱቅ|ሱቆች|shop|shops|commercial|ንግድ\s*ቤት|store", "COMMERCIAL"),
    (r"ቢሮ|office|offices", "OFFICE"),
    (r"መጋዘን|warehouse|ware.?house|storage", "WAREHOUSE"),
    (r"መሸጫ", "COMMERCIAL"),
    (r"መሬት|land|plot|ቦታ", "LAND"),
    (r"\bvillage\b", "VILLA"),
    (r"g\+1|g\+2|compound", "VILLA"),
    (r"villa|ቪላ|villas", "VILLA"),
    (r"townhouse|town.?house|taun.?haus", "TOWNHOUSE"),
    (r"condo(?:minium)?|ኮንዶ|condominium", "CONDOMINIUM"),
    (r"garden|tower|residence|mall", "APARTMENT"),
    (r"duplex|penthouse|studio", "APARTMENT"),
    (r"\bfloor\b|sqm|m2|㎡", "APARTMENT"),
    (r"apartment|አፓርትማ|apt|flat|loft", "APARTMENT"),
]

# ── Developer → Property Type Hints ──────────────────────────────────────────
DEVELOPER_TYPE_HINTS = {
    r"janbo": "VILLA",
    r"jembo": "VILLA",
    r"sunshine": "VILLA",
    r"temer": "APARTMENT",
    r"metro.?homes|metrohomes": "APARTMENT",
    r"visco": "APARTMENT",
    r"damla": "APARTMENT",
    r"gifted": "APARTMENT",
    r"champion": "APARTMENT",
    r"gift.?real.?estate": "APARTMENT",
    r"ayat.?real.?estate": "CONDOMINIUM",
    r"luxury.?homes": "VILLA",
}

# ── Compile all patterns ──────────────────────────────────────────────────────
LOCATION_RE = [(re.compile(p, re.IGNORECASE), loc) for p, loc in LOCATION_PATTERNS]
PROPERTY_RE = [(re.compile(p, re.IGNORECASE), pt) for p, pt in PROPERTY_TYPE_PATTERNS]
DEVELOPER_RE = [(re.compile(p, re.IGNORECASE), pt) for p, pt in DEVELOPER_TYPE_HINTS.items()]


def resolve_location(topic_title: str):
    """Extract location slug from topic_title. Returns (location_slug, city) or (None, None)."""
    if not topic_title:
        return None, None
    for pattern, location in LOCATION_RE:
        if pattern.search(topic_title):
            city = "SHEGER_CITY" if location in SHEGER_LOCATIONS else "ADDIS_ABABA"
            return location, city
    return None, None


def resolve_property_type(topic_title: str):
    """Extract property type from topic_title. Returns type string or None."""
    if not topic_title:
        return None
    # Check explicit property type keywords first
    for pattern, ptype in PROPERTY_RE:
        if pattern.search(topic_title):
            return ptype
    # Fall back to developer hints
    for pattern, ptype in DEVELOPER_RE:
        if pattern.search(topic_title):
            return ptype
    return None


def get_resolution_candidates(conn):
    """
    Get all telegram_listings that have a topic_title and whose
    raw text maps to a processed_listing with location = 'other_addis'.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH joined AS (
                SELECT DISTINCT ON (pl.id)
                    tl.id          AS telegram_id,
                    tl.message_id,
                    tl.text        AS body_text,
                    tl.topic_title,
                    tl.channel     AS channel,
                    pl.id          AS processed_id,
                    pl.location,
                    pl.property_type,
                    pl.city
                FROM telegram_listings tl
                JOIN processed_listings pl
                  ON pl.raw_text = tl.text
                 AND pl.source_channel = tl.channel
                WHERE tl.topic_title IS NOT NULL
                  AND tl.topic_title != ''
                  AND (
                        pl.location = 'other_addis'
                     OR pl.property_type = 'UNKNOWN'
                     OR pl.property_type IS NULL
                  )
                ORDER BY pl.id, tl.id DESC
            )
            SELECT *
            FROM joined
            ORDER BY channel, telegram_id
        """)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in rows]


def get_resolution_candidates_fallback(conn):
    """
    Alternative join strategy (kept for compatibility).
    Joins on raw_text + source_channel, de-duplicated by processed_id.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH joined AS (
                SELECT DISTINCT ON (pl.id)
                    tl.id          AS telegram_id,
                    tl.message_id,
                    tl.text        AS body_text,
                    tl.topic_title,
                    tl.channel     AS channel,
                    pl.id          AS processed_id,
                    pl.location,
                    pl.property_type,
                    pl.city
                FROM telegram_listings tl
                JOIN processed_listings pl
                  ON pl.raw_text = tl.text
                 AND pl.source_channel = tl.channel
                WHERE tl.topic_title IS NOT NULL
                  AND tl.topic_title != ''
                  AND (
                        pl.location = 'other_addis'
                     OR pl.property_type = 'UNKNOWN'
                     OR pl.property_type IS NULL
                  )
                ORDER BY pl.id, tl.id DESC
            )
            SELECT *
            FROM joined
            ORDER BY channel, telegram_id
        """)
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row)) for row in rows]


def check_schema(conn):
    """Check which columns exist and what join keys are available."""
    with conn.cursor() as cur:
        # Check processed_listings columns
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'processed_listings'
            ORDER BY ordinal_position
        """)
        pl_cols = [r[0] for r in cur.fetchall()]

        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'telegram_listings'
            ORDER BY ordinal_position
        """)
        tl_cols = [r[0] for r in cur.fetchall()]

        return pl_cols, tl_cols


def build_updates(candidates):
    """
    For each candidate row, attempt to resolve location and/or property_type.
    Returns list of dicts with processed_id + resolved fields.
    """
    updates = []
    unresolved = []

    for row in candidates:
        topic = row["topic_title"] or ""
        location, city = resolve_location(topic)
        property_type = resolve_property_type(topic)

        body_text = (row.get("body_text") or "").strip()
        blob = f"{topic} {body_text}".lower()

        # If we found a location but still can't infer type, try a keyword-only pass.
        # This helps catch cases where topic titles use developer/project naming
        # rather than explicit "apartment/villa" keywords.
        if location and not property_type:
            t = topic.lower()
            if any(k in t for k in ("luxury", "g+1", "g+2", "compound", "village")):
                property_type = "VILLA"
            elif any(k in t for k in ("duplex", "penthouse", "studio")):
                property_type = "APARTMENT"
            elif any(k in t for k in ("garden", "tower", "residence", "mall", "floor", "sqm", "m2", "㎡")):
                property_type = "APARTMENT"

        # Pattern guess for media-only forum posts:
        # when there's no body text, use the topic title keywords to classify commercial.
        if (not body_text) and (not property_type) and topic:
            t = topic.lower()
            if any(k in t for k in ("commercial", "shop", "mall")):
                property_type = "COMMERCIAL"

        # High-frequency Amharic signals (topic + body):
        # - መጋዘን / መሸጫ => COMMERCIAL
        # - መኝታ / ባለ => APARTMENT default for multi-room listings
        # - ክፍያ + ባለ => APARTMENT (payment-plan language)
        if not property_type:
            if ("መጋዘን" in blob) or ("መሸጫ" in blob):
                property_type = "COMMERCIAL"
            elif ("ባለ" in blob) and (("መኝታ" in blob) or ("ክፍያ" in blob)):
                property_type = "APARTMENT"
            elif ("መኝታ" in blob) or ("ባለ" in blob):
                property_type = "APARTMENT"

        # Only update if we actually resolved something new
        new_location = location if location and row["location"] == "other_addis" else None
        new_city = city if location and row["location"] == "other_addis" else None
        new_type = (
            property_type
            if property_type and row["property_type"] in ("UNKNOWN", None)
            else None
        )

        if new_location or new_type:
            updates.append({
                "processed_id": row["processed_id"],
                "new_location": new_location or row["location"],
                "new_city": new_city or row["city"],
                "new_type": new_type or row["property_type"],
                "topic_title": topic,
                "channel": row["channel"],
            })
        else:
            unresolved.append(row)

    return updates, unresolved


def apply_updates(conn, updates):
    """Write resolved locations and property types to processed_listings."""
    if not updates:
        print("No updates to apply.")
        return 0

    with conn.cursor() as cur:
        for u in updates:
            cur.execute("""
                UPDATE processed_listings
                SET
                    location      = %s,
                    city          = %s,
                    property_type = %s
                WHERE id = %s
            """, (
                u["new_location"],
                u["new_city"],
                u["new_type"],
                u["processed_id"],
            ))
    conn.commit()
    return len(updates)


def print_stats(conn):
    """Print current other_addis and UNKNOWN counts."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM processed_listings WHERE location = 'other_addis'")
        other_addis = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM processed_listings WHERE property_type = 'UNKNOWN' OR property_type IS NULL")
        unknown_type = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM processed_listings")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT location, COUNT(*) as cnt
            FROM processed_listings
            WHERE location != 'other_addis'
            GROUP BY location
            ORDER BY cnt DESC
            LIMIT 20
        """)
        top_locations = cur.fetchall()

        cur.execute("""
            SELECT property_type, COUNT(*) as cnt
            FROM processed_listings
            GROUP BY property_type
            ORDER BY cnt DESC
        """)
        type_dist = cur.fetchall()

    print("\n" + "=" * 60)
    print("OLLAA DATABASE STATE")
    print("=" * 60)
    print(f"  Total processed listings : {total:,}")
    print(f"  Stuck in other_addis     : {other_addis:,}")
    print(f"  Unknown property type    : {unknown_type:,}")
    print("\nTop 20 Locations:")
    for loc, cnt in top_locations:
        print(f"  {loc:<30} {cnt:>5}")
    print("\nProperty Type Distribution:")
    for ptype, cnt in type_dist:
        print(f"  {str(ptype):<20} {cnt:>5}")
    print("=" * 60)


def print_sample_resolutions(updates, n=20):
    """Show a sample of what will be resolved."""
    print(f"\nSample resolutions (showing {min(n, len(updates))} of {len(updates)}):")
    print("-" * 80)
    for u in updates[:n]:
        print(f"  [{u['channel']}]")
        print(f"    topic  : {u['topic_title'][:70]}")
        print(f"    → loc  : {u['new_location']}  city: {u['new_city']}")
        print(f"    → type : {u['new_type']}")
        print()


def print_unresolved_sample(unresolved, n=20):
    """Show unresolved topics so we can expand patterns."""
    print(f"\nUnresolved topics (showing {min(n, len(unresolved))} of {len(unresolved)}):")
    print("-" * 80)
    seen = set()
    count = 0
    for row in unresolved:
        t = (row["topic_title"] or "").strip()
        if t not in seen:
            seen.add(t)
            print(f"  [{row.get('channel')}] {t[:80]}")
            count += 1
            if count >= n:
                break


def main():
    dry_run = "--apply" not in sys.argv
    stats_only = "--stats" in sys.argv

    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)

    if stats_only:
        print_stats(conn)
        conn.close()
        return

    # Check schema first
    pl_cols, tl_cols = check_schema(conn)
    print(f"\nprocessed_listings columns: {', '.join(pl_cols)}")
    print(f"telegram_listings columns  : {', '.join(tl_cols)}")

    # Determine join strategy
    use_fallback = (
        "raw_text" not in pl_cols
        or "source_channel" not in pl_cols
        or "text" not in tl_cols
        or "channel" not in tl_cols
        or "source_channel" not in pl_cols
    )

    print("\nFetching resolution candidates...")
    if use_fallback:
        print("Using fallback join...")
        candidates = get_resolution_candidates_fallback(conn)
    else:
        candidates = get_resolution_candidates(conn)
        if not candidates:
            print("Primary join returned 0 results, trying fallback join...")
            candidates = get_resolution_candidates_fallback(conn)

    print(f"Found {len(candidates):,} candidates with topic_title to resolve")

    if not candidates:
        print("\nNothing to resolve. Either:")
        print("  - No rows have topic_title set in telegram_listings")
        print("  - Join between tables is not matching")
        print("\nRunning stats anyway:")
        print_stats(conn)
        conn.close()
        return

    # Build updates
    updates, unresolved = build_updates(candidates)

    print(f"\nResolution summary:")
    print(f"  Resolvable     : {len(updates):,}")
    print(f"  Unresolved     : {len(unresolved):,}")

    print_sample_resolutions(updates)
    print_unresolved_sample(unresolved)

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — no changes written to database.")
        print("Run with --apply to write changes.")
        print("=" * 60)
    else:
        print("\nApplying updates...")
        applied = apply_updates(conn, updates)
        print(f"Successfully updated {applied:,} rows.")

        # Refresh materialized view
        print("Refreshing market_price_model...")
        try:
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW market_price_model;")
            conn.commit()
            print("market_price_model refreshed.")
        except Exception as e:
            print(f"Note: Could not refresh materialized view: {e}")

        print("\nPost-update stats:")
        print_stats(conn)

    conn.close()


if __name__ == "__main__":
    main()