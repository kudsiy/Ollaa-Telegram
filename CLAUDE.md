# Rules for working on Ollaa-Telegram

Read `STATUS.md` first: it has the audit findings and the numbered fix list (S1, S2, …).

## Working with the owner

- The owner is not a programmer. Explain in simple words, do the technical work yourself,
  and stop only for things the owner must do in person (paste a key, approve a login).
- Never show a password, API key, token or phone-login code in the chat, in a commit, or
  in a file other than `.env`. When printing code or data that might contain one, mask it.

## Git and GitHub

- The GitHub repository `kudsiy/Ollaa-Telegram` is **public**.
- Its history was rewritten on 27 October 2026 to remove old secrets (task S10). Never
  push from a copy cloned before that date, and never force-push without the owner's
  approval; a copy made earlier must be deleted and cloned again.
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
- Two database logins (task S9): scripts use `DB_USER` = `ollaa_user`, which owns the
  Ollaa tables but is not a superuser. The `postgres` login (`DB_ADMIN_USER`,
  `DB_ADMIN_PASSWORD`, `settings.admin_config()`) is only for backups,
  `database/export_schema.py` and one-off migrations that need it. Never switch the
  scripts back to `postgres`. Tables or views created as `postgres` (for example in
  pgAdmin) must be given to `ollaa_user`: run
  `database\migrations\2026_10_27_s9_app_login.py --apply`.
- Scripts in `src/` import it directly: `from settings import DB_URL`.
  Scripts in the project root first add `src` to the import path (see `test_db.py`).
- `check_setup.py` tests that `.env` is complete, both database logins work, the
  everyday one is not a superuser, and the Gemini key works.

## Database safety

- Database: PostgreSQL 18 on this laptop, database `ollaa`. Main tables:
  `telegram_listings` (raw messages) and `processed_listings` (parsed listings).
- Before any task that changes data, take a backup:
  `"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U postgres -Fc -f backups\ollaa_<date>.dump ollaa`
  (the password is `DB_ADMIN_PASSWORD` in `.env`; keep `backups\` out of git).
- `database/schema.sql` rebuilds the whole structure (no data). It is made by
  `database/export_schema.py` from the live database; never edit it by hand. After any
  change to tables, views or functions, run `database\export_schema.py` and then
  `database\export_schema.py --check` (it must say "identical"), and commit both.
- Repairs and deletions are protected automatically (task S4, `src/protection.py`):
  - Changing a parser field of a listing by anything other than the parser (a repair
    script, pgAdmin, a hand-written UPDATE) is recorded in `listing_overrides`, and that
    value then always wins over the parser. To undo a protection, delete its row there.
  - Deleting a listing records its message in `processing_exclusions`, so it never comes
    back. To let a message back in, delete its row there, then run `etl_runner.py`.
  - Code that writes parser output must run `protection.PARSER_WRITE_SQL` first in its
    transaction (as `etl_runner.py`, `listener.py` and `reprocess.py` do), or its writes
    get recorded as repairs.
  - If `TRACKED_FIELDS` in `src/protection.py` changes, the database trigger must be
    updated to the same list; `reprocess.py` refuses to run until they match.
- To bring parser fixes to existing listings, run `src\reprocess.py` (report only), read
  the report, back up, then `src\reprocess.py --apply`. It never deletes listings.
  `--reset` was removed from `etl_runner.py` and `run_all.py`: it deleted every listing.
- Measure first: count the rows a change will touch, change them, count again, and
  report both numbers. `database\recount_findings.py` counts the audit findings in the
  stored data (read-only); run it before and after re-processing.
- The 829 protected values left after S8 were kept on purpose by the owner (see
  `database/migrations/2026_10_27_s8_release_protections.py`); 749 remain after S9,
  where the parser came to agree with 80 of them. Do not release them without asking.

## How the project runs

- Python: always use the project's own environment, `venv\Scripts\python.exe`.
  Install packages from `requirements.txt` (versions are pinned on purpose).
- `src/channels.py` is the one list of Telegram channels and groups (`REGULAR_CHANNELS`,
  `FORUM_GROUPS`). `src/telegram_scraper.py` reads exactly these into `telegram_listings`.
- `src/listener.py` saves messages only from chats in `src/channels.py`, never from private
  chats. `tests/test_listener_privacy.py` checks this; run it after any listener change.
- `src/etl_runner.py` runs `src/run_pipeline.py` (`ValuationPipeline`) on new raw
  messages (skipping `processing_exclusions`) and writes `processed_listings` and
  `rental_listings`. It only adds listings; `src/reprocess.py` updates existing ones
  with the same code (`build_processed_values`).
- `src/listener.py` does the same live, as messages arrive (configured chats only).
- `src/run_all.py` runs scrape → ETL → repair scripts → dedup → views → report.
- `src/processor.py` holds shared price, area and label helpers used by the pipeline.
  Price reading (decimals, spellings of "million", prices per m²) is checked by
  `tests/test_prices.py`; run it after any change to prices. After any parser change,
  also run the old and new parser on all listings and explain every difference, as S5 did.
- Noise and photo-only rules (`is_strictly_noise` in `run_pipeline.py`, `is_photo_only` in
  `processor.py`) are checked by `tests/test_classification.py`. A link never makes a
  listing noise; a photo-only post is `MEDIA_PENDING`. (`src/fix_418.py` and
  `upgrade_brain.py`, which overwrote `run_pipeline.py` with old rules, were removed in
  S9; never bring them back.)
- `src/locations.py` is the only table of places. Every location code written anywhere
  must be a key of `PLACES` (or `noise` / `other_addis`). To add a place, add it to
  `PLACES` and its English and Amharic names to `ALIASES`, more specific names before the
  wider area ("bole bulbula" before "bole"); to retire a code, add it to `RENAMED_CODES`
  and rename it in the database. `tests/test_locations.py` checks the matching rules;
  run it, and compare old and new parser output, after any change to places.
