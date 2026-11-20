r"""
web_completeness_check.py
-------------------------
Did every post of a day end up in the database? (Phase 1 of ROADMAP.md, the owner's definition of 20 November
2026: Phase 1 is done after 3 days in a row on which every advert posted in the channels reached the database,
through the listener or its catch-up read.)

It reads each channel's public web page, https://t.me/s/<channel>, which needs no Telegram account: the post
numbers and times of the day, page after page back to the day's start, then looks each one up in
telegram_listings. Read-only; it never uses the Telegram login.

Web safety, as for src/media_web_fetch.py: one request every 20-40 seconds (random), at most 4 pages per channel
and 120 requests per run, and it stops at the first error or sign of blocking. A chat without a public page (the
forum groups, and channels that show none) cannot be checked and is reported as such.

Each day's result goes to data/listener/completeness/<day>.json (data/ is never committed);
listener_service.py runs it daily for the days not yet checked, and database\scrape_check.py shows the result.

Usage:
    venv\Scripts\python.exe database\web_completeness_check.py                  (yesterday, Addis Ababa time)
    venv\Scripts\python.exe database\web_completeness_check.py --day 2026-11-21
    venv\Scripts\python.exe database\web_completeness_check.py --streak         (complete days in a row; no web)
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import telegram_safety as safety  # noqa: E402
from channels import FORUM_GROUPS, REGULAR_CHANNELS  # noqa: E402

RESULTS_DIR = BASE_DIR / "data" / "listener" / "completeness"
PAUSE = (20, 40)            # seconds between two web requests, random
PAGES_PER_CHANNEL = 4
REQUESTS_PER_RUN = 120
POST_RE = re.compile(r'tgme_widget_message_date" href="https://t\.me/[^/"]+/(\d+)"><time datetime="([^"]+)"')
MORE_RE = re.compile(r'tme_messages_more[^"]*" data-before="(\d+)"')


class Blocked(Exception):
    """The web page answered with an error or looks blocked: the run stops."""


def posts_on_page(html: str) -> list[tuple[int, datetime]]:
    """(post number, time in Addis Ababa) of every post on one public page; service notes have no date link."""
    return [(int(n), datetime.fromisoformat(t).astimezone(safety.ETHIOPIA)) for n, t in POST_RE.findall(html)]


def older_page(html: str):
    m = MORE_RE.search(html)
    return int(m.group(1)) if m else None


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        raise Blocked(f"{url}: {type(e).__name__}: {e}")
    if "tgme_widget_message" not in html and "tgme_channel_info" not in html and "tgme_page_extra" not in html:
        raise Blocked(f"{url}: an unexpected page (a sign of blocking)")
    return html   # a channel without a public page sends its plain "View in Telegram" page: no posts


class Web:
    """Paced requests: one every 20-40 seconds, at most REQUESTS_PER_RUN in one run."""

    def __init__(self, get=fetch, sleep=time.sleep):
        self.get, self.sleep, self.made = get, sleep, 0

    def page(self, url: str) -> str:
        if self.made >= REQUESTS_PER_RUN:
            raise Blocked(f"the limit of {REQUESTS_PER_RUN} web requests for one run is reached")
        if self.made:
            self.sleep(random.uniform(*PAUSE))
        self.made += 1
        return self.get(url)


def posts_of_day(web: Web, channel: str, day: date):
    """The day's posts of one channel from its public pages; None when it has no public page."""
    start = datetime.combine(day, datetime.min.time(), safety.ETHIOPIA)
    end = start + timedelta(days=1)
    name = channel.lstrip("@")
    found, before = {}, None
    for page in range(PAGES_PER_CHANNEL):
        html = web.page(f"https://t.me/s/{name}" + (f"?before={before}" if before else ""))
        posts = posts_on_page(html)
        if not posts:
            return None if page == 0 else (found, True)
        found.update({n: t for n, t in posts if start <= t < end})
        before = older_page(html)
        if min(t for _, t in posts) < start or before is None:
            return found, True
    return found, False   # the day did not fit in PAGES_PER_CHANNEL pages: older posts not checked


