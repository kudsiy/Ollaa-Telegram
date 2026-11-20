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

**Done (the owner's definition of 20 November 2026)** when, on 3 days in a row, every advert posted in the
channels ended up in the database, through the listener or its catch-up read, checked against the channels'
public web pages with no account (`database\web_completeness_check.py`, run daily by the service; the result is
shown by `database\scrape_check.py`); then the scheduled scraper is changed to one weekly catch-up run. The forum
groups (`@luxury_freelancers`, `@championallsites`) and channels without a public page cannot be checked this way;
the check names them every day.

| # | Task | State |
|---|---|---|
| 1.1 | It saves only messages from the channels in `src/channels.py`, never private chats or people (`tests/test_listener_privacy.py`) | done 16 Nov 2026 |
| 1.2 | Every new message goes into the database at once by the scraper's and the ETL's own code: the raw message, the parser with the channel rules (Bet_afri), the listing and its rent row, and the repeat check (a clear repeat from the same channel or agent is removed at once). Daily, with no Telegram use: the ETL (for any message whose live processing failed), the units table and the views; the full repeat review stays in the attended scrape run, and `run_all.py`'s repair scripts never run unattended | done 16 Nov 2026 |
| 1.3 | `src/listener_service.py` starts with the laptop (`src/listener_autostart.py --install`), waits for the internet and the database, restarts the listener after a crash (1, 2, 5, 10, 30 minutes, at most 10 a day), never logs in, stops at any Telegram warning, and makes way for the scraper and the photo pilot (`tests/test_listener_service.py`, `tests/test_telegram_safety.py`) | built 16 Nov 2026; autostart installed 19 Nov 2026 22:40, started the listener by itself at 23:20 when the scrape ended |
| 1.4 | Photos, videos and PDFs are only noted in `media_queue` for phase 3 (not downloaded) | done 16 Nov 2026 |
| 1.5 | A daily health log: messages received, listings added, warnings (`data/listener/health/`, shown by `database\scrape_check.py`) | done 16 Nov 2026 |
| 1.6 | A 1-hour live test, and what came in | done 19 Nov 2026, 23:20–00:20: connected with 1 request, no warning, no error, no crash; 0 messages arrived (normal for that hour: the 30 days before had 15 messages in all between 23:00 and 01:00, against about 100 in a daytime hour). The laptop was off on 20 Nov from 01:20 to 21:34, so the first live message is still to be checked |
| 1.7 | After 3 complete days in a row: the scheduled scraper becomes one weekly catch-up run. Its "skip if messages were saved in the last 48 hours" rule must then look at the last scraper run instead (the listener saves messages every day, so until then the every-3-days task skips, and the listener is the only source) | waiting for 3 complete days |
| 1.8 | Self-healing after a power cut, sleep or no internet: about once a minute the listener marks that it is connected and the internet answers; every gap of 10 minutes or more goes into the health log; after a gap of more than 2 hours, ONE catch-up read while it goes on listening: per chat, the messages posted since the last one saved (at most the 40 newest), one request each, the scraper's pauses between chats; it counts as one of the day's 2 scraper runs, is refused when those or the 150 requests are used up, and any warning stops everything. The time the scraper has the account is no gap (it reads the channels itself) (`tests/test_telegram_safety.py` section 11) | built 20 Nov 2026; goes live on 21 Nov after the photo pilot (started before midnight, its first catch-up would have counted as a scraper run on the pilot's day) |
| 1.9 | The daily completeness check: each ended day's posts on the public web pages (one request every 20–40 s, at most 4 pages per channel and 120 requests per run, stop at the first error) compared with the database; run by the service for yesterday once the listener has been connected for 15 minutes and no catch-up is running (`tests/test_web_completeness.py`, `tests/test_listener_service.py`) | built 20 Nov 2026 |

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
approved and queued before this roadmap; it did not run (the app closed on 16 November). On 20 November
the owner asked for it to run on 21 November (not a scrape day): the listener steps aside, the pilot runs with
all its limits, then the listener starts again; its results go into the reports.

## Phase 4: Estate IQ

Estate IQ fed daily from the Ollaa database, then launched. To be planned when phase 3 is done.

## Log

- 20 Nov 2026 (late): the owner set the laptop to never sleep when plugged in, and asked for Phase 1 to heal
  itself after power cuts. Built: the gap log and the one catch-up read after more than 2 hours off (1.8), and the
  daily completeness check against the public web pages, the new test of "Phase 1 done" (1.9). All 14 checks pass.
- 20 Nov 2026: the laptop went to sleep at 01:20 and was off until 21:34 (on battery it sleeps after 1 hour; plugged in, never), so the day's posts (09:33–20:33 on the public pages) were missed; the scrape of 22 Nov brings them in. At log-on the service started by itself and the listener was back at 21:57 (autostart works). Not a clean day: the 3 clean days count from the first whole day the laptop stays on. The first live message is still to be seen. No new feature.
- 20 Nov 2026: the 1-hour live test (19 Nov 23:20–00:20) ran clean, with no message at that hour; the listener keeps running.
- 19 Nov 2026: the scheduled scrape ran once (S43, 203 new messages, no warning); the listener stepped aside for it and came back after it. No new feature.
- 19 Nov 2026: the Phase 1 code committed (all tests passing); the live test to be repeated.
- 16 Nov 2026: roadmap written. Phase 1 started: listener rebuilt on the scraper's and the ETL's code, the
  service (autostart, restarts, internet wait, step aside), the health log, the pre-push test check.
