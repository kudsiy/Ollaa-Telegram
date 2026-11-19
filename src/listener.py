r"""
listener.py
-----------
The live listener (Phase 1 of ROADMAP.md): the main way data comes in. It saves new messages from the
channels and groups in channels.py only; private chats and every other chat are ignored
(tests/test_listener_privacy.py).

Each new message goes into the database at once, by the same code as the scraper and the ETL:
  1) the raw message into telegram_listings, under the same channel name, with its forum topic's title,
     and a note in media_queue for a photo, video or PDF (never downloaded: Phase 3 reads them);
  2) etl_runner.save_listing: the parser with the channel rules, the listing, and its rental row;
  3) dedup_strict.remove_new_repeat: a new listing that clearly repeats an older advert from the same
     channel or agent is removed at once (the owner's standing rule).
The repair steps, the full repeat check, the units table and the views follow in the daily run of
`run_all.py --skip-scrape` (listener_service.py). Each day's counts and warnings: listener_health.py.

Account safety (see "Telegram account safety" in CLAUDE.md and telegram_safety.py):
- it uses the existing login file and stops if that is missing or no longer valid; it never logs in;
- it never runs at the same time as the scraper or the photo pilot (one lock); when one of them asks
  (telegram_safety.StepAside), it disconnects within seconds and does not start again until it is done;
- it only listens; each start and each forum topic's title (asked once, then remembered) count toward
  the daily cap of 150 requests;
- any warning from Telegram stops it at once and keeps Telegram unused until the next day.

Run (listener_service.py runs it all day; by hand for a test):
  venv\Scripts\python.exe src\listener.py      (Ctrl+C stops it)
  venv\Scripts\python.exe src\listener.py --minutes 60
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.functions.messages import GetForumTopicsByIDRequest

import dedup_strict
import etl_runner
import listener_health as health
import telegram_safety as safety
import telegram_scraper as scraper
from channels import configured_name

TITLES_FILE = Path(__file__).resolve().parents[1] / "data" / "listener" / "topic_titles.json"
STEP_ASIDE_CHECK = 5     # seconds between two looks at a step-aside request


def topic_id_of(msg) -> Optional[int]:
    """The forum topic a message belongs to (None in the "General" topic or outside a forum)."""
    reply = getattr(msg, "reply_to", None)
    if reply is None:
        return None
    top = getattr(reply, "reply_to_top_id", None)
    if top:
        return int(top)
    return int(reply.reply_to_msg_id) if getattr(reply, "forum_topic", False) and getattr(reply, "reply_to_msg_id", None) else None


class TopicTitles:
    """Forum topic titles, each asked from Telegram once and remembered in a file (no request after a restart)."""

    def __init__(self):
        try:
            self.known = json.loads(TITLES_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.known = {}

    async def get(self, client, budget: safety.DailyBudget, entity, topic_id: int) -> Optional[str]:
        key = f"{getattr(entity, 'id', None)}:{topic_id}"
        if key not in self.known:
            if not budget.can_spend():
                return None   # today's request limit is used up: the message is saved without its topic
            budget.spend()
            try:
                result = await client(GetForumTopicsByIDRequest(peer=entity, topics=[topic_id]))
            except (OSError, asyncio.TimeoutError):
                return None
            topics = getattr(result, "topics", None) or []
            self.known[key] = getattr(topics[0], "title", None) if topics else None
            TITLES_FILE.parent.mkdir(parents=True, exist_ok=True)
            TITLES_FILE.write_text(json.dumps(self.known, ensure_ascii=False, indent=1), encoding="utf-8")
        return self.known[key]


def store(pipeline, name: str, msg, topic_title: Optional[str]) -> dict:
    """The database part (no Telegram): raw message and media note as the scraper saves them, then the
    listing by the ETL's own code, then the live repeat check. Returns what happened."""
    if not scraper.save_messages(name, [msg], topic_title):
        return {"saved": False}
    media = bool(getattr(msg, "photo", None) or getattr(msg, "document", None))
    with etl_runner.engine.connect() as conn:
        row = conn.execute(text(etl_runner.RAW_ROWS_SQL + " AND t.channel = :c AND t.message_id = :m"),
                           {"c": scraper.channel_url(name), "m": msg.id}).fetchone()
    if row is None:   # a message kept out on purpose (processing_exclusions)
        return {"saved": True, "media": media, "listing": False}
    added, rental, rental_error = etl_runner.save_listing(pipeline, row)
    repeat_of = dedup_strict.remove_new_repeat(etl_runner.engine, str(row.id)) if added else None
    return {"saved": True, "media": media, "listing": added and not repeat_of, "rental": rental and not repeat_of,
            "repeat_of": repeat_of, "rental_error": rental_error, "raw_id": row.id}


