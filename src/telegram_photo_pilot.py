r"""
telegram_photo_pilot.py
-----------------------
The championallsites photo pilot (task S41, the owner's decision of 16 November 2026): 30 photos from the
forum topics of developers with projects in Bole, downloaded through the owner's existing Telegram login,
then read with Gemini. It is the only program allowed to download photos with the login, and only these 30:
more need the owner's approval again (CLAUDE.md, "Telegram account safety").

Safety, on top of src/telegram_safety.py (one program at a time, the existing login only, never a new one,
the shared daily cap of 150 requests, any warning from Telegram stops everything for the day):
  - never on a day of the scheduled scrape (the 1st, 4th, 7th, … of a month) or on a day the scraper ran;
  - at most 30 photo downloads a day and 30 in all, with a random pause of 60-180 seconds between two;
  - each download and each message lookup counts as one request toward the daily 150;
  - the first FloodWait or other warning stops the run at once, with no retry that day.

Steps (each can be run on its own; only --download uses Telegram):
    venv\Scripts\python.exe src\telegram_photo_pilot.py --plan                    choose the 30 (database only)
    venv\Scripts\python.exe src\telegram_photo_pilot.py --download                download them (Telegram)
    venv\Scripts\python.exe src\telegram_photo_pilot.py --read --allow-free-tier  read them with Gemini, report

Output (data/ is never committed): data/photo_pilot/plan.json, photos/, downloads.json, results.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

import settings
import telegram_safety as safety
from locations import PLACES, find_location

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "data" / "photo_pilot"
PLAN_FILE, LOG_FILE, RESULTS_FILE = OUT_DIR / "plan.json", OUT_DIR / "downloads.json", OUT_DIR / "results.json"
PHOTO_DIR = OUT_DIR / "photos"
GROUP = "championallsites"
PILOT_SIZE = 30                      # photos in the pilot, in all
PHOTOS_PER_DAY = 30
PAUSE_BETWEEN_PHOTOS = (60, 180)     # seconds, random
SEED = 2026_11_16


def scheduled_scrape_day(day: datetime) -> bool:
    """The app's task "Ollaa: scrape every 3 days" runs on the 1st, 4th, 7th, … of each month."""
    return (day.day - 1) % 3 == 0


def plan(conn) -> list[dict]:
    """30 photo posts, spread evenly over the championallsites topics whose place is in Bole."""
    rows = conn.execute(text("""
        SELECT t.id, t.message_id, t.topic_title FROM telegram_listings t
        JOIN processed_listings p ON p.id = t.id::text
        JOIN media_queue m ON m.channel = t.channel AND m.message_id = t.message_id AND m.file_type = 'IMAGE'
        WHERE t.channel ILIKE :group AND p.listing_class = 'MEDIA_PENDING' ORDER BY t.id"""), {"group": f"%{GROUP}%"}).fetchall()
    by_topic = defaultdict(list)
    for r in rows:
        code = find_location(r.topic_title or "")
        if code in PLACES and PLACES[code].sub_city == "Bole":
            by_topic[r.topic_title].append(r)
    rng = random.Random(SEED)
    for posts in by_topic.values():
        rng.shuffle(posts)
    chosen, i = [], 0
    while len(chosen) < PILOT_SIZE and any(i < len(p) for p in by_topic.values()):
        for topic in sorted(by_topic):
            if i < len(by_topic[topic]) and len(chosen) < PILOT_SIZE:
                r = by_topic[topic][i]
                chosen.append({"raw_id": r.id, "message_id": r.message_id, "topic": topic})
        i += 1
    return chosen


def load_log() -> dict:
    return json.loads(LOG_FILE.read_text(encoding="utf-8")) if LOG_FILE.exists() else {"downloaded": {}, "days": {}}


