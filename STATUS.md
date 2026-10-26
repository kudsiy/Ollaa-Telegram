# Ollaa-Telegram: project status

Last updated: 26 October 2026 (audit redone on the home laptop, which holds the database).

## In plain words

This project reads property adverts from Telegram channels in Addis Ababa, stores them
in a PostgreSQL database (`ollaa`), and turns each message into a structured listing
(price, size, location, type) for valuation work.

The audit found three kinds of problems:

1. **Secrets were written inside the code.** The database password was in 26 files on
   GitHub (28 on this laptop) and a Gemini API key was in `extract_images.py`. The GitHub
   repository is public, so both were visible to anyone. Task S1 fixed this.
2. **The parser misreads some messages.** Some prices lose their decimals, some
   per-square-metre prices are saved as the full price, and some locations are wrong.
   The numbers below say how many of your listings each problem touches.
3. **Fixing old data is risky.** Re-running the parser does not update old rows, and the
   "reset" option deletes everything, including repairs that were made by hand.

## Database snapshot (this laptop)

| Table | Rows |
|---|---|
| `telegram_listings` (raw messages) | 6,291 |
| `processed_listings` (parsed listings) | 4,310 |
| `media_queue` (photos waiting to be read) | 3,333 |
| `rental_listings` | 177 |
| `web_scraped_listings` | 76 |

## Findings and how many listings each affects

Counts come from running the project's own parser against the stored raw text, once
as it is and once with the single bug patched out, and comparing with what is stored.

