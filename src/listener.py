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
The ETL (for any message whose live processing failed), the units table and the views follow daily
(listener_service.py); the full repeat review stays in the attended scrape run. Each day's counts and warnings: listener_health.py.

Self-healing after a power cut, sleep or no internet (the owner's decision of 20 November 2026): the listener notes
about once a minute that it is connected and the internet answers (listener_health.mark_alive). Every gap of
10 minutes or more goes into the day's health log. After a gap of more than 2 hours it makes ONE catch-up read while it
goes on listening: for each channel and group in channels.py, only the messages posted since the last one saved (at
most the 40 newest), one request each, with the scraper's pauses between channels. It counts as one of the day's 2
scraper runs, is refused when those or the day's 150 requests are used up or Telegram use is paused, and any warning
from Telegram stops it and the listener at once. Each message it reads goes through the same steps as a live one.

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
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.functions.messages import GetForumTopicsByIDRequest, GetHistoryRequest

import dedup_strict
import etl_runner
import listener_health as health
import telegram_safety as safety
import telegram_scraper as scraper
from channels import FORUM_GROUPS, REGULAR_CHANNELS, configured_name, is_forum_group

TITLES_FILE = Path(__file__).resolve().parents[1] / "data" / "listener" / "topic_titles.json"
STEP_ASIDE_CHECK = 5     # seconds between two looks at a step-aside request
ALIVE_EVERY = 60         # seconds between two "still connected" marks
GAP_TO_LOG = 10 * 60     # a gap this long or longer goes into the health log
CATCH_UP_AFTER = 2 * 3600   # a gap longer than this brings one catch-up read
SOURCES = REGULAR_CHANNELS + FORUM_GROUPS


def online() -> bool:
    """The internet answers (a connection to Telegram's web address; no account, no request)."""
    try:
        socket.create_connection(("t.me", 443), timeout=10).close()
        return True
    except OSError:
        return False


def last_saved_ids() -> dict:
    """For each channel and group in channels.py, the newest message id already saved (0 for none)."""
    with scraper.engine.connect() as conn:
        rows = conn.execute(text("SELECT channel, MAX(message_id) FROM telegram_listings GROUP BY channel")).all()
    saved = {ch: int(m) for ch, m in rows if m is not None}
    return {name: saved.get(scraper.channel_url(name), 0) for name in SOURCES}


def last_saved_at() -> Optional[datetime]:
    """When the newest message was saved (by the listener or the scraper): the start of the gap when there is no
    "alive" mark yet (the first start of this code, or the mark was lost)."""
    with scraper.engine.connect() as conn:
        newest = conn.execute(text("SELECT MAX(created_at) FROM telegram_listings")).scalar()
    return newest.replace(tzinfo=safety.ETHIOPIA) if newest else None   # the database keeps Addis Ababa time


def hours(seconds: float) -> str:
    return f"{int(seconds // 3600)} h {int(seconds % 3600 // 60)} min"


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
        key = f"{getattr(entity, 'id', None) or getattr(entity, 'channel_id', None)}:{topic_id}"   # a chat or its address
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
    catching_up: list = []    # the catch-up task, once one has started (one per gap)

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
        await process(name, entity, msg, forum=bool(getattr(entity, "forum", False)))

    async def process(name: str, entity, msg, forum: bool, caught_up: bool = False) -> dict:
        """One message from a chat in channels.py, live or from the catch-up: the same steps for both."""
        topic = topic_id_of(msg) if forum else None
        topic_title = await titles.get(client, budget, entity, topic) if topic else None
        try:
            async with one_at_a_time:
                done = await asyncio.to_thread(store, pipeline, name, msg, topic_title)
        except Exception as e:   # the database or the parser: this message only; the daily ETL re-reads it
            health.add(errors=1)
            health.note("error", f"{name} message {msg.id}: {type(e).__name__}: {e}")
            return {"saved": False}
        health.add(saved=int(done["saved"]), listings_added=int(bool(done.get("listing"))),
                   rentals_added=int(bool(done.get("rental"))), repeats_removed=int(bool(done.get("repeat_of"))),
                   media_queued=int(bool(done.get("saved") and done.get("media"))),
                   caught_up=int(bool(caught_up and done["saved"])))
        if done.get("rental_error"):
            health.add(errors=1)
            health.note("error", f"{name} message {msg.id}: rent row: {done['rental_error']}")
        if done["saved"]:
            what = ("listing added" if done.get("listing") else
                    f"repeat of listing {done['repeat_of']}, removed" if done.get("repeat_of") else "no new listing")
            print(f"{safety.now():%H:%M} {'catch-up ' if caught_up else ''}{name} {msg.id}"
                  f"{' (' + topic_title + ')' if topic_title else ''}: {what}", flush=True)
        return done

    async def catch_up(off_seconds: float) -> None:
        """ONE read after a gap of more than 2 hours: per chat, the messages since the last one saved."""
        try:
            budget.start_scraper_run()   # one of the day's 2 runs; refused when used up, at the cap, or paused
        except safety.SafetyStop as e:
            health.note("catch-up", f"no catch-up after {hours(off_seconds)} off: {e}")
            print(f"{safety.now():%H:%M} No catch-up: {e}", flush=True)
            return
        health.add(catch_ups=1)
        health.catch_up_running(True)
        health.note("catch-up", f"catch-up started after {hours(off_seconds)} off: {len(SOURCES)} channels and "
                                "groups, the messages posted since the last one saved")
        print(f"{safety.now():%H:%M} Catch-up after {hours(off_seconds)} off ({len(SOURCES)} chats)", flush=True)
        requests_before, read, saved, skipped, full = budget.state["requests"], 0, 0, [], []
        why = "done"
        try:
            since = await asyncio.to_thread(last_saved_ids)
            for i, name in enumerate(SOURCES):
                if i:
                    await safety.pause(safety.PAUSE_BETWEEN_CHANNELS)
                if stops or ended:
                    why = "interrupted (the listener ended)"
                    break
                try:
                    entity = await asyncio.wait_for(scraper.find_channel(client, budget, name), scraper.CHANNEL_TIMEOUT)
                    budget.spend()
                    history = await asyncio.wait_for(client(GetHistoryRequest(
                        peer=entity, limit=safety.MESSAGES_PER_CHANNEL, offset_date=None, offset_id=0, max_id=0,
                        min_id=since.get(name, 0), add_offset=0, hash=0)), scraper.CHANNEL_TIMEOUT)
                except (*safety.CHANNEL_PROBLEMS, ValueError) as e:   # left, renamed or private: skip this one only
                    skipped.append(f"{name} ({type(e).__name__})")
                    continue
                read += 1
                messages = [m for m in history.messages
                            if getattr(m, "action", None) is None and m.id > since.get(name, 0)]   # no service notes
                if len(history.messages) >= safety.MESSAGES_PER_CHANNEL:
                    full.append(name)
                for msg in sorted(messages, key=lambda m: m.id):   # oldest first, as they were posted
                    saved += bool((await process(name, entity, msg, forum=is_forum_group(name), caught_up=True))["saved"])
        except RPCError as e:   # any warning from Telegram: everything stops at once, no retry
            if not (stops or ended):
                stops.append(safety.stop_after_warning(budget, e, "during the catch-up read"))
                asyncio.get_running_loop().create_task(client.disconnect())
            why = f"stopped by a warning from Telegram ({type(e).__name__})"
        except safety.SafetyStop as e:   # today's 150 requests reached: the catch-up stops, listening goes on
            why = f"stopped: {e}"
        except (OSError, asyncio.TimeoutError) as e:
            why = ("interrupted: the listener stepped aside or ended" if (stops or ended)
                   else f"stopped by a connection problem ({type(e).__name__})")
        except asyncio.CancelledError:
            why = "interrupted: the listener ended"
            raise
        finally:
            health.catch_up_running(False)
            health.catch_up_ended()   # the days checked before it are checked again against the web pages
            health.note("catch-up", f"catch-up {why}: {read} of {len(SOURCES)} chats read, {saved} new messages saved, "
                                    f"{budget.state['requests'] - requests_before} requests"
                                    + (f"; skipped: {', '.join(skipped)}" if skipped else "")
                                    + (f"; 40 or more new in {', '.join(full)}: older ones may be missing" if full else ""))
            print(f"{safety.now():%H:%M} Catch-up {why}: {saved} new messages saved", flush=True)

    def gap(began: datetime, came_back: datetime) -> None:
        """Logs a gap of 10 minutes or more; after more than 2 hours, starts the one catch-up read."""
        off = (came_back - began).total_seconds()
        if off < GAP_TO_LOG:
            return
        health.add(gaps=1)
        health.note("gap", f"the listener was off from {began:%d %b %H:%M} to {came_back:%d %b %H:%M} ({hours(off)})")
        if off > CATCH_UP_AFTER and not (stops or ended) and not any(not t.done() for t in catching_up):
            catching_up.append(asyncio.get_running_loop().create_task(catch_up(off)))

    async def watch(last_seen: datetime) -> None:
        """Disconnects when the scraper or the photo pilot asks, or when the test time is up; about once a minute
        marks that the listener is connected and the internet answers, so a gap (sleep, power cut, no internet)
        is noticed also while the program kept running."""
        loop = asyncio.get_running_loop()
        end = loop.time() + minutes * 60 if minutes else None
        next_mark = loop.time() + ALIVE_EVERY
        while not stops:
            by = safety.step_aside_request()
            if by or (end and loop.time() >= end):
                ended.append(f"stepped aside for the {by}" if by else "the test time is up")
                await client.disconnect()
                return
            if loop.time() >= next_mark:
                next_mark = loop.time() + ALIVE_EVERY
                if await asyncio.to_thread(online):
                    seen = safety.now()
                    if (seen - last_seen).total_seconds() > ALIVE_EVERY + GAP_TO_LOG:
                        gap(last_seen, seen)
                    last_seen = seen
                    health.mark_alive()
            await asyncio.sleep(STEP_ASIDE_CHECK)

    was_alive = health.last_alive()   # before this start: when the listener was last connected
    if was_alive is None:   # no mark yet: the gap began when the newest message was saved
        try:
            was_alive = await asyncio.to_thread(last_saved_at)
        except Exception as e:
            print(f"Could not read when the last message was saved ({type(e).__name__}): no gap check", flush=True)
    try:
        budget.spend()   # connecting counts as a request
        await safety.connect_with_existing_login(client, budget)
        print(f"{safety.now():%Y-%m-%d %H:%M} Listening for new messages... (Ctrl+C stops the listener)", flush=True)
        came_back = safety.now()
        health.mark_alive()
        watcher = asyncio.get_running_loop().create_task(watch(came_back))
        if was_alive:
            gap(was_alive, came_back)
        await client.run_until_disconnected()
        watcher.cancel()
    except RPCError as e:
        raise safety.stop_after_warning(budget, e, "while the listener was running")
    except (OSError, asyncio.TimeoutError) as e:
        raise safety.SafetyStop(f"The connection to Telegram was lost ({type(e).__name__}): the listener "
                                "stopped. Start it again later.")
    finally:
        for task in catching_up:
            if not task.done():
                task.cancel()
        for task in catching_up:
            try:
                await task
            except BaseException:   # its end is already in the health log
                pass
        if not stops:
            health.mark_alive()
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