async def download(chosen: list[dict]) -> int:
    from telethon import TelegramClient
    from telethon.errors import RPCError

    log = load_log()
    today = safety.now().date().isoformat()
    todo = [c for c in chosen if str(c["raw_id"]) not in log["downloaded"]]
    if not todo:
        print("All 30 photos of the pilot are already downloaded. More need the owner's approval.")
        return 0
    if len(log["downloaded"]) >= PILOT_SIZE:
        raise safety.SafetyStop("The pilot's 30 photos are used up. More need the owner's approval.")
    if scheduled_scrape_day(safety.now()):
        raise safety.SafetyStop(f"Today ({today}) is a day of the scheduled scrape: no photo downloads today.")
    left_today = PHOTOS_PER_DAY - log["days"].get(today, 0)
    if left_today <= 0:
        raise safety.SafetyStop(f"Today's {PHOTOS_PER_DAY} photo downloads are used up.")
    session = safety.require_session_file()
    api_id, api_hash = safety.api_credentials()
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with safety.StepAside("photo pilot", hours=2):   # a running listener disconnects first
        budget = safety.DailyBudget()
        budget.new_day()
        budget.check_not_blocked()
        if budget.state.get("runs", 0):
            raise safety.SafetyStop("The scraper ran today: no photo downloads on the day of a scrape.")
        todo = todo[:min(left_today, safety.DAILY_REQUEST_CAP - budget.state["requests"] - 2)]
        if not todo:
            raise safety.SafetyStop("Today's Telegram requests are used up.")
        client = TelegramClient(str(session.with_suffix("")), api_id, api_hash, flood_sleep_threshold=safety.FLOOD_SLEEP_THRESHOLD)
        try:
            await safety.connect_with_existing_login(client, budget)
            try:
                try:
                    entity = client.session.get_input_entity(GROUP)
                except ValueError:
                    budget.spend()
                    entity = await client.get_input_entity(GROUP)
                    await safety.pause(safety.PAUSE_BETWEEN_REQUESTS)
                budget.spend()
                messages = await client.get_messages(entity, ids=[c["message_id"] for c in todo])
                for n, (c, msg) in enumerate(zip(todo, messages)):
                    if n:
                        await safety.pause(PAUSE_BETWEEN_PHOTOS)
                    if msg is None or not getattr(msg, "photo", None):
                        print(f"  {c['raw_id']}: no longer a photo on Telegram, skipped")
                        log["downloaded"][str(c["raw_id"])] = None
                        continue
                    budget.spend()
                    path = await client.download_media(msg, file=str(PHOTO_DIR / f"{c['raw_id']}.jpg"))
                    log["downloaded"][str(c["raw_id"])] = Path(path).name if path else None
                    log["days"][today] = log["days"].get(today, 0) + 1
                    LOG_FILE.write_text(json.dumps(log, indent=1), encoding="utf-8")
                    print(f"  {n + 1}/{len(todo)} {c['raw_id']} ({c['topic']}): saved; "
                          f"{budget.state['requests']} of {safety.DAILY_REQUEST_CAP} requests used today")
            except RPCError as e:
                raise safety.stop_after_warning(budget, e, "while downloading pilot photos")
            except (OSError, asyncio.TimeoutError) as e:
                raise safety.SafetyStop(f"Network problem ({type(e).__name__}): stopped; what was saved is kept.")
        finally:
            await client.disconnect()
            LOG_FILE.write_text(json.dumps(log, indent=1), encoding="utf-8")
    return len([v for v in log["downloaded"].values() if v])


def read_and_report(allow_free_tier: bool) -> None:
    from google import genai

    import payment_terms as pt
    from media_pilot import SECONDS_BETWEEN_CALLS, free_tier, read_image
    from processor import MILLION_RE, PRICE_PER_SQM_RE

    if not allow_free_tier:
        sys.exit("Pass --allow-free-tier: the owner allowed Gemini's free tier for the photo pilot (CLAUDE.md).")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    print("Gemini key on the free tier:", free_tier(client))
    log = load_log()
    results = json.loads(RESULTS_FILE.read_text(encoding="utf-8")) if RESULTS_FILE.exists() else {}
    plan_by_id = {str(c["raw_id"]): c for c in json.loads(PLAN_FILE.read_text(encoding="utf-8"))}
    for raw_id, name in log["downloaded"].items():
        if not name or raw_id in results:
            continue
        answer, tokens, seconds = read_image(client, PHOTO_DIR / name)
        results[raw_id] = {"topic": plan_by_id.get(raw_id, {}).get("topic"), **answer}
        RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {raw_id}: read ({seconds:.0f} s)")
        time.sleep(SECONDS_BETWEEN_CALLS)

    from accuracy_check import mask

    plan_word = re.compile(pt._DP_WORD + r"|ዙር|instal|ቀሪ\w*\s*ክፍያ|payment\s*plan|አከፋፈል", re.I)
    tests = {
        "price list": lambda t: len(MILLION_RE.findall(t)) + len(PRICE_PER_SQM_RE.findall(t)) >= 1,
        "payment plan": lambda t: bool(plan_word.search(t)),
        "cash discount": lambda t: bool(pt.discount_schedule(t) or (re.search(r"ቅናሽ|discount", t, re.I)
                                                                     and re.search(r"100\s*%|cash|ካሽ|ሙሉ\s*ክፍያ|ሙሉ\s*ለሚከፍ", t, re.I))),
        "handover date or period": lambda t: bool(pt.handover_date(t) or pt.handover_months(t) is not None),
    }
    found = {k: [i for i, r in results.items() if test(r.get("text") or "")] for k, test in tests.items()}
    print(f"\nPhotos read: {len(results)}; with any words: {sum(bool((r.get('text') or '').strip()) for r in results.values())}")
    for k, ids in found.items():
        print(f"  {k}: {len(ids)}")
    for k, ids in found.items():
        print(f"\n{k}, examples:")
        for i in ids[:5]:
            words = " / ".join(x.strip() for x in mask(results[i].get("text") or "").split("\n") if x.strip())
            print(f"  {i} ({results[i].get('topic')}): {words[:220]}")
    (OUT_DIR / "found.json").write_text(json.dumps(found, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--allow-free-tier", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.plan:
        if PLAN_FILE.exists():
            print(f"The plan exists already ({PLAN_FILE}); it is not redrawn.")
        else:
            with create_engine(settings.DB_URL).connect() as conn:
                chosen = plan(conn)
            PLAN_FILE.write_text(json.dumps(chosen, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Chosen: {len(chosen)} photos from {len({c['topic'] for c in chosen})} topics.")
    if args.download:
        chosen = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
        try:
            got = asyncio.run(download(chosen))
        except safety.SafetyStop as e:
            print(f"\nSTOPPED: {e}")
            return 2
        print(f"\nDownloaded so far: {got} of {len(chosen)}.")
    if args.read:
        read_and_report(args.allow_free_tier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
