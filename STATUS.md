# Ollaa-Telegram: project status

Last updated: 28 October 2026 (audit redone on 26 October on the home laptop, which holds
the database; tasks S1–S12 done since).

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
  (Fixed in S9.)
- `listener.py` step 3 updates `processed_listings` by `str(tl_id)`, but forum rows are
  stored under `channel::topic::N`, so the topic-based fix never reaches them.
- `dedup_fast.py` picks the "older" listing with `min()` on ids, but ids are text, so
  "1000" counts as older than "999". (Fixed in S9.)
- Price reading gaps left after S5: totals given as "ሙሉ ክፍያ 5.7ሚሊዮን" (full payment, read
  since S9) or "80.7ካሬ = 5,770,000" without a price word are not read; the intent check
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
  discarded every post with a link. (Both removed in S9.)
- A building's monthly income ("180,000 ብር ገቢ ያለው") can be read as its sale price
  when the total is written without a price word (seen on listing 3432). (Fixed in S9.)
- `etl_runner.py` hides every error (`except Exception: errors += 1; continue`). (Fixed in S9.)
- `extract_images.py` reads images from `C:\Projects\ollaa\data\...`, which does not
  exist on this laptop (the images are in `data\images\telegram`, 747 files).
- `extract_images.py` uses the preview model `gemini-3.1-flash-lite-preview`. On
  26 October 2026 it answered every request with "503 high demand", while the new Gemini
  key worked at once with `gemini-2.5-flash`. A stable `gemini-3.1-flash-lite` is now
  available and is the likely replacement.
- `requirements.txt` had no versions and was missing `google-genai`, `pydantic`,
  `rapidfuzz`, `ollama` and `numpy`.
- Empty placeholder files: `config/telegram_channels.py`, `src/main.py`,
  `src/ocr/run_ocr.py`, `src/telegram/fetch_messages.py`, `src/utils/db.py`. (Removed in S9.)
- Copies of code saved as `.txt` (`fix_single_room.py.txt`, `src/srcshow_duplicates.py.txt`)
  and a duplicate `srcshow_duplicates.py` in the project root. (Removed in S9; the script
  is now `src/show_duplicates.py`.)
- All scripts log in as the `postgres` superuser. PostgreSQL listens on every network
  address, but its access rules only accept connections from this laptop, so it was not
  reachable from outside. (Since S9 the scripts use the limited login `ollaa_user`.)
