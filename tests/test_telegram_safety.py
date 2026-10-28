r"""
test_telegram_safety.py
-----------------------
Checks the account-safety stops of telegram_scraper.py and listener.py (see
telegram_safety.py and "Telegram account safety" in CLAUDE.md):

  1. no login file: both stop before creating a Telegram client (no file is created)
  2. expired login: both stop without ever starting a login, and wait at least 24 hours
  3. one at a time: the scraper refuses while the listener runs, and the other way round,
     also when the other one is a separate program; a crashed program frees the lock
  4. slow and small: the limits per channel, the pauses, 2 runs a day, a new day
  5. the daily request cap stops a run
  6. a FloodWait stops the whole run at once, with no retry until the next day
  7. an ended login in the middle of a run stops it for at least 24 hours
  8. a problem with one channel (private, renamed) only skips that channel
  9. the listener asks for each forum topic once and stops at a FloodWait

Runs the real scraper and listener code with a fake Telegram client and a fake
database: it never connects to Telegram and writes nothing. The login file, the lock
and the daily counts live in a temporary folder.

Usage:
    venv\Scripts\python.exe tests\test_telegram_safety.py
"""

import asyncio
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from telethon.errors import ChannelPrivateError, FloodWaitError, SessionRevokedError  # noqa: E402
from telethon.tl.types import Channel, ChatPhotoEmpty  # noqa: E402

import listener  # noqa: E402
import telegram_safety as safety  # noqa: E402
import telegram_scraper as scraper  # noqa: E402
from channels import FORUM_GROUPS, REGULAR_CHANNELS  # noqa: E402

STATE = Path(tempfile.mkdtemp(prefix="tg_safety_test_"))
REAL_NOW = safety.now
PAUSES = []
SOURCES = REGULAR_CHANNELS + FORUM_GROUPS
UNKNOWN = REGULAR_CHANNELS[0]   # the one channel the fake login file does not remember


# ── Fakes ────────────────────────────────────────────────────────
class FakeConn:
    def execute(self, statement, params=None):
        return SimpleNamespace(rowcount=1, scalar=lambda: 1)


class FakeEngine:
    def begin(self):
        return contextlib.nullcontext(FakeConn())


def message(i, **extra):
    return SimpleNamespace(id=i, message=f"ለሽያጭ ቤት {i}", photo=None, document=None,
                           date=datetime.now(timezone.utc), reply_to=None, reply_to_top_id=None, **extra)


class FakeTelegram:
    """Stands in for TelegramClient and records every request; never touches the network."""
    made = []
    authorized = True
    fail_on = {}   # channel -> error raised when its messages or topics are asked for

    def __init__(self, session, api_id, api_hash, **settings):
        self.session_name, self.settings = session, settings
        self.requests, self.connected, self.handler = [], False, None
        self.session = SimpleNamespace(get_input_entity=self.remembered)
        FakeTelegram.made.append(self)

    def remembered(self, channel):
        if channel == UNKNOWN:
            raise ValueError("not in the login file")
        return SimpleNamespace(name=channel, id=hash(channel))

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def is_user_authorized(self):
        return FakeTelegram.authorized

    async def start(self, *args, **kwargs):
        raise AssertionError("a new login was started")

    send_code_request = sign_in = start

    async def get_input_entity(self, channel):
        self.requests.append(("find channel", channel, None))
        return SimpleNamespace(name=channel, id=hash(channel))

    async def __call__(self, request):
        kind = type(request).__name__
        peer = getattr(request.peer, "name", None) or request.peer.username   # the listener passes the group itself
        self.requests.append((kind, peer, getattr(request, "limit", None)))
        if peer in FakeTelegram.fail_on:
            raise FakeTelegram.fail_on[peer]
        if kind == "GetHistoryRequest":
            return SimpleNamespace(messages=[message(i) for i in range(request.limit)])
        if kind == "GetForumTopicsRequest":   # Telegram may send more topics than asked for
            return SimpleNamespace(topics=[SimpleNamespace(id=i, title=f"topic {i}") for i in range(1, 30)])
        if kind == "GetForumTopicsByIDRequest":
            return SimpleNamespace(topics=[SimpleNamespace(title=f"topic {request.topics[0]}")])
        raise AssertionError(f"unexpected request {kind}")

    async def get_messages(self, entity, limit, reply_to):
        self.requests.append(("GetRepliesRequest", entity.name, limit))
        return [message(i) for i in range(limit)]

    # the listener's side
    def on(self, _event_type):
        def register(fn):
            self.handler = fn
            return fn
        return register

    async def run_until_disconnected(self):
        self.handled = 0
        for ev in FakeTelegram.events_to_send:
            if not self.connected:
                break
            await self.handler(ev)
            self.handled += 1
            await asyncio.sleep(0)   # lets a disconnect the handler asked for happen


