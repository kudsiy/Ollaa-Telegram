r"""
dedup_strict.py
---------------
Removes listings that repeat the same property, by rules a valuer can check. It replaces
semantic_dedup.py, which compared the look of the texts, ignored prices, and would have
deleted different flats posted on one broker's template (task S20).

Two listings are the same property only if:
  1. same words: the same text, once contacts, links, hashtags, punctuation and channel
     footers are left out (and the same forum topic); or
  2. same facts: a usable listing with the same type, named place, price and size, and no
     different bedrooms or floor; or
  3. nearly the same words: 95% or more alike, with the same type and place, the same numbers
     (a broker's template with another code or room size is another property), and no different
     price, size, bedrooms or floor.
Floors are also read from the text ("3floor", "ግራውንድ ፍሎር"), as the parser misses some, and two
houses of the same size and price but different heights (G+2, G+3) are different properties.
A price change is never treated as a repeat: such pairs are only reported.

Of each group one listing stays: one with a protected value (hand repair) first, then the
one in the model sample, then the most complete, then the newest. A listing with a protected
value is never removed. A removed listing's message goes to processing_exclusions, with the
listing it repeats, so it never comes back; to undo, delete that row and run etl_runner.py.

Usage:
    venv\Scripts\python.exe src\dedup_strict.py            (report only)
    venv\Scripts\python.exe src\dedup_strict.py --apply
    venv\Scripts\python.exe src\dedup_strict.py --apply --only 1744    (only the listings named)
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))

from rapidfuzz import fuzz  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

import data_quality as dq  # noqa: E402
from locations import NOISE, UNKNOWN  # noqa: E402
from processor import is_photo_only, strip_footer  # noqa: E402
from settings import DB_URL  # noqa: E402

NEARLY_SAME = 95
MIN_WORDS_CHARS = 15
_CONTACT_RE = re.compile(r"https?://\S+|t\.me/\S+|@\w+|#\S+|\+?\d[\d\s-]{8,}\d", re.IGNORECASE)
_GROUND_RE = re.compile(r"ግራውንድ\s*(?:ፍሎር|ላይ)|ደረጃ\s*[=:፦]?\s*(?:00\s*/?\s*)?ግራውንድ|\bground\s*(?:floor|f\b)|•\s*ground\s*•")
_FLOOR_RE = re.compile(r"(?<![\d+])(\d{1,2})\s*(?:ኛ|ተኛ|th|st|nd|rd)?\s*(?:ፎቅ|ፍሎር|floor|f\b)")
_HEIGHT_RE = re.compile(r"(?:\bg|[ጂጅ])\s*\+\s*(\d{1,2})")
RULES = {1: "same words", 2: "same type, place, price and size", 3: "nearly the same words"}


def _plain(text_: str) -> str:
    return _CONTACT_RE.sub(" ", unicodedata.normalize("NFKC", strip_footer(text_ or "")).lower())


def numbers_of(text_: str) -> set:
    return set(re.findall(r"\d+(?:[.,]\d+)*", _plain(text_)))


def floor_of(r):
    """The floor the advert states: 0 for the ground floor (not "ground parking" or "under ground water")."""
    t = _plain(r.raw_text)
    if _GROUND_RE.search(t):
        return 0
    m = _FLOOR_RE.search(t)
    return int(m.group(1)) if m else r.floor_level


def height_of(r):
    """The building's height the advert states: "G+3", "ጅ+2", "ጂ +5"."""
    m = _HEIGHT_RE.search(_plain(r.raw_text))
    return int(m.group(1)) if m else None


def words_of(text_: str) -> str:
    """The advert's words and numbers only."""
    t = unicodedata.normalize("NFKC", strip_footer(text_ or "")).lower()
    return re.sub(r"[\W_]+", "", _CONTACT_RE.sub(" ", t))


def price_of(r):
    return r.sale_price_birr if r.intent in ("SALE", "MIXED") else r.rent_price_birr


def size_of(r):
    return r.builtup_sqm or r.plot_sqm


def differ(a, b) -> bool:
    return a is not None and b is not None and float(a) != float(b)


def named_place(r) -> bool:
    return r.location not in (None, UNKNOWN, NOISE, "other_addis")


def no_conflict(a, b) -> bool:
    """Nothing known about the two says they are different properties."""
    return (a.property_type == b.property_type and a.location == b.location and a.intent == b.intent
            and not differ(price_of(a), price_of(b)) and not differ(a.builtup_sqm, b.builtup_sqm)
            and not differ(a.plot_sqm, b.plot_sqm) and not differ(a.bedrooms, b.bedrooms)
            and not differ(floor_of(a), floor_of(b)) and not differ(height_of(a), height_of(b)))


