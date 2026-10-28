r"""
telegram_scraper.py
-------------------
Reads the newest messages of the channels and forum groups in channels.py into
telegram_listings (text and metadata only). Photos and files are never downloaded with
the account: media are only noted in media_queue (file_path PENDING:...).

Account safety comes first (see "Telegram account safety" in CLAUDE.md and
telegram_safety.py):
- it uses the existing login file and stops if that is missing or no longer valid; it
  never logs in by itself;
- it never runs at the same time as the listener;
- it is slow: the 40 newest messages per channel, 10 forum topics of 20 messages per
  group, 45-120 seconds between channels, at most 150 requests and 2 runs a day;
- any warning from Telegram (a wait, an ended login, a limited account) stops the whole
  run and keeps Telegram unused until the next day.
Each channel is saved as soon as it is read, so a stop loses nothing already read.

Usage:
    venv\Scripts\python.exe src\telegram_scraper.py
"""

import asyncio
import sys

from sqlalchemy import create_engine, text
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.tl.functions.messages import GetForumTopicsRequest, GetHistoryRequest

import telegram_safety as safety
from channels import FORUM_GROUPS, REGULAR_CHANNELS
from settings import DB_URL

engine = create_engine(DB_URL)

# Longest time one channel or forum group may take (its pauses included) before the run stops.
CHANNEL_TIMEOUT = 180
FORUM_TIMEOUT = 15 * 60

INSERT_SQL = text("""
    INSERT INTO telegram_listings (channel, message_id, text, topic_title, posted_at, has_media)
    SELECT :channel, :message_id, :text, :topic_title, :posted_at, :has_media
    WHERE NOT EXISTS (
        SELECT 1 FROM telegram_listings
        WHERE channel = :channel AND message_id = :message_id
    )
""")

MEDIA_QUEUE_SQL = text("""
    INSERT INTO media_queue (channel, message_id, topic_title, file_path, file_type, posted_at)
    SELECT :channel, :message_id, :topic_title, :file_path, :file_type, :posted_at
    WHERE NOT EXISTS (
        SELECT 1 FROM media_queue
        WHERE channel = :channel AND message_id = :message_id
    )
""")


def channel_url(channel: str) -> str:
    return f"https://t.me/{channel.lstrip('@')}"


def detect_media_type(msg) -> str:
    """Identify media type from message object without downloading."""
    if msg.photo:
        return "IMAGE"
    if msg.document:
        mime = getattr(msg.document, 'mime_type', '') or ''
        if 'pdf' in mime.lower():
            return "PDF"
        return "DOCUMENT"
    return "UNKNOWN"


def ensure_tables() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS topic_title TEXT;"))
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE telegram_listings ADD COLUMN IF NOT EXISTS has_media BOOLEAN DEFAULT false;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS media_queue (
                id           SERIAL PRIMARY KEY,
                channel      TEXT NOT NULL,
                message_id   BIGINT NOT NULL,
                topic_title  TEXT,
                file_path    TEXT NOT NULL,
                file_type    TEXT NOT NULL,
                posted_at    TIMESTAMP WITH TIME ZONE,
                processed    BOOLEAN DEFAULT false,
                result_json  JSONB,
                processed_at TIMESTAMP WITH TIME ZONE,
                error_msg    TEXT,
                UNIQUE(channel, message_id)
            );
        """))


def save_messages(channel: str, messages, topic_title) -> int:
    """Store new messages (and note their media) in one transaction; returns how many were new."""
    inserted = 0
    with engine.begin() as conn:
        for msg in messages:
            has_media = bool(msg.photo or msg.document)
            text_content = msg.message or ("[MEDIA ONLY]" if has_media else None)
            if not text_content:
                continue
            result = conn.execute(INSERT_SQL, {
                "channel": channel_url(channel), "message_id": msg.id, "text": text_content,
                "topic_title": topic_title, "posted_at": msg.date, "has_media": has_media,
            })
            if result.rowcount == 0:
                continue
            inserted += 1
            if has_media:   # only a note: the file is never downloaded with the account
                conn.execute(MEDIA_QUEUE_SQL, {
                    "channel": channel_url(channel), "message_id": msg.id, "topic_title": topic_title,
                    "file_path": f"PENDING:{channel.lstrip('@')}_{msg.id}",
                    "file_type": detect_media_type(msg), "posted_at": msg.date,
                })
    return inserted


async def find_channel(client, budget, channel: str):
    """The channel's address. The login file remembers channels already read, so this
    usually needs no request; a channel read for the first time costs one."""
    try:
        return client.session.get_input_entity(channel)
    except ValueError:
        budget.spend()
        peer = await client.get_input_entity(channel)
        await safety.pause(safety.PAUSE_BETWEEN_REQUESTS)
        return peer


async def scrape_regular_channel(client, budget, channel: str) -> int:
    entity = await find_channel(client, budget, channel)
    budget.spend()
    history = await client(GetHistoryRequest(
        peer=entity, limit=safety.MESSAGES_PER_CHANNEL, offset_date=None,
        offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0,
    ))
    return save_messages(channel, history.messages, None)


async def scrape_forum_group(client, budget, channel: str) -> int:
    entity = await find_channel(client, budget, channel)
    budget.spend()
    topics = (await client(GetForumTopicsRequest(
        peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=safety.TOPICS_PER_GROUP,
    ))).topics[:safety.TOPICS_PER_GROUP]
    print(f"  {len(topics)} topics with the newest messages")
    total = 0
    for topic in topics:
        await safety.pause(safety.PAUSE_BETWEEN_TOPICS)
        budget.spend()
        messages = await client.get_messages(entity, limit=safety.MESSAGES_PER_TOPIC, reply_to=topic.id)
        title = getattr(topic, "title", "General")
        new = save_messages(channel, messages, title)
        print(f"    {title}: {new} new")
        total += new
    return total


async def scrape(client, budget) -> None:
    sources = [(c, False) for c in REGULAR_CHANNELS] + [(g, True) for g in FORUM_GROUPS]
    for i, (channel, forum) in enumerate(sources):
        if i:
            await safety.pause(safety.PAUSE_BETWEEN_CHANNELS)
        print(f"{'Forum group' if forum else 'Channel'} {channel}")
        try:
            reader = scrape_forum_group if forum else scrape_regular_channel
            new = await asyncio.wait_for(reader(client, budget, channel), FORUM_TIMEOUT if forum else CHANNEL_TIMEOUT)
            print(f"  {new} new messages")
        except (*safety.CHANNEL_PROBLEMS, ValueError) as e:   # left, renamed or private: skip this one only
            print(f"  skipped: {type(e).__name__}")
        except RPCError as e:
            raise safety.stop_after_warning(budget, e, f"while reading {channel}")
        except (OSError, asyncio.TimeoutError) as e:
            raise safety.SafetyStop(f"Network problem while reading {channel} ({type(e).__name__}): the run "
                                    "stopped. Try again later.")


async def main() -> int:
    try:
        session = safety.require_session_file()      # before anything else: no login file, no run
        api_id, api_hash = safety.api_credentials()
        with safety.TelegramLock("scraper"):
            budget = safety.DailyBudget()
            budget.start_scraper_run()
            ensure_tables()
            client = TelegramClient(str(session.with_suffix("")), api_id, api_hash,
                                    flood_sleep_threshold=safety.FLOOD_SLEEP_THRESHOLD)
            try:
                await safety.connect_with_existing_login(client, budget)
                await scrape(client, budget)
            finally:
                await client.disconnect()
    except safety.SafetyStop as e:
        print(f"\nSTOPPED: {e}")
        return 2
    print("\nScraping complete.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
