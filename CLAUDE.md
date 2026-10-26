# Rules for working on Ollaa-Telegram

Read `STATUS.md` first: it has the audit findings and the numbered fix list (S1, S2, …).

## Working with the owner

- The owner is not a programmer. Explain in simple words, do the technical work yourself,
  and stop only for things the owner must do in person (paste a key, approve a login).
- Never show a password, API key, token or phone-login code in the chat, in a commit, or
  in a file other than `.env`. When printing code or data that might contain one, mask it.

## Git and GitHub

- The GitHub repository `kudsiy/Ollaa-Telegram` is **public**.
- Commit and push after every finished task, so work never stays on one computer.
  Do each task on its own branch, then merge into `main` when it is safe.
- After a task is finished, update its row in the `STATUS.md` fix list.
- Never commit: `.env`, `*.session` (Telegram logins), `venv/`, `data/`, or the large
  `*.txt` / `*.csv` dumps in the project root. They hold secrets or other people's phone
  numbers, and `.gitignore` already lists them.

## Secrets and settings

- Every password, key and connection detail lives in `.env` (project root, never
  committed). `.env.example` lists the names with empty values.
- Code reads them only through `src/settings.py` (`DB_URL`, `DB_CONFIG`, `GEMINI_API_KEY`,
  `TG_API_ID`, `TG_API_HASH`, `TG_PHONE`). Never write a password or key into a script.
- Scripts in `src/` import it directly: `from settings import DB_URL`.
  Scripts in the project root first add `src` to the import path (see `test_db.py`).
- `check_setup.py` tests that `.env` is complete, the database login works and the
  Gemini key works.

## Database safety

- Database: PostgreSQL 18 on this laptop, database `ollaa`. Main tables:
  `telegram_listings` (raw messages) and `processed_listings` (parsed listings).
- Before any task that changes data, take a backup:
  `"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U postgres -Fc -f backups\ollaa_<date>.dump ollaa`
  (the password is `DB_PASSWORD` in `.env`; keep `backups\` out of git).
- `database/schema.sql` rebuilds the whole structure (no data). It is made by
  `database/export_schema.py` from the live database; never edit it by hand. After any
  change to tables, views or functions, run `database\export_schema.py` and then
  `database\export_schema.py --check` (it must say "identical"), and commit both.
- Never run `etl_runner.py --reset` or `run_all.py --reset`: they delete every processed
  row, including hand repairs (finding 12 in `STATUS.md`).
- Measure first: count the rows a change will touch, change them, count again, and
  report both numbers.

## How the project runs

- Python: always use the project's own environment, `venv\Scripts\python.exe`.
  Install packages from `requirements.txt` (versions are pinned on purpose).
- `src/channels.py` is the one list of Telegram channels and groups (`REGULAR_CHANNELS`,
  `FORUM_GROUPS`). `src/telegram_scraper.py` reads exactly these into `telegram_listings`.
- `src/listener.py` saves messages only from chats in `src/channels.py`, never from private
  chats. `tests/test_listener_privacy.py` checks this; run it after any listener change.
- `src/etl_runner.py` runs `src/run_pipeline.py` (`ValuationPipeline`) on every raw
  message and writes `processed_listings` and `rental_listings`.
- `src/listener.py` does the same live, as messages arrive (configured chats only).
- `src/run_all.py` runs scrape → ETL → repair scripts → dedup → views → report.
- `src/processor.py` holds shared price, area and label helpers used by the pipeline.
- Location codes come from `LOCATION_MAP` in `src/run_pipeline.py`. `src/topic_resolver.py`
  and `src/geocoder.py` use different codes for the same places until task S6 merges them.
