# Ollaa-Telegram: data quality report

State of the `ollaa` database on 1 November 2026, after the first scrape with the new
login (S18), parser fixes (S19), duplicate removal and an accuracy check (S20), and the return of
listings the old duplicate steps had removed (S22, S24), the clearing of copied built-up sizes (S25), and parser fixes
from the accuracy check (S26). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9, S12, S19 and S26). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 324 values that earlier hand repairs set are kept on purpose and win over the
parser; 164 of the usable listings hold at least one of them.

## Summary

- **1,577 usable listings** out of 5,774 stored listings (6,115 raw Telegram messages from
  34 channels and groups): 1,299 for sale, 273 for rent, 5 for both.
- **3,401 listings (59%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **484 sale listings are ready for a hedonic model** (price, size, named place, known type, priced
  in birr, no obvious outlier). About 6 are repeats not yet removed, and some may be a property
  re-advertised (see "Duplicates"); read it as about 465 to 480 different properties. Only **34 rent
  listings** are ready, so a rent model is not possible yet.
- **Accuracy improved, by Claude's reading: 20 of 60 random listings (33%) had a value the advert
  contradicts before the parser fixes of task S26, 6 of a new random 60 (10%, likely 5% to 20%) after
  them.** The owner has not yet checked either set (see "Accuracy check").
- **Only 15 houses are in the sale sample; 248 more have a plot size only.** A model using plot size
  as its own variable could use them; the sample as defined today needs a built-up size for a house.
- Bedrooms are known for 74% of the model sample (88% of its homes). Floor, bathrooms, posting date,
  building height, finishing and payment terms are known for 40% or less, too few to use as model
  variables.

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
| Apartment | 451 | 87 | 2 | 540 |
| Villa (houses, G+0 to G+4) | 361 | 27 | 1 | 389 |
| Unknown type | 153 | 5 | 1 | 159 |
| Condominium | 113 | 19 | 0 | 132 |
| Land | 74 | 6 | 0 | 80 |
| Commercial (shop) | 42 | 21 | 0 | 63 |
| Single room | 0 | 61 | 0 | 61 |
| Commercial building (whole building) | 54 | 5 | 0 | 59 |
| Studio | 17 | 32 | 1 | 50 |
| Office | 19 | 7 | 0 | 26 |
| Warehouse | 11 | 3 | 0 | 14 |
| Townhouse | 4 | 0 | 0 | 4 |
| **Total** | **1,299** | **273** | **5** | **1,577** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 423 | 76 | 2 | 501 |
| Yeka | 102 | 66 | 0 | 168 |
| Kirkos | 82 | 18 | 1 | 101 |
| Kolfe | 62 | 13 | 0 | 75 |
| Arada | 68 | 0 | 0 | 68 |
| Nifas Silk | 51 | 11 | 0 | 62 |
| Akaki | 26 | 4 | 0 | 30 |
| Lideta | 12 | 1 | 0 | 13 |
| Addis Ketema | 3 | 0 | 0 | 3 |
| Gulele | 1 | 2 | 0 | 3 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 21 | 0 | 0 | 21 |
| Gelan, Dukem (counted as Addis Ababa) | 8 | 1 | 0 | 9 |
| Place named, sub-city not in the place table | 299 | 54 | 0 | 353 |
| No place found in the text | 140 | 27 | 2 | 169 |

The 353 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

84 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 194 | 8 | 1 | 203 |
| Bole | Bole | 89 | 27 | 0 | 116 |
| Summit | — | 83 | 5 | 0 | 88 |
| Megenagna | Yeka | 59 | 7 | 0 | 66 |
| Piassa | Arada | 60 | 0 | 0 | 60 |
| CMC | Yeka | 31 | 28 | 0 | 59 |
| Kazanchis | Kirkos | 45 | 11 | 1 | 57 |
| Bole Bulbula | Bole | 39 | 9 | 0 | 48 |
| Sarbet / Old Airport | Nifas Silk | 37 | 8 | 0 | 45 |
| Figa | — | 38 | 5 | 0 | 43 |
| Jemo | Kolfe | 37 | 5 | 0 | 42 |
| Ayat 49 | Bole | 36 | 3 | 0 | 39 |
| Summit 72 | — | 33 | 0 | 0 | 33 |
| Gerji | Yeka | 6 | 24 | 0 | 30 |
| Jacros | — | 15 | 13 | 0 | 28 |
| Haya Hulet (22) | Bole | 11 | 15 | 1 | 27 |
| Mexico | Kirkos | 21 | 5 | 0 | 26 |
| Kality | Akaki | 22 | 4 | 0 | 26 |
| Bole Arabsa | Bole | 22 | 3 | 0 | 25 |
| Bulgaria | — | 19 | 1 | 0 | 20 |

## How complete each field is (usable listings)

| Field | Sale (1,299) | Rent (273) | Both (5) | All (1,577) |
|---|---|---|---|---|
| Price (sale or rent) | 85% | 75% | 0% | 83% |
| Size (built-up or plot) | 80% | 22% | 40% | 69% |
| Bedrooms | 54% | 49% | 60% | 53% |
| Bathrooms | 17% | 4% | 20% | 15% |
| Named place | 89% | 90% | 60% | 89% |
| Sub-city | 66% | 70% | 60% | 67% |
| Map coordinates (from the place table) | 77% | 72% | 60% | 76% |
| Property type | 88% | 98% | 80% | 90% |
| Floor | 20% | 23% | 20% | 21% |
| Finishing | 16% | 11% | 0% | 15% |
| Payment terms | 17% | 5% | 0% | 15% |
| Building height (G+n) | 20% | 5% | 0% | 17% |
| Posting date | 40% | 68% | 20% | 45% |

**Price, size, bedrooms and place all known: 569 listings (36%)**: 536 sale, 33 rent.

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

**5 usable listings break a rule today**, and are left out of the model samples:

| Listing | Stored | What the advert says |
|---|---|---|
| 6726 | 250,000 birr for 20 m² | shops from 20 m²; 250,000 birr is the price per m² |
| 2022 | flat, 20,000 birr for 161 m² | a price written "32,20,000" |
| 2868 | house, 12,500 birr | a price written "12,500..ሚሊየን" |
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
- 6939 is a G+3 building called an apartment.
- 6930 is stored as land (22 million birr, 150 m²), but its advert does not say whether it
  is land or a house. Left out of the model sample with 6726 (see below).
- 153 usable listings had neither a price nor a size at that point. They are counted as usable but
  cannot enter the model samples.

## Duplicates

**Rule.** `src/dedup_strict.py` (tasks S20, S22, S26) removes a listing only if it has the same words as
another (contacts, links, hashtags and channel footers left out); or the same type, named place,
price and size, with no different bedrooms, floor or building height; or 95% the same words and the same numbers,
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

**Not removed yet.** After the parser fixes of S26 corrected types, `dedup_strict.py` reports 9 more
repeats (6 in the sale sample), for example 1103 and 1309 (Sarbet, 81 m², 5.7 million). The owner has not
been asked yet, so they are still stored.

**What is still not certain.** In the sample, 15 listings in 7 groups look like one property whose
price changed and were kept, so up to 8 of the 484 may not be different properties (for example 7150
and 2704). More extra copies share type, place, price and size but differ in floor, bedrooms or second
size, or hold protected values, and 6 of the listings returned in S24 are uncertain (below). A property
advertised by two brokers with different prices or wording cannot always be detected, and different units
at one price can look alike, so read 484 as about 465 to 480 different properties.

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

**Sale sample: 484 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, has no obvious outlier and repeats no other listing. By type:
apartment 281, condominium 98, land 54, shop 18, villa 15, studio 8, office 5, warehouse 5.
Whole buildings and houses with a plot size only are not in it (no built-up size).

**Left out by the owner's decision (1 November 2026):**

- **6930**: 22 million birr for 150 m²; the advert does not say whether it is land or a house.
- **6726**: 250,000 birr is the price per m², read as the total; the unit's total is not stated.

| Variable | Known in the sale sample (484) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition; see "Accuracy check") | core variables |
| Map coordinates | 85% | usable (rough, one point per place) |
| Sub-city | 76% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 74% (homes only: 88% of 402) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 40% | too incomplete |
| Bathrooms | 25% (homes: 30%) | too incomplete |
| Posting date | 39% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 4% | too incomplete |
| Finishing | 20% | too incomplete |
| Payment terms | 18% | too incomplete |

