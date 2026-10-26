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

These are the counts at the time of the audit. After the S2 and S11 clean-ups:
5,091 raw messages, 4,276 processed listings, 172 rental listings.

## Findings and how many listings each affects

Counts come from running the project's own parser against the stored raw text, once
as it is and once with the single bug patched out, and comparing with what is stored.

| # | Problem | Where | Listings affected |
|---|---|---|---|
| 1 | Gemini API key written in the code | `extract_images.py` line 8 | key exposed publicly (old keys now deleted) |
| 2 | Database password written in the code | 26 files on GitHub, 28 on this laptop (+ a second login's password in `test_db.py`) | password exposed publicly |
| 3 | Decimals cut off: "5.5 million" saved as 5,000,000 | `processor.py` `_extract_first_anchored_price` uses `int(float(...))` before multiplying | **60** sale prices too low (e.g. 23.5M saved as 23M, 4.3M as 4M); recounted in S5: **54** stored listings. Fixed in the parser by S5 |
| 4 | Price per m² saved as the total price | no "per m²" detection anywhere; `extract_prices` in `run_pipeline.py` takes the first "… ብር" number | **68** listings (147 posts mention a per-m² price); recounted in S5: **53** stored listings (the audit's search also matched sizes such as "81 ካሬ"). Per-m² numbers were also read as sizes (8 listings). Fixed in the parser by S5 |
| 5 | Bole/Ayat listings tagged "yeka": the Amharic word for "per square metre" (የካሬ) contains the letters of Yeka (የካ) | `run_pipeline.py` `LOCATION_MAP` + `normalize_location` | **6** of the 10 "yeka" listings are wrong. Recounted in S6: **9** of 10 (the month የካቲት, "Yekatit", also contains የካ); fixed by S6, stored listings change in S8 |
| 6 | Phone numbers containing "22" turn a listing into `22_area` | `LOCATION_MAP` key `"22"`; `topic_resolver.py` has the same pattern for topic titles | **5** of the 6 `22_area` listings are wrong. Fixed by S6 (bare "22" is no longer a place, except a hashtag "#22"); stored listings change in S8 |
| 7 | "#Bole" or "Location: Bole" saved as Bole Bulbula (a short label matches any longer name that contains it) | `normalize_location`: `labeled_norm in k` and `tag_lower in k` | **76** listings got the wrong sub-area (40 Bole Bulbula, 13 Ayat 49, 8 Haile Garment, …); 43 of the 66 Bole Bulbula listings never mention Bulbula. Fixed by S6; **63** stored listings change in S8 (others are protected values, reviewed in S8) |
| 8 | Same place, different codes in three scripts (e.g. `6kilo`/`6_kilo`, `ayat_zone`/`ayat`, `cmc_michael`/`cmc`, `sarbet_old_airport`/`sarbet`, `haya_hulet`/`hayahulet`, `wello_sefer`/`wollo_sefer`, `kality`/`kaliti`; Gelan is Addis in one and Sheger in another) | `run_pipeline.py`, `topic_resolver.py`, `geocoder.py` | makes location totals unreliable; `LOCATION_MAP` even defines `"6 kilo"` twice. S6 found two more tables (`dedup_and_fix_locations.py`, the mapping in `fast_repair.py`/`fix_spaces.py`) and 85 different codes in the database; all now use `src/locations.py`, and the database's old codes were renamed (79 codes left) |
| 9 | Adverts with web links thrown away as noise | `is_strictly_noise` treats any `https://` as noise | **101** posts discarded; **67** of them have a price or a size. Fixed by S7: the parser now reads 266 link posts it used to discard (197 with a price or size, 110 valuation-eligible); in stored data 132 change in S8 (65 with a price or size, 34 valuation-eligible), the rest hold protected values |
| 10 | Photo-only posts labelled as adverts instead of `MEDIA_PENDING` | `is_strictly_noise` catches `[MEDIA ONLY]` before `classify_listing_class` can return `MEDIA_PENDING` | **2,843** photo-only posts: a one-off repair moved 2,209 to `MEDIA_PENDING`, **634** are still labelled `ADVERTISEMENT`. Fixed by S7: all photo-only posts are `MEDIA_PENDING`; the 634 change in S8 and the 2,209 repaired ones stop needing protection |
| 11 | Parser fixes never reach old rows | `etl_runner.py` and `listener.py` use `ON CONFLICT DO NOTHING` | **3,229 of 4,310** stored rows differ from what today's parser produces (class 2,497, intent 1,377, location 1,279, type 620, built-up area 256, sale price 95, plot 76). Fixed by S4: `src/reprocess.py` updates existing listings |
| 12 | A full reset wipes earlier one-off repairs | `etl_runner.py --reset` / `run_all.py --reset` delete every processed row | would undo the 2,209 `MEDIA_PENDING` repair and the other hand repairs, and bring back **1,981** deleted duplicates. Fixed by S4: `--reset` removed; repairs and deletions are protected automatically |
| 13 | No script creates the two main tables from scratch | `database/schema.sql` was empty; nothing had `CREATE TABLE telegram_listings` or `processed_listings` | fixed by S3: `database/schema.sql` now rebuilds the whole structure |
| 14 | The live listener saves **all** your Telegram chats, including private ones | `listener.py`: `@client.on(events.NewMessage)` has no `chats=` filter | every message you receive while it runs; the database already holds **237** messages from **3** chats that are not on the channel list (saved 28 Dec 2025 to 3 Jan 2026) |
| 15 | `test_db.py` fails with SQLAlchemy 2.1, which changed its default PostgreSQL driver to `psycopg` (v3, not installed) | `test_db.py` uses `postgresql://` with no driver; versions not pinned | fails on the office PC; works here only because this laptop still has SQLAlchemy 2.0.45 |
| 16 | The live listener cannot save any message: its save command needs a "one row per channel + message" rule that `telegram_listings` does not have (found during S3) | `listener.py` uses `ON CONFLICT (channel, message_id)`; the table only has a primary key on `id` | every message the listener receives fails with "no unique or exclusion constraint matching the ON CONFLICT specification" (shown on a test copy); the table already holds **409** messages saved more than once (**1,143** extra copies). Fixed by S11 |
| 17 | `dedup_fast.py` would fail when it first runs (found during S3) | it adds `duplicate_of INTEGER REFERENCES processed_listings(id)`, but `processed_listings.id` is text | the script stops before deduplicating. Fixed by S11 (column is now `TEXT`) |

### Other things noticed

- `processor.py` defines `extract_price_birr`, `extract_price_candidates_birr`,
  `_extract_first_anchored_price`, `STRICT_ANCHORED_PRICE_RE` and `extract_labeled_sqm`
  more than once. Only the last copy is used, so the earlier ones are misleading.
- `listener.py` step 3 updates `processed_listings` by `str(tl_id)`, but forum rows are
  stored under `channel::topic::N`, so the topic-based fix never reaches them.
- `dedup_fast.py` picks the "older" listing with `min()` on ids, but ids are text, so
  "1000" counts as older than "999". Fix before relying on it (S9).
- Price reading gaps left after S5: totals given as "ሙሉ ክፍያ 5.7ሚሊዮን" (full payment) or
  "80.7ካሬ = 5,770,000" without a price word are not read; the intent check
  (`SALE_SIGNALS` in `run_pipeline.py`) still does not know the spelling ሚልዮን; a sale
  advert that mentions rent ("Rent in Dollars") can get a down payment as its rent (S7);
  the fallback "ዋጋ …" pattern in `run_pipeline.extract_prices` has no phone-number guard
  (no stored listing is affected).
- Locations, left after S6: developer names that contain a place name ("Ayat Real Estate")
  still give that place; listings with several places get the first one in the table's
  priority order; Gelan and Dukem count as Addis Ababa and Chacha has no city of its own
  (owner to confirm); the coordinates moved from `geocoder.py` unchanged and some look
  rough (e.g. Summit is placed in Nifas Silk).
- Danger: `src/fix_418.py` and `upgrade_brain.py` rewrite `run_pipeline.py` when run
  (they were one-off upgrades). Running either would bring back the old noise rule that
  discarded every post with a link. Remove or disable them (S9).
- A building's monthly income ("180,000 ብር ገቢ ያለው") can be read as its sale price
  when the total is written without a price word (seen on listing 3432).
- `etl_runner.py` hides every error (`except Exception: errors += 1; continue`).
- `extract_images.py` reads images from `C:\Projects\ollaa\data\...`, which does not
  exist on this laptop (the images are in `data\images\telegram`, 747 files).
- `extract_images.py` uses the preview model `gemini-3.1-flash-lite-preview`. On
  26 October 2026 it answered every request with "503 high demand", while the new Gemini
  key worked at once with `gemini-2.5-flash`. A stable `gemini-3.1-flash-lite` is now
  available and is the likely replacement.
- `requirements.txt` had no versions and was missing `google-genai`, `pydantic`,
  `rapidfuzz`, `ollama` and `numpy`.
- Empty placeholder files: `config/telegram_channels.py`, `src/main.py`,
  `src/ocr/run_ocr.py`, `src/telegram/fetch_messages.py`, `src/utils/db.py`.
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
| S2 | Listener privacy: only save messages from the configured channels; review and delete the 237 messages from the 3 unlisted chats | listener fixed 26 Oct 2026 (channel list now in `src/channels.py`, checked by `tests/test_listener_privacy.py`). The 237 messages turned out to come from 3 public business channels, not private chats (Bamacon 100, Champion 80, a furniture market 57). Owner's decision: kept Bamacon and Champion (real property adverts, channel list unchanged); deleted the 57 furniture-market messages and their 22 processed rows after a backup (`backups/ollaa_2026-10-26_before_S2.dump`). Totals now 6,234 raw / 4,288 processed. Done 26 Oct 2026. The listener could not save anything until S11 fixed finding 16 |
| S3 | Write `database/schema.sql` that creates every table, view and index from scratch (taken from the live database) | done 26 Oct 2026: made by `database/export_schema.py`; `--check` rebuilt an empty database from it that is identical to the live one (8 tables, 2 views, 2 materialized views, 2 functions, 6 indexes, 6 sequences); the ETL ran on it with 0 errors |
| S4 | Safe re-processing: replace `DO NOTHING` / `--reset` with an update that refreshes parser fields but keeps hand repairs and deletions (record each repair as a rule that is re-applied) | done 26 Oct 2026. Old repairs could not be re-created (some labels came from a one-off Gemini run), so they are protected instead: new tables `listing_overrides` (protected values, always win over the parser) and `processing_exclusions` (messages kept out), each filled automatically by a database trigger whenever a listing is changed outside the parser or deleted. Switched on after a backup (`backups/ollaa_2026-10-26_before_S4.dump`) without changing any listing: 815 removed messages kept out (125 same text, 97 same price/size/location, 593 likely near-duplicates) and 6,406 values in 3,226 listings protected (they differ from today's parser). New `src/reprocess.py` re-runs the parser with the ETL's own code, reports, and with `--apply` updates listings, never deleting; legacy protections retire when the parser agrees. `--reset` removed. Tested on a full copy: identical ETL output, protected values untouched, second run finds nothing, hand repair kept, deleted listing stays out. Live report (not applied): only the 3 edited ads and recalculated per-m² / confidence figures would change |
| S5 | Prices: keep decimals; detect per-m² prices and store them as price per m², not as the total | done 26 Oct 2026, in the parser only (existing listings change in S8). Decimals kept; "million" also read when spelled ሚልዮን (the most common spelling, 203 uses), ሚልየን, ሚሊዬን, ሚለን, ሚሊ or written "3.9M" after a price word; "ዋጋ = …" read; a number under 1,000 birr after "ዋጋ" is no longer taken as a sale price. Per-m² prices ("በካሬ 85,000 ብር", "110,000 Birr per sqm", "75,000 Birr/sqm", "በካሬ 110ሺ", "የካሬ ዋጋ=…", ranges) are found by `processor.find_price_per_sqm`, never read as a total or a size, and give total = price per m² × size when the size is known, otherwise they are stored as `price_per_builtup_sqm` (plot for land). Checked by `tests/test_prices.py` (28 checks) and by running old and new parser on all 4,276 listings: 189 sale prices change, all for these reasons; nothing outside prices, sizes and the labels that depend on them changes. Re-processing preview: 184 stored sale prices would be corrected; 91 protected sale prices still differ (review in S8) |
| S6 | Locations: whole-word matching (fixes Yeka and "22"), one-way label and hashtag matching (fixes Bole Bulbula), one shared location table for all three scripts | done 26 Oct 2026. New `src/locations.py` is the only place table (PLACES: code, name, city, sub-city, coordinates; ALIASES: English and Amharic names, specific before general), used by the parser, `topic_resolver.py`, `dedup_and_fix_locations.py`, `geocoder.py`, `fast_repair.py` and `fix_spaces.py`. Whole words only (Amharic prefixes such as በ/ከ/የ still match); labels and hashtags match one way; joined-up hashtags ("#summithouse", "#ቦሌቡልጋሪያ") still work; duplicate codes merged (e.g. `twenty_two`/`22_area`/`22_mazoria` → `haya_hulet`, `piyasa` → `piassa`). The geocoder now takes coordinates from the table (it also queried a column that does not exist). Checked by `tests/test_locations.py` and by old vs new parser on all 4,276 listings: 216 locations change, each reviewed (the 8 that lose a location were false matches such as the holidays Buhe and Meskel and "#TeamExcellence" read as Mexico). After a backup (`backups/ollaa_2026-10-26_before_S6.dump`) the database's old codes were renamed (18 listings, 8 protected values, 3 rental rows; 1 city fixed). Re-processing preview: 140 stored locations would change; 38 protections retire |
| S7 | Classification: web links are not noise; photo-only posts become `MEDIA_PENDING` | done 26 Oct 2026, in the parser (stored listings change in S8). A post is noise only if, links left out, fewer than 30 characters remain; a link-only post still is. Photo-only posts ("[MEDIA ONLY]", "[PDF ONLY]") get listing_class `MEDIA_PENDING`, intent `UNKNOWN`, type `MEDIA_LINK` as before, and the location of their forum topic title when it names one (849 do), else `noise`. The listener no longer gives them its own type `PENDING_MEDIA_REVIEW`. Checked by `tests/test_classification.py` and by old vs new parser on all 4,276 listings: only photo-only posts (2,843) and link posts (266) change. Re-processing preview: 4,655 legacy protections now agree with the parser and retire; 1,751 still differ |
| S8 | Re-run the fixed parser on old rows with S4's safe method (`src/reprocess.py`, report first, backup, then `--apply`), then re-count findings 3 to 12 (they should drop to 0). Review with the owner the legacy protections that still hold a value the fixed parser disagrees with (6,406 when S4 started; 1,751 after S5–S7, the rest retire automatically because the parser now agrees) | to do |
| S9 | Clean-ups: remove duplicate functions and `.txt` code copies, fill or delete empty files, make the ETL report its errors, use a limited database login instead of `postgres` | to do |
| S10 | Optional: remove the old secrets from the GitHub history | to do |
| S11 | Do before S4 (it blocks the listener): after a backup and the owner's decision, remove the 1,143 duplicate raw messages, then add a unique rule on `telegram_listings (channel, message_id)` so the listener can save; re-run `database/export_schema.py`. Also fix the column type in `dedup_fast.py` (finding 17) | done 26 Oct 2026. All duplicates came from the scraper's first runs (28 Dec 2025 three times, 3 Jan 2026). Kept, per message, the copy its processed listing uses; for 3 ads the broker had edited, the kept copy got the newest text (owner's choice; their processed listings still show the old text until S8). Removed 1,143 raw copies, 12 duplicate processed listings (none valuation-eligible) and 5 duplicate rental rows, after a backup (`backups/ollaa_2026-10-26_before_S11.dump`). Added `UNIQUE (channel, message_id)`; the listener's and scraper's save commands now store each message once (tested on the live table in a rolled-back transaction). Totals now 5,091 raw / 4,276 processed / 172 rental |