async def no_pause(seconds_range):
    PAUSES.append(seconds_range)


def fresh_state():
    """An empty temporary folder for the login file, lock and counts; fakes reset."""
    shutil.rmtree(STATE, ignore_errors=True)
    STATE.mkdir()
    safety.SESSION, safety.LEGACY_SESSION = STATE / "ollaa_session.session", STATE / "legacy.session"
    safety.LOCK_FILE, safety.USAGE_FILE = STATE / "telegram.lock", STATE / "telegram_usage.json"
    safety.now = REAL_NOW
    FakeTelegram.made, FakeTelegram.authorized, FakeTelegram.fail_on = [], True, {}
    FakeTelegram.events_to_send = []
    PAUSES.clear()


def login_file():
    safety.SESSION.write_text("stand-in login file")


def run(program):
    """Run the real main() of the scraper or listener; returns (exit code, what it printed)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = asyncio.run(program.main())
    return code, out.getvalue()


def usage():
    return json.loads(safety.USAGE_FILE.read_text(encoding="utf-8"))


def last_client():
    return FakeTelegram.made[-1]


def asked(client, kind):
    return [r for r in client.requests if r[0] == kind]


def next_midnight():
    return datetime.combine(REAL_NOW().date() + timedelta(days=1), datetime.min.time(), safety.ETHIOPIA)


def blocked_until_tomorrow(wait_seconds):
    """Blocked until the next midnight, or until Telegram's wait plus an hour if that ends later."""
    blocked = datetime.fromisoformat(usage()["blocked_until"])
    expected = max(next_midnight(), REAL_NOW() + timedelta(seconds=wait_seconds + 3600))
    return abs((blocked - expected).total_seconds()) < 60


def check(label, condition):
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    assert condition, label


# ── Tests ────────────────────────────────────────────────────────
def test_no_login_file():
    print("1. No login file")
    for program in (scraper, listener):
        fresh_state()
        code, said = run(program)
        name = program.__name__
        check(f"{name}: stops (exit 2) with a clear message", code == 2 and "No Telegram login file" in said)
        check(f"{name}: no Telegram client created, so nothing connected", FakeTelegram.made == [])
        check(f"{name}: no login file created", not safety.SESSION.exists())
        check(f"{name}: no lock taken, nothing counted", not safety.LOCK_FILE.exists() and not safety.USAGE_FILE.exists())


