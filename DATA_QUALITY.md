# Ollaa-Telegram: data quality report

State of the `ollaa` database on 1 November 2026, after the first scrape with the new
login (S18), the parser fixes it led to (S19), and duplicate removal and an accuracy check (S20). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9, S12 and S19). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 423 values that earlier hand repairs set are kept on purpose and win over the
parser; 247 of the usable listings hold at least one of them.

## Summary

- **1,217 usable listings** out of 5,244 stored listings (6,115 raw Telegram messages from
  34 channels and groups): 989 for sale, 224 for rent, 4 for both.
- **3,401 listings (65%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **457 sale listings are ready for a hedonic model, all different properties as far as the
  checks can tell** (price, size, named place, known type, priced in birr, no obvious
  outlier, no repeat). Only **33 rent listings** are, so a rent model is not possible yet.
- **An accuracy check found these 457 not yet reliable enough for a thesis:** of 60 drawn at
  random, 20 (33%) have at least one value the advert contradicts, most often the type (see
  "Accuracy check"). Nothing has been corrected yet; the owner is checking the same 60.
- **91 of the 109 houses in the sample have one size stored as both plot and built-up**, from
  an old repair, so their built-up size is really a guess (see "Houses and plot size").
- Bedrooms are known for 56% of the model sample (62% of its homes). Floor, bathrooms,
  posting date, building height, finishing and payment terms are known for about a third
  or less, too few to use as model variables.

## Definitions

- **Usable listing**: a post offering a property for sale, rent or both, whose text was
  read. Excluded: photo-only posts (`MEDIA_PENDING`), service adverts, adverts for company
  shares, inquiries ("looking for…"), junk, and property posts whose sale/rent intent
  could not be told.
- **Prices** are asking prices taken from adverts, not transaction prices, in birr.
  Sizes are in m².
- **Named place**: one of the places in `src/locations.py`. **Sub-city** comes from the
  same table.

## From stored listings to usable listings

| Step | Listings |
|---|---|
| Stored listings | 5,244 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −3,401 |
| Service or share adverts, inquiries ("looking for"), junk | −569 |
| Property post, but neither sale nor rent could be told | −57 |
| **Usable listings** | **1,217** |

The 871 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 312 | 64 | 1 | 377 |
| Villa (houses, G+0 to G+4) | 261 | 24 | 2 | 287 |
| Unknown type | 134 | 5 | 1 | 140 |
| Commercial (shop) | 65 | 23 | 0 | 88 |
| Condominium | 60 | 17 | 0 | 77 |
| Commercial building (whole building) | 50 | 3 | 0 | 53 |
| Office | 37 | 9 | 0 | 46 |
| Single room | 0 | 46 | 0 | 46 |
| Studio | 15 | 29 | 0 | 44 |
| Land | 36 | 1 | 0 | 37 |
| Warehouse | 18 | 3 | 0 | 21 |
| Townhouse | 1 | 0 | 0 | 1 |
| **Total** | **989** | **224** | **4** | **1,217** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 323 | 58 | 1 | 382 |
| Yeka | 83 | 54 | 1 | 138 |
| Kirkos | 65 | 17 | 0 | 82 |
| Arada | 61 | 0 | 0 | 61 |
| Kolfe | 33 | 11 | 0 | 44 |
| Nifas Silk | 35 | 8 | 0 | 43 |
| Akaki | 16 | 4 | 0 | 20 |
| Lideta | 11 | 1 | 0 | 12 |
| Addis Ketema | 4 | 0 | 0 | 4 |
| Gulele | 1 | 1 | 0 | 2 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 16 | 0 | 0 | 16 |
| Gelan, Dukem (counted as Addis Ababa) | 6 | 1 | 0 | 7 |
| Place named, sub-city not in the place table | 225 | 51 | 0 | 276 |
| No place found in the text | 109 | 18 | 2 | 129 |

The 276 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

83 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 135 | 8 | 0 | 143 |
| Bole | Bole | 85 | 19 | 0 | 104 |
| Summit | — | 65 | 5 | 0 | 70 |
| Piassa | Arada | 54 | 0 | 0 | 54 |
| Megenagna | Yeka | 47 | 6 | 0 | 53 |
| CMC | Yeka | 27 | 22 | 1 | 50 |
| Kazanchis | Kirkos | 37 | 11 | 0 | 48 |
| Bole Bulbula | Bole | 28 | 8 | 0 | 36 |
| Sarbet / Old Airport | Nifas Silk | 25 | 6 | 0 | 31 |
| Summit 72 | — | 28 | 0 | 0 | 28 |
| Gerji | Yeka | 6 | 21 | 0 | 27 |
| Figa | — | 21 | 5 | 0 | 26 |
| Ayat 49 | Bole | 24 | 2 | 0 | 26 |
| Haya Hulet (22) | Bole | 10 | 11 | 1 | 22 |
| Jacros | — | 11 | 10 | 0 | 21 |
| Mexico | Kirkos | 15 | 5 | 0 | 20 |
| Jemo | Kolfe | 15 | 5 | 0 | 20 |
| Bulgaria | — | 16 | 2 | 0 | 18 |
| Bole Arabsa | Bole | 16 | 2 | 0 | 18 |
| Kality | Akaki | 14 | 4 | 0 | 18 |

## How complete each field is (usable listings)

| Field | Sale (989) | Rent (224) | Both (4) | All (1,217) |
|---|---|---|---|---|
| Price (sale or rent) | 83% | 75% | 0% | 81% |
| Size (built-up or plot) | 78% | 25% | 50% | 68% |
| Bedrooms | 48% | 17% | 50% | 42% |
| Bathrooms | 17% | 4% | 25% | 15% |
| Named place | 89% | 92% | 50% | 89% |
| Sub-city | 66% | 69% | 50% | 67% |
| Map coordinates (from the place table) | 76% | 71% | 50% | 75% |
| Property type | 86% | 98% | 75% | 88% |
| Floor | 21% | 26% | 25% | 22% |
| Finishing | 16% | 10% | 0% | 15% |
| Payment terms | 18% | 6% | 0% | 16% |
| Building height (G+n) | 20% | 6% | 0% | 18% |
| Posting date | 38% | 68% | 25% | 44% |

**Price, size, bedrooms and place all known: 359 listings (29%)**: 352 sale, 7 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 36 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for 533 usable listings (11 in 2025, 522 in 2026). The
  other 684 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
  an upper bound, not the posting date.
- **Coordinates** are one point per place (neighbourhood centre), and some are rough. They
  suit distance-to-centre variables, not exact positions.
- **Whole buildings** (`COMMERCIAL_BUILDING`) are stored with the land they stand on as
  their plot and no built-up size, because adverts give the land or footprint, not the
  floor area. Their price per built-up m² is therefore unknown.
- **Posts listing several properties** (a broker's list of buildings, a developer's unit
  options) are stored once, with the first property's price and size.

## Photo-only posts (`MEDIA_PENDING`)

3,401 listings (64% of all stored listings) are photos or files without readable text.
947 of them get a place from their forum topic; everything else about them is unknown.
4,301 images wait in `media_queue`, none read yet. The photo pilot (`MEDIA_PILOT.md`) found
that of 45 photos, 3 carried the words of an offer and none had a price and a size, so
reading them is not advised.

## Obvious outliers

A value is flagged when it cannot be right for Addis Ababa in 2025–2026: a sale price under
500,000 birr; under 20,000 or over 1,000,000 birr per m² (built-up; plot for land); a rent
outside 1,000–2,000,000 birr a month; a flat, studio or room under 15 m² or over 500 m²
(studios and rooms over 100 m²); a flat with more than 6 bedrooms.

**1 usable listing breaks a rule today**: 6726 (ApartmentForYouAyatRealEstate), stored as a
shop of 20 m² for 250,000 birr. The advert sells shops from 20 m² and 250,000 birr is the
price per m². It is too rare a wording to justify a rule of its own.

The first scrape brought 5 such listings; the other 4 were fixed in task S19.
On 27 October 34 did. Reading their adverts
showed parser mistakes only, all fixed in task S12 (one more, 6043, a 3-bedroom flat of
125 m² that the Bet_afri channel rule called a single room, was fixed in S14, when that
rule began reading what each post offers):

- a rent, rental income, remaining balance or the cash part read as the sale price
  (now skipped; cash plus a bank loan the buyer takes over makes the price);
- a price per m² read as the total ("95,000 እስከ 115,000", "በካሬ semi finished 95,000");
- houses (G+1 to G+4) filed as apartments, which made "flats with 10 bedrooms";
- plot or building sizes read as a flat's size, and whole-building prices paired with one
  unit's size;
- "6,400 000" read as 6,400;
- adverts for company shares read as property (now adverts, not listings).

## Mistakes found in the first scrape

Reading the 336 new usable listings of 1 November showed parser mistakes. Task S19 fixed
these (old and new parser compared on every listing; 102 listings changed, 27 of them older
ones; backup `backups/ollaa_2026-11-01_before_S19.dump`):

- 26 houses and plots called warehouses, because many posts of houseapartmentcarreleator and
  hugeAddisababamarket2025 end with a menu of links, one of them "land and warehouses".
  16 were in the sale sample;
- construction news and company posts called rentals, because "current" and "different"
  contain "rent";
- the broker's stated 2% commission read as the sale price (6930, 6931), now the bank part
  plus the cash part;
- prices missed: "8,5 ሚሊየን" (a comma as the decimal point), a price alone on its line;
- sizes missed: "4,500 ካሬ" (a comma for thousands);
- vehicles and car parts (ET_Creatives_Homes_And_Cars) and captions with only
  realityaddisababa's name and contacts, counted as property. These are no longer listings.

**Known mistakes that remain:**

- 6726, above; and all those found by the accuracy check below.
- Some wrong types and places seen while reading, not counted: 7368 is land but called a
  villa; 6939 is a G+3 building called an apartment; 7158 is in Gerji but placed in Bole.
- 6930 is stored as land (22 million birr, 150 m²), but its advert does not say whether it
  is land or a house. Left out of the model sample with 6726 (see below).
- 153 usable listings had neither a price nor a size at that point. They are counted as usable but
  cannot enter the model samples.

## Duplicates

**Rule.** `src/dedup_strict.py` (task S20) removes a listing only if it has the same words as
another (contacts, links, hashtags and channel footers left out); or the same type, named
place, price and size, with no different bedrooms or floor; or 95% the same words with
nothing in conflict. It keeps the listing with a protected value, else the one in the
sample, else the most complete, else the newest, and never removes a protected value.

**Result on 5,300 listings: 56 repeats removed** (36 same words, 19 same facts, 1 nearly the
same words): 30 were usable, 8 in the sale sample, which went from **465 to 457 different
properties**. 13 repeated across channels, 43 within one channel. Backup:
`backups/ollaa_2026-11-01_before_S20.dump`. To undo one, delete its row in
`processing_exclusions` and run `etl_runner.py`.

Examples:

| Removed | Kept | Why |
|---|---|---|
| 7512 (luxury_freelancers) | 7526, same channel | same words: Bisrate Gabriel flat, 12 million, 89 m² |
| 6654 (mygojo1) | 6939 (houseapartmentcarreleator) | same facts in two channels: Haile Garment G+3, 24 million, 72 m² |
| 1719 (mygojo1) | 1897 (houseapartmentcarreleator) | same facts in two channels: Wingate, 9 million, 122 m², 7th floor |
| 2402 (brokercom11) | 5575, same channel | same facts: Kazanchis Hilton, 24,999,000 birr, 141 m², other wording |
| 6828 (TemerApartmentShop) | 6831, same channel | same facts: Sarbet shop, 7 million, 20 m², other wording |

**What is still not certain.** Two pairs in the sample look like one property whose price
changed, and were kept (7150 and 2704, 7160 and 2735, same broker and size). 4 more share type,
place, price and size but were kept: their floor, bedrooms or second size differ, or both hold
protected values. A
property advertised by two brokers with different prices cannot be detected, so 457 is an
upper limit.

**The old step was not run.** `semantic_dedup.py`, the step `run_all.py` used, was previewed
first: it would have deleted 257 listings, 174 of them usable and 58 in the sample, and 130
of the 174 had a different price from the listing kept (for example flats of 47 and 40 m² in
Jemo 3 and Jemo 1, posted on one template). It compared how texts look and ignored prices.
It was removed, and `run_all.py` now uses `dedup_strict.py`.

**Earlier deletions need review.** 593 messages were removed before 26 October 2026, most likely by
that same script. Parsed again today (read only): 375 would be usable and 98 would fit the
sale sample, and 91 of those 98 have no stored listing with the same type, place, price and size. So
up to about 83 different properties may have been lost. They have not been read one by one
and nothing has been restored.

## Fitness for a hedonic price model

**Sale sample: 457 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, has no obvious outlier and repeats no other listing. By type:
apartment 206, villa 109, condominium 52, shop 34, land 24, office 14, warehouse 11, studio 7.
Whole buildings are not in it (no built-up size, see above).

**Left out by the owner's decision (1 November 2026):**

- **6930**: 22 million birr for 150 m²; the advert does not say whether it is land or a house.
- **6726**: 250,000 birr is the price per m², read as the total; the unit's total is not stated.

| Variable | Known in the sale sample (457) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition; see "Accuracy check") | core variables |
| Map coordinates | 86% | usable (rough, one point per place) |
| Sub-city | 74% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 56% (homes only: 62% of 374) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 33% | too incomplete |
| Bathrooms | 24% (homes: 28%) | too incomplete |
| Posting date | 33% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 17% | too incomplete |
| Finishing | 17% | too incomplete |
| Payment terms | 18% | too incomplete |

