r"""
media_downloader.py
-------------------
Downloads the photos of chosen photo-only posts from Telegram, slowly and carefully.
The scraper does not download files on purpose (see its comment: downloading can get a
flagged account's login revoked), so this runs separately: one photo every 6-10 seconds,
and it stops at the first sign of trouble (Telegram asks us to wait, or the login is no
longer valid). It never asks for a login: run src/telegram_login.py first.

Reads the list of posts made by `src/media_pilot.py --plan N` and writes
data/images/telegram/<channel>_<message id>.jpg (skipping photos already there). The
database is not changed.

Usage:
    venv\Scripts\python.exe src\media_downloader.py
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError, SessionRevokedError

import settings

BASE_DIR = Path(__file__).resolve().parents[1]
SESSION = BASE_DIR / "data" / "sessions" / "ollaa_session"
PLAN_FILE = BASE_DIR / "data" / "media_pilot" / "round2_plan.json"
IMAGE_DIR = BASE_DIR / "data" / "images" / "telegram"
PAUSE_SECONDS = (6, 10)


async def main() -> None:
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    todo = [p for p in plan if not ((IMAGE_DIR / p["image"]).exists() and (IMAGE_DIR / p["image"]).stat().st_size)]
    print(f"posts in the plan: {len(plan)}; photos still to download: {len(todo)}")
    if not SESSION.with_suffix(".session").exists():
        sys.exit("Not logged in to Telegram. Run src/telegram_login.py first.")

    client = TelegramClient(str(SESSION), int(settings.TG_API_ID), settings.TG_API_HASH)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            sys.exit("The Telegram login is no longer valid. Run src/telegram_login.py again.")
        done = gone = other = 0
        for i, p in enumerate(todo, 1):
            try:
                message = await client.get_messages(p["channel_name"], ids=p["message_id"])
                if message is None:
                    gone += 1
                    print(f"{i:>3}/{len(todo)} {p['image']}: post no longer on Telegram")
                elif message.photo:
                    await client.download_media(message, file=str(IMAGE_DIR / p["image"]))
                    done += 1
                    print(f"{i:>3}/{len(todo)} {p['image']}: downloaded")
                else:
                    other += 1
                    print(f"{i:>3}/{len(todo)} {p['image']}: not a photo, skipped")
            except FloodWaitError as e:
                print(f"Telegram asks us to wait {e.seconds} seconds: stopping here. Run again later.")
                break
            except (AuthKeyUnregisteredError, SessionRevokedError):
                print("Telegram ended the login: stopping. Run src/telegram_login.py again before retrying.")
                break
            await asyncio.sleep(random.uniform(*PAUSE_SECONDS))
        print(f"downloaded {done}; no longer on Telegram {gone}; not a photo {other}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