def saved_ids(channel: str, ids: list[int]) -> set[int]:
    from sqlalchemy import create_engine, text

    from settings import DB_URL
    if not ids:
        return set()
    with create_engine(DB_URL).connect() as conn:
        rows = conn.execute(text("SELECT message_id FROM telegram_listings WHERE lower(channel) = lower(:c) "
                                 "AND message_id = ANY(:ids)"),
                            {"c": f"https://t.me/{channel.lstrip('@')}", "ids": ids}).all()
    return {int(r[0]) for r in rows}


def check_day(day: date, web: Web | None = None, lookup=saved_ids, channels=None) -> dict:
    web = web or Web()
    result = {"day": day.isoformat(), "checked_at": safety.now().isoformat(timespec="minutes"),
              "channels": {}, "no_public_page": [f"{g} (forum group)" for g in FORUM_GROUPS], "stopped": None}
    for channel in channels or REGULAR_CHANNELS:
        try:
            got = posts_of_day(web, channel, day)
        except Blocked as e:
            result["stopped"] = str(e)
            break
        if got is None:
            result["no_public_page"].append(channel)
            continue
        posts, whole_day = got
        have = lookup(channel, sorted(posts))
        missing = sorted(set(posts) - have)
        result["channels"][channel] = {"posted": len(posts), "saved": len(posts) - len(missing), "whole_day": whole_day,
                                       "missing": [[n, posts[n].strftime("%H:%M")] for n in missing]}
    ch = result["channels"].values()
    result["posted"] = sum(c["posted"] for c in ch)
    result["missing"] = sum(len(c["missing"]) for c in ch)
    result["complete"] = (result["stopped"] is None and result["missing"] == 0 and all(c["whole_day"] for c in ch)
                          and len(result["channels"]) + len(result["no_public_page"]) == len(REGULAR_CHANNELS) + len(FORUM_GROUPS))
    return result


def save(result: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{result['day']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def read(day: date):
    try:
        return json.loads((RESULTS_DIR / f"{day.isoformat()}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def streak(until: date | None = None) -> int:
    """Complete days in a row, ending with `until` (yesterday by default)."""
    day, n = until or safety.now().date() - timedelta(days=1), 0
    while (r := read(day)) and r.get("complete"):
        n, day = n + 1, day - timedelta(days=1)
    return n


def report(r: dict) -> str:
    lines = [f"{r['day']}: {r['posted']} posts on the public pages, {r['missing']} not in the database "
             f"-> {'COMPLETE' if r['complete'] else 'NOT COMPLETE'}"]
    for name, c in r["channels"].items():
        if c["missing"] or not c["whole_day"]:
            lines.append(f"    {name}: {c['saved']} of {c['posted']} saved"
                         + (f"; missing {', '.join(f'{n} ({t})' for n, t in c['missing'])}" if c["missing"] else "")
                         + ("" if c["whole_day"] else "; the day did not fit in 4 pages"))
    lines.append(f"    not checkable (no public page): {', '.join(r['no_public_page'])}")
    if r["stopped"]:
        lines.append(f"    STOPPED early: {r['stopped']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", help="YYYY-MM-DD (default: yesterday, Addis Ababa time)")
    ap.add_argument("--streak", action="store_true", help="only count the complete days in a row (no web)")
    args = ap.parse_args()
    if args.streak:
        print(f"Complete days in a row (ending yesterday): {streak()} of 3")
        return 0
    day = date.fromisoformat(args.day) if args.day else safety.now().date() - timedelta(days=1)
    if day >= safety.now().date():
        print("Only a day that has ended can be checked.")
        return 1
    r = check_day(day)
    save(r)
    print(report(r))
    print(f"Complete days in a row (ending yesterday): {streak()} of 3")
    return 0 if r["stopped"] is None else 2


if __name__ == "__main__":
    sys.exit(main())