Location is thin at the neighbourhood level. The 457 listings fall in 61 places, but only
24 places have 5 or more listings and 14 have 10 or more. Only 23 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 33 listings** with rent, size, place and type (condominium 14, apartment 11,
villa 3, shop 3, others 2), so a rent model is not possible. Without requiring size there
are 164 (apartment 50, single room 45, studio 28, condominium 14, villa 14, others 13),
mostly flats, rooms and studios. That is enough to describe rents, not to model them.
`rental_listings` (rebuilt in task S13) has one row for every rent or mixed listing with a
rent: 172 rows, the 168 usable rentals with a rent plus 4 whose class keeps them out of the
usable listings (2046, 7249, 7251, 7303).

### Houses and plot size

Sizes have two separate fields, `plot_sqm` and `builtup_sqm`. Nothing is guessed for the 5
houses 6920, 6929, 6946, 6969 and 6979: their plot size is in `plot_sqm` and `builtup_sqm`
is empty, so no data needed to change. The sample needs a built-up size for a house, so they
are outside it, ready for a model that uses plot size as its own variable.

| Houses (villas, townhouses) | Listings |
|---|---|
| In the sale sample, with a built-up and a different plot size | 18 |
| In the sale sample, with the same number stored as both | 91 |
| In the sale sample, with a built-up size only, or a plot size only | 0 |
| **All houses in the sale sample** | **109** |
| Outside the sample, otherwise fit, with a plot size only (including the 5 above) | 79 |

