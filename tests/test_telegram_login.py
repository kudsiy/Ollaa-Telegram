r"""
test_telegram_login.py
----------------------
Checks src/telegram_login.py, the owner's one-time login, with a fake Telegram: it never
connects to Telegram and never logs in.

  1. a login file already there: nothing asked, nothing sent
  2. the phone number: typed twice the same, with its country code, and the one in .env;
     otherwise nothing is sent to Telegram
  3. a normal login: only the login steps, the login file appears where the scraper looks,
     nothing typed is printed, and Telegram use is paused for the rest of the day
  4. two-step password, with a wrong code and a wrong password first
  5. wrong code 3 times, an expired code, a warning from Telegram: no file is left behind,
     and a warning pauses Telegram use
  6. not while the scraper or listener runs, and not while Telegram use is paused

Usage:
    venv\Scripts\python.exe tests\test_telegram_login.py
"""

import asyncio
import contextlib
import io
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telethon.errors import (FloodWaitError, PasswordHashInvalidError, PhoneCodeExpiredError,  # noqa: E402
                             PhoneCodeInvalidError, SessionPasswordNeededError)

import telegram_login as login  # noqa: E402
import telegram_safety as safety  # noqa: E402

STATE = Path(tempfile.mkdtemp(prefix="tg_login_test_"))
PHONE, CODE, PASSWORD = "+251 911 234 567", "52817", "secret two-step words"
EXPIRED = "40404"   # a code the fake Telegram calls expired
SECRETS = ("911234567", "911 234 567", CODE, PASSWORD)


class FakeTelegram:
    """Stands in for TelegramClient during a login; records every step, never connects."""
    made = []
    password = None        # the account's two-step password, if it has one
    fail_on_send = None    # an error Telegram answers the code request with

    def __init__(self, session, api_id, api_hash, **settings):
        self.file = Path(session + ".session")
        self.settings, self.steps, self.connected = settings, [], False
        FakeTelegram.made.append(self)

    async def connect(self):
        self.connected = True
        self.file.write_text("new key, not logged in")   # Telethon writes the file on connecting

    async def disconnect(self):
        self.connected = False

    async def send_code_request(self, phone):
        self.steps.append(("send code", phone))
        if FakeTelegram.fail_on_send:
            raise FakeTelegram.fail_on_send

    async def sign_in(self, phone=None, code=None, password=None):
        if code is not None:
            self.steps.append(("code", phone))
            if code == EXPIRED:
                raise PhoneCodeExpiredError(request=None)
            if code != CODE:
                raise PhoneCodeInvalidError(request=None)
            if FakeTelegram.password:
                raise SessionPasswordNeededError(request=None)
        else:
            self.steps.append(("password",))
            if password != FakeTelegram.password:
                raise PasswordHashInvalidError(request=None)
        self.file.write_text("logged in")

    def __getattr__(self, name):   # start(), get_messages(), join… : anything else fails the test
        raise AssertionError(f"the login script used {name}()")

    async def __call__(self, request):
        raise AssertionError(f"the login script sent {type(request).__name__}")


def fresh_state(tg_phone=PHONE):
    shutil.rmtree(STATE, ignore_errors=True)
    STATE.mkdir()
    safety.STATE_DIR = STATE
    safety.SESSION, safety.LEGACY_SESSION = STATE / "ollaa_session.session", STATE / "legacy.session"
    safety.LOCK_FILE, safety.USAGE_FILE = STATE / "telegram.lock", STATE / "telegram_usage.json"
    login.TG_PHONE = tg_phone
    FakeTelegram.made, FakeTelegram.password, FakeTelegram.fail_on_send = [], None, None


def run(*answers):
    """Run the real login with these typed answers; returns (exit code, printed text, prompts)."""
    queue, prompts = list(answers), []

    def ask(prompt):
        prompts.append(prompt)
        assert queue, f"asked more than expected: {prompt}"
        return queue.pop(0)

    login.ask = ask
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = asyncio.run(login.main())
    assert not queue, f"answers not asked for: {len(queue)}"
    return code, out.getvalue(), prompts


def leftovers():
    return sorted(p.name for p in STATE.glob("*.session*"))


def paused_until():
    until = json.loads(safety.USAGE_FILE.read_text(encoding="utf-8")).get("blocked_until")
    return datetime.fromisoformat(until) if until else None


def check(label, condition):
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")
    assert condition, label


def test_login_file_exists():
    print("1. A login file is already there")
    for existing in ("SESSION", "LEGACY_SESSION"):
        fresh_state()
        getattr(safety, existing).write_text("the working login")
        code, said, prompts = run()
        check(f"{existing.lower()}: stops without asking anything", code == 2 and "already exists" in said and prompts == [])
        check(f"{existing.lower()}: nothing sent to Telegram", FakeTelegram.made == [])
        check(f"{existing.lower()}: the login file is untouched", getattr(safety, existing).read_text() == "the working login")


