"""
test_listener_service.py
------------------------
Checks when listener_service.py starts the listener and when it waits (Phase 1): never without a login
file, never after Telegram ended the login until the owner has logged in again by hand, never during a
pause after a warning, never while the scraper or the photo pilot has the account, never with today's
requests used up, never without the internet or the database; and the restarts after a crash slow down.
No Telegram, no database, no network: everything it looks at is a stand-in in a temporary folder.

Usage:
    venv\\Scripts\\python.exe tests\\test_listener_service.py
"""

import json
import os
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import listener_service as service  # noqa: E402
import telegram_safety as safety  # noqa: E402

failures = 0


def check(label, condition):
    global failures
    failures += not condition
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")


state = Path(tempfile.mkdtemp())
safety.SESSION, safety.LEGACY_SESSION = state / "ollaa_session.session", state / "old.session"
safety.LOCK_FILE, safety.USAGE_FILE = state / "telegram.lock", state / "telegram_usage.json"
safety.STEP_ASIDE_FILE = state / "listener_step_aside.json"
os.environ.pop("TG_SESSION_NAME", None)
service.online = lambda: True
service.database_up = lambda: True


def usage(**fields):
    safety.USAGE_FILE.write_text(json.dumps({"day": safety.now().date().isoformat(), "requests": 0, "runs": 0, **fields}),
                                 encoding="utf-8")


def reason():
    r = service.why_not_start()
    return r[0] if r else None


print("1. The login")
usage()
check("no login file: waits for the owner, never logs in", "no login file" in reason())
safety.SESSION.write_text("stand-in login file")
check("with a login file and nothing in the way: starts", reason() is None)
ended = safety.now() - timedelta(hours=30)   # the login ended 30 hours ago: the 25-hour pause is over
os.utime(safety.SESSION, (ended.timestamp() - 3600, ended.timestamp() - 3600))
usage(blocked_until=(ended + timedelta(seconds=safety.LOGIN_ENDED_WAIT)).isoformat(),
      block_reason="the login has ended (AuthKeyUnregisteredError)")
check("after Telegram ended the login: still waits once the pause is over, until the owner logs in again",
      "ended the login" in reason())
os.utime(safety.SESSION, None)   # the owner logged in again by hand: a newer login file
check("once the owner has logged in again (a newer login file): starts", reason() is None)

print("2. Warnings, limits and the other programs")
usage(blocked_until=(safety.now() + timedelta(hours=5)).isoformat(), block_reason="FloodWaitError")
check("during the pause after a warning: waits", "paused" in reason())
usage(requests=safety.DAILY_REQUEST_CAP)
check("today's 150 requests used up: waits", "used up" in reason())
usage()
safety.STEP_ASIDE_FILE.write_text(json.dumps({"by": "photo pilot", "until": (safety.now() + timedelta(hours=1)).isoformat()}))
check("while the photo pilot has asked: waits", "photo pilot" in reason())
safety.STEP_ASIDE_FILE.write_text(json.dumps({"by": "scraper", "until": (safety.now() - timedelta(minutes=1)).isoformat()}))
check("a request left by a crashed scraper ends by itself", reason() is None)
service.online = lambda: False
check("no internet: waits", reason() == "no internet")
service.online, service.database_up = (lambda: True), (lambda: False)
check("the database not answering: waits", "database" in reason())
service.database_up = lambda: True

print("3. The daily upkeep")
steps = [s[0] for s in service.MAINTENANCE_STEPS]
check("only the safe steps: the ETL and the units table (no Telegram)", steps == ["etl_runner.py", "listing_units.py"])
check("never run_all.py or its repair scripts, which write guesses as protected values",
      not {"run_all.py", "Fix_extraction.py", "dedup_and_fix_locations.py", "telegram_scraper.py"} & set(steps))

print("4. Crashes")
check("restarts after a crash slow down: 1, 2, 5, 10, then 30 minutes", service.CRASH_WAITS == [60, 120, 300, 600, 1800])
check("at most 10 restarts a day", service.CRASHES_PER_DAY == 10)
waits, codes = [], iter([1, 1, 0])
service.SERVICE_DIR, service.LOG_FILE = state, state / "service.log"
service.MAINTENANCE_FILE = state / "maintenance.txt"
service.MAINTENANCE_FILE.write_text(safety.now().date().isoformat())   # today's upkeep is done
service.health.HEALTH_DIR = state / "health"
service.run_listener = lambda: next(codes)