def test_expired_login():
    print("2. Expired login")
    fresh_state()
    login_file()
    FakeTelegram.authorized = False
    code, said = run(scraper)
    client = last_client()
    check("scraper: stops with a clear message", code == 2 and "no longer valid" in said and "without logging in" in said)
    check("scraper: never started a login (start() would have failed the test)", True)
    check("scraper: no channel was read", client.requests == [])
    check("scraper: disconnected", not client.connected)
    check("login file left exactly as it was", safety.SESSION.read_text() == "stand-in login file")
    blocked = datetime.fromisoformat(usage()["blocked_until"])
    check("Telegram not used for at least 24 hours", blocked >= REAL_NOW() + timedelta(hours=24))
    made = len(FakeTelegram.made)
    code, said = run(scraper)
    check("next scraper run refused before connecting", code == 2 and len(FakeTelegram.made) == made)
    code, said = run(listener)
    check("listener refused too, before connecting", code == 2 and len(FakeTelegram.made) == made)

    fresh_state()
    login_file()
    FakeTelegram.authorized = False
    code, said = run(listener)
    check("listener on its own: stops without a login", code == 2 and "no longer valid" in said
          and last_client().requests == [] and not last_client().connected)


HOLDER = r"""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import telegram_safety as safety
safety.LOCK_FILE = Path(sys.argv[2])
with safety.TelegramLock(sys.argv[3]):
    print("holding", flush=True)
    sys.stdin.readline()
"""


