r"""
telegram_safety.py
------------------
Protects the owner's Telegram account (see "Telegram account safety" in CLAUDE.md).
telegram_scraper.py and listener.py use it; nothing else in the project opens the account.

- Login: the existing login file is used as it is. If it is missing or no longer valid the
  program stops with a message; it never starts a new login (no code is ever requested).
- One at a time: the scraper and the listener hold one lock file while they run, so they
  can never run together (the lock is released automatically when a program ends).
- Slow: long random pauses, few messages per channel, and a daily cap on requests and runs,
  counted in data/sessions/telegram_usage.json.
- Warnings: any warning from Telegram (it asks us to wait, the login is ended, the account
  is limited) stops the program and blocks Telegram use until the next day (or longer, if
  Telegram asked for a longer wait).
tests/test_telegram_safety.py checks all of this without connecting to Telegram.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from telethon.errors import (AuthKeyError, ChannelForumMissingError, ChannelInvalidError, ChannelPrivateError,
                             ChatAdminRequiredError, RPCError, UnauthorizedError, UsernameInvalidError,
                             UsernameNotOccupiedError)

BASE_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = BASE_DIR / "data" / "sessions"
SESSION = STATE_DIR / "ollaa_session.session"     # the one login file
LEGACY_SESSION = BASE_DIR / "ollaa_session.session"  # where older copies of the scraper kept it
LOCK_FILE = STATE_DIR / "telegram.lock"
USAGE_FILE = STATE_DIR / "telegram_usage.json"
ETHIOPIA = timezone(timedelta(hours=3))          # days start at midnight Addis Ababa time

# ── Limits ───────────────────────────────────────────────────────
MESSAGES_PER_CHANNEL = 40           # newest messages read per channel per run (was up to 100)
TOPICS_PER_GROUP = 10               # forum topics with the newest messages, per group per run (was all)
MESSAGES_PER_TOPIC = 20             # newest messages per forum topic (was up to 720)
PAUSE_BETWEEN_CHANNELS = (45, 120)  # seconds, random (was 8-15)
PAUSE_BETWEEN_TOPICS = (20, 45)     # seconds, random (was 2)
PAUSE_BETWEEN_REQUESTS = (5, 15)    # seconds, random, between two requests for one channel (was none)
DAILY_REQUEST_CAP = 150             # Telegram requests per day, scraper and listener together
RUNS_PER_DAY = 2                    # scraper runs per day
LOGIN_ENDED_WAIT = 24 * 3600        # after a login ends: no use for at least 24 hours
# Telethon waits out short FloodWaits by itself and carries on; 0 makes every one stop us.
FLOOD_SLEEP_THRESHOLD = 0

# A problem with one channel (left, renamed, private, not a forum): skip that channel only.
CHANNEL_PROBLEMS = (ChannelPrivateError, ChannelInvalidError, UsernameInvalidError, UsernameNotOccupiedError,
                    ChatAdminRequiredError, ChannelForumMissingError)


class SafetyStop(Exception):
    """The program must stop now; the message says why, in plain words."""


def now() -> datetime:
    return datetime.now(ETHIOPIA)


def session_file() -> Path:
    override = os.getenv("TG_SESSION_NAME")
    if override:
        path = Path(override) if Path(override).is_absolute() else BASE_DIR / override
        return path if path.suffix == ".session" else path.with_name(path.name + ".session")
    return LEGACY_SESSION if not SESSION.exists() and LEGACY_SESSION.exists() else SESSION


def require_session_file() -> Path:
    """The login file to use; stops if there is none. Call before creating a TelegramClient,
    which would otherwise create an empty login file."""
    path = session_file()
    if not path.exists():
        raise SafetyStop(f"No Telegram login file on this computer ({path}). The scraper and the listener "
                         "never log in by themselves. Run them only on the computer that holds the working "
                         "login (see CLAUDE.md).")
    return path


def api_credentials() -> tuple[int, str]:
    from settings import TG_API_HASH, TG_API_ID
    if not (TG_API_ID and TG_API_HASH and TG_API_ID.strip().isdigit()):
        raise SafetyStop("TG_API_ID and TG_API_HASH are missing from .env (the owner's own values from "
                         "my.telegram.org).")
    return int(TG_API_ID), TG_API_HASH


async def connect_with_existing_login(client, budget: DailyBudget) -> None:
    """Connect with the login file as it is; stop if it is no longer valid. Never calls
    client.start(), which would ask Telegram for a login code."""
    try:
        await client.connect()
        authorized = await client.is_user_authorized()
    except RPCError as e:
        await client.disconnect()
        raise stop_after_warning(budget, e, "on connecting")
    except (OSError, asyncio.TimeoutError) as e:
        await client.disconnect()
        raise SafetyStop(f"Could not reach Telegram ({type(e).__name__}). Nothing was read; try again later.")
    if not authorized:
        await client.disconnect()
        until = budget.block("the login is no longer valid", LOGIN_ENDED_WAIT)
        raise SafetyStop("The Telegram login on this computer is no longer valid. Stopped without logging in. "
                         f"Telegram is not used again until {until:%Y-%m-%d %H:%M} (Addis Ababa time); after "
                         "that the owner logs in once, by hand, on this one computer (see CLAUDE.md).")


class TelegramLock:
    """Only one program uses the account at a time (scraper or listener)."""

    def __init__(self, program: str):
        self.program, self.handle = program, None

    def __enter__(self):
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        info = LOCK_FILE.with_suffix(".info")
        self.handle = open(LOCK_FILE, "a+")
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            who = info.read_text(encoding="utf-8") if info.exists() else "another program"
            raise SafetyStop(f"Telegram is already in use by {who}. The scraper and the listener never run "
                             "at the same time: wait until it has finished (or stop the listener).")
        info.write_text(f"the {self.program} (started {now():%Y-%m-%d %H:%M})", encoding="utf-8")
        return self

    def __exit__(self, *exc):
        if self.handle:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()   # closing the file releases the lock (also if the program crashes)
            self.handle = None


class DailyBudget:
    """Requests and runs per day, and the "stopped until" mark after a warning."""

    def __init__(self):
        self.state = json.loads(USAGE_FILE.read_text(encoding="utf-8")) if USAGE_FILE.exists() else {}
        self.new_day()

    def new_day(self) -> None:
        """Counts start again at midnight; a "stopped until" mark is kept until it ends."""
        today = now().date().isoformat()
        if self.state.get("day") != today:
            self.state = {"day": today, "requests": 0, "runs": 0,
                          "blocked_until": self.state.get("blocked_until"),
                          "block_reason": self.state.get("block_reason")}

    def save(self) -> None:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def check_not_blocked(self) -> None:
        until = self.state.get("blocked_until")
        if until and datetime.fromisoformat(until) > now():
            raise SafetyStop(f"Telegram use is paused until {datetime.fromisoformat(until):%Y-%m-%d %H:%M} (Addis "
                             f"Ababa time): {self.state.get('block_reason')}.")

    def start_scraper_run(self) -> None:
        self.new_day()
        self.check_not_blocked()
        if self.state["runs"] >= RUNS_PER_DAY:
            raise SafetyStop(f"The scraper already ran {self.state['runs']} times today (limit {RUNS_PER_DAY}). "
                             "Try again tomorrow.")
        if self.state["requests"] >= DAILY_REQUEST_CAP:
            raise SafetyStop(f"Today's limit of {DAILY_REQUEST_CAP} Telegram requests is used up. Try again tomorrow.")
        self.state["runs"] += 1
        self.save()

    def can_spend(self) -> bool:
        self.new_day()
        return self.state["requests"] < DAILY_REQUEST_CAP

    def spend(self) -> None:
        """Count one request before it is made; stop when the day's cap is reached."""
        if not self.can_spend():
            raise SafetyStop(f"Today's limit of {DAILY_REQUEST_CAP} Telegram requests is reached: stopping. "
                             "What was read so far is saved; the rest waits until tomorrow.")
        self.state["requests"] += 1
        self.save()

    def block(self, reason: str, seconds: int = 0) -> datetime:
        """After a warning: no Telegram use until the next day, or longer if Telegram asked."""
        tomorrow = datetime.combine(now().date() + timedelta(days=1), datetime.min.time(), ETHIOPIA)
        until = max(tomorrow, now() + timedelta(seconds=seconds + 3600 if seconds else 0))
        self.state["blocked_until"] = until.isoformat()
        self.state["block_reason"] = reason
        self.save()
        return until


def stop_after_warning(budget: DailyBudget, error: RPCError, where: str) -> SafetyStop:
    """Block Telegram use until tomorrow (or longer) and return the stop to raise."""
    if isinstance(error, (UnauthorizedError, AuthKeyError)):
        reason, seconds = f"the login has ended ({type(error).__name__})", LOGIN_ENDED_WAIT
    else:
        reason, seconds = f"{type(error).__name__}", getattr(error, "seconds", 0) or 0
    until = budget.block(reason, seconds)
    return SafetyStop(f"Telegram gave a warning {where}: {reason}. Everything stopped at once, with no retry; "
                      f"Telegram is not used again until {until:%Y-%m-%d %H:%M} (Addis Ababa time).")


async def pause(seconds_range) -> None:
    await asyncio.sleep(random.uniform(*seconds_range))
