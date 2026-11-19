"""
test_listener_privacy.py
------------------------
Checks that listener.py saves messages only from the channels in channels.py, never from private chats,
and that a saved message goes through the scraper's own save step and the ETL's own listing step.

Runs the real listener code with a fake Telegram client; the database steps are stand-ins, so it needs
no Telegram login, never connects, and writes nothing (its login file, lock, daily counts and health
log live in a temporary folder).

Usage:
    venv\\Scripts\\python.exe tests\\test_listener_privacy.py
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telethon.tl.types import Channel, ChatPhotoEmpty, User, Username  # noqa: E402

import channels  # noqa: E402
import etl_runner  # noqa: E402
import dedup_strict  # noqa: E402
import listener  # noqa: E402
import listener_health as health  # noqa: E402
import telegram_safety as safety  # noqa: E402
import telegram_scraper as scraper  # noqa: E402

LISTING = "ለሽያጭ ባለ 2 መኝታ አፓርታማ ቦሌ 120 ካሬ ዋጋ 9.5 ሚሊየን ብር"


def channel(username=None, usernames=None):
    return Channel(id=1, title="t", photo=ChatPhotoEmpty(), date=None,
                   username=username, usernames=usernames)


def event(entity, is_private=False, msg_id=7):
    msg = SimpleNamespace(message=LISTING, photo=None, document=None, id=msg_id,
                          date=datetime.now(timezone.utc), reply_to=None)

    async def get_chat():
        return entity

    return SimpleNamespace(message=msg, is_private=is_private, chat=entity, get_chat=get_chat)


class FakeClient:
    """Stands in for TelegramClient: captures the handler and feeds it test events."""
    events_to_send = []

    def __init__(self, *args, **kwargs):
        self.handler, self.connected = None, False

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    async def is_user_authorized(self):
        return True

    def on(self, _event_type):
        def register(fn):
            self.handler = fn
            return fn
        return register

    async def run_until_disconnected(self):
        for _label, ev in self.events_to_send:
            await self.handler(ev)


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement, params=None):
        CALLS.append(("raw row", params))
        return SimpleNamespace(fetchone=lambda: SimpleNamespace(id=500 + params["m"]))


CALLS = []


def main():
    # 1. The helper on its own.
    assert channels.is_configured_chat(channel("Bet_afri"))
    assert channels.is_configured_chat(channel("BET_AFRI")), "usernames are case-insensitive"
    assert channels.configured_name(channel("BET_AFRI")) == "@Bet_afri", "saved under the name in channels.py"
    assert channels.is_configured_chat(channel(None, [Username(username="championallsites", active=True)]))
    assert not channels.is_configured_chat(channel("Bamaconrealestateplc"))
    assert not channels.is_configured_chat(channel(None)), "private group without a username"
    assert not channels.is_configured_chat(User(id=2, username="Bet_afri")), "a person, even with a listed name"

    # 2. The real listener handler, with stand-ins for the database steps it calls.
    state = Path(tempfile.mkdtemp())
    safety.SESSION, safety.LEGACY_SESSION = state / "ollaa_session.session", state / "old.session"
    safety.LOCK_FILE, safety.USAGE_FILE = state / "telegram.lock", state / "telegram_usage.json"
    safety.STEP_ASIDE_FILE = state / "listener_step_aside.json"
    safety.SESSION.write_text("stand-in login file")
    safety.api_credentials = lambda: (1, "test")
    health.HEALTH_DIR = state / "health"
    listener.TITLES_FILE = state / "titles.json"
    os.environ.pop("TG_SESSION_NAME", None)
    listener.TelegramClient = FakeClient
    scraper.ensure_tables = lambda: None
    scraper.save_messages = lambda name, msgs, topic: CALLS.append(("save raw", name, msgs[0].id, topic)) or 1
    etl_runner.engine = SimpleNamespace(connect=FakeConn)
    etl_runner.save_listing = lambda pipeline, row: CALLS.append(("save listing", row.id)) or (True, False, None)
    dedup_strict.remove_new_repeat = lambda engine, listing_id: CALLS.append(("repeat check", listing_id)) or None

    FakeClient.events_to_send = [
        ("private chat", event(User(id=2, username="someone"), is_private=True, msg_id=1)),
        ("a person with a listed name", event(User(id=3, username="Bet_afri"), is_private=True, msg_id=2)),
        ("unlisted channel", event(channel("Bamaconrealestateplc"), msg_id=3)),
        ("private group", event(channel(None), msg_id=4)),
        ("listed channel", event(channel("BET_AFRI"), msg_id=5)),
    ]
    assert asyncio.run(listener.main()) == 0

    raw = [c for c in CALLS if c[0] == "save raw"]
    for label, ev in FakeClient.events_to_send:
        saved = any(c[2] == ev.message.id for c in raw)
        print(f"{label:<28} saved: {'yes' if saved else 'no'}")
        assert saved == (label == "listed channel"), label
    assert raw == [("save raw", "@Bet_afri", 5, None)], raw
    assert [c[0] for c in CALLS] == ["save raw", "raw row", "save listing", "repeat check"], CALLS
    assert CALLS[1][1]["c"] == "https://t.me/Bet_afri", "the same channel address as the scraper's"
    h = health.read()
    assert (h["received"], h["saved"], h["listings_added"]) == (1, 1, 1), h
    print("\nPASS: only the listed channel was saved, under its channels.py name, through the scraper's save, "
          "the ETL's listing step and the repeat check; the health log counted it.")


if __name__ == "__main__":
    main()