class Done(Exception):
    pass


def fake_sleep(seconds):
    waits.append(seconds)
    if len(waits) == 3:
        raise Done


service.time = type("T", (), {"sleep": staticmethod(fake_sleep)})
service.threading = type("Th", (), {"Thread": lambda **k: type("X", (), {"start": lambda self: None})()})
try:
    service.serve()
except Done:
    pass
check("two crashes: restarted after 1, then 2 minutes; a normal end: back after 30 seconds", waits == [60, 120, 30])
check("the crashes are in the day's health log", service.health.read()["restarts"] == 2)

print("5. The gaps and the daily completeness check")
service.COMPLETENESS_DIR = state / "completeness"
service.health._alive_file().unlink(missing_ok=True)
waits.clear()
service.why_not_start = lambda: ("the scraper is using Telegram", 60)
try:
    service.serve()
except Done:
    pass
check("while the scraper has the account, the listener counts as alive (the scraper reads the channels itself)",
      service.health.last_alive() is not None and (safety.now() - service.health.last_alive()).total_seconds() < 60)
service.LISTENER_STARTED[:] = [safety.now() - timedelta(minutes=30)]
service.FIRST_CHECK_DAY = safety.now().date() - timedelta(days=10)
service.health.mark_alive()
yesterday, before = safety.now().date() - timedelta(days=1), safety.now().date() - timedelta(days=2)
check("connected for 30 minutes, nothing checked yet: yesterday and the day before are due",
      service.completeness_due() == [before, yesterday])
service.COMPLETENESS_DIR.mkdir(parents=True, exist_ok=True)
(service.COMPLETENESS_DIR / f"{before}.json").write_text(json.dumps({"day": str(before), "stopped": None}))
check("a day already checked is not checked again", service.completeness_due() == [yesterday])
(service.COMPLETENESS_DIR / f"{before}.json").write_text(json.dumps(
    {"day": str(before), "stopped": "HTTP Error 429", "checked_at": (safety.now() - timedelta(hours=4)).isoformat()}))
check("a check stopped early (a sign of blocking) is tried again only after 3 hours",
      service.completeness_due() == [before, yesterday])
service.health.catch_up_running(True)
check("not while a catch-up read is running: its messages must be in first", service.completeness_due() == [])
service.health.catch_up_running(False)
service.LISTENER_STARTED[:] = [safety.now() - timedelta(minutes=5)]
check("not in the first 15 minutes after the listener started (a catch-up may be about to begin)",
      service.completeness_due() == [])
service.LISTENER_STARTED[:] = [safety.now() - timedelta(minutes=30)]
service.health._alive_file().write_text((safety.now() - timedelta(minutes=20)).isoformat())
check("not while the listener is not connected", service.completeness_due() == [])
service.health.mark_alive()
for d in (before, yesterday):
    (service.COMPLETENESS_DIR / f"{d}.json").write_text(json.dumps(
        {"day": str(d), "stopped": None, "complete": d == before, "checked_at": (safety.now() - timedelta(hours=2)).isoformat()}))
check("days checked and done: nothing due", service.completeness_due() == [])
service.health.catch_up_ended()
check("a catch-up read after the check: an incomplete day is checked again (its messages may be in now), "
      "a complete one is not", service.completeness_due() == [yesterday])
(service.COMPLETENESS_DIR / f"{yesterday}.json").write_text(json.dumps(
    {"day": str(yesterday), "stopped": None, "complete": False, "checked_at": (safety.now() + timedelta(seconds=1)).isoformat()}))
check("checked again after the catch-up: not a third time", service.completeness_due() == [])
service.FIRST_CHECK_DAY = yesterday
for d in (before, yesterday):
    (service.COMPLETENESS_DIR / f"{d}.json").unlink()
check("never a day before the owner's test began (20 November 2026)", service.completeness_due() == [yesterday])

print(f"\n{'PASS: the service starts the listener only when it is safe' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