async def listen(session: Path, api_id: int, api_hash: str, budget: safety.DailyBudget,
                 minutes: Optional[float] = None) -> str:
    """Listens until a stop; returns why it ended normally ("stepped aside …", "time is up")."""
    from run_pipeline import ValuationPipeline

    pipeline = ValuationPipeline()
    scraper.ensure_tables()
    titles = TopicTitles()
    client = TelegramClient(str(session.with_suffix("")), api_id, api_hash,
                            flood_sleep_threshold=safety.FLOOD_SLEEP_THRESHOLD)
    stops: list = []          # the stop a message ran into, if any
    ended: list = []          # why the listener ended without a stop
    one_at_a_time = asyncio.Lock()   # the database steps of two messages never overlap

    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event) -> None:
        if stops or ended:
            return
        try:
            await save_message(event)
        except RPCError as e:
            if isinstance(e, safety.CHANNEL_PROBLEMS):
                return
            stops.append(safety.stop_after_warning(budget, e, "while the listener was running"))
            asyncio.get_running_loop().create_task(client.disconnect())   # ends run_until_disconnected
        except safety.SafetyStop as e:   # today's requests used up while asking for a chat
            stops.append(e)
            asyncio.get_running_loop().create_task(client.disconnect())

    async def save_message(event: events.NewMessage.Event) -> None:
        msg = event.message
        # Privacy: save nothing from private chats or from chats not in channels.py.
        if not msg or event.is_private:
            return
        entity = getattr(event, "chat", None)
        if entity is None:   # not sent along with the message: asking for it is a request
            if not budget.can_spend():
                return
            budget.spend()
            try:
                entity = await event.get_chat()
            except (OSError, asyncio.TimeoutError, ValueError):
                return
        name = configured_name(entity)
        if name is None:
            return
        health.add(received=1)
        topic = topic_id_of(msg) if getattr(entity, "forum", False) else None
        topic_title = await titles.get(client, budget, entity, topic) if topic else None
        try:
            async with one_at_a_time:
                done = await asyncio.to_thread(store, pipeline, name, msg, topic_title)
        except Exception as e:   # the database or the parser: this message only; the weekly catch-up re-reads it
            health.add(errors=1)
            health.note("error", f"{name} message {msg.id}: {type(e).__name__}: {e}")
            return
        health.add(saved=int(done["saved"]), listings_added=int(bool(done.get("listing"))),
                   rentals_added=int(bool(done.get("rental"))), repeats_removed=int(bool(done.get("repeat_of"))),
                   media_queued=int(bool(done.get("saved") and done.get("media"))))
        if done.get("rental_error"):
            health.add(errors=1)
            health.note("error", f"{name} message {msg.id}: rent row: {done['rental_error']}")
        if done["saved"]:
            what = ("listing added" if done.get("listing") else
                    f"repeat of listing {done['repeat_of']}, removed" if done.get("repeat_of") else "no new listing")
            print(f"{safety.now():%H:%M} {name} {msg.id}{' (' + topic_title + ')' if topic_title else ''}: {what}", flush=True)

    async def watch() -> None:
        """Disconnects when the scraper or the photo pilot asks, or when the test time is up."""
        loop = asyncio.get_running_loop()
        end = loop.time() + minutes * 60 if minutes else None
        while not stops:
            by = safety.step_aside_request()
            if by or (end and loop.time() >= end):
                ended.append(f"stepped aside for the {by}" if by else "the test time is up")
                await client.disconnect()
                return
            await asyncio.sleep(STEP_ASIDE_CHECK)

    try:
        budget.spend()   # connecting counts as a request
        await safety.connect_with_existing_login(client, budget)
        print(f"{safety.now():%Y-%m-%d %H:%M} Listening for new messages... (Ctrl+C stops the listener)", flush=True)
        watcher = asyncio.get_running_loop().create_task(watch())
        await client.run_until_disconnected()
        watcher.cancel()
    except RPCError as e:
        raise safety.stop_after_warning(budget, e, "while the listener was running")
    except (OSError, asyncio.TimeoutError) as e:
        raise safety.SafetyStop(f"The connection to Telegram was lost ({type(e).__name__}): the listener "
                                "stopped. Start it again later.")
    finally:
        await client.disconnect()
    if stops:
        raise stops[0]
    return ended[0] if ended else "disconnected from Telegram"


async def main(minutes: Optional[float] = None) -> int:
    try:
        session = safety.require_session_file()   # before anything else: no login file, no listener
        api_id, api_hash = safety.api_credentials()
        if safety.step_aside_request():
            raise safety.SafetyStop(f"The {safety.step_aside_request()} is using Telegram: the listener waits.")
        with safety.TelegramLock("listener"):
            budget = safety.DailyBudget()
            budget.check_not_blocked()
            health.add(starts=1)
            why = await listen(session, api_id, api_hash, budget, minutes)
    except safety.SafetyStop as e:
        print(f"\nSTOPPED: {e}", flush=True)
        health.note("warning" if "warning" in str(e) or "no longer valid" in str(e) else "info", f"stopped: {e}")
        return 2
    print(f"Listener ended: {why}.", flush=True)
    health.note("info", f"ended: {why}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, help="listen this long, then stop (a test)")
    args = ap.parse_args()
    try:
        sys.exit(asyncio.run(main(args.minutes)))
    except KeyboardInterrupt:
        print("\nListener stopped (Ctrl+C).")
