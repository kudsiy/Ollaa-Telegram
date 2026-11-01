# Ollaa-Telegram: data quality report

State of the `ollaa` database on 1 November 2026, after the first scrape with the new
login (S18), parser fixes (S19), duplicate removal and an accuracy check (S20), and the return of
listings the old duplicate steps had removed (S22, S24). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9, S12 and S19). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 423 values that earlier hand repairs set are kept on purpose and win over the
parser; 247 of the usable listings hold at least one of them.

## Summary

- **1,577 usable listings** out of 5,774 stored listings (6,115 raw Telegram messages from
  34 channels and groups): 1,299 for sale, 273 for rent, 5 for both.
- **3,401 listings (59%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **576 sale listings are ready for a hedonic model** (price, size, named place, known type, priced
  in birr, no obvious outlier, no repeat); the sample grew by 85 in S22 and 34 in S24. Some may still be a
  property re-advertised (see "Duplicates"); read it as about 560 to 575 different properties. Only **35 rent listings** are ready, so a rent
  model is not possible yet.
- **An accuracy check found this sample not yet reliable enough for a thesis:** of 60 drawn at
  random, 20 (33%) have at least one value the advert contradicts, most often the type (see
  "Accuracy check"). Nothing has been corrected yet; the owner is checking the same 60.
- **91 of the 118 houses in the sample have one size stored as both plot and built-up**, from
  an old repair, so their built-up size is really a guess (see "Houses and plot size").
- Bedrooms are known for 58% of the model sample (65% of its homes). Floor, bathrooms,
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
| Stored listings | 5,774 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −3,401 |
| Service or share adverts, inquiries ("looking for"), junk | −730 |
| Property post, but neither sale nor rent could be told | −66 |
| **Usable listings** | **1,577** |

The 341 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 410 | 83 | 1 | 494 |
| Villa (houses, G+0 to G+4) | 372 | 27 | 2 | 401 |
| Unknown type | 161 | 5 | 1 | 167 |
| Condominium | 95 | 19 | 0 | 114 |
| Commercial (shop) | 68 | 23 | 0 | 91 |
| Land | 60 | 6 | 0 | 66 |
| Single room | 0 | 61 | 0 | 61 |
| Commercial building (whole building) | 54 | 5 | 0 | 59 |
| Studio | 17 | 32 | 1 | 50 |
| Office | 39 | 9 | 0 | 48 |
| Warehouse | 19 | 3 | 0 | 22 |
| Townhouse | 4 | 0 | 0 | 4 |
| **Total** | **1,299** | **273** | **5** | **1,577** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 424 | 76 | 2 | 502 |
| Yeka | 105 | 66 | 1 | 172 |
| Kirkos | 90 | 18 | 0 | 108 |
| Arada | 69 | 0 | 0 | 69 |
| Kolfe | 61 | 13 | 0 | 74 |
| Nifas Silk | 41 | 10 | 0 | 51 |
| Akaki | 26 | 4 | 0 | 30 |
| Lideta | 12 | 1 | 0 | 13 |
| Addis Ketema | 4 | 0 | 0 | 4 |
| Gulele | 1 | 2 | 0 | 3 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 20 | 0 | 0 | 20 |
| Gelan, Dukem (counted as Addis Ababa) | 8 | 1 | 0 | 9 |
| Place named, sub-city not in the place table | 297 | 55 | 0 | 352 |
| No place found in the text | 140 | 27 | 2 | 169 |

The 352 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

84 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 189 | 8 | 1 | 198 |
| Bole | Bole | 99 | 27 | 0 | 126 |
| Summit | — | 88 | 5 | 0 | 93 |
| Megenagna | Yeka | 59 | 7 | 0 | 66 |
| CMC | Yeka | 36 | 28 | 1 | 65 |
| Piassa | Arada | 61 | 0 | 0 | 61 |
| Kazanchis | Kirkos | 48 | 11 | 0 | 59 |
| Bole Bulbula | Bole | 35 | 9 | 0 | 44 |
| Jemo | Kolfe | 37 | 5 | 0 | 42 |
| Ayat 49 | Bole | 37 | 3 | 0 | 40 |
| Mexico | Kirkos | 29 | 5 | 0 | 34 |
| Sarbet / Old Airport | Nifas Silk | 27 | 7 | 0 | 34 |
| Figa | — | 29 | 5 | 0 | 34 |
| Summit 72 | — | 33 | 0 | 0 | 33 |
| Gerji | Yeka | 7 | 24 | 0 | 31 |
| Jacros | — | 15 | 13 | 0 | 28 |
| Haya Hulet (22) | Bole | 11 | 15 | 1 | 27 |
| Kality | Akaki | 22 | 4 | 0 | 26 |
| Bulgaria | — | 23 | 2 | 0 | 25 |
| Bole Arabsa | Bole | 22 | 3 | 0 | 25 |

## How complete each field is (usable listings)

| Field | Sale (1,299) | Rent (273) | Both (5) | All (1,577) |
|---|---|---|---|---|
| Price (sale or rent) | 85% | 75% | 0% | 83% |
| Size (built-up or plot) | 80% | 22% | 40% | 69% |
| Bedrooms | 47% | 14% | 60% | 42% |
| Bathrooms | 17% | 4% | 20% | 15% |
| Named place | 89% | 90% | 60% | 89% |
| Sub-city | 66% | 70% | 60% | 67% |
| Map coordinates (from the place table) | 77% | 71% | 60% | 76% |
| Property type | 88% | 98% | 80% | 89% |
| Floor | 20% | 23% | 20% | 21% |
| Finishing | 16% | 11% | 0% | 15% |
| Payment terms | 17% | 5% | 0% | 15% |
| Building height (G+n) | 20% | 7% | 0% | 18% |
| Posting date | 40% | 68% | 20% | 45% |

**Price, size, bedrooms and place all known: 475 listings (30%)**: 468 sale, 7 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 61 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for 709 usable listings (11 in 2025, 698 in 2026). The
  other 868 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
  an upper bound, not the posting date.
- **Coordinates** are one point per place (neighbourhood centre), and some are rough. They
  suit distance-to-centre variables, not exact positions.
- **Whole buildings** (`COMMERCIAL_BUILDING`) are stored with the land they stand on as
  their plot and no built-up size, because adverts give the land or footprint, not the
  floor area. Their price per built-up m² is therefore unknown.
- **Posts listing several properties** (a broker's list of buildings, a developer's unit
  options) are stored once, with the first property's price and size.

## Photo-only posts (`MEDIA_PENDING`)

3,401 listings (59% of all stored listings) are photos or files without readable text.
947 of them get a place from their forum topic; everything else about them is unknown.
4,301 images wait in `media_queue`, none read yet. The photo pilot (`MEDIA_PILOT.md`) found
that of 45 photos, 3 carried the words of an offer and none had a price and a size, so
reading them is not advised.

## Obvious outliers

A value is flagged when it cannot be right for Addis Ababa in 2025–2026: a sale price under
500,000 birr; under 20,000 or over 1,000,000 birr per m² (built-up; plot for land); a rent
outside 1,000–2,000,000 birr a month; a flat, studio or room under 15 m² or over 500 m²
(studios and rooms over 100 m²); a flat with more than 6 bedrooms.

**6 usable listings break a rule today**, and are left out of the model samples:

| Listing | Stored | What the advert says |
|---|---|---|
| 6726 | shop, 250,000 birr for 20 m² | shops from 20 m²; 250,000 birr is the price per m² |
| 2022 | flat, 20,000 birr for 161 m² | a price written "32,20,000" |
| 2868 | house, 12,500 birr | a price written "12,500..ሚሊየን" |
| 5723 | 300,000 birr | a price written "4.300,000" |
| 3597 | building for rent, 500 million birr a month | for sale at 500 million, "also available for rent" |
| 2600 | building for rent, 2.5 million birr a month | a G+6 building for rent: over the rule's limit, possibly right |

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

**Rule.** `src/dedup_strict.py` (tasks S20, S22) removes a listing only if it has the same words as
another (contacts, links, hashtags and channel footers left out); or the same type, named place,
price and size, with no different bedrooms or floor; or 95% the same words and the same numbers,
with nothing in conflict. Floors are also read from the text. It keeps the listing with a protected
value, else the one in the sample, else the most complete, else the newest, and never removes a protected
value. To undo a removal, delete its row in `processing_exclusions` and run `etl_runner.py`.

**Result.** S20 removed 56 repeats from 5,300 listings. S22 brought back 593 messages and removed 98
repeats (77 same words, 21 same facts): 78 of the returned messages and 20 older listings whose
returned copy was kept. 50 were usable, 13 in the sale sample. Backups:
`backups/ollaa_2026-11-01_before_S20.dump` and `backups/ollaa_2026-11-01_before_S22.dump`.

Examples:

| Removed | Kept | Why |
|---|---|---|
| 7512 (luxury_freelancers) | 7526, same channel | same words: Bisrate Gabriel flat, 12 million, 89 m² |
| 6654 (mygojo1) | 6939 (houseapartmentcarreleator) | same facts in two channels: Haile Garment G+3, 24 million, 72 m² |
| 1719 (mygojo1) | 1897 (houseapartmentcarreleator) | same facts in two channels: Wingate, 9 million, 122 m², 7th floor |
| 2402 (brokercom11) | 5575, same channel | same facts: Kazanchis Hilton, 24,999,000 birr, 141 m², other wording |
| 5366 (mygojo1) | 5727 (hugeAddisababamarket2025) | same facts in two channels: Wingate condominium, 8 million, 107 m², 13th floor |

**The first version of the rule was too loose.** Before S22 was applied, reading the planned removals
showed 4 different properties merged: a ground-floor and a 3rd-floor flat, "3floor" and "5floor", and two
rooms with other codes and sizes. The floor is now read from the text, and nearly-same adverts need the same
numbers. Listing 3785, removed in S20 by the looser rule (7th floor against 8th), was brought back.

**What is still not certain.** In the sample, 15 listings in 7 groups look like one property whose
price changed and were kept, so up to 8 of the 576 may not be different properties (for example 7150
and 2704). 7 more extra copies share type, place, price and size but differ in floor, bedrooms or second
size, or hold protected values, and 6 of the listings returned in S24 are uncertain (below). A property
advertised by two brokers with different prices or wording cannot always be detected, and different units
at one price can look alike, so read 576 as about 560 to 575 different properties.

**The old step.** `semantic_dedup.py` compared how texts look and ignored prices. A preview on 5,300
listings showed it would delete 174 usable listings, 130 with a different price from the one kept (for
example flats of 47 and 40 m² in Jemo 3 and Jemo 1, on one template). It was removed.

**Earlier deletions (tasks S21, S22).** `database/review_earlier_deletions.py` parses the kept-out
messages again:

| Removed by | Messages | Usable | Usable, a true repeat | Would fit the sale sample and repeat nothing | Now |
|---|---|---|---|---|---|
| Old near-duplicate step (`semantic_dedup.py`) | 593 | 375 | about 50 | 83 | **brought back by the owner's decision, 1 Nov 2026** |
| Old rule: same text | 125 | 69 | 69 | 0 | kept out: sound |
| Old rule: same price, size and location | 97 | 89 | 33 | 38 | **34 of the 38 brought back by the owner's decision, 1 Nov 2026**; the other 63 kept out |

The returned listings have the same parser mistakes: about 17 of the 83 sample-fit ones show a wrong type
or place in their first lines (for example 2033, an apartment called an office; 5911, 5 Kilo placed in
Mexico). They were not in the accuracy check's draw.

**The 38 of the old same-price rule (tasks S23, S24).** The first lines of each were read next to any
stored listing with the same price and size. The 28 different and 6 uncertain ones were brought back
(backup `backups/ollaa_2026-11-01_before_S24.dump`); no repeat was found among them and all 34 fit the sample:

- **28 look like different properties**, mostly condominiums in Ayat 49, Jemo and Bole Arabsa that now
  match no stored listing at all.
- **6 are uncertain** (45 and 5391; 1722; 1730; 2593; 5889): the same price and size as another listing,
  but another floor, area or building height.
- **4 are repeats** of stored listings and stay out: 10 (listing 1), 2972 (5393), and at another price
  2717 (1036) and 2732 (2735, 7160).
- About 5 of the 38 show a wrong type (for example 1302, a condominium called land).
- Why the old rule removed them cannot be shown now; most likely the parser of that time read other values.
- The other 51 usable messages of this rule that would not fit the sale sample were not read.

## Fitness for a hedonic price model

**Sale sample: 576 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, has no obvious outlier and repeats no other listing. By type:
apartment 259, villa 118, condominium 86, land 43, shop 35, office 15, warehouse 12, studio 8.
Whole buildings are not in it (no built-up size, see above).

**Left out by the owner's decision (1 November 2026):**

- **6930**: 22 million birr for 150 m²; the advert does not say whether it is land or a house.
- **6726**: 250,000 birr is the price per m², read as the total; the unit's total is not stated.

| Variable | Known in the sale sample (576) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition; see "Accuracy check") | core variables |
| Map coordinates | 86% | usable (rough, one point per place) |
| Sub-city | 74% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 58% (homes only: 65% of 471) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 34% | too incomplete |
| Bathrooms | 23% (homes: 27%) | too incomplete |
| Posting date | 37% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 14% | too incomplete |
| Finishing | 18% | too incomplete |
| Payment terms | 17% | too incomplete |

