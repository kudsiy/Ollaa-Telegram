# Photo pilot: reading photo-only posts with Gemini (task S15)

28 October 2026. Code: `src/media_pilot.py` (reads the images) and
`database/media_pilot_report.py` (summary, read-only). The database was backed up first
(`backups/ollaa_2026-10-28_before_S15_pilot.dump`) and **was not changed**: nothing was
written to `processed_listings` or `media_queue`. The full results, including the words
copied from each image, are in `data/media_pilot/results.json`, which is never committed
(it can hold phone numbers).

## How it works

1. Gemini (`gemini-3.1-flash-lite`) only copies the words and numbers it sees in the image
   (Amharic and English, as written) and says in one sentence what the image shows.
2. The copied words then go through the same parser as every text post
   (`etl_runner.build_processed_values`): price, size, bedrooms, place (the location codes
   of `src/locations.py`), type and sale/rent follow exactly the text rules.
3. "Usable" and "fit for a hedonic model" use the definitions of `DATA_QUALITY.md`.

**Free tier.** A check made afterwards showed that the Gemini key's Google project has no
billing, so these 26 images were read on the free tier, where Google may use what it
receives to improve its products (2 of them showed a phone number). Since then
`media_pilot.py` checks the tier first and sends no image while the key is on the free
tier, unless told otherwise (`--allow-free-tier`).

## Why only 26 posts, not 50

- Of the 2,860 photo-only posts, only 91 have their image on this laptop; the other
  ~2,770 images were never downloaded (`media_queue` marks 3,296 of its 3,333 files as
  `PENDING`). Downloading was removed from the scraper on purpose: its comment warns that
  downloading files can make Telegram revoke the login of a flagged account, and the
  "slow and safe" downloader it planned (`media_downloader.py`) was never written.
- 16 of the 91 are extra photos of an album whose caption is already a listing (posted in
  the same second, a few messages apart); reading them would only repeat that listing.
- 54 of the 747 image files on this laptop are **empty** (0 bytes) from an interrupted
  download. Of the remaining 75 candidates, 49 were empty; Gemini rejected them.
- That leaves **26 real images**, all read: 15 from mygojo1, 10 from condoaddis, 1 from
  realityaddisababa. Reaching 50 needs downloads from Telegram (see "Decision needed").

## Results

