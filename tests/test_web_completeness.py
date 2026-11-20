"""
test_web_completeness.py
------------------------
Checks database/web_completeness_check.py, the Phase 1 test of ROADMAP.md (every post of a day reached the
database), with stand-in web pages and a stand-in database: no network, no database, no Telegram.

Usage:
    venv\\Scripts\\python.exe tests\\test_web_completeness.py
"""

import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "database"))
sys.path.insert(0, str(ROOT / "src"))

import web_completeness_check as wc  # noqa: E402

failures = 0


def check(label, condition):
    global failures
    failures += not condition
    print(f"  {'ok  ' if condition else 'FAIL'} {label}")


def post(channel, n, utc):
    return (f'<div class="tgme_widget_message js-widget_message" data-post="{channel}/{n}">'
            f'<a class="tgme_widget_message_date" href="https://t.me/{channel}/{n}"><time datetime="{utc}" class="time">'
            "</time></a></div>")


def page(channel, posts, before=None):
    more = f'<a class="tme_messages_more js-messages_more" data-before="{before}"></a>' if before else ""
    return "<html>" + more + "".join(post(channel, n, t) for n, t in posts) + "</html>"


DAY = date(2026, 11, 21)   # posts are given in UTC; Addis Ababa is UTC+3
PAGES = {
    # three posts on the day (one at 23:30 Addis = 20:30 UTC), one the day before (22:00 Addis on 20 Nov)
    "https://t.me/s/chanA": page("chanA", [(10, "2026-11-20T19:00:00+00:00"), (11, "2026-11-21T06:00:00+00:00"),
                                           (12, "2026-11-21T12:00:00+00:00"), (13, "2026-11-21T20:30:00+00:00"),
                                           (14, "2026-11-21T21:30:00+00:00")]),
    # the day runs over two pages
    "https://t.me/s/chanB": page("chanB", [(30, "2026-11-21T10:00:00+00:00"), (31, "2026-11-21T11:00:00+00:00")], before=30),
    "https://t.me/s/chanB?before=30": page("chanB", [(28, "2026-11-20T15:00:00+00:00"), (29, "2026-11-21T01:00:00+00:00")]),
    # no public page: Telegram's plain "View in Telegram" page
    "https://t.me/s/chanC": '<html><div class="tgme_page"><div class="tgme_page_extra">1 subscriber</div></div></html>',
}
asked, pauses = [], []


def fake_get(url):
    asked.append(url)
    if url not in PAGES:
        raise wc.Blocked(f"{url}: HTTP Error 429")
    return PAGES[url]


def lookup(saved):
    return lambda channel, ids: {i for i in ids if i in saved.get(channel, set())}


wc.REGULAR_CHANNELS, wc.FORUM_GROUPS = ["@chanA", "@chanB", "@chanC"], ["@forum"]
wc.RESULTS_DIR = Path(tempfile.mkdtemp()) / "completeness"   # never the real results

print("1. Reading the public pages")
r = wc.check_day(DAY, wc.Web(fake_get, pauses.append), lookup({"@chanA": {11, 12, 13}, "@chanB": {29, 30, 31}}))
check("only the day's posts, by Addis Ababa time (23:30 counts, 00:30 the next day does not)",
      r["channels"]["@chanA"]["posted"] == 3)
check("a day over two pages: the older page is read too, and it stops at the day's start",
      r["channels"]["@chanB"]["posted"] == 3 and asked.count("https://t.me/s/chanB?before=30") == 1)
check("a channel without a public page, and the forum groups: reported as not checkable",
      r["no_public_page"] == ["@forum (forum group)", "@chanC"])
check("one request every 20-40 seconds: a pause before every request but the first",
      len(pauses) == len(asked) - 1 and all(20 <= p <= 40 for p in pauses))
check("everything saved: the day is complete", r["complete"] and r["missing"] == 0)

print("2. A missing post")
r = wc.check_day(DAY, wc.Web(fake_get, pauses.append), lookup({"@chanA": {11, 13}, "@chanB": {29, 30, 31}}))
check("a post not in the database is named, with its time", r["channels"]["@chanA"]["missing"] == [[12, "15:00"]])
check("then the day is not complete", not r["complete"] and r["missing"] == 1)

print("3. Web safety")
PAGES.pop("https://t.me/s/chanB?before=30")
asked.clear()
r = wc.check_day(DAY, wc.Web(fake_get, pauses.append), lookup({}))
check("the first error stops the run: no request after it", r["stopped"] and asked[-1] == "https://t.me/s/chanB?before=30"
      and "https://t.me/s/chanC" not in asked)
check("a stopped run never counts as complete", not r["complete"])
web = wc.Web(lambda url: PAGES["https://t.me/s/chanA"], lambda s: None)
web.made = wc.REQUESTS_PER_RUN
try:
    web.page("https://t.me/s/chanA")
    check("at most 120 requests in one run", False)
except wc.Blocked:
    check("at most 120 requests in one run", True)

print("4. Three days in a row")
for i, done in enumerate([True, True, False, True]):   # 21, 20, 19, 18 Nov
    wc.save({"day": (DAY - timedelta(days=i)).isoformat(), "complete": done})
check("counts the complete days in a row back from the given day, and stops at the first that is not",
      wc.streak(DAY) == 2)
check("a day not checked yet breaks the run", wc.streak(DAY + timedelta(days=1)) == 0)

print(f"\n{'PASS: the completeness check reads the pages safely and counts right' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
