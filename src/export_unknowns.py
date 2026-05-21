"""
export_unknowns.py
------------------
Quick utility to inspect unresolved listings:
  - Pulls raw_text + topic_title for rows where:
      processed_listings.property_type is UNKNOWN/NULL OR location = other_addis
  - Exports first 200 rows to unresolved_samples.csv
  - Prints the top 20 most frequent words in those rows

Run:
  python src/export_unknowns.py

Env:
  DB_URL (optional) defaults to local ollaa
"""

from __future__ import annotations

import csv
import os
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_CSV = BASE_DIR / "unresolved_samples.csv"

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:REMOVED_OLD_PASSWORD@localhost:5432/ollaa")
engine = create_engine(DB_URL)


WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)  # unicode "word" tokens, excludes underscores


def tokenize(s: str) -> list[str]:
    if not s:
        return []
    s = s.lower()
    return [w for w in WORD_RE.findall(s) if len(w) >= 2]


def main() -> None:
    query = text("""
        WITH joined AS (
            SELECT DISTINCT ON (pl.id)
                pl.id AS processed_id,
                pl.property_type,
                pl.location,
                pl.source_channel,
                pl.raw_text,
                COALESCE(tl.topic_title, '') AS topic_title
            FROM processed_listings pl
            LEFT JOIN telegram_listings tl
              ON pl.raw_text = tl.text
             AND pl.source_channel = tl.channel
            WHERE
                pl.property_type IS NULL
             OR pl.property_type = 'UNKNOWN'
             OR pl.location = 'other_addis'
            ORDER BY pl.id, tl.id DESC
        )
        SELECT processed_id, location, property_type, source_channel, raw_text, topic_title
        FROM joined
        ORDER BY processed_id
        LIMIT 200;
    """)

    with engine.begin() as conn:
        rows = conn.execute(query).mappings().all()

    # Export CSV
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["processed_id", "source_channel", "location", "property_type", "topic_title", "raw_text"],
        )
        w.writeheader()
        for r in rows:
            w.writerow({
                "processed_id": r.get("processed_id"),
                "source_channel": r.get("source_channel"),
                "location": r.get("location"),
                "property_type": r.get("property_type"),
                "topic_title": r.get("topic_title") or "",
                "raw_text": r.get("raw_text") or "",
            })

    # Word frequency
    counts: Counter[str] = Counter()
    for r in rows:
        blob = f"{r.get('topic_title') or ''} {r.get('raw_text') or ''}"
        counts.update(tokenize(blob))

    print(f"Wrote {len(rows)} rows to {OUT_CSV}")
    print("\nTop 20 words:")
    for word, cnt in counts.most_common(20):
        print(f"  {word:<20} {cnt}")


if __name__ == "__main__":
    main()

