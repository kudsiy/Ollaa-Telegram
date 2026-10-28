r"""
telegram_login.py
-----------------
Logs the project in to Telegram once, so the scraper, the listener and
media_downloader.py can use the account. The owner runs it in a terminal: Telegram
sends a code to the Telegram app (and asks for the two-step password, if one is set),
and the owner types it here. Nothing is printed about the account.

The login is saved in data/sessions/ollaa_session.session, the file the scraper and the
listener look for first. Like every *.session file it is never committed.

Usage (in a terminal):
    venv\Scripts\python.exe src\telegram_login.py
"""

import asyncio
from pathlib import Path

from telethon import TelegramClient

import settings

SESSION = Path(__file__).resolve().parents[1] / "data" / "sessions" / "ollaa_session"


async def main() -> None:
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(SESSION), int(settings.TG_API_ID), settings.TG_API_HASH)
    await client.start(phone=settings.TG_PHONE)   # asks for the code (and password) in this terminal
    print("\nLogged in to Telegram. You can close this window.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