Location is thin at the neighbourhood level. The 576 listings fall in 63 places, but only
26 places have 5 or more listings and 17 have 10 or more. Only 28 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 35 listings** with rent, size, place and type (condominium 15, apartment 12,
villa 3, shop 3, others 2), so a rent model is not possible. Without requiring size there
are 199 (apartment 67, single room 56, studio 31, condominium 16, villa 16, others 13),
mostly flats, rooms and studios. That is enough to describe rents, not to model them.
`rental_listings` (rebuilt in task S13) has one row for every rent or mixed listing with a
rent: 209 rows, the 205 usable rentals with a rent plus 4 whose class keeps them out of the
usable listings (2046, 7249, 7251, 7303).

### Houses and plot size

Sizes have two separate fields, `plot_sqm` and `builtup_sqm`. Nothing is guessed for the 5
houses 6920, 6929, 6946, 6969 and 6979: their plot size is in `plot_sqm` and `builtup_sqm`
is empty, so no data needed to change. The sample needs a built-up size for a house, so they
are outside it, ready for a model that uses plot size as its own variable.

| Houses (villas, townhouses) | Listings |
|---|---|
| In the sale sample, with a built-up and a different plot size | 27 |
| In the sale sample, with the same number stored as both | 91 |
| In the sale sample, with a built-up size only, or a plot size only | 0 |
| **All houses in the sale sample** | **118** |
| Outside the sample, otherwise fit, with a plot size only (including the 5 above) | 150 |

**The 91 are a problem.** Their built-up size is a copy of one stated size, set by a repair before
26 October 2026, and is kept as a protected value. Where the advert says, the size is usually the
land ("የቦታ ስፋት 250 ካሬ"; "1,000 m² in a CCD compound" for a G+1 house). So their price per
built-up m² is not reliable, and only 27 houses in the sample have two real sizes. Releasing these
protections would leave 91 fewer houses in the sample as it is defined today, and needs the
owner's decision.

## Accuracy check

60 listings were drawn at random from the sale sample when it held 457 listings, before S22
(`random.seed(20261101)`; all 60 are still in it), and
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
2. Decide on the 91 houses whose built-up size is a copy of one stated size. 150 more houses have a
   plot size only, so a model with plot size as its own variable could use far more houses.
3. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
4. Fetch the real posting dates from Telegram for the 868 undated usable listings (the
   message ids are stored), so the model can include time.
5. Give a sub-city to the places that lack one in `src/locations.py` (352 listings).