| # | Problem | Where | Listings affected |
|---|---|---|---|
| 1 | Gemini API key written in the code | `extract_images.py` line 8 | key exposed publicly (old keys now deleted) |
| 2 | Database password written in the code | 26 files on GitHub, 28 on this laptop (+ a second login's password in `test_db.py`) | password exposed publicly |
| 3 | Decimals cut off: "5.5 million" saved as 5,000,000 | `processor.py` `_extract_first_anchored_price` uses `int(float(...))` before multiplying | **60** sale prices too low (e.g. 23.5M saved as 23M, 4.3M as 4M) |
| 4 | Price per m² saved as the total price | no "per m²" detection anywhere; `extract_prices` in `run_pipeline.py` takes the first "… ብር" number | **68** listings (147 posts mention a per-m² price) |
| 5 | Bole/Ayat listings tagged "yeka": the Amharic word for "per square metre" (የካሬ) contains the letters of Yeka (የካ) | `run_pipeline.py` `LOCATION_MAP` + `normalize_location` | **6** of the 10 "yeka" listings are wrong |
| 6 | Phone numbers containing "22" turn a listing into `22_area` | `LOCATION_MAP` key `"22"`; `topic_resolver.py` has the same pattern for topic titles | **5** of the 6 `22_area` listings are wrong |
| 7 | "#Bole" or "Location: Bole" saved as Bole Bulbula (a short label matches any longer name that contains it) | `normalize_location`: `labeled_norm in k` and `tag_lower in k` | **76** listings got the wrong sub-area (40 Bole Bulbula, 13 Ayat 49, 8 Haile Garment, …); 43 of the 66 Bole Bulbula listings never mention Bulbula |
| 8 | Same place, different codes in three scripts (e.g. `6kilo`/`6_kilo`, `ayat_zone`/`ayat`, `cmc_michael`/`cmc`, `sarbet_old_airport`/`sarbet`, `haya_hulet`/`hayahulet`, `wello_sefer`/`wollo_sefer`, `kality`/`kaliti`; Gelan is Addis in one and Sheger in another) | `run_pipeline.py`, `topic_resolver.py`, `geocoder.py` | makes location totals unreliable; `LOCATION_MAP` even defines `"6 kilo"` twice |
| 9 | Adverts with web links thrown away as noise | `is_strictly_noise` treats any `https://` as noise | **101** posts discarded; **67** of them have a price or a size |
| 10 | Photo-only posts labelled as adverts instead of `MEDIA_PENDING` | `is_strictly_noise` catches `[MEDIA ONLY]` before `classify_listing_class` can return `MEDIA_PENDING` | **2,843** photo-only posts: a one-off repair moved 2,209 to `MEDIA_PENDING`, **634** are still labelled `ADVERTISEMENT` |
| 11 | Parser fixes never reach old rows | `etl_runner.py` and `listener.py` use `ON CONFLICT DO NOTHING` | **3,229 of 4,310** stored rows differ from what today's parser produces (class 2,497, intent 1,377, location 1,279, type 620, built-up area 256, sale price 95, plot 76) |
| 12 | A full reset wipes earlier one-off repairs | `etl_runner.py --reset` / `run_all.py --reset` delete every processed row | would undo the 2,209 `MEDIA_PENDING` repair and the other hand repairs, and bring back **1,981** deleted duplicates |
| 13 | No script creates the two main tables from scratch | `database/schema.sql` is empty; nothing has `CREATE TABLE telegram_listings` or `processed_listings` | the tables exist only inside this laptop's database |
| 14 | The live listener saves **all** your Telegram chats, including private ones | `listener.py`: `@client.on(events.NewMessage)` has no `chats=` filter | every message you receive while it runs; the database already holds **237** messages from **3** chats that are not on the channel list (saved 28 Dec 2025 to 3 Jan 2026) |
| 15 | `test_db.py` fails with SQLAlchemy 2.1, which changed its default PostgreSQL driver to `psycopg` (v3, not installed) | `test_db.py` uses `postgresql://` with no driver; versions not pinned | fails on the office PC; works here only because this laptop still has SQLAlchemy 2.0.45 |

### Other things noticed

- `processor.py` defines `extract_price_birr`, `extract_price_candidates_birr`,
  `_extract_first_anchored_price`, `STRICT_ANCHORED_PRICE_RE` and `extract_labeled_sqm`
  more than once. Only the last copy is used, so the earlier ones are misleading.
- `listener.py` step 3 updates `processed_listings` by `str(tl_id)`, but forum rows are
  stored under `channel::topic::N`, so the topic-based fix never reaches them.
- `etl_runner.py` hides every error (`except Exception: errors += 1; continue`).
- `extract_images.py` reads images from `C:\Projects\ollaa\data\...`, which does not
  exist on this laptop (the images are in `data\images\telegram`, 747 files).
- `extract_images.py` uses the preview model `gemini-3.1-flash-lite-preview`. On
  26 October 2026 it answered every request with "503 high demand", while the new Gemini
  key worked at once with `gemini-2.5-flash`. A stable `gemini-3.1-flash-lite` is now
  available and is the likely replacement.
- `requirements.txt` had no versions and was missing `google-genai`, `pydantic`,
  `rapidfuzz`, `ollama` and `numpy`.
- Empty placeholder files: `database/schema.sql`, `config/telegram_channels.py`,
  `src/main.py`, `src/ocr/run_ocr.py`, `src/telegram/fetch_messages.py`, `src/utils/db.py`.
- Copies of code saved as `.txt` (`fix_single_room.py.txt`, `src/srcshow_duplicates.py.txt`)
  and a duplicate `srcshow_duplicates.py` in the project root.
- All scripts log in as the `postgres` superuser. PostgreSQL listens on every network
  address, but its access rules only accept connections from this laptop, so it was not
  reachable from outside.

## Security status

- The GitHub repository `kudsiy/Ollaa-Telegram` is **public**. Since 21 May 2026 its
  history has contained the old database password and an old Gemini key.
- The old Gemini keys have been deleted by the owner. A new key is kept only in `.env`.
- Both database passwords (`postgres` and `ollaa_user`) were changed on 26 October 2026
  (task S1) to long random ones kept only in `.env`. The old ones are rejected, so the
  copies in the GitHub history no longer work. Removing them from the history is
  optional (task S10).
- Three old copies of the ollaa-web project (`C:\Projects\New folder`, `New folder (2)`,
  `New folder (4)`) still contain the old password and would need the new one if run.
- `.env`, Telegram `*.session` files and the large text dumps (which contain other
  people's phone numbers) are ignored by git and must never be committed.

## Fix list

Work top to bottom. Each task ends with a commit and a push. Before any task that
changes data, take a database backup (see CLAUDE.md).

| Task | What | Status |
|---|---|---|
| S1 | Move all passwords and keys into `.env` through one settings helper (`src/settings.py`); add `.env.example`; keep `.env` out of git; pin package versions (SQLAlchemy 2.0.55); change the database passwords | done 26 Oct 2026 |
| S2 | Listener privacy: only save messages from the configured channels; review and delete the 237 messages from the 3 unlisted chats | listener fixed 26 Oct 2026 (channel list now in `src/channels.py`, checked by `tests/test_listener_privacy.py`). The 237 messages turned out to come from 3 public business channels, not private chats (Bamacon 100, Champion 80, a furniture market 57). Owner's decision: kept Bamacon and Champion (real property adverts, channel list unchanged); deleted the 57 furniture-market messages and their 22 processed rows after a backup (`backups/ollaa_2026-10-26_before_S2.dump`). Totals now 6,234 raw / 4,288 processed. Done 26 Oct 2026 |
| S3 | Write `database/schema.sql` that creates every table, view and index from scratch (taken from the live database) | to do |
| S4 | Safe re-processing: replace `DO NOTHING` / `--reset` with an update that refreshes parser fields but keeps hand repairs and deletions (record each repair as a rule that is re-applied) | to do |
| S5 | Prices: keep decimals; detect per-m² prices and store them as price per m², not as the total | to do |
| S6 | Locations: whole-word matching (fixes Yeka and "22"), one-way label and hashtag matching (fixes Bole Bulbula), one shared location table for all three scripts | to do |
| S7 | Classification: web links are not noise; photo-only posts become `MEDIA_PENDING` | to do |
| S8 | Re-run the fixed parser on old rows with S4's safe method, then re-count findings 3 to 12 (they should drop to 0) | to do |
| S9 | Clean-ups: remove duplicate functions and `.txt` code copies, fill or delete empty files, make the ETL report its errors, use a limited database login instead of `postgres` | to do |
| S10 | Optional: remove the old secrets from the GitHub history | to do |
