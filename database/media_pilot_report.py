r"""
media_pilot_report.py
---------------------
Summarises the photo pilot (src/media_pilot.py, task S15) from
data/media_pilot/results.json: how many posts became usable listings, how many images
had nothing useful, likely repeats of listings already stored, token use, and one table
row per post. Read-only. Prints Markdown; phone numbers and @usernames are masked.

Usage:
    venv\Scripts\python.exe database\media_pilot_report.py              # all rounds
    venv\Scripts\python.exe database\media_pilot_report.py --round 2    # one round
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "database"))

from sqlalchemy import create_engine, text  # noqa: E402

import data_quality as dq  # noqa: E402
from settings import DB_URL  # noqa: E402

RESULTS = BASE_DIR / "data" / "media_pilot" / "results.json"
PHONE_RE = re.compile(r"(?:\+?251|0)\s?[79][\d\s-]{7,12}|@\w+")


def mask(s: str) -> str:
    return PHONE_RE.sub("<contact>", s or "")


def usable(p) -> bool:
    return (p.intent in ("SALE", "RENT", "MIXED") and p.listing_class not in dq.EXCLUDED_CLASSES
            and p.property_type not in dq.EXCLUDED_TYPES)


def model_ready(p) -> bool:
    price = p.sale_price_birr if p.intent in ("SALE", "MIXED") else p.rent_price_birr
    return (usable(p) and price is not None and dq.size_of(p) is not None and p.location not in (None, dq.UNKNOWN, dq.NOISE)
            and p.property_type != "UNKNOWN" and p.price_currency == "ETB" and not dq.outlier_reasons(p))


def main() -> None:
    only_round = int(sys.argv[sys.argv.index("--round") + 1]) if "--round" in sys.argv else None
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    if only_round:   # round 1 entries were written before rounds were recorded
        results = {k: v for k, v in results.items() if v.get("round", 1) == only_round}
    done = {k: v for k, v in results.items() if "error" not in v}
    errors = len(results) - len(done)
    rows = {k: SimpleNamespace(**v["parsed"]) for k, v in done.items()}

    with create_engine(DB_URL).connect() as conn:
        stored = conn.execute(text("""
            SELECT p.id, p.source_channel, p.sale_price_birr, p.rent_price_birr, p.builtup_sqm, p.plot_sqm
            FROM processed_listings p WHERE p.listing_class <> 'MEDIA_PENDING'""")).fetchall()

    def repeat_of(k):
        """An existing text listing of the same channel with the same price and size."""
        p, ch = rows[k], done[k]["channel"]
        price = p.sale_price_birr or p.rent_price_birr
        size = p.builtup_sqm or p.plot_sqm
        if not price:
            return None
        for s in stored:
            if (s.source_channel.rsplit("/", 1)[-1] == ch and (s.sale_price_birr or s.rent_price_birr) == price
                    and (size is None or (s.builtup_sqm or s.plot_sqm) == size)):
                return s.id
        return None

    no_text = [k for k in done if not done[k]["text"].strip()]
    use = [k for k in done if usable(rows[k])]
    ready = [k for k in use if model_ready(rows[k])]
    repeats = {k: repeat_of(k) for k in use}
    new_use = [k for k in use if not repeats[k]]
    tokens = [v["tokens"] for v in done.values()]
    n = len(done)

    print(f"# Photo pilot numbers\n\nPosts read: {n} (errors: {errors}); channels: "
          f"{dict(Counter(v['channel'] for v in done.values()))}\n")
    print(f"- No words in the image at all: {len(no_text)}")
    print(f"- Usable listings: {len(use)}; of them new (not a repeat of a stored text listing): {len(new_use)}; "
          f"fit for a hedonic model: {len(ready)}")
    print(f"- Not usable: {n - len(use)} (classes: {dict(Counter(rows[k].listing_class for k in done if k not in use))})")
    for label, test in (("price", lambda p: p.sale_price_birr or p.rent_price_birr), ("size", dq.size_of),
                        ("bedrooms", lambda p: p.bedrooms), ("named place", lambda p: p.location not in (dq.UNKNOWN, dq.NOISE)),
                        ("known type", lambda p: p.property_type != "UNKNOWN")):
        print(f"- Usable listings with {label}: {sum(1 for k in use if test(rows[k]))} of {len(use)}")
    print(f"- Usable listings with both a price and a size: "
          f"{sum(1 for k in use if (rows[k].sale_price_birr or rows[k].rent_price_birr) and dq.size_of(rows[k]))}")
    print(f"- Sale / rent / both among usable: {dict(Counter(rows[k].intent for k in use))}")
    print(f"- Types among usable: {dict(Counter(rows[k].property_type for k in use))}")
    print(f"- Likely repeats of stored listings: {[(k, v) for k, v in repeats.items() if v]}")
    avg_in = sum(t["input"] for t in tokens) / n
    avg_out = sum(t["output"] + t["thinking"] for t in tokens) / n
    avg_s = sum(v["seconds"] for v in done.values()) / n
    print(f"- Tokens per image: {avg_in:.0f} in, {avg_out:.0f} out; seconds per image: {avg_s:.1f}\n")

    print("| Post | Channel | The image shows | Sale/rent | Type | Price (birr) | Size m² | Beds | Place | Usable |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for k in sorted(done, key=int):
        p, v = rows[k], done[k]
        price = p.sale_price_birr or p.rent_price_birr
        size = dq.size_of(p) or p.builtup_sqm or p.plot_sqm
        verdict = ("model-ready" if k in ready else "yes") if k in use else "no"
        if repeats.get(k):
            verdict += f" (repeat of {repeats[k]})"
        print(f"| {k} | {v['channel']} | {mask(v['shows']).replace('|', '/')} | {p.intent} | {p.property_type} | "
              f"{f'{price:,.0f}' if price else ''} | {f'{size:g}' if size else ''} | {p.bedrooms or ''} | "
              f"{dq.place_name(p.location)} | {verdict} |")


if __name__ == "__main__":
    main()