def find_pairs(rows):
    """(id, id, rule) for every pair found; also the pairs that look alike but whose price differs."""
    pairs, price_changed = [], []
    texts = {r.id: words_of(r.raw_text) for r in rows if not is_photo_only(r.raw_text)}

    by_words = defaultdict(list)
    for r in rows:
        if len(texts.get(r.id, "")) >= MIN_WORDS_CHARS:
            by_words[(getattr(r, "topic_title", None), texts[r.id])].append(r)
    for group in by_words.values():
        pairs += [(group[0].id, r.id, 1) for r in group[1:]]

    usable = [r for r in rows if dq.is_usable(r) and r.id in texts]
    by_facts = defaultdict(list)
    for r in usable:
        if price_of(r) is not None and size_of(r) is not None and named_place(r):
            by_facts[(r.intent, r.property_type, r.location, float(price_of(r)), float(size_of(r)))].append(r)
    for group in by_facts.values():
        for i, a in enumerate(group):
            pairs += [(a.id, b.id, 2) for b in group[i + 1:] if no_conflict(a, b)]

    by_place = defaultdict(list)
    for r in usable:
        if named_place(r) and len(texts[r.id]) >= MIN_WORDS_CHARS:
            by_place[(r.property_type, r.location, r.intent)].append(r)
    for group in by_place.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if getattr(a, "topic_title", None) != getattr(b, "topic_title", None):
                    continue
                if fuzz.ratio(texts[a.id], texts[b.id], score_cutoff=NEARLY_SAME):
                    if no_conflict(a, b):
                        if numbers_of(a.raw_text) == numbers_of(b.raw_text):
                            pairs.append((a.id, b.id, 3))
                    elif differ(price_of(a), price_of(b)) and not differ(size_of(a), size_of(b)):
                        price_changed.append((a.id, b.id))
    return pairs, price_changed


def groups_of(pairs):
    """Listings joined by any pair, with the first rule that joined each."""
    parent = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    rule_of = {}
    for a, b, rule in pairs:
        parent[root(a)] = root(b)
        rule_of[a] = min(rule, rule_of.get(a, rule))
        rule_of[b] = min(rule, rule_of.get(b, rule))
    groups = defaultdict(list)
    for x in parent:
        groups[root(x)].append(x)
    return list(groups.values()), rule_of


def _order(listing_id: str):
    return int(listing_id) if listing_id.isdigit() else 0


def plan(rows, protected):
    """(listing removed, listing kept, rule) for all, and the pairs whose price differs."""
    by_id = {r.id: r for r in rows}
    in_sample = {r.id for r in dq.sale_sample(rows)}
    pairs, price_changed = find_pairs(rows)
    groups, rule_of = groups_of(pairs)
    filled = ("sale_price_birr", "rent_price_birr", "builtup_sqm", "plot_sqm", "bedrooms", "bathrooms",
              "floor_level", "posted_at")

    def keep_rank(i):
        r = by_id[i]
        return (i in protected, i in in_sample, sum(getattr(r, f) is not None for f in filled), _order(i))

    removals = []
    for group in groups:
        keep = max(group, key=keep_rank)
        removals += [(i, keep, rule_of[i]) for i in group if i != keep and i not in protected]
    return removals, price_changed


def load(conn):
    return conn.execute(text("""
        SELECT p.*, t.topic_title FROM processed_listings p
        LEFT JOIN telegram_listings t ON p.id = t.id::text""")).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="remove the repeats (default: report only)")
    parser.add_argument("--only", nargs="+", metavar="ID", help="consider only these listings for removal")
    args = parser.parse_args()
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        rows = load(conn)
        protected = {r[0] for r in conn.execute(text("SELECT DISTINCT listing_id FROM listing_overrides"))}
    removals, price_changed = plan(rows, protected)
    if args.only:
        removals = [x for x in removals if x[0] in args.only]
    by_id = {r.id: r for r in rows}
    sample = {r.id for r in dq.sale_sample(rows)}
    print(f"Listings checked: {len(rows):,}")
    print(f"Repeats found: {len(removals)}; {dict(Counter(RULES[r] for _, _, r in removals))}")
    print(f"  usable: {sum(dq.is_usable(by_id[i]) for i, _, _ in removals)}; in the sale sample: "
          f"{sum(i in sample for i, _, _ in removals)}")
    print(f"Sale sample: {len(sample)} -> {len(sample - {i for i, _, _ in removals})} different properties")
    print(f"Look alike but the price differs (not removed): {len(price_changed)}")
    if not args.apply:
        print("REPORT ONLY: nothing was changed (use --apply).")
        return
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL application_name = 'dedup_strict.py'"))
        for gone, keep, rule in removals:
            conn.execute(text("DELETE FROM rental_listings WHERE id = :i"), {"i": f"{gone}_rent"})
            conn.execute(text("DELETE FROM processed_listings WHERE id = :i"), {"i": gone})
            conn.execute(text("UPDATE processing_exclusions SET reason = :why WHERE raw_id = :raw"),
                         {"why": f"duplicate of listing {keep}: {RULES[rule]} (dedup_strict.py)", "raw": int(gone)})
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW market_price_model"))
        conn.execute(text("REFRESH MATERIALIZED VIEW rental_yields"))
    print(f"APPLIED: removed {len(removals)} listings; refreshed the materialized views.")


if __name__ == "__main__":
    main()
