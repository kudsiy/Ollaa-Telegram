"""
test_listener_privacy.py
------------------------
Checks that listener.py saves messages only from the channels in channels.py.

Runs the real listener code with a fake Telegram client and a fake database,
so it needs no Telegram login and writes nothing.

Usage:
    venv\\Scripts\\python.exe tests\\test_listener_privacy.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telethon.tl.types import Channel, ChatPhotoEmpty, User, Username  # noqa: E402

import channels  # noqa: E402
import listener  # noqa: E402

LISTING = "ለሽያጭ ባለ 2 መኝታ አፓርታማ ቦሌ 120 ካሬ ዋጋ 9.5 ሚሊየን ብር"


def channel(username=None, usernames=None):
    return Channel(id=1, title="t", photo=ChatPhotoEmpty(), date=None,
                   username=username, usernames=usernames)


def event(entity, is_private=False):
    msg = SimpleNamespace(message=LISTING, photo=None, document=None, id=7,
                          date=datetime.now(timezone.utc), reply_to_top_id=None, reply_to=None)

    async def get_chat():
        return entity

    return SimpleNamespace(message=msg, is_private=is_private, get_chat=get_chat)


class FakeConn:
    def __init__(self, log):
        self.log = log

    def execute(self, statement, params=None):
        self.log.append(str(statement))
        return SimpleNamespace(scalar=lambda: 1)


class FakeEngine:
    def __init__(self):
        self.log = []

    def begin(self):
        engine = self

        class Ctx:
            def __enter__(self):
                return FakeConn(engine.log)

            def __exit__(self, *exc):
                return False

        return Ctx()


class FakeClient:
    """Stands in for TelegramClient: captures the handler and feeds it test events."""
    events_to_send = []
    saved_by_event = []

    def __init__(self, *args, **kwargs):
        self.handler = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def connect(self):
        pass

    async def is_user_authorized(self):
        return True

    def on(self, _event_type):
        def register(fn):
            self.handler = fn
            return fn
        return register

    async def run_until_disconnected(self):
        for label, ev in self.events_to_send:
            before = len(listener.engine.log)
            await self.handler(ev)
            inserts = [s for s in listener.engine.log[before:] if "INSERT INTO telegram_listings" in s]
            FakeClient.saved_by_event.append((label, bool(inserts)))


def main():
    # 1. The helper on its own.
    assert channels.is_configured_chat(channel("Bet_afri"))
    assert channels.is_configured_chat(channel("BET_AFRI")), "usernames are case-insensitive"
    assert channels.is_configured_chat(channel(None, [Username(username="championallsites", active=True)]))
    assert not channels.is_configured_chat(channel("Bamaconrealestateplc"))
    assert not channels.is_configured_chat(channel(None)), "private group without a username"

    # 2. The real listener handler.
    FakeClient.events_to_send = [
        ("private chat", event(User(id=2, username="someone"), is_private=True)),
        ("unlisted channel", event(channel("Bamaconrealestateplc"))),
        ("private group", event(channel(None))),
        ("listed channel", event(channel("Bet_afri"))),
    ]
    listener.TelegramClient = FakeClient
    listener.engine = FakeEngine()
    asyncio.run(listener.main())

    expected = {"private chat": False, "unlisted channel": False, "private group": False, "listed channel": True}
    for label, saved in FakeClient.saved_by_event:
        print(f"{label:<17} saved: {'yes' if saved else 'no'}")
        assert saved == expected[label], label
    assert len(FakeClient.saved_by_event) == len(expected)
    print("\nPASS: only the listed channel was saved.")


if __name__ == "__main__":
    main()
