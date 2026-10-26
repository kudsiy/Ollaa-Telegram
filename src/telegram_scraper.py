from pathlib import Path
import os
import asyncio
import sys
import random
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, GetForumTopicsRequest
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError,
    FloodWaitError, SessionRevokedError,
)

from channels import FORUM_GROUPS, REGULAR_CHANNELS
from settings import DB_URL

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_session_name() -> Path:
    override = os.getenv("TG_SESSION_NAME")
    if override:
        session_name = Path(override)
        if not session_name.is_absolute():
            session_name = BASE_DIR / session_name
        return session_name.with_suffix("") if session_name.suffix == ".session" else session_name

    session_dir = BASE_DIR / "data" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)

    preferred = session_dir / "ollaa_session"
    legacy    = BASE_DIR / "ollaa_session"

    if preferred.with_suffix(".session").exists():
        return preferred
    if legacy.with_suffix(".session").exists():
        return legacy
    return preferred


api_id   = int(require_env("TG_API_ID"))
api_hash = require_env("TG_API_HASH")
phone    = os.getenv("TG_PHONE")

FETCH_LIMIT  = int(os.getenv("TG_FETCH_LIMIT", "720"))
SESSION_NAME = resolve_session_name()
SESSION_FILE = SESSION_NAME.with_suffix(".session")

engine = create_engine(DB_URL)

# ── Insert: text + metadata only ─────────────────────────────────
# MEDIA DOWNLOADING IS INTENTIONALLY REMOVED.
# Downloading files during scraping switches Telegram data centers,
# which triggers automatic session revocation on flagged accounts.
# Media references are logged to media_queue with file_path=PENDING:...
# A separate media_downloader.py will fetch files slowly and safely.
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


async def safe_sleep(seconds: float) -> None:
    try:
        await asyncio.sleep(seconds)
    except asyncio.CancelledError:
        pass


async def scrape_regular_channel(client, conn, channel: str) -> int:
    inserted = 0
    try:
        entity = await client.get_entity(channel)
        messages = await client(GetHistoryRequest(
            peer=entity,
            limit=FETCH_LIMIT,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=0,
            add_offset=0,
            hash=0,
        ))

        for msg in messages.messages:
            has_media    = bool(msg.photo or msg.document)
            text_content = msg.message or ("[MEDIA ONLY]" if has_media else None)

            if not text_content:
                continue

            result = conn.execute(INSERT_SQL, {
                "channel":     channel_url(channel),
                "message_id":  msg.id,
                "text":        text_content,
                "topic_title": None,
                "posted_at":   msg.date,
                "has_media":   has_media,
            })

            if result.rowcount == 0:
                continue

            inserted += 1

            # Log media reference only — no downloading
            if has_media:
                try:
                    conn.execute(MEDIA_QUEUE_SQL, {
                        "channel":     channel_url(channel),
                        "message_id":  msg.id,
                        "topic_title": None,
                        "file_path":   f"PENDING:{channel.lstrip('@')}_{msg.id}",
                        "file_type":   detect_media_type(msg),
                        "posted_at":   msg.date,
                    })
                except Exception:
                    pass

    except SessionRevokedError:
        print(f"\n  CRITICAL: Session revoked by Telegram on {channel}. Stopping.")
        raise
    except ChannelPrivateError:
        print(f"  Skipping {channel}: private, not a member")
    except ChatAdminRequiredError:
        print(f"  Skipping {channel}: admin access required")
    except asyncio.CancelledError:
        print(f"  Skipping {channel}: connection interrupted")
    except OSError:
        print(f"  Skipping {channel}: network error")
    except Exception as e:
        print(f"  Skipping {channel}: {type(e).__name__}: {e}")

    return inserted


