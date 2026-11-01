r"""
review_earlier_deletions.py
---------------------------
Reviews the messages kept out before 26 October 2026 (tasks S21, S22). The 593 removed by the old
semantic_dedup.py were brought back in S22; those removed by the two older rules remain. Each is
parsed again and compared with the stored listings by the rules of dedup_strict.py. Read-only:
nothing is restored. Prints the numbers and writes data/review/earlier_deletions.html (contacts
masked; data/ is never committed) with the messages of the same-price rule that would fit the sale
sample and repeat no stored listing.

Usage:
    venv\Scripts\python.exe database\review_earlier_deletions.py
"""

import html
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "database"))

from sqlalchemy import create_engine, text  # noqa: E402

import data_quality as dq  # noqa: E402
import dedup_strict as ds  # noqa: E402
from accuracy_check import STYLE, mask  # noqa: E402
from etl_runner import build_processed_values  # noqa: E402
from run_pipeline import ValuationPipeline  # noqa: E402
from settings import DB_URL  # noqa: E402

OUT = BASE_DIR / "data" / "review" / "earlier_deletions.html"
GROUPS = {"duplicate: same text": "old rule: same text",
          "duplicate: same price": "old rule: same price, size and location"}
# Claude's reading of the first lines of the 38 (1 November 2026); the others look like different properties.
READING = {
    "10": "repeat: same advert as stored listing 1",
    "2717": "repeat at another price: stored listing 1036 (Megenagna, 134 m², 8th floor, 16,080,000); type should be apartment",
    "2732": "repeat at another price: stored listings 2735 and 7160 (4 Kilo Ambassador Mall, 123 m²)",
    "2972": "repeat: stored listing 5393, same broker (Bole Arabsa, 54 m², 1st floor, 4.5 million)",
    "45": "uncertain: maybe 5391 at another price (Ayat 49, 72 m², 10th floor)",
    "5391": "uncertain: maybe 45 at another price (Ayat 49, 72 m², 10th floor)",
    "1722": "uncertain: stored 1890 has the same size and price in Jemo 1, but on the 3rd floor",
    "1730": "uncertain: stored 5616 has the same size, price and floor, but in Jemo 1, not Jemo 3",
    "2593": "uncertain: stored 3003 and 1212 have the same size and price at Ayat, but G+3 and G+2; type should be building",
    "5889": "uncertain: stored 3791 has the same broker, size and price at Wesen, but on the 4th floor",
    "1302": "different; type should be condominium, not land",
    "2971": "different; type should be studio, not apartment",
    "5679": "different; part-built (2 slabs), stored as land",
    "5700": "different; part-built (3 slabs), stored as land",
}
NO_MATCH, PRICE_DIFFERS = "no match", "same advert, price differs"
STORED, OTHER = "repeat of a stored listing", "repeat of another removed message"


def parsed(messages):
    pipeline = ValuationPipeline()
    rows = []
    for m in messages:
        values, _, _ = build_processed_values(pipeline, m)
        values = {"floor_level": None, "bathrooms": None, "posted_at": m.posted_at, **values,
                  "raw_text": m.text, "topic_title": m.topic_title, "id": f"x{m.id}", "reason": m.reason}
        rows.append(SimpleNamespace(**values))
    return rows


def compare(stored, removed):
    """How each removed message relates to the stored listings, by the rules of dedup_strict.py."""
    pairs, price_changed = ds.find_pairs(list(stored) + removed)
    groups, _ = ds.groups_of(pairs)
    group_of = {i: g for g in groups for i in g}
    differs = {i for pair in price_changed for i in pair}
    status = {}
    for r in removed:
        g = group_of.get(r.id)
        if g and any(not i.startswith("x") for i in g):
            status[r.id] = STORED
        elif g and r.id != min(g, key=lambda i: int(i[1:])):
            status[r.id] = OTHER
        else:
            status[r.id] = PRICE_DIFFERS if r.id in differs else NO_MATCH
    return status


def fits_sale(r):
    return dq.is_usable(r) and r.intent in ("SALE", "MIXED") and dq.model_ready(r, "sale_price_birr")


def main() -> None:
    with create_engine(DB_URL).connect() as conn:
        stored = ds.load(conn)
        messages = conn.execute(text("""
            SELECT t.id, t.text, t.channel, t.posted_at, t.reply_to_top_id, t.topic_title, e.reason
            FROM processing_exclusions e JOIN telegram_listings t ON t.id = e.raw_id""")).fetchall()
    sample_now = len(dq.sale_sample(stored))
    rows = parsed([m for m in messages if m.reason.startswith(tuple(GROUPS))])
    for start, label in GROUPS.items():
        removed = [r for r in rows if r.reason.startswith(start)]
        status = compare(stored, removed)
        usable = [r for r in removed if dq.is_usable(r)]
        print(f"\n{label}: {len(removed)} messages, {len(usable)} usable "
              f"({dict(Counter(r.intent for r in usable))})")
        print(f"  all:     {dict(Counter(status.values()))}")
        print(f"  usable:  {dict(Counter(status[r.id] for r in usable))}")
        print(f"  fit the sale sample: {dict(Counter(status[r.id] for r in removed if fits_sale(r)))}")
        if start != "duplicate: same price":
            continue
        read = sorted((r for r in removed if fits_sale(r) and status[r.id] in (NO_MATCH, PRICE_DIFFERS)),
                      key=lambda r: int(r.id[1:]))
        print(f"  to read: {len(read)}; by type {dict(Counter(r.property_type for r in read))}")
        print(f"  sale sample now {sample_now}; if all these came back {sample_now + len(read)}")
        out = [f"<!doctype html><meta charset=utf-8><title>Earlier deletions</title><style>{STYLE}</style>",
               f"<h1>{len(read)} messages removed earlier that would fit the sale sample</h1>",
               "<p>Nothing has been restored. The values are what today's parser reads from each message. Contacts are "
               "masked.</p><table><tr><th>Message</th><th>Advert</th><th>What the parser reads</th><th>Rules</th><th>My reading</th></tr>"]
        for r in read:
            fmt = lambda v: f"{v:g} m²" if v is not None else "—"  # noqa: E731
            out.append(f"<tr><td>{r.id[1:]}<br><small>{html.escape(r.source_channel.rsplit('/', 1)[-1])}</small></td>"
                       f"<td class=ad>{html.escape(mask(r.raw_text))}</td>"
                       f"<td class=v>{r.property_type}<br>{html.escape(dq.place_name(r.location))}<br>{r.sale_price_birr:,.0f} birr<br>"
                       f"built-up {fmt(r.builtup_sqm)}<br>plot {fmt(r.plot_sqm)}<br>bedrooms {r.bedrooms if r.bedrooms is not None else '—'}</td>"
                       f"<td>{status[r.id]}</td><td>{html.escape(READING.get(r.id[1:], 'different property'))}</td></tr>")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(out) + "</table>", encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