def test_phone_checks():
    print("2. The phone number")
    cases = [("typed differently twice", (PHONE, "+251 911 234 568"), "not the same"),
             ("without the country code", ("0911234567", "0911234567"), "country code"),
             ("not the number in .env", ("+251 922 222 222", "+251 922 222 222"), "not the number in .env")]
    for label, answers, message in cases:
        fresh_state()
        code, said, prompts = run(*answers)
        check(f"{label}: stops before contacting Telegram", code == 2 and message in said and FakeTelegram.made == [])
        check(f"{label}: no file made", leftovers() == [])
    fresh_state(tg_phone="0911234567")
    code, said, prompts = run(PHONE, PHONE, CODE)
    check(".env number without the country code still matches", code == 0)


def test_normal_login():
    print("3. A normal login")
    fresh_state()
    code, said, prompts = run(PHONE, PHONE, CODE)
    client = FakeTelegram.made[-1]
    check("logged in", code == 0 and "LOGGED IN" in said)
    check("only the login steps: ask for the code, then check it",
          client.steps == [("send code", "+251911234567"), ("code", "+251911234567")])
    check("Telethon never waits out a FloodWait by itself", client.settings.get("flood_sleep_threshold") == 0)
    check("the login file is where the scraper and the listener look",
          safety.session_file() == safety.SESSION and safety.SESSION.read_text() == "logged in")
    check("no other file left behind", leftovers() == ["ollaa_session.session"])
    check("disconnected", not client.connected)
    check("asked 3 times, always hidden (phone twice, code)", len(prompts) == 3 and all("hidden" in p for p in prompts))
    check("nothing typed is printed", not any(s in said for s in SECRETS))
    until = paused_until()
    tomorrow = datetime.combine(safety.now().date() + timedelta(days=1), datetime.min.time(), safety.ETHIOPIA)
    check("scraper and listener paused until midnight and for at least 12 hours",
          until >= tomorrow and until >= safety.now() + timedelta(hours=11, minutes=59))
    try:
        safety.DailyBudget().start_scraper_run()
        refused = False
    except safety.SafetyStop as e:
        refused = "no scraping on the day of the login" in str(e)
    check("so the scraper refuses to start today, and says why", refused)
    code, said, prompts = run()
    check("running the login again does nothing", code == 2 and "already exists" in said and len(FakeTelegram.made) == 1)


def test_two_step():
    print("4. Two-step password")
    fresh_state()
    FakeTelegram.password = PASSWORD
    code, said, prompts = run(PHONE, PHONE, "11111", CODE, "wrong password", PASSWORD)
    client = FakeTelegram.made[-1]
    check("logged in after a wrong code and a wrong password", code == 0 and safety.SESSION.read_text() == "logged in")
    check("said the code and the password were not right",
          "code is not right" in said and "password is not right" in said)
    check("only the login steps", [s[0] for s in client.steps] == ["send code", "code", "code", "password", "password"])
    check("nothing typed is printed", not any(s in said for s in SECRETS))


def test_failures():
    print("5. Failed logins leave nothing behind")
    fresh_state()
    code, said, prompts = run(PHONE, PHONE, "1", "2", "3")
    check("wrong code 3 times: stops", code == 2 and "wrong 3 times" in said)
    check("no login file, no half-made file", leftovers() == [])
    check("no pause (a typo is not a warning from Telegram)", not safety.USAGE_FILE.exists() or paused_until() is None)

    fresh_state()
    FakeTelegram.password = PASSWORD
    code, said, prompts = run(PHONE, PHONE, CODE, "a", "b", "c")
    check("wrong password 3 times: stops, nothing left behind", code == 2 and "wrong 3 times" in said and leftovers() == [])

    fresh_state()
    code, said, prompts = run(PHONE, PHONE, EXPIRED)
    check("expired code: stops, nothing left behind", code == 2 and "expired" in said and leftovers() == [])

    fresh_state()
    FakeTelegram.fail_on_send = FloodWaitError(request=None, capture=600)
    code, said, prompts = run(PHONE, PHONE)
    check("a FloodWait when asking for the code: stops at once, nothing left behind",
          code == 2 and "FloodWaitError" in said and leftovers() == [])
    check("and Telegram use is paused until at least midnight", paused_until() >= safety.now() + timedelta(minutes=10))
    check("nothing typed is printed", not any(s in said for s in SECRETS))


def test_lock_and_pause():
    print("6. Not alongside the scraper or listener, not while paused")
    fresh_state()
    with safety.TelegramLock("scraper"):
        code, said, prompts = run()
    check("refused while the scraper runs, before asking anything",
          code == 2 and "already in use by the scraper" in said and prompts == [])
    fresh_state()
    safety.DailyBudget().block("FloodWaitError", 600)
    code, said, prompts = run()
    check("refused while Telegram use is paused, before asking anything",
          code == 2 and "paused until" in said and prompts == [] and FakeTelegram.made == [])


def main():
    safety.api_credentials = lambda: (12345, "test")
    login.TelegramClient = FakeTelegram
    try:
        test_login_file_exists()
        test_phone_checks()
        test_normal_login()
        test_two_step()
        test_failures()
        test_lock_and_pause()
    finally:
        shutil.rmtree(STATE, ignore_errors=True)
    print("\nPASS: the login script only logs in, keeps everything typed hidden, and Telegram was never contacted.")


if __name__ == "__main__":
    main()