async def scrape_forum_group(client, conn, channel: str) -> int:
    total_inserted = 0

    try:
        entity = await client.get_entity(channel)

        print(f"  Fetching topics from {channel}...")
        topics_result = await client(GetForumTopicsRequest(
            peer=entity,
            offset_date=None,
            offset_id=0,
            offset_topic=0,
            limit=FETCH_LIMIT,
        ))

        topics = topics_result.topics
        print(f"  Found {len(topics)} topics")

        for topic in topics:
            topic_title = getattr(topic, 'title', 'General')
            topic_id    = topic.id
            inserted    = 0

            print(f"    Scraping topic: {topic_title}")

            try:
                async for msg in client.iter_messages(
                    entity,
                    limit=FETCH_LIMIT,
                    reply_to=topic_id,
                ):
                    has_media    = bool(msg.photo or msg.document)
                    text_content = msg.message or ("[MEDIA ONLY]" if has_media else None)

                    if not text_content:
                        continue

                    result = conn.execute(INSERT_SQL, {
                        "channel":     channel_url(channel),
                        "message_id":  msg.id,
                        "text":        text_content,
                        "topic_title": topic_title,
                        "posted_at":   msg.date,
                        "has_media":   has_media,
                    })

                    if result.rowcount == 0:
                        continue

                    inserted += 1

                    if has_media:
                        try:
                            conn.execute(MEDIA_QUEUE_SQL, {
                                "channel":     channel_url(channel),
                                "message_id":  msg.id,
                                "topic_title": topic_title,
                                "file_path":   f"PENDING:{channel.lstrip('@')}_{msg.id}",
                                "file_type":   detect_media_type(msg),
                                "posted_at":   msg.date,
                            })
                        except Exception:
                            pass

            except SessionRevokedError:
                print(f"\n  CRITICAL: Session revoked in topic '{topic_title}'. Stopping.")
                raise
            except asyncio.CancelledError:
                print(f"    Connection interrupted on topic '{topic_title}', continuing...")
            except OSError:
                print(f"    Network error on topic '{topic_title}', continuing...")
            except Exception as e:
                print(f"    Error in topic '{topic_title}': {type(e).__name__}: {e}")
                continue

            print(f"    Inserted {inserted} from '{topic_title}'")
            total_inserted += inserted
            await safe_sleep(2)

    except SessionRevokedError:
        raise
    except ChannelPrivateError:
        print(f"  Skipping {channel}: private group, not a member")
    except asyncio.CancelledError:
        print(f"  Skipping {channel}: connection interrupted")
    except OSError:
        print(f"  Skipping {channel}: network error")
    except Exception as e:
        print(f"  Skipping {channel}: {type(e).__name__}: {e}")

    return total_inserted


async def main() -> None:
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

    try:
        async with TelegramClient(str(SESSION_NAME), api_id, api_hash) as client:
            if await client.is_user_authorized():
                print(f"Connected using session {SESSION_FILE}")
            else:
                if not phone:
                    raise RuntimeError(
                        f"No session found at {SESSION_FILE} and TG_PHONE is not set."
                    )
                await client.start(phone=phone)
                print(f"Created new session at {SESSION_FILE}")

            with engine.begin() as conn:

                print(f"\nScraping {len(REGULAR_CHANNELS)} channels...")
                for channel in REGULAR_CHANNELS:
                    print(f"Fetching {channel}")
                    try:
                        inserted = await asyncio.wait_for(scrape_regular_channel(client, conn, channel), timeout=120)
                        print(f"Inserted {inserted} new messages from {channel}")
                    except SessionRevokedError:
                        raise
                    except FloodWaitError as e:
                        print(f"Telegram is asking to wait {e.seconds} seconds.")
                        time.sleep(e.seconds + 10)
                    except (asyncio.TimeoutError, Exception) as e:
                        print(f"[SKIP] {channel} — timed out or error, skipping")
                    time.sleep(random.uniform(8, 15))

                print(f"\nScraping {len(FORUM_GROUPS)} forum groups...")
                for channel in FORUM_GROUPS:
                    print(f"Fetching topics from {channel}")
                    try:
                        inserted = await asyncio.wait_for(scrape_forum_group(client, conn, channel), timeout=600)
                        print(f"Inserted {inserted} total from {channel}")
                    except SessionRevokedError:
                        raise
                    except FloodWaitError as e:
                        print(f"Telegram is asking to wait {e.seconds} seconds.")
                        time.sleep(e.seconds + 10)
                    except (asyncio.TimeoutError, Exception) as e:
                        print(f"[SKIP] {channel} — timed out or error, skipping")
                    time.sleep(random.uniform(8, 15))

    except SessionRevokedError:
        print("\n" + "="*60)
        print("SESSION REVOKED — scraper stopped to protect your account.")
        print("="*60)
        print("\nNext steps:")
        print(f"  1. Wait 24 hours before scraping again")
        print(f"  2. Delete the dead session file:")
        print(f"     del {SESSION_FILE}")
        print(f"  3. Re-run to authenticate with a fresh verification code")
        print("="*60 + "\n")
        sys.exit(1)

    print("\nScraping complete.")


if __name__ == "__main__":
    asyncio.run(main())
