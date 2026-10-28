# Rules for working on Ollaa-Telegram

Read `STATUS.md` first: it has the audit findings and the numbered fix list (S1, S2, …).

## Working with the owner

- The owner is not a programmer. Explain in simple words, do the technical work yourself,
  and stop only for things the owner must do in person (paste a key, approve a login).
- Never show a password, API key, token or phone-login code in the chat, in a commit, or
  in a file other than `.env`. When printing code or data that might contain one, mask it.

## Telegram account safety (top priority)

The owner's Telegram account has been revoked many times and banned once, and the whole
scraper depends on it (owner, 28 October 2026). Protecting it comes before everything else.

- **Photos never use the owner's Telegram login.** Do not download photos or files with
  the account, do not create a new session, and do not ask the owner to log in for photo
  work. Photos come only from the public web preview, `https://t.me/s/<channel>`, which
  needs no account: `src/media_web_fetch.py`, one request every 20–40 seconds (random), a
  hard cap per run (50 for the pilot), stopping at the first error or sign of blocking.
  A channel without a public preview (forum groups) is skipped and reported.
- **The safety stops are in the code** (`src/telegram_safety.py`, used by
  `telegram_scraper.py` and `listener.py`; checked by `tests/test_telegram_safety.py`
  with a fake Telegram, never the real one). Never weaken them, raise the limits, or add
  another program that opens the account without the owner's approval. Run
  `tests/test_telegram_safety.py` after any change to the scraper, the listener or the
  safety module.
  - **No login file, or an expired one: stop.** They use the existing login file
    (`data/sessions/ollaa_session.session`, or the older `ollaa_session.session` in the
    project root) and stop with a message if it is missing or no longer valid. They never
    start a new login and never ask for a code (no `client.start()`, no `async with
    TelegramClient`). An expired login also blocks Telegram use for 25 hours.
  - **One at a time.** The scraper and the listener share one lock
    (`data/sessions/telegram.lock`): while one runs, the other refuses to start. The lock
    is freed when a program ends, even after a crash.
  - **Slow and small.** Per scraper run: the 40 newest messages per channel; per forum
    group the 10 topics with the newest messages, 20 messages each; random pauses of
    45–120 seconds between channels, 20–45 seconds between topics and 5–15 seconds
    between two requests for one channel. Channels the login file already knows cost one
    request each. At most 2 scraper runs and 150 requests a day (scraper and listener
    together, counted in `data/sessions/telegram_usage.json`; days start at midnight
    Addis Ababa time). The listener only listens; it asks for each forum topic's title
    once and skips titles when the day's requests are used up.
  - **Any warning from Telegram stops everything.** A FloodWait (or any other error
    from Telegram about the account, such as an ended login) stops the whole run at
    once, with no retry; neither program may use Telegram again until the next midnight
    (longer if Telegram asked for a longer wait, 25 hours after an ended login). Telethon's
    own short automatic waits are switched off (`flood_sleep_threshold=0`). A problem
    with one channel only (private, renamed, left) just skips that channel.
- **One login, one computer.** Use one login file on one computer only. Never copy a
  `.session` file to another computer, and never use one login from two places at once:
  Telegram ends a login used from two internet addresses at the same time.
- **This laptop has no working login** (checked 28 October 2026; the old
  `session.session` in the project root is logged out and is not used). Do not log in
  here.
- **As few logins as possible.** Each new login is a new device for Telegram. Keep the
  working login file; never delete it to "fix" an error; never add scripts that open the
  account (`src/srctest_scrape_channel.py`, which made a second session, was removed).
- **Read only.** Scripts only read channels the account already follows: no sending
  messages, no joining or leaving channels, no reactions, no contacting anyone.
- **Run the scraper once or twice a day, never in a loop**, and never at the same time
  as the listener. `run_all.py` carries on with the other steps when the scraper stops
  for safety (what was read before the stop is saved).
- **After a revocation or ban:** stop everything, wait at least 24 hours (longer after
  repeated ones), then the owner logs in once, by hand, on the one computer.
- **Same identity:** always the owner's own `TG_API_ID` / `TG_API_HASH` from
  my.telegram.org, the same computer and the same internet connection; no VPN or network
  switching while the scraper runs. The owner keeps two-step verification on and keeps
  using the account normally on the phone.

**Gemini free tier (owner's decision, 28 October 2026).** Billing cannot be paid from
Ethiopia. For the photo pilot the owner accepts the free tier, where Google may use what it
receives: the photos are public broker adverts that the brokers posted themselves, and the
owner takes responsibility for that choice. Run `media_pilot.py` with `--allow-free-tier`,
well under the free-tier limits (at most 6 requests a minute, far below the daily cap). A
full run needs the owner's approval again.

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
- `DATA_QUALITY.md` (for the owner's thesis) reports usable listings, field completeness,
  outliers and the hedonic-model sample. Its numbers come from `database\data_quality.py`
  (read-only); after re-processing or new data, re-run it and update the report.
- The 829 protected values left after S8 were kept on purpose by the owner (see
  `database/migrations/2026_10_27_s8_release_protections.py`); 749 remained after S9 and
  636 after S12, as the parser came to agree with the others, 622 after the owner
  released 14 "advert" labels on real rentals in S13, and 423 after S14 (192 retired as
  the parser agreed, 7 wrong Bet_afri labels released by the owner). Do not release them
  without asking.

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
  with the same code (`build_processed_values`) and keeps `rental_listings` in step (one
  row per rent or mixed listing with a rent, made by `etl_runner.rental_row`).
- `src/listener.py` does the same live, as messages arrive (configured chats only).
- Bet_afri, Betafrivip and Bet_afri_Business are rent-only channels; a post's type is what
  it states after its rent (`etl_runner.bet_afri_type`, checked by
  `tests/test_classification.py`). The ETL and `reprocess.py` apply it; `listener.py`
  calls the parser without the channel rules, so its posts get them at the next
  re-processing.
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
- Photo-only posts: `src/media_pilot.py` (task S15) has Gemini copy the words in an image and
  runs them through the text parser; see `MEDIA_PILOT.md`. Its full output
  (`data/media_pilot/`) holds unmasked text with phone numbers: never commit it. Photos
  come from the public web preview only (`src/media_web_fetch.py`, see "Telegram account
  safety"); `media_pilot.py` sends images to Gemini on the free tier only with
  `--allow-free-tier`.
- `src/locations.py` is the only table of places. Every location code written anywhere
  must be a key of `PLACES` (or `noise` / `other_addis`). To add a place, add it to
  `PLACES` and its English and Amharic names to `ALIASES`, more specific names before the
  wider area ("bole bulbula" before "bole"); to retire a code, add it to `RENAMED_CODES`
  and rename it in the database. `tests/test_locations.py` checks the matching rules;
  run it, and compare old and new parser output, after any change to places.
