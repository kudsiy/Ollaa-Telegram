# Ollaa-Telegram: data quality report

State of the `ollaa` database on 1 November 2026, after the first scrape with the new
login (task S18) and the parser fixes it led to (task S19). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9, S12 and S19). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 423 values that earlier hand repairs set are kept on purpose and win over the
parser; 247 of the usable listings hold at least one of them.

## Summary

- **1,247 usable listings** out of 5,300 stored listings (6,115 raw Telegram messages from
  34 channels and groups): 1,013 for sale, 229 for rent, 5 for both.
- **3,401 listings (64%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **466 sale listings are ready for a hedonic model** (price, size, named place, known
  type, priced in birr, no obvious outlier). Only **35 rent listings** are, so a rent
  model is not possible yet.
- Bedrooms are known for 56% of the model sample (62% of its homes). Floor, bathrooms,
  posting date, building height, finishing and payment terms are known for about a third
  or less, too few to use as model variables.
- **1 usable listing has an obviously impossible value** (6726, see "Obvious outliers"). It
  is left out of the model samples. Other mistakes remain (see "Known mistakes").

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
| Stored listings | 5,300 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −3,401 |
| Service or share adverts, inquiries ("looking for"), junk | −595 |
| Property post, but neither sale nor rent could be told | −57 |
| **Usable listings** | **1,247** |

The 815 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 321 | 66 | 1 | 388 |
| Villa (houses, G+0 to G+4) | 269 | 24 | 3 | 296 |
| Unknown type | 136 | 5 | 1 | 142 |
| Commercial (shop) | 67 | 23 | 0 | 90 |
| Condominium | 60 | 19 | 0 | 79 |
| Commercial building (whole building) | 50 | 3 | 0 | 53 |
| Office | 40 | 9 | 0 | 49 |
| Single room | 0 | 47 | 0 | 47 |
| Studio | 15 | 29 | 0 | 44 |
| Land | 36 | 1 | 0 | 37 |
| Warehouse | 18 | 3 | 0 | 21 |
| Townhouse | 1 | 0 | 0 | 1 |
| **Total** | **1,013** | **229** | **5** | **1,247** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 328 | 60 | 1 | 389 |
| Yeka | 85 | 54 | 1 | 140 |
| Kirkos | 67 | 17 | 0 | 84 |
| Arada | 63 | 0 | 0 | 63 |
| Nifas Silk | 38 | 8 | 0 | 46 |
| Kolfe | 34 | 12 | 0 | 46 |
| Akaki | 16 | 4 | 0 | 20 |
| Lideta | 11 | 1 | 0 | 12 |
| Addis Ketema | 4 | 0 | 0 | 4 |
| Gulele | 1 | 1 | 0 | 2 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 16 | 0 | 0 | 16 |
| Gelan, Dukem (counted as Addis Ababa) | 6 | 1 | 0 | 7 |
| Place named, sub-city not in the place table | 234 | 52 | 0 | 286 |
| No place found in the text | 109 | 19 | 3 | 131 |

The 286 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

83 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 137 | 9 | 0 | 146 |
| Bole | Bole | 87 | 19 | 0 | 106 |
| Summit | — | 66 | 5 | 0 | 71 |
| Piassa | Arada | 56 | 0 | 0 | 56 |
| Megenagna | Yeka | 48 | 6 | 0 | 54 |
| CMC | Yeka | 28 | 22 | 1 | 51 |
| Kazanchis | Kirkos | 39 | 11 | 0 | 50 |
| Bole Bulbula | Bole | 28 | 8 | 0 | 36 |
| Sarbet / Old Airport | Nifas Silk | 27 | 6 | 0 | 33 |
| Summit 72 | — | 28 | 0 | 0 | 28 |
| Gerji | Yeka | 6 | 21 | 0 | 27 |
| Figa | — | 21 | 5 | 0 | 26 |
| Ayat 49 | Bole | 24 | 2 | 0 | 26 |
| Jacros | — | 13 | 10 | 0 | 23 |
| Haya Hulet (22) | Bole | 10 | 11 | 1 | 22 |
| Jemo | Kolfe | 15 | 6 | 0 | 21 |
| Mexico | Kirkos | 15 | 5 | 0 | 20 |
| Wello Sefer | Bole | 16 | 3 | 0 | 19 |
| Bulgaria | — | 17 | 2 | 0 | 19 |
| Bole Arabsa | Bole | 16 | 2 | 0 | 18 |

## How complete each field is (usable listings)

| Field | Sale (1,013) | Rent (229) | Both (5) | All (1,247) |
|---|---|---|---|---|
| Price (sale or rent) | 83% | 75% | 0% | 81% |
| Size (built-up or plot) | 78% | 25% | 40% | 68% |
| Bedrooms | 48% | 17% | 40% | 42% |
| Bathrooms | 17% | 4% | 20% | 15% |
| Named place | 89% | 92% | 40% | 89% |
| Sub-city | 66% | 69% | 40% | 67% |
| Map coordinates (from the place table) | 76% | 71% | 40% | 75% |
| Property type | 87% | 98% | 80% | 89% |
| Floor | 21% | 26% | 20% | 22% |
| Finishing | 16% | 10% | 0% | 15% |
| Payment terms | 18% | 6% | 0% | 16% |
| Building height (G+n) | 20% | 6% | 0% | 18% |
| Posting date | 39% | 68% | 40% | 44% |

**Price, size, bedrooms and place all known: 372 listings (30%)**: 364 sale, 8 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 39 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for 552 usable listings (11 in 2025, 541 in 2026). The
  other 695 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
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

**1 usable listing breaks a rule today**, and is left out of the model samples: 6726
(ApartmentForYouAyatRealEstate), stored as a shop of 20 m² for 250,000 birr. The advert sells
shops from 20 m² and 250,000 birr is the price per m². It is too rare a wording to justify
a rule of its own.

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

- 6726, above.
- Some wrong types and places seen while reading, not counted: 7368 is land but called a
  villa; 6939 is a G+3 building called an apartment; 7158 is in Gerji but placed in Bole.
- 6930 is stored as land (22 million birr, 150 m²), but its advert does not say whether it
  is land or a house.
- A villa with one stated size stores it as the plot, and the sale sample needs a built-up
  size for a villa, so 5 real houses from these channels are outside the sample (6920,
  6929, 6946, 6969, 6979).
- 153 usable listings have neither a price nor a size. They are counted as usable but
  cannot enter the model samples.
- The repair and duplicate-removal steps of `run_all.py` were not run on the 1 November
  listings.

## Fitness for a hedonic price model

**Sale sample: 466 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, and has no obvious outlier. By type: apartment 211,
villa 110, condominium 52, shop 36, land 25, office 14, warehouse 11, studio 7. Whole
buildings are not in it (no built-up size, see above). 12 look like reposts of the same
advert (same type, place, price and size).

| Variable | Known in the sale sample (466) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition) | core variables |
| Map coordinates | 85% | usable (rough, one point per place) |
| Sub-city | 73% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 56% (homes only: 62% of 380) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 33% | too incomplete |
| Bathrooms | 24% (homes: 28%) | too incomplete |
| Posting date | 33% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 17% | too incomplete |
| Finishing | 17% | too incomplete |
| Payment terms | 19% | too incomplete |

Location is thin at the neighbourhood level. The 466 listings fall in 61 places, but only
24 places have 5 or more listings and 15 have 10 or more. Only 23 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 35 listings** with rent, size, place and type (condominium 16, apartment 11,
villa 3, shop 3, others 2), so a rent model is not possible. Without requiring size there
are 168 (apartment 52, single room 45, studio 28, condominium 16, villa 14, others 13),
mostly flats, rooms and studios. That is enough to describe rents, not to model them.
`rental_listings` (rebuilt in task S13) has one row for every rent or mixed listing with a
rent: 176 rows, the 172 usable rentals with a rent plus 4 whose class keeps them out of the
usable listings (2046, 7249, 7251, 7303).

## What would improve the data most

1. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
2. Fetch the real posting dates from Telegram for the 695 undated usable listings (the
   message ids are stored), so the model can include time.
3. Give a sub-city to the places that lack one in `src/locations.py` (286 listings).
4. Check how common the remaining wrong types and places are ("Known mistakes that remain").
