r"""
listener_service.py
-------------------
Keeps the live listener running all day (Phase 1 of ROADMAP.md). It starts with the laptop
(listener_autostart.py puts it in Windows' Startup folder) and runs without a window:

  - waits for the internet and the database before starting the listener;
  - restarts the listener if it crashes: after 1, 2, 5, 10, then 30 minutes, at most 10 times a day;
  - never logs in: with no login file, or after Telegram ended the login, it waits and does nothing
    until the owner has logged in again by hand (a newer login file);
  - after any warning from Telegram it waits until the pause in telegram_usage.json has ended;
  - makes way for the scraper and the photo pilot (telegram_safety.StepAside): the listener disconnects,
    and starts again when they are done; it never runs at the same time as them (one lock);
  - once a day (after 03:00 Addis Ababa time) runs `run_all.py --skip-scrape` with no Telegram use: the
    repair steps, the full repeat check (with its backup), the units table and the views, as after a scrape.

Only one copy runs (data/listener/service.lock). Its log: data/listener/service.log; the day's counts and
warnings: listener_health.py (database\scrape_check.py shows them).

    venv\Scripts\pythonw.exe src\listener_service.py      (normally started by Windows at log-on)
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import listener_health as health
import telegram_safety as safety

BASE_DIR = Path(__file__).resolve().parents[1]
SERVICE_DIR = BASE_DIR / "data" / "listener"
LOG_FILE = SERVICE_DIR / "service.log"
SERVICE_LOCK = SERVICE_DIR / "service.lock"
MAINTENANCE_FILE = SERVICE_DIR / "last_maintenance.txt"
PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe"
CRASH_WAITS = [60, 120, 300, 600, 1800]   # seconds before the 1st, 2nd, … restart after a crash
CRASHES_PER_DAY = 10
MAINTENANCE_HOUR = 3


def log(text: str) -> None:
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{safety.now():%Y-%m-%d %H:%M:%S} {text}\n")


def online() -> bool:
    """The internet answers (a name lookup and a connection to Telegram's web address, no account used)."""
    try:
        socket.create_connection(("t.me", 443), timeout=10).close()
        return True
    except OSError:
        return False


def database_up() -> bool:
    try:
        from sqlalchemy import create_engine, text

        from settings import DB_URL
        with create_engine(DB_URL).connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def login_ended_waiting_for_owner() -> bool:
    """Telegram ended the login and the owner has not logged in again since (the login file is older)."""
    state = safety.DailyBudget().state
    if "login" not in (state.get("block_reason") or "") or not state.get("blocked_until"):
        return False
    path = safety.session_file()
    ended_at = datetime.fromisoformat(state["blocked_until"]) - timedelta(seconds=safety.LOGIN_ENDED_WAIT)
    return not path.exists() or datetime.fromtimestamp(path.stat().st_mtime, safety.ETHIOPIA) < ended_at


def why_not_start() -> tuple[str, float] | None:
    """(reason, seconds to wait) when the listener must not start now; None when it may."""
    if not safety.session_file().exists():
        return "no login file: waiting for the owner to log in by hand", 1800
    if login_ended_waiting_for_owner():
        return "Telegram ended the login: waiting for the owner to log in again by hand", 1800
    state = safety.DailyBudget().state
    until = state.get("blocked_until")
    if until and datetime.fromisoformat(until) > safety.now():
        wait = (datetime.fromisoformat(until) - safety.now()).total_seconds()
        return f"Telegram use is paused until {datetime.fromisoformat(until):%Y-%m-%d %H:%M} ({state.get('block_reason')})", min(wait + 60, 3600)
    if state.get("requests", 0) >= safety.DAILY_REQUEST_CAP:
        return "today's 150 Telegram requests are used up", 1800
    by = safety.step_aside_request()
    if by:
        return f"the {by} is using Telegram", 60
    if not online():
        return "no internet", 60
    if not database_up():
        return "the database is not answering", 60
    return None


def maintenance_due() -> bool:
    today = safety.now().date().isoformat()
    try:
        done = MAINTENANCE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        done = ""
    return done != today and safety.now().hour >= MAINTENANCE_HOUR


def run_maintenance() -> None:
    """The steps after a scrape, without scraping (no Telegram use)."""
    MAINTENANCE_FILE.write_text(safety.now().date().isoformat(), encoding="utf-8")
    log("daily maintenance: run_all.py --skip-scrape")
    with open(SERVICE_DIR / "maintenance.log", "w", encoding="utf-8") as out:
        code = subprocess.call([str(PYTHON), "-X", "utf8", str(BASE_DIR / "src" / "run_all.py"), "--skip-scrape"],
                               cwd=BASE_DIR, stdout=out, stderr=subprocess.STDOUT, creationflags=_NO_WINDOW)
    log(f"daily maintenance ended (exit code {code})")
    if code:
        health.note("error", f"daily run_all.py --skip-scrape ended with exit code {code} (data/listener/maintenance.log)")


_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run_listener() -> int:
    with open(SERVICE_DIR / "listener.log", "a", encoding="utf-8") as out:
        return subprocess.call([str(PYTHON), "-X", "utf8", str(BASE_DIR / "src" / "listener.py")], cwd=BASE_DIR,
                               stdout=out, stderr=subprocess.STDOUT, creationflags=_NO_WINDOW)


def maintenance_loop() -> None:
    """Beside the listener: the daily upkeep, once a day after 03:00."""
    while True:
        try:
            if maintenance_due():
                run_maintenance()
        except Exception as e:
            log(f"daily maintenance failed: {type(e).__name__}: {e}")
        time.sleep(600)


def serve() -> None:
    crashes: dict[str, int] = {}
    last_wait = None
    log("service started")
    threading.Thread(target=maintenance_loop, daemon=True).start()
    while True:
        blocked = why_not_start()
        if blocked:
            reason, seconds = blocked
            if reason != last_wait:
                log(f"waiting: {reason}")
                last_wait = reason
            time.sleep(seconds)
            continue
        last_wait = None
        log("starting the listener")
        code = run_listener()
        log(f"the listener ended (exit code {code})")
        if code in (0, 2):   # ended normally, stepped aside, or a safety stop (why_not_start then explains)
            time.sleep(30)
            continue
        today = safety.now().date().isoformat()
        crashes[today] = crashes.get(today, 0) + 1
        n = crashes[today]
        health.add(restarts=1)
        health.note("error", f"the listener crashed (exit code {code}); restart {n} of {CRASHES_PER_DAY} today")
        if n >= CRASHES_PER_DAY:
            log("too many crashes today: waiting until tomorrow")
            tomorrow = datetime.combine(safety.now().date() + timedelta(days=1), datetime.min.time(), safety.ETHIOPIA)
            time.sleep((tomorrow - safety.now()).total_seconds() + 60)
        else:
            time.sleep(CRASH_WAITS[min(n, len(CRASH_WAITS)) - 1])


def main() -> int:
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None:   # started without a window (pythonw): print nowhere
        sys.stdout = sys.stderr = open(os.devnull, "w")
    handle = open(SERVICE_LOCK, "a+")
    try:
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, ImportError):
        print("The listener service is already running.")
        return 1
    try:
        serve()
    except Exception as e:   # never silent: the reason goes to the log and the day's health notes
        log(f"service stopped by an error: {type(e).__name__}: {e}")
        health.note("error", f"the listener service stopped: {type(e).__name__}: {e}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
