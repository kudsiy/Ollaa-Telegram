# Ollaa roadmap

Ollaa is first a company product, and the thesis data comes from it (owner's decision, 16 November 2026).
The work goes in four phases. **Finish one phase before starting the next. No new features outside the
current phase.** This file is updated in every working session: what was done, what is left, and the date.

| Phase | Goal | State |
|---|---|---|
| 1 | The live listener runs 24/7 and is the main way data comes in | **current**, started 16 Nov 2026 |
| 2 | Telegram and web data merged into one database | waiting for phase 1 |
| 3 | Photos, PDFs, then videos read automatically | waiting for phase 2 |
| 4 | Estate IQ fed daily from the Ollaa database, and launched | waiting for phase 3 |

## Phase 1: the listener live 24/7 (current)

Done when the listener has run for 3 clean days (no warning from Telegram, no crash it could not recover
from, messages arriving every day) and the scheduled scraper is changed to one weekly catch-up run.

| # | Task | State |
|---|---|---|
| 1.1 | It saves only messages from the channels in `src/channels.py`, never private chats or people (`tests/test_listener_privacy.py`) | done 16 Nov 2026 |
| 1.2 | Every new message goes into the database at once by the scraper's and the ETL's own code: the raw message, the parser with the channel rules (Bet_afri), the listing and its rent row, and the repeat check (a clear repeat from the same channel or agent is removed at once). Daily, with no Telegram use: the ETL (for any message whose live processing failed), the units table and the views; the full repeat review stays in the attended scrape run, and `run_all.py`'s repair scripts never run unattended | done 16 Nov 2026 |
| 1.3 | `src/listener_service.py` starts with the laptop (`src/listener_autostart.py --install`), waits for the internet and the database, restarts the listener after a crash (1, 2, 5, 10, 30 minutes, at most 10 a day), never logs in, stops at any Telegram warning, and makes way for the scraper and the photo pilot (`tests/test_listener_service.py`, `tests/test_telegram_safety.py`) | built 16 Nov 2026; autostart installed 19 Nov 2026 22:40, started the listener by itself at 23:20 when the scrape ended |
| 1.4 | Photos, videos and PDFs are only noted in `media_queue` for phase 3 (not downloaded) | done 16 Nov 2026 |
| 1.5 | A daily health log: messages received, listings added, warnings (`data/listener/health/`, shown by `database\scrape_check.py`) | done 16 Nov 2026 |
| 1.6 | A 1-hour live test, and what came in | done 19 Nov 2026, 23:20–00:20: connected with 1 request, no warning, no error, no crash; 0 messages arrived (normal for that hour: the 30 days before had 15 messages in all between 23:00 and 01:00, against about 100 in a daytime hour). The first daytime messages are to be checked on 20 Nov |
| 1.7 | After 3 clean days: the scheduled scraper becomes one weekly catch-up run. Its "skip if messages were saved in the last 48 hours" rule must then look at the last scraper run instead (the listener saves messages every day, so until then the every-3-days task skips, and the listener is the only source) | waiting for 3 clean days |

Process rule (owner, 16 November 2026): commit and push only after **all** tests pass. `tests\run_all_tests.py`
runs them all with the database structure check, and the git pre-push check (`.githooks/pre-push`) runs it
before every push.

## Phase 2: one database for Telegram and web data (next)

The ollaa-web project's listings (`web_listings`, `web_offplan_properties`) and this project's Telegram
listings in one set of tables, with one place table, one sub-city rule, one repeat check across both sources
and one units table. To be planned when phase 1 is done.

## Phase 3: photos, PDFs, then videos read automatically

Read what `media_queue` holds: photos first, then PDFs (price lists), then videos. The photo rules in
`CLAUDE.md` apply: photos come from the public web preview, never the owner's login, except the 30-photo
championallsites pilot the owner approved on 16 November 2026 (`src/telegram_photo_pilot.py`), which was
approved and queued before this roadmap; it did not run (the app closed on 16 November), and it waits for the owner's word.

## Phase 4: Estate IQ

Estate IQ fed daily from the Ollaa database, then launched. To be planned when phase 3 is done.

## Log

- 20 Nov 2026: the 1-hour live test (19 Nov 23:20–00:20) ran clean, with no message at that hour; the listener keeps running. Clean day 1 of 3 counts from 20 Nov. No new feature.
- 19 Nov 2026: the scheduled scrape ran once (S43, 203 new messages, no warning); the listener stepped aside for it and came back after it. No new feature.
- 19 Nov 2026: the Phase 1 code committed (all tests passing); the live test to be repeated.
- 16 Nov 2026: roadmap written. Phase 1 started: listener rebuilt on the scraper's and the ETL's code, the
  service (autostart, restarts, internet wait, step aside), the health log, the pre-push test check.
