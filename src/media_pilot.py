r"""
media_pilot.py
--------------
Pilot (task S15): read photo-only posts (MEDIA_PENDING) with Gemini and put the
words found in each image through the same parser as every other listing.

Gemini only copies the words and numbers it sees (Amharic and English, as written)
and says in one sentence what the image shows. The copied text then goes through
etl_runner.build_processed_values, so price, size, bedrooms, place (location codes
from locations.py), type and sale/rent follow exactly the text rules.

Read-only for the database: nothing is written to processed_listings or media_queue.
Only posts whose image is already on this laptop (data/images/telegram) are used (54 of
those 747 files are empty, from an interrupted download, and are skipped); album extras
(a photo posted together with a captioned listing) are left out.

Usage:
    venv\Scripts\python.exe src\media_pilot.py --sample 50

Output (data/ is never committed: the copied text can hold phone numbers):
    data/media_pilot/results.json   one entry per post; re-running skips posts already read
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from google import genai
from google.genai import types
from sqlalchemy import create_engine, text

import settings
from etl_runner import build_processed_values
from run_pipeline import ValuationPipeline

BASE_DIR = Path(__file__).resolve().parents[1]
IMAGE_DIR = BASE_DIR / "data" / "images" / "telegram"
OUT_FILE = BASE_DIR / "data" / "media_pilot" / "results.json"
MODEL_ID = "gemini-3.1-flash-lite"
SECONDS_BETWEEN_CALLS = 5          # at most 12 requests a minute, inside the free tier's limit
SEED = 2026_10_28

PROMPT = """This image comes from an Ethiopian real-estate Telegram channel (Addis Ababa).
Return JSON with two fields:
- "text": every word and number visible in the image, copied exactly as written, line by line,
  in its own script (Amharic in Ge'ez letters, English as English). Do not translate, correct,
  summarise or add anything. Write <phone> instead of any phone number and <user> instead of
  any @username. Use an empty string if the image has no text.
- "shows": one short English sentence saying what the image shows, for example "a flyer for a
  3-bedroom apartment for sale with price and size" or "a photo of a kitchen, no text".
  Do not include phone numbers or names of people."""

SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={"text": types.Schema(type=types.Type.STRING), "shows": types.Schema(type=types.Type.STRING)},
    required=["text", "shows"],
)

# Album extras: a photo posted at the same second as a text listing a few messages away.
CANDIDATES_SQL = text("""
    SELECT t.id, t.channel, t.message_id, t.posted_at, t.reply_to_top_id, t.topic_title, p.location
    FROM processed_listings p JOIN telegram_listings t ON t.id::text = p.id
    WHERE p.listing_class = 'MEDIA_PENDING'
      AND NOT EXISTS (
        SELECT 1 FROM telegram_listings s JOIN processed_listings q ON q.id = s.id::text
        WHERE s.channel = t.channel AND abs(s.message_id - t.message_id) <= 10
          AND s.posted_at = t.posted_at AND q.listing_class <> 'MEDIA_PENDING')
    ORDER BY t.id
""")


def image_path(row) -> Path:
    return IMAGE_DIR / f"{row.channel.rstrip('/').rsplit('/', 1)[-1]}_{row.message_id}.jpg"


def choose(rows, n):
    """Every post from the smaller channels, then a seeded random choice from the largest one."""
    by_channel = {}
    for r in rows:
        by_channel.setdefault(r.channel, []).append(r)
    biggest = max(by_channel, key=lambda c: len(by_channel[c]))
    chosen = [r for c, rs in by_channel.items() if c != biggest for r in rs][:n]
    rest = by_channel[biggest]
    random.Random(SEED).shuffle(rest)
    return sorted(chosen + rest[: n - len(chosen)], key=lambda r: r.id)


def read_image(client, path: Path) -> tuple[dict, dict, float]:
    """(Gemini's answer, token counts, seconds), retrying when the service is busy."""
    for attempt in range(5):
        started = time.time()
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"), PROMPT],
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                                                   response_schema=SCHEMA),
            )
            usage = response.usage_metadata
            tokens = {"input": usage.prompt_token_count or 0, "output": usage.candidates_token_count or 0,
                      "thinking": getattr(usage, "thoughts_token_count", 0) or 0}
            return json.loads(response.text), tokens, time.time() - started
        except Exception as e:   # 429 (too many requests), 503 (busy) or no connection: wait and try again
            busy = any(code in str(e) for code in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"))
            if (busy or "Connect" in type(e).__name__ or "Timeout" in type(e).__name__) and attempt < 4:
                time.sleep(2 ** attempt * 10)
                continue
            raise


def parse(pipeline, row, copied_text):
    """The listing the copied text gives, with the same code as the ETL."""
    raw = SimpleNamespace(id=row.id, text=copied_text or "[MEDIA ONLY]", channel=row.channel,
                          posted_at=row.posted_at, reply_to_top_id=row.reply_to_top_id, topic_title=row.topic_title)
    values, _, _ = build_processed_values(pipeline, raw)
    return {k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in values.items()
            if k in ("intent", "listing_class", "property_type", "location", "city", "sale_price_birr",
                     "rent_price_birr", "builtup_sqm", "plot_sqm", "bedrooms", "bathrooms", "price_currency",
                     "floor_level", "finish_state")}


def main() -> None:
    ap = argparse.ArgumentParser(description="Read photo-only posts with Gemini (pilot).")
    ap.add_argument("--sample", type=int, default=50)
    args = ap.parse_args()

    with create_engine(settings.DB_URL).connect() as conn:
        rows = [r for r in conn.execute(CANDIDATES_SQL) if image_path(r).exists() and image_path(r).stat().st_size]
    chosen = choose(rows, args.sample)
    print(f"candidates with a (non-empty) image on this laptop: {len(rows)}; chosen: {len(chosen)}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    results = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {}
    # Entries of posts no longer chosen (e.g. an empty image file) are dropped.
    results = {k: v for k, v in results.items() if k in {str(r.id) for r in chosen}}
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    pipeline = ValuationPipeline()

    for i, row in enumerate(chosen, 1):
        key = str(row.id)
        if key in results and "error" not in results[key]:
            continue
        try:
            answer, tokens, seconds = read_image(client, image_path(row))
            copied = re.sub(r"\n{3,}", "\n\n", answer.get("text", "")).strip()
            results[key] = {
                "channel": row.channel.rsplit("/", 1)[-1], "message_id": row.message_id,
                "image": image_path(row).name, "stored_location": row.location,
                "text": copied, "shows": answer.get("shows", ""), "tokens": tokens, "seconds": round(seconds, 1),
                "parsed": parse(pipeline, row, copied),
            }
            print(f"{i:>3}/{len(chosen)} {key}: {tokens['input']}+{tokens['output']} tokens, {seconds:.1f}s")
        except Exception as e:
            results[key] = {"channel": row.channel.rsplit("/", 1)[-1], "message_id": row.message_id,
                            "error": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"{i:>3}/{len(chosen)} {key}: ERROR {type(e).__name__}")
        OUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"wrote {OUT_FILE.relative_to(BASE_DIR)} ({len(results)} posts)")


if __name__ == "__main__":
    main()