| | Posts |
|---|---|
| Images read | 26 (no errors after retrying 7 dropped connections) |
| No words in the image at all (room photos: kitchen, bedroom, bathroom…) | 13 |
| Words, but not a property offer (news, logos, an advertising banner, a child's alphabet chart) | 11 |
| Words of a property offer, dropped by mistake (see "Mistakes") | 2 (Ayat 49 and Summit condominiums for sale) |
| **Became usable listings** | **0** (2 after the fix, both without price or size) |
| Fit for a hedonic model | 0 |

7 of the 26 were posted within a minute of a captioned listing nearby: most likely the
same album, so even a readable image there would repeat that listing.

### 10 examples

| Post | What the image shows (Gemini) | Words found (masked, in English) | Parser result | Right? |
|---|---|---|---|---|
| 2004 | A doorway with text advertising a 40/60 condominium unit for sale in Ayat 49 | "Ayat 49, 40/60, for sale, <phone>" | advert / noise | **Mistake**: a sale offer for a condominium in Ayat 49 (no price or size) |
| 1999 | An empty room in a condominium apartment for sale | "Summit condominium, house for sale" (Gemini copied ሠሚት, Summit, as "ሀሚት") | advert / noise | **Two mistakes**: a sale offer in Summit (no price or size), and Gemini misread the place name |
| 1993 | A man and a woman holding a document in front of an unfinished high-rise | "2005 registrants' association … 20 years of waiting" | not a listing | Right: news about condominium registrants |
| 2690 | A text announcement for condominium registrants | "Good news for 1997 and 2005 condominium registrants" | not a listing | Right: news |
| 2698 | A video thumbnail about a condominium lottery | "Will the condominium lottery be drawn? How many winners are there?" | not a listing | Right: news |
| 1994 | The logo of Telega.io | "Telega.io" | advert / noise | Right: a logo |
| 2675 | An advert for an advertising service on Telegram channels | "Native Advertising in Telegram Channels …" | not a listing | Right: an advert |
| 2973 | A room with a wardrobe and a children's alphabet chart | the Amharic alphabet, "MY FIRST ALPHABETS" | not a listing | Right: a toy chart in a room photo |
| 2962 | An empty, modern living room with a chandelier | (no words) | photo, unknown | Right: a room photo has nothing to read |
| 2976 | A kitchen | (no words) | photo, unknown | Right |

The full table of the 26 posts is at the end.

### Mistakes

- **Short image text is thrown away.** The parser treats a post of fewer than 30
  characters as junk (a rule written for captions). The words on a flyer are often that
  short: "አያት 49 40/60 የሚሸጥ" (Ayat 49, 40/60, for sale) was dropped. Before a full run,
  image text must not be judged by that rule. (Parser rules were not changed in this task.)
- **Album photos.** Photos posted within a minute of a captioned listing are most likely
  that listing's album. The pilot only left out same-second photos; a full run should also
  leave out photos within a minute (134 more posts) or attach them to that listing.
- **Gemini misread one place name.** Post 1999 shows "ሠሚት ኮንዶሚንየም ※የሚሸጥ ቤት" (Summit
  condominium, house for sale); Gemini copied "ሠሚት" as "ሀሚት", so Summit would be lost
  even after the short-text fix. Amharic letters that look alike can be swapped; a full
  run should spot-check place names. Three images were checked by eye (1999, 2962, 2973);
  the other two match Gemini's sentence and copied words exactly.

## Estimate for all photo-only posts

**Which posts.** 2,860 photo-only posts; about 470 are album photos of listings already
stored (same second: 318; within a minute: 134; within 10 minutes: 19). That leaves
**2,389 standalone posts**: championallsites 929, luxury_freelancers 131, mygojo1 99,
livingethio 95, addishomeset 87, hugeAddisababamarket2025 85, ET_Creatives_Homes_And_Cars 71,
Roya_King4102 66, Apartments_for_rent_Addis_Ababa 64, Betafrivip 63, and 699 in 22 other
channels. All 929 championallsites photos sit in 44 forum topics (one per developer
project), so they describe at most 44 projects, not 929 listings.

**Cost.** Measured in the pilot: 1,263 tokens in and 42 out per image. Prices from
Google's pricing page (per million tokens):

| Model | Price in / out | 2,389 posts | 2,860 posts |
|---|---|---|---|
| gemini-3.1-flash-lite (used in the pilot) | $0.25 / $1.50 | about **$0.90** | about $1.10 |
| same, Batch mode (half price, results within a day) | $0.125 / $0.75 | about $0.45 | about $0.55 |
| gemini-2.5-flash-lite (older, cheaper) | $0.10 / $0.40 | about $0.35 | about $0.40 |
| Free tier | free | $0 | $0 |

On the **free tier, Google may use the images to improve its products** (Google's pricing
page: "Used to improve our products: Yes"; paid tier: "No"). These images contain other
people's phone numbers, so the paid tier (about one dollar) is the safer choice.

**Time.**
- Downloading the 2,389 photos from Telegram, slowly (one every 5 seconds): about 3½ hours,
  about 375 MB. Needs a working Telegram login on this laptop: the scraper's login file is
  not here (only an old test login from April), so the owner may have to log in again and
  type the code Telegram sends.
- Reading them at the pilot's pace (about 13 seconds per post): about 8½ hours. On the free
  tier the daily limit (shown in Google AI Studio; reported as about 1,000 requests a day
  for Flash-Lite, not confirmed) stretches this to about 3 days. On the paid tier several
  can run at once: 1–2 hours.

**Usable listings it would add.** In the pilot: 0 of 26, or 2 of 26 (8%) after the
short-text fix, none with a price or size. Taken at face value, that is **0 to about 190
new listings from 2,389 posts, very few of them fit for the price model.** This sample is
weak: it covers two small channels (mostly mygojo1 room photos and condoaddis news), none
of the large ones. Developer brochures (championallsites, luxury_freelancers) and broker
flyers may well carry prices and sizes, so the true number could be higher, but the 929
championallsites photos can add at most 44 projects.

## Round 2: 50 photos from the large channels (prepared, waiting for the owner)

The owner approved downloading about 50 photos from the large channels and reading them on
the paid tier. Everything is ready; two steps only the owner can do come first:

1. **Log in to Telegram.** The old login on this laptop has expired. The owner runs
   `src/telegram_login.py` in a terminal and types the code Telegram sends (and the
   two-step password, if set). The login is kept in `data/sessions/` and never committed.
2. **Turn on billing for the Gemini key** in Google AI Studio (the key's project is on the
   free tier). 50 photos cost about $0.02.

Then: `src/media_pilot.py --plan 50` has chosen the posts (photos only, standalone, one per
developer project on championallsites): championallsites 10, luxury_freelancers 5,
livingethio 5, addishomeset 5, hugeAddisababamarket2025 5, ET_Creatives_Homes_And_Cars 5,
Roya_King4102 5, Apartments_for_rent_Addis_Ababa 4, Betafrivip 3, mygojo1 3.
`src/media_downloader.py` fetches them one every 6–10 seconds (about 7 minutes) and stops
at the first sign of trouble from Telegram; `src/media_pilot.py --round 2` reads them.

## All 26 posts

| Post | Channel | The image shows | Sale/rent | Type | Price (birr) | Size m² | Beds | Place | Usable |
|---|---|---|---|---|---|---|---|---|---|
| 1993 | condoaddis | A man and a woman holding a document in front of an unfinished high-rise building. | UNKNOWN | UNKNOWN |  |  |  | (no place found) | no |
| 1994 | condoaddis | The logo of the platform Telega.io. | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 1999 | condoaddis | a photo of an empty room in a condominium apartment for sale | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2000 | condoaddis | a photo of a room with a clock, a pillow, and a television box. | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2004 | condoaddis | a photo of a doorway leading to a room with curtains, with text advertising a 40/60 condominium unit for sale in Ayat 49. | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2546 | realityaddisababa | the TikTok logo | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2675 | condoaddis | An advertisement for a platform that provides native advertising services in Telegram channels. | UNKNOWN | UNKNOWN |  |  |  | (no place found) | no |
| 2684 | condoaddis | a photo of a bedroom dresser with a mirror and various items on top | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2690 | condoaddis | A text-based announcement for condominium registrants. | UNKNOWN | CONDOMINIUM |  |  |  | (no place found) | no |
| 2694 | condoaddis | a photo of residential apartment buildings with text in Amharic overlaid on top | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2698 | condoaddis | A thumbnail for a video about a condominium lottery in Addis Ababa. | UNKNOWN | CONDOMINIUM |  |  |  | (no place found) | no |
| 2959 | mygojo1 | a photo of an empty room with a window and white walls | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2960 | mygojo1 | a photo of an empty room with white walls and a hallway | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2961 | mygojo1 | a photo of an empty room viewed through an open doorway | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2962 | mygojo1 | a photo of an empty, modern living room with a chandelier and large windows. | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2963 | mygojo1 | a photo of an interior hallway in an unfinished apartment with recessed lighting. | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2964 | mygojo1 | a photo of a small bathroom with a toilet and a shower head. | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2965 | mygojo1 | a photo of a bedroom with a bed and a balcony door | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2966 | mygojo1 | a photo of an empty, bright room with white walls, tiled floors, and a chandelier. | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2973 | mygojo1 | a photo of a room with a large wooden wardrobe and a children's alphabet chart on the wall | UNKNOWN | UNKNOWN |  |  |  | (no place found) | no |
| 2974 | mygojo1 | a room with a mattress leaning against the wall and toys scattered on the floor | ADVERT | ADVERTISEMENT |  |  |  | (noise) | no |
| 2975 | mygojo1 | a photo of a hallway leading to a room with a dresser and mirror | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2976 | mygojo1 | a photo of a kitchen | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2977 | mygojo1 | A photo of a bathroom with a sink, toilet, and bathtub. | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2978 | mygojo1 | a photo of a bedroom with a bed, a dresser with a mirror, and a small nightstand | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
| 2979 | mygojo1 | a photo of a living room with a sofa, curtains, and a coffee table | UNKNOWN | MEDIA_LINK |  |  |  | (noise) | no |