**The 91 are a problem.** Their built-up size is a copy of one stated size, set by a repair before
26 October 2026, and is kept as a protected value. Where the advert says, the size is usually the
land ("የቦታ ስፋት 250 ካሬ"; "1,000 m² in a CCD compound" for a G+1 house). So their price per
built-up m² is not reliable, and only 18 houses in the sample have two real sizes. Releasing these
protections would leave 91 fewer houses in the sample as it is defined today, and needs the
owner's decision.

## Accuracy check

60 listings were drawn at random from the 457 of the sale sample (`random.seed(20261101)`) and
each advert was read against the stored type, place, price, size and bedrooms by Claude. The
owner, a valuer, is checking the same 60: `database/accuracy_check.py` writes the file
`data/accuracy_check/accuracy_check_60.html` (not committed). These are Claude's counts, not yet
confirmed. Nothing has been corrected.

**20 of 60 (33%) have at least one value the advert contradicts.** With only 60 listings the true
share is roughly between 23% and 46% (95% interval).

| Field | Wrong, of 60 | Listings | Typical cause |
|---|---|---|---|
| Type | 12 | 21, 37, 1036, 1123, 1260, 1312, 1316, 2095, 2341, 2519, 2842, 7333 | a word elsewhere in the advert: "sale office" and "Property Management office" make an office, "መጋዘን" in a broker's footer a warehouse, "ሱቅ" a shop, "በምርጥ ቦታ" (in a good place) land |
| Size | 9 | 21, 1111, 1260, 1283, 1316, 2519, 2842, 6632, 7333 | adverts listing several units or sizes: the price of one is paired with the size of another |
| Place | 4 | 1019, 1260, 1316, 7156 | a channel's standing hashtags (#Bole, #ሰሚት) instead of the advert's own place |
| Bedrooms | 3 | 1123, 2426, 2444 | adverts with 2- and 3-bedroom units |
| Price | 2 | 1893, 7333 | an old price kept next to the reduced one; cash part without the bank loan |

The price is the most reliable field and the type the least. 8 of the 12 wrong types are residential
homes stored as a shop, office or warehouse, so they would distort a model's type effects.

Other things seen, not counted as wrong:

- **13 of 60:** houses with one size stored as both plot and built-up (see above). With them, 32 of
  60 have a problem (listing 1893 is in both groups).
- **10 of 60:** bedrooms stated but not stored (for example "ባለ ሶስት መኝታ", "Bedroom: 3").
- **4 of 60:** a right but less exact place (Ayat for Ayat 49, Bole for Bole 22).
- **2 of 60:** a plot size stored for a flat, not in the advert.
- Size conventions differ: 155(145) m² stores the gross size in 1809 and the net size in 5552.
- 1260 is a list of many properties and should not be one listing; 1893 says it was sold.

## What would improve the data most

1. Finish the accuracy check with the owner and correct the sample: the type rules first, then
   adverts listing several units.
2. Decide on the 91 houses whose built-up size is a copy of one stated size.
3. Review the 593 earlier deletions: up to about 83 different properties may have been lost.
4. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
5. Fetch the real posting dates from Telegram for the 684 undated usable listings (the
   message ids are stored), so the model can include time.
6. Give a sub-city to the places that lack one in `src/locations.py` (276 listings).
