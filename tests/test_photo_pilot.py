r"""
test_photo_pilot.py
-------------------
Checks the safety stops of src/telegram_photo_pilot.py (task S41) with a fake Telegram: it never
connects to Telegram and writes only to a temporary folder.

  1. never on a day of the scheduled scrape, nor on a day the scraper ran
  2. a pause of 60-180 seconds between two downloads; each download counts as a request
  3. at most 30 downloads a day and 30 in all
  4. the first FloodWait stops the run at once, with no retry, and blocks Telegram for the day
  5. no login file, or an expired one: stop without logging in

Usage:
    venv\Scripts\python.exe tests\test_photo_pilot.py
"""

import asyncio
import contextlib
import io
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import telethon  # noqa: E402
from telethon.errors import FloodWaitError  # noqa: E402

import telegram_photo_pilot as pilot  # noqa: E402
import telegram_safety as safety  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="photo_pilot_test_"))
PAUSES = []
failures = 0


class FakeTelegram:
    made, authorized, fail_at = [], True, None

    def __init__(self, session, api_id, api_hash, **settings):
        self.settings, self.requests, self.downloads = settings, [], 0
        self.session = SimpleNamespace(get_input_entity=lambda name: SimpleNamespace(name=name))
        FakeTelegram.made.append(self)

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def is_user_authorized(self):
        return FakeTelegram.authorized

    async def start(self, *a, **k):
        raise AssertionError("a new login was started")

    async def get_messages(self, entity, ids):
        self.requests.append(("messages", len(ids)))
        return [SimpleNamespace(id=i, photo=object()) for i in ids]

    async def download_media(self, msg, file):
        self.downloads += 1
        if FakeTelegram.fail_at == self.downloads:
            raise FloodWaitError(request=None, capture=60)
        self.requests.append(("download", msg.id))
        Path(file).write_bytes(b"jpg")
        return file


async def no_pause(seconds_range):
    PAUSES.append(seconds_range)


def fresh(day):
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir()
    safety.SESSION, safety.LEGACY_SESSION = TMP / "ollaa_session.session", TMP / "legacy.session"
    safety.LOCK_FILE, safety.USAGE_FILE = TMP / "telegram.lock", TMP / "telegram_usage.json"
    safety.SESSION.write_text("stand-in login file")
    safety.now = lambda: datetime(2026, 11, day, 14, 0, tzinfo=safety.ETHIOPIA)
    pilot.OUT_DIR, pilot.PHOTO_DIR, pilot.LOG_FILE = TMP, TMP / "photos", TMP / "downloads.json"
    FakeTelegram.made, FakeTelegram.authorized, FakeTelegram.fail_at = [], True, None
    PAUSES.clear()


def run(chosen):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            asyncio.run(pilot.download(chosen))
            return 0, out.getvalue()
        except safety.SafetyStop as e:
            return 2, str(e)


def check(label, condition):
    global failures
    failures += not condition
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")


telethon.TelegramClient = FakeTelegram
safety.pause = no_pause
plan = [{"raw_id": 1000 + i, "message_id": 500 + i, "topic": "Prime_Bole Japan Apartment (ቦሌ ጃፓን)"} for i in range(30)]
usage = lambda: json.loads(safety.USAGE_FILE.read_text(encoding="utf-8"))

print("1. Not on a scrape day")
fresh(16)
code, said = run(plan)
check("the 16th, a day of the scheduled scrape, is refused before connecting", code == 2 and "scheduled scrape" in said and not FakeTelegram.made)
fresh(17)
safety.USAGE_FILE.write_text(json.dumps({"day": "2026-11-17", "requests": 40, "runs": 1}), encoding="utf-8")
code, said = run(plan)
check("a day the scraper ran is refused before connecting", code == 2 and "scraper ran today" in said and not FakeTelegram.made)

print("2. Slow, and counted")
fresh(17)
code, said = run(plan[:5])
client = FakeTelegram.made[-1]
check("5 photos downloaded", code == 0 and len([r for r in client.requests if r[0] == "download"]) == 5)
check("one pause of 60-180 seconds between two downloads", PAUSES == [pilot.PAUSE_BETWEEN_PHOTOS] * 4 and pilot.PAUSE_BETWEEN_PHOTOS == (60, 180))
check("each download and the lookup count as requests (5 + 1)", usage()["requests"] == 6)
check("Telethon never waits out a FloodWait by itself", client.settings.get("flood_sleep_threshold") == 0)

print("3. At most 30 a day and 30 in all")
fresh(17)
code, said = run(plan + [{"raw_id": 2000, "message_id": 900, "topic": "x"}])
check("only 30 downloaded in a day", len([r for r in FakeTelegram.made[-1].requests if r[0] == "download"]) == 30)
code, said = run(plan + [{"raw_id": 2000, "message_id": 900, "topic": "x"}])
check("the 31st photo is refused: more need the owner's approval", code == 2 and "approval" in said)

print("4. A FloodWait stops everything")
fresh(17)
FakeTelegram.fail_at = 3
code, said = run(plan)
client = FakeTelegram.made[-1]
check("the run stops at the first FloodWait, without a retry", code == 2 and "FloodWait" in said and client.downloads == 3)
check("Telegram is blocked until the next day at least", datetime.fromisoformat(usage()["blocked_until"]) >= datetime(2026, 11, 18, tzinfo=safety.ETHIOPIA))
check("what was saved before the stop is kept", len(json.loads(pilot.LOG_FILE.read_text())["downloaded"]) == 2)
code, said = run(plan)
check("a new run the same day is refused before connecting", code == 2 and len(FakeTelegram.made) == 1)

print("5. The login")
fresh(17)
safety.SESSION.unlink()
code, said = run(plan)
check("no login file: stopped, no client made", code == 2 and not FakeTelegram.made)
fresh(17)
FakeTelegram.authorized = False
code, said = run(plan)
check("an expired login: stopped without logging in", code == 2 and "no longer valid" in said)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'PASS: every safety stop of the photo pilot works, and Telegram was never contacted' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
