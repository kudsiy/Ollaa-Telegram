r"""
scrape_check.py
---------------
What the Telegram scraper did, checked without contacting Telegram. Read-only.

- the login file: there or not (never its content)
- Telegram use today (data/sessions/telegram_usage.json): scraper runs, requests used,
  and any pause with its reason
- raw messages saved in the last 24 hours, per channel, with the newest post date

Usage:
    venv\Scripts\python.exe database\scrape_check.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

import telegram_safety as safety  # noqa: E402
from settings import DB_URL  # noqa: E402

SAVED_SQL = text("""
    SELECT channel, count(*) AS saved, max(posted_at) AS newest
    FROM telegram_listings
    WHERE created_at >= LOCALTIMESTAMP - interval '24 hours'
    GROUP BY channel
    ORDER BY saved DESC, channel
""")


def main() -> None:
    login = safety.session_file()
    print(f"Login file: {'there' if login.exists() else 'MISSING'} ({login})")

    budget = safety.DailyBudget()   # reads the counts; changes nothing
    state = budget.state
    print(f"Today ({state['day']}): {state['runs']} of {safety.RUNS_PER_DAY} scraper runs, "
          f"{state['requests']} of {safety.DAILY_REQUEST_CAP} Telegram requests used")
    try:
        budget.check_not_blocked()
        print("Telegram use: allowed")
    except safety.SafetyStop as e:
        print(str(e).replace("Telegram use is paused", "Telegram use: paused"))

    with create_engine(DB_URL).connect() as conn:
        rows = conn.execute(SAVED_SQL).fetchall()
        total = conn.execute(text("SELECT count(*) FROM telegram_listings")).scalar()
    print(f"\nRaw messages saved in the last 24 hours: {sum(r.saved for r in rows)} "
          f"(all raw messages: {total:,})")
    for r in rows:
        newest = f"{r.newest:%Y-%m-%d}" if r.newest else "?"
        print(f"  {r.saved:>4}  {r.channel.rsplit('/', 1)[-1]:<40} newest post {newest}")
    if rows:
        print("\nNext step, to turn them into listings: venv\\Scripts\\python.exe src\\etl_runner.py")


if __name__ == "__main__":
    main()