- Left after S12: `reprocess.py` updates `processed_listings` but not `rental_listings`,
  so that table is out of date: 7 of its 172 rows belong to listings that are now sales
  (their "rent" was the building's income, e.g. 1281, 22), 40 rows have had no listing
  since earlier clean-ups, and 4 rentals have a rent but no row. Listing 1972 stores a
  bank loan (3,770,000, half of 65,000/m² × 116 m²) as its price; its type is unknown, so
  it is outside the model sample. `listener.py` step 3 (above). Posts listing several
  properties keep only the first one.
- Data quality (`DATA_QUALITY.md`, numbers from `database/data_quality.py`). On 27 October:
  779 usable listings, 266 sale listings fit for a hedonic model, 70 rent listings with a
  sale price, 34 obvious outliers, all parser mistakes. After S12 (28 October): 933 usable
  listings, 394 fit for a hedonic model, none with a sale price on a rental, no outliers;
  2,860 photo-only posts still unread; 216 listings name a place that has no sub-city in
  `src/locations.py`.

## Recount after S8 (27 October 2026)

Counted in the stored listings by `database/recount_findings.py` (read-only), before and
after re-processing:

| # | Finding | Before S8 | After S8 |
|---|---|---|---|
| 3 | Decimals cut off | 56 | 1 (listing 1291: "cash 11 million, bank 11.5 million" stores the cash price, which is right) |
| 4 | Price per m² stored as the total | 53 | 0 |
| 5 | "Yeka" where the text never names Yeka | 9 | 0 |
| 6 | 22 area where the text only has the number 22 | 6 | 1 (listing 2030 has "#22" and "Apartment 22", which is right) |
| 7 | A place named nowhere in the text | 93 | 1 (the same listing 2030) |
| 8 | Location codes not in the shared table | 0 of 79 | 0 of 89 (more, because places such as Lebu Varnero now have their own code) |
| 9 | Posts with a web link thrown away as noise | 60 | 0 |
| 10 | Photo-only posts labelled ADVERTISEMENT | 634 | 0 (2,860 are `MEDIA_PENDING`) |
| 11 | Listings that differ from today's parser | 2,941 | 0, apart from the 829 values the owner chose to protect |
| 12 | Deleted messages back as listings | 0 | 0 (815 kept out) |

Valuation data (before → after): listings with a price and a size 366 → 410; valuation
comparables (`v_valid_comparables`) 303 → 281; price segments (`market_price_model`) 189 → 175.
The comparables fell because 41 bad ones left (16 adverts or inquiries, 13 whose place was
a bug, 4 whose price or size was a misread, 8 moved to their correct segment or class and
fell out; 12 of the 41 had an impossible price per m² under 20,000 birr) while 19 joined.

## Security status

- The GitHub repository `kudsiy/Ollaa-Telegram` is **public**. From 21 May 2026 its
  history contained the old database password, an old `ollaa_user` password and an old
  Gemini key. On 27 October 2026 (task S10) they were replaced by `REMOVED_OLD_PASSWORD` /
  `REMOVED_OLD_GEMINI_KEY` in every commit of every branch, and the branches on GitHub
  were replaced. GitHub keeps showing the old commits to anyone who has their exact link
  until it cleans up; only GitHub Support can remove them sooner, which is not needed
  because all three secrets are dead.
- Any other copy of the repository made before 27 October 2026 (for example on the
  office PC) still has the old history. Do not push from it: delete that folder and clone
  the repository again. The old history is kept only in the local backup
  `backups/git_history_before_S10_2026-10-27.bundle` (never commit or upload it).
- The old Gemini keys have been deleted by the owner. A new key is kept only in `.env`.
- Both database passwords (`postgres` and `ollaa_user`) were changed on 26 October 2026
  (task S1) to long random ones kept only in `.env`. The old ones are rejected, so the
  copies that were in the GitHub history no longer work (removed in task S10).
- Since 27 October 2026 (task S9) the scripts log in as `ollaa_user`, which owns the Ollaa
  tables but cannot create databases or logins or read the server's files. The
  all-powerful `postgres` login (`DB_ADMIN_USER` / `DB_ADMIN_PASSWORD` in `.env`) is only
  used for backups and `database/export_schema.py`. `check_setup.py` warns if the
  everyday login is ever a superuser again.
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
| S8 | Re-run the fixed parser on old rows with S4's safe method (`src/reprocess.py`, report first, backup, then `--apply`), then re-count findings 3 to 12 (they should drop to 0). Review with the owner the legacy protections that still hold a value the fixed parser disagrees with (6,406 when S4 started; 1,751 after S5–S7, the rest retire automatically because the parser now agrees) | done 27 Oct 2026. The owner approved the review of the 1,751: 922 released (old "advert" labels and "noise" on photo and link posts, rent-only channels, better types, smaller areas, places named nowhere in the text, 2 prices checked by hand), 829 kept (sizes and prices filled by old repairs, the Bet_afri SINGLE_ROOM rule, repaired places, labels); rules in `database/migrations/2026_10_27_s8_release_protections.py`. After a backup (`backups/ollaa_2026-10-27_before_S8.dump`) re-processing updated 2,941 listings and retired 4,655 protections; a second run finds nothing to change; 829 protections remain. One more per-m² form ("65,000/በካሬ") was added and applied (3 listings). See "Recount after S8" below |
| S9 | Clean-ups: remove duplicate functions and `.txt` code copies, fill or delete empty files, make the ETL report its errors, use a limited database login instead of `postgres`. Added during S5–S8: remove `src/fix_418.py` and `upgrade_brain.py` (they rewrite the parser); `run_all.py` step 4 marks every SALE listing with a price and size as a comparable, adverts included; the ETL rule that makes every Bet_afri post a SINGLE_ROOM also hits Bet_afri_Business (offices); landmarks such as "Lem Hotel" outrank neighbourhood names ("Shola, behind Lem Hotel"); totals without a price word (a loan amount or a monthly income can be read instead); `dedup_fast.py` compares ids as text | done 27 Oct 2026, in three steps. (1) No change to results: removed the unused copies of the price reader in `processor.py` (752 → ~470 lines), `src/fix_418.py`, `upgrade_brain.py`, the `.txt` code copies and five empty files (`srcshow_duplicates.py` is now `src/show_duplicates.py`); the ETL lists its errors, counts skipped listings, and adds rental rows only for listings it newly adds (a junk rental row for sale listing 5651 was removed); `run_all.py` step 4 skips adverts, inquiries, junk and unread photos; `dedup_fast.py` orders ids as numbers. Old and new parser identical on all 4,276 listings. (2) Parser: Bet_afri_Business posts are no longer forced to SINGLE_ROOM; landmarks (Lem Hotel, Golagol, Sheraton, …) decide the place only when no neighbourhood is named; "ሙሉ ክፍያ" / "ጠቅላላ ክፍያ" / "full payment" are price words, and a down payment, loan, income or commission is no longer read as the sale price. Old vs new: 127 listings change, each reviewed. After a backup (`backups/ollaa_2026-10-27_before_S9.dump`) re-processing updated 45 stored listings and retired 80 protections; 749 remain. (3) Login: after a backup (`backups/ollaa_2026-10-27_before_S9_login.dump`) `ollaa_user` became the owner of every table, view and function (`database/migrations/2026_10_27_s9_app_login.py`) and `.env` now uses it; `postgres` is kept for backups and `export_schema.py` (`DB_ADMIN_USER`, `DB_ADMIN_PASSWORD`). Checked as `ollaa_user`: all tests, `check_setup.py`, re-processing report (0 changes), ETL (0 errors), recount unchanged, adding columns, refreshing the materialized views, protections still recorded; creating databases or logins is refused |
| S10 | Optional: remove the old secrets from the GitHub history | done 27 Oct 2026. A search of every version of every file in all 18 commits found three old secrets, all already dead: the old database password (24 places in about 20 old scripts), an old `ollaa_user` password (old `test_db.py`) and the old Gemini key (old `extract_images.py`). None of today's passwords or keys was ever committed. The phone numbers in the code are made-up examples (0911-234-567 style) and the Telegram `api_id` is the placeholder 123456, so they stay. After a backup of the full history (`backups/git_history_before_S10_2026-10-27.bundle`), the history was rewritten with git's own fast-export/fast-import, swapping each secret for `REMOVED_OLD_PASSWORD` / `REMOVED_OLD_GEMINI_KEY`. Checked before pushing: every commit keeps its author, date and message, only the secret lines differ, and the latest files of all 11 branches are identical. All 11 branches on GitHub were replaced (the repository has no forks or pull requests); a fresh download from GitHub contains none of the secrets. Commit ids changed, so other copies must be cloned again (see Security status) |
| S11 | Do before S4 (it blocks the listener): after a backup and the owner's decision, remove the 1,143 duplicate raw messages, then add a unique rule on `telegram_listings (channel, message_id)` so the listener can save; re-run `database/export_schema.py`. Also fix the column type in `dedup_fast.py` (finding 17) | done 26 Oct 2026. All duplicates came from the scraper's first runs (28 Dec 2025 three times, 3 Jan 2026). Kept, per message, the copy its processed listing uses; for 3 ads the broker had edited, the kept copy got the newest text (owner's choice; their processed listings still show the old text until S8). Removed 1,143 raw copies, 12 duplicate processed listings (none valuation-eligible) and 5 duplicate rental rows, after a backup (`backups/ollaa_2026-10-26_before_S11.dump`). Added `UNIQUE (channel, message_id)`; the listener's and scraper's save commands now store each message once (tested on the live table in a rolled-back transaction). Totals now 5,091 raw / 4,276 processed / 172 rental |
| S12 | Fix the parser mistakes `DATA_QUALITY.md` found: 70 rent listings carrying a sale price, and the causes of the 34 obvious outliers | done 28 Oct 2026. Causes, read in the adverts: sale adverts mentioning their rental income or a channel footer listing "ኪራይ / ሽያጭ" services were filed as rentals; rentals copied their rent into the sale price; a rent, income, remaining balance or the cash part was read as the price; prices per m² written "95,000 እስከ 115,000" or "በካሬ semi finished 95,000" were read as totals; G+1–G+4 houses were filed as apartments ("flats with 10 bedrooms") and flats in G+5+ buildings as commercial buildings; plot or building sizes were read as a flat's size; "6,400 000" was read as 6,400; adverts for company shares were read as property. The parser now decides sale or rent from words only one of them uses, ignores footers and a property's income, treats a price of 5 million or more without rental words as a sale, gives rentals no sale price, reads broker headings ("HILTON – 24,999,000 - 3 Beds"), decorative digits, "ዋጋ ....... 60 ሚልዮን", cash plus a bank loan taken over, and skips old prices ("ነበር"), dollar amounts and "from …" prices; sizes keep their whole number ("158.72 ካሬ" is 158). Checked by 61 price and 31 classification tests and by old vs new parser on all 4,276 listings (619 change, each group reviewed). After a backup (`backups/ollaa_2026-10-28_before_S12.dump`) re-processing updated 899 listings (type 240, price 231, sale/rent 298, location 0; most also got new confidence figures) and retired 113 protections the parser now agrees with; 636 remain. A second run finds nothing to change. Usable listings 779 → 933, rent listings with a sale price 70 → 0, obvious outliers 34 → 0, hedonic sale sample 266 → 394; valuation comparables 280 → 355, price segments 174 → 190. Recount: finding 3 shows 2 (1291 and 2127, both correct prices) |