Location is thin at the neighbourhood level. The 484 listings fall in 57 places, but only
27 places have 5 or more listings and 16 have 10 or more. Only 26 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 34 listings** with rent, size, place and type (condominium 15, apartment 12,
shop 3, villa 2, others 2), so a rent model is not possible. Without requiring size there
are 199 (apartment 70, single room 56, studio 31, condominium 16, villa 16, others 10),
mostly flats, rooms and studios. That is enough to describe rents, not to model them.
`rental_listings` (rebuilt in task S13) has one row for every rent or mixed listing with a
rent: 209 rows, the 205 usable rentals with a rent plus 4 whose class keeps them out of the
usable listings (2046, 7249, 7251, 7303).

### Houses and plot size

Sizes have two separate fields, `plot_sqm` and `builtup_sqm`. No built-up size is guessed: where an advert
gives one size for a house, it is the plot and built-up stays empty.

**Copied sizes cleared (task S25, the owner's decision).** 91 houses in the sale sample had one stated size stored as both
plot and built-up, by a repair before 26 October 2026, kept as a protected value. Where the advert
says, that size was usually the land ("የቦታ ስፋት 250 ካሬ"; "1,000 m² in a CCD compound" for a G+1 house). The 91
protections were released (`database/migrations/2026_11_01_s25_clear_copied_builtup.py`, backup
`backups/ollaa_2026-11-01_before_S25.dump`) and `reprocess.py` updated exactly those 91: built-up is empty, the plot
size is unchanged. Protected values went from 423 to 332. The sale sample went from 576 to 485.

| Houses (villas, townhouses) | Before S25 | After S25 | After S26 |
|---|---|---|---|
| In the sale sample, with a built-up and a different plot size | 27 | 27 | 15 |
| In the sale sample, with the same number stored as both | 91 | 0 | 0 |
| **All houses in the sale sample** | **118** | **27** | **15** |
| Outside the sample, otherwise fit, with a plot size only | 150 | 241 | 248 |

In S26, houses whose two sizes are the land on the title deed and the land held ("በካርታ 120 ካሬ, በይዞታ 160 ካሬ")
lost a built-up size that was never stated. Of the 15 left, some built-up sizes are the house's footprint ("300 ካሬ ላይ
ያረፈ", for a G+3), not its floor area.

19 other houses outside the sample (no price or no named place) still hold the same kind of copied size. They
are protected and were not part of the owner's decision.

## Accuracy check

**These are Claude's counts from reading the adverts; the owner has not confirmed them.** The owner asked to
go ahead on them on 1 November 2026, and can still check either file: `database/accuracy_check.py` writes
`data/accuracy_check/accuracy_check_60.html` (round 1, with the values as they then were) and
`accuracy_check_60_round2.html` (not committed). A listing counts as wrong when the advert contradicts a stored
type, place, price, size or bedrooms.

| | Round 1, before the fixes | Round 2, after the fixes |
|---|---|---|
| Listings drawn at random from the sale sample | 60 of 457 | 60 of 492, none from round 1 |
| **With at least one wrong value** | **20 (33%)** | **6 (10%)** |
| Likely true share (95% interval) | 23% to 46% | 5% to 20% |
| Type wrong | 12 | 3 |
| Size wrong | 9 | 4 |
| Place wrong | 4 | 1 |
| Price wrong | 2 | 1 |
| Bedrooms wrong | 3 | 0 |
| Bedrooms stated but not stored | 10 | 1 |

Three cautions. One reader made both counts, knowing the rules. That reader read about the first 620 characters of each
advert, and long ones run past that. And 2 of round 2's 6 (2836, 2841) showed the title-deed-and-holding mistake, which was
then fixed; they left the sample and 2 random listings replaced them, so the file shows 4 wrong. 10% is the fair figure, because
that rule was written after seeing them.

**The 4 still in the file:** 1099 and 1744 are flats called offices, because the wrong type is a **protected value** (with 2625,
3 such types are in the sample, which the owner must decide on). 2342 and 2887 are adverts for several sites or projects, with
no one unit's price and size: the parser has no good answer for those.

**What task S26 changed in the parser** (`src/run_pipeline.py`, `src/processor.py`, `src/locations.py`; 34 new cases in
`tests/test_classification.py`, backup `backups/ollaa_2026-11-01_before_S26.dump`). `reprocess.py` updated 527
listings, none added or lost, and retired 8 protections the parser now agrees with (332 to 324):

| Mistake | Rule now | Listings changed |
|---|---|---|
| Type: a word elsewhere made it an office, shop or warehouse | such a word counts only before the words of a home; hashtags and a broker's list of what it sells do not count | type: 179 |
| Type: spellings, developers, land | "ኮዶሚኔም", "ምኝታ"; a developer's homes are flats; an advert opening with land is land | (in the 179) |
| Size: price of one unit, size of another | the first unit's size, not the smallest; not the land, a footprint or the end of a range | built-up: 77, plot: 43 |
| Size: title deed and holding | both are land: no built-up size | (in the above) |
| Place: a channel's standing hashtags | the top of the advert first, then hashtags; decorative letters read; a hashtag may narrow a wide area; Bet_afri unchanged | 92 |
| Bedrooms: another unit's; not read | those on the line of the stored size; "ባለ ሶስት", "Bedroom: 3", "5 ምቹ መኝታ" | 213 |
| Price: old price, loan left out | the reduced price; "የባንክ እዳ ... ለጁ" adds up; "4.300,000" | 18 |

Effect on the sale sample (485 to 484):

| Type | Before | After |
|---|---|---|
| Apartment | 259 | 281 |
| Condominium | 86 | 98 |
| Land | 43 | 54 |
| Shop | 35 | 18 |
| Villa | 27 | 15 |
| Office | 15 | 5 |
| Warehouse | 12 | 5 |
| Studio | 8 | 8 |

Usable listings stayed 1,577. Bedrooms known in them went from 655 to 832.

Other things seen, not counted as wrong:

(Round 1, before the fixes.)

- **13 of 60:** houses with one size stored as both plot and built-up, cleared in S25.
- **10 of 60:** bedrooms stated but not stored, fixed in S26.
- **4 of 60:** a right but less exact place (Ayat for Ayat 49, Bole for Bole 22).
- **2 of 60:** a plot size stored for a flat, not in the advert.
- Size conventions differ: 155(145) m² stores the gross size in 1809 and the net size in 5552.
- 1260 is a list of many properties and should not be one listing; 1893 says it was sold.

## What would improve the data most

1. The owner's own check of the round 2 file, to confirm the 10%.
2. Decide how to model houses: 248 with a plot size only are outside the sample, against 15 inside it.
3. Release the 3 protected wrong types (1099, 1744, 2625) and remove the 9 repeats found after the fixes.
4. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
5. Fetch the real posting dates from Telegram for the 868 undated usable listings (the
   message ids are stored), so the model can include time.
6. Give a sub-city to the places that lack one in `src/locations.py` (353 listings).