def hold_lock_elsewhere(program):
    """Another program (a separate process) that holds the lock until told to stop."""
    holder = subprocess.Popen([sys.executable, "-c", HOLDER, str(SRC), str(safety.LOCK_FILE), program],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "holding"
    return holder


def test_one_at_a_time():
    print("3. Scraper and listener never together")
    fresh_state()
    login_file()
    holder = hold_lock_elsewhere("listener")
    code, said = run(scraper)
    check("scraper refused while the listener runs (another program)",
          code == 2 and "already in use by the listener" in said and FakeTelegram.made == [])
    holder.stdin.write("\n")
    holder.stdin.flush()
    holder.wait(10)
    code, said = run(scraper)
    check("scraper runs once the listener has ended", code == 0)

    with safety.TelegramLock("scraper"):
        made = len(FakeTelegram.made)
        code, said = run(listener)
        check("listener refused while the scraper runs",
              code == 2 and "already in use by the scraper" in said and len(FakeTelegram.made) == made)
        code, said = run(scraper)
        check("a second scraper refused too", code == 2 and "already in use" in said)

    holder = hold_lock_elsewhere("scraper")
    holder.kill()
    holder.wait(10)
    freed = False
    for _ in range(25):   # Windows frees the lock of an ended program within moments
        try:
            with safety.TelegramLock("listener"):
                freed = True
            break
        except safety.SafetyStop:
            time.sleep(0.2)
    check("a program that crashed does not leave the lock behind", freed)


def test_limits_and_runs():
    print("4. Slow and small")
    fresh_state()
    login_file()
    code, said = run(scraper)
    client = last_client()
    check("a normal run finishes", code == 0 and "Scraping complete" in said)
    check("Telethon never waits out a FloodWait by itself (flood_sleep_threshold=0)",
          client.settings.get("flood_sleep_threshold") == 0)
    history = asked(client, "GetHistoryRequest")
    check(f"each of the {len(REGULAR_CHANNELS)} channels: one request for its newest {safety.MESSAGES_PER_CHANNEL} messages",
          len(history) == len(REGULAR_CHANNELS) and {r[2] for r in history} == {safety.MESSAGES_PER_CHANNEL})
    check("only the channel the login file does not remember is looked up",
          asked(client, "find channel") == [("find channel", UNKNOWN, None)])
    topics, replies = asked(client, "GetForumTopicsRequest"), asked(client, "GetRepliesRequest")
    check(f"forum groups: {safety.TOPICS_PER_GROUP} topics of {safety.MESSAGES_PER_TOPIC} messages, even when "
          "Telegram offers more", len(topics) == len(FORUM_GROUPS)
          and len(replies) == len(FORUM_GROUPS) * safety.TOPICS_PER_GROUP
          and {r[2] for r in replies} == {safety.MESSAGES_PER_TOPIC})
    check(f"random pause of {safety.PAUSE_BETWEEN_CHANNELS} s before every channel but the first",
          PAUSES.count(safety.PAUSE_BETWEEN_CHANNELS) == len(SOURCES) - 1)
    check(f"random pause of {safety.PAUSE_BETWEEN_TOPICS} s before every forum topic",
          PAUSES.count(safety.PAUSE_BETWEEN_TOPICS) == len(FORUM_GROUPS) * safety.TOPICS_PER_GROUP)
    check(f"every request counted: {len(client.requests)} of {safety.DAILY_REQUEST_CAP} today",
          usage()["requests"] == len(client.requests) and usage()["runs"] == 1)

    code, said = run(scraper)
    check("a second run the same day is allowed", code == 0 and usage()["runs"] == 2)
    made = len(FakeTelegram.made)
    code, said = run(scraper)
    check(f"a third run the same day is refused (limit {safety.RUNS_PER_DAY}), before connecting",
          code == 2 and "Try again tomorrow" in said and len(FakeTelegram.made) == made)
    safety.now = lambda: REAL_NOW() + timedelta(days=1)
    code, said = run(scraper)
    check("the next day the counts start again", code == 0 and usage()["runs"] == 1)


def test_daily_cap():
    print("5. Daily request cap")
    fresh_state()
    login_file()
    safety.USAGE_FILE.write_text(json.dumps({"day": REAL_NOW().date().isoformat(), "requests": safety.DAILY_REQUEST_CAP - 5,
                                             "runs": 0}), encoding="utf-8")
    code, said = run(scraper)
    check("the run stops when the day's cap is reached", code == 2 and "limit" in said)
    check("exactly the 5 requests left were made", len(last_client().requests) == 5)
    check("the count stays at the cap", usage()["requests"] == safety.DAILY_REQUEST_CAP)


def test_floodwait():
    print("6. FloodWait stops everything")
    fresh_state()
    login_file()
    third = REGULAR_CHANNELS[2]
    FakeTelegram.fail_on = {third: FloodWaitError(request=None, capture=30)}
    code, said = run(scraper)
    client = last_client()
    read = [r[1] for r in client.requests]
    check("the run stops with a clear message", code == 2 and "FloodWaitError" in said and "no retry" in said)
    check("no channel after it was asked for", read[-1] == third and not set(read) & set(SOURCES[3:]))
    check("the FloodWait was not retried", read.count(third) == 1)
    check("disconnected", not client.connected)
    check("Telegram not used again until midnight (or the wait plus an hour, if later)", blocked_until_tomorrow(30))
    made = len(FakeTelegram.made)
    code, said = run(scraper)
    check("a new scraper run today is refused before connecting", code == 2 and "FloodWaitError" in said
          and len(FakeTelegram.made) == made)
    code, said = run(listener)
    check("the listener is refused too", code == 2 and len(FakeTelegram.made) == made)
    FakeTelegram.fail_on = {}
    block_ends = datetime.fromisoformat(usage()["blocked_until"])
    safety.now = lambda: block_ends + timedelta(minutes=1)
    code, said = run(scraper)
    check("once the block has ended (the next day) the scraper may run again", code == 0)

    fresh_state()
    login_file()
    FakeTelegram.fail_on = {REGULAR_CHANNELS[0]: FloodWaitError(request=None, capture=2 * 86400)}
    run(scraper)
    blocked = datetime.fromisoformat(usage()["blocked_until"])
    check("a wait longer than a day is respected, plus an hour", blocked >= REAL_NOW() + timedelta(days=2, minutes=59))


def test_login_ended_mid_run():
    print("7. Login ended in the middle of a run")
    fresh_state()
    login_file()
    FakeTelegram.fail_on = {REGULAR_CHANNELS[1]: SessionRevokedError(request=None)}
    code, said = run(scraper)
    check("the run stops and says the login has ended", code == 2 and "login has ended" in said)
    check("nothing after it was asked for", last_client().requests[-1][1] == REGULAR_CHANNELS[1])
    check("Telegram not used for at least 24 hours",
          datetime.fromisoformat(usage()["blocked_until"]) >= REAL_NOW() + timedelta(hours=24))


def test_channel_problem():
    print("8. A problem with one channel")
    fresh_state()
    login_file()
    FakeTelegram.fail_on = {REGULAR_CHANNELS[1]: ChannelPrivateError(request=None)}
    code, said = run(scraper)
    check("that channel is skipped and the run finishes", code == 0 and "skipped: ChannelPrivateError" in said)
    check("all other channels were read", len(asked(last_client(), "GetHistoryRequest")) == len(REGULAR_CHANNELS))
    check("no stop is recorded", not usage().get("blocked_until"))


def forum_event(topic, message_id):
    group = Channel(id=5, title="forum", photo=ChatPhotoEmpty(), date=None, username="championallsites", forum=True)
    msg = message(message_id)
    msg.reply_to_top_id = topic

    async def get_chat():
        raise AssertionError("the chat came with the message: no request needed")

    return SimpleNamespace(message=msg, is_private=False, chat=group, get_chat=get_chat)


def test_listener():
    print("9. Listener")
    listener.engine = FakeEngine()
    fresh_state()
    login_file()
    FakeTelegram.events_to_send = [forum_event(11, 1), forum_event(11, 2), forum_event(12, 3)]
    code, said = run(listener)
    client = last_client()
    check("listens and ends normally", code == 0 and client.handled == 3)
    check("Telethon never waits out a FloodWait by itself", client.settings.get("flood_sleep_threshold") == 0)
    check("each forum topic's title is asked for once (2 topics, 3 messages)",
          len(asked(client, "GetForumTopicsByIDRequest")) == 2 and usage()["requests"] == 2)

    fresh_state()
    login_file()
    FakeTelegram.fail_on = {"championallsites": FloodWaitError(request=None, capture=30)}
    FakeTelegram.events_to_send = [forum_event(11, 1), forum_event(12, 2), forum_event(13, 3)]
    code, said = run(listener)
    client = last_client()
    check("a FloodWait stops the listener with a clear message", code == 2 and "FloodWaitError" in said)
    check("no message after it was handled, no retry", client.handled == 1
          and len(asked(client, "GetForumTopicsByIDRequest")) == 1)
    check("disconnected", not client.connected)
    check("Telegram not used again until midnight (or the wait plus an hour, if later)", blocked_until_tomorrow(30))
    made = len(FakeTelegram.made)
    code, said = run(scraper)
    check("the scraper is refused today too", code == 2 and len(FakeTelegram.made) == made)


def test_login_file_location():
    print("10. Which login file")
    fresh_state()
    check("the usual place", safety.session_file() == safety.SESSION)
    safety.LEGACY_SESSION.write_text("old place")
    check("an older copy's place, if the usual one is empty", safety.session_file() == safety.LEGACY_SESSION)
    login_file()
    check("the usual place wins when both exist", safety.session_file() == safety.SESSION)
    os.environ["TG_SESSION_NAME"] = str(STATE / "other")
    check("TG_SESSION_NAME in .env chooses another file", safety.session_file() == STATE / "other.session")
    os.environ.pop("TG_SESSION_NAME")


def main():
    os.environ.pop("TG_SESSION_NAME", None)
    safety.api_credentials = lambda: (12345, "test")
    safety.pause = no_pause
    scraper.TelegramClient = listener.TelegramClient = FakeTelegram
    scraper.engine = FakeEngine()
    listener.engine = FakeEngine()
    try:
        test_no_login_file()
        test_expired_login()
        test_one_at_a_time()
        test_limits_and_runs()
        test_daily_cap()
        test_floodwait()
        test_login_ended_mid_run()
        test_channel_problem()
        test_listener()
        test_login_file_location()
    finally:
        shutil.rmtree(STATE, ignore_errors=True)
    print("\nPASS: every safety stop works, and Telegram was never contacted.")


if __name__ == "__main__":
    main()
