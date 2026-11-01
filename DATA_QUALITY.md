# Ollaa-Telegram: data quality report

State of the `ollaa` database on 1 November 2026, after the first scrape with the new
login (task S18). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9 and S12). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 423 values that earlier hand repairs set are kept on purpose and win over the
parser; 247 of the usable listings hold at least one of them.

## Summary

- **1,282 usable listings** out of 5,300 stored listings (6,115 raw Telegram messages from
  34 channels and groups): 1,036 for sale, 241 for rent, 5 for both. The scrape of 1
  November added 336 of them.
- **3,401 listings (64%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **469 sale listings are ready for a hedonic model** (price, size, named place, known
  type, priced in birr, no obvious outlier), **but 16 of them have the wrong type** (see
  "Known mistakes"). Only **35 rent listings** are, so a rent model is not possible yet.
- Bedrooms are known for 56% of the model sample (62% of its homes). Floor, bathrooms,
  posting date, building height, finishing and payment terms are known for about a third
  or less, too few to use as model variables.
- **5 usable listings have an obviously impossible value**, all from the new scrape (see
  "Obvious outliers"). They are parser mistakes and one car part, and are left out of the
  model samples.

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
| Service or share adverts, inquiries ("looking for"), junk | −560 |
| Property post, but neither sale nor rent could be told | −57 |
| **Usable listings** | **1,282** |

The 815 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 318 | 66 | 1 | 385 |
| Villa (houses, G+0 to G+4) | 284 | 24 | 3 | 311 |
| Unknown type | 128 | 17 | 1 | 146 |
| Commercial (shop) | 67 | 23 | 0 | 90 |
| Condominium | 55 | 19 | 0 | 74 |
| Commercial building (whole building) | 50 | 3 | 0 | 53 |
| Office | 40 | 9 | 0 | 49 |
| Warehouse (26 of these are wrong, see "Known mistakes") | 44 | 3 | 0 | 47 |
| Single room | 0 | 47 | 0 | 47 |
| Studio | 15 | 29 | 0 | 44 |
| Land | 34 | 1 | 0 | 35 |
| Townhouse | 1 | 0 | 0 | 1 |
| **Total** | **1,036** | **241** | **5** | **1,282** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 331 | 62 | 1 | 394 |
| Yeka | 80 | 54 | 1 | 135 |
| Kirkos | 67 | 18 | 0 | 85 |
| Arada | 63 | 0 | 0 | 63 |
| Nifas Silk | 38 | 8 | 0 | 46 |
| Kolfe | 34 | 12 | 0 | 46 |
| Akaki | 16 | 4 | 0 | 20 |
| Lideta | 10 | 1 | 0 | 11 |
| Addis Ketema | 4 | 0 | 0 | 4 |
| Gulele | 1 | 1 | 0 | 2 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 16 | 0 | 0 | 16 |
| Gelan, Dukem (counted as Addis Ababa) | 6 | 1 | 0 | 7 |
| Place named, sub-city not in the place table | 234 | 52 | 0 | 286 |
| No place found in the text | 135 | 28 | 3 | 166 |

The 286 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

83 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 137 | 9 | 0 | 146 |
| Bole | Bole | 88 | 19 | 0 | 107 |
| Summit | — | 66 | 5 | 0 | 71 |
| Piassa | Arada | 56 | 0 | 0 | 56 |
| CMC | Yeka | 28 | 22 | 1 | 51 |
| Kazanchis | Kirkos | 39 | 11 | 0 | 50 |
| Megenagna | Yeka | 43 | 6 | 0 | 49 |
| Bole Bulbula | Bole | 29 | 9 | 0 | 38 |
| Sarbet / Old Airport | Nifas Silk | 27 | 6 | 0 | 33 |
| Summit 72 | — | 28 | 0 | 0 | 28 |
| Gerji | Yeka | 6 | 21 | 0 | 27 |
| Ayat 49 | Bole | 24 | 2 | 0 | 26 |
| Figa | — | 20 | 5 | 0 | 25 |
| Jacros | — | 14 | 10 | 0 | 24 |
| Haya Hulet (22) | Bole | 10 | 11 | 1 | 22 |
| Mexico | Kirkos | 15 | 6 | 0 | 21 |
| Jemo | Kolfe | 15 | 6 | 0 | 21 |
| Wello Sefer | Bole | 16 | 3 | 0 | 19 |
| Bulgaria | — | 17 | 2 | 0 | 19 |
| Bole Arabsa | Bole | 17 | 2 | 0 | 19 |

## How complete each field is (usable listings)

| Field | Sale (1,036) | Rent (241) | Both (5) | All (1,282) |
|---|---|---|---|---|
| Price (sale or rent) | 80% | 71% | 0% | 78% |
| Size (built-up or plot) | 75% | 24% | 40% | 65% |
| Bedrooms | 46% | 17% | 40% | 40% |
| Bathrooms | 16% | 4% | 20% | 14% |
| Named place | 87% | 88% | 40% | 87% |
| Sub-city | 64% | 67% | 40% | 65% |
| Map coordinates (from the place table) | 74% | 69% | 40% | 73% |
| Property type | 88% | 93% | 80% | 89% |
| Floor | 21% | 25% | 20% | 21% |
| Finishing | 15% | 10% | 0% | 14% |
| Payment terms | 17% | 5% | 0% | 15% |
| Building height (G+n) | 20% | 6% | 0% | 17% |
| Posting date | 41% | 67% | 40% | 45% |

**Price, size, bedrooms and place all known: 366 listings (29%)**: 358 sale, 8 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 39 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for 583 usable listings (11 in 2025, 572 in 2026). The
  other 699 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
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

**5 usable listings break a rule today**, all from the scrape of 1 November; they are left
out of the model samples:

| Listing | Channel | Stored value | What the advert says |
|---|---|---|---|
| 6726 | ApartmentForYouAyatRealEstate | shop, 250,000 birr for 20 m² | a developer's shops from 20 m²; 250,000 birr is the price per m² |
| 6902 | ET_Creatives_Homes_And_Cars | 7,200 birr | a brake disc for a car, not a property |
| 6930 | houseapartmentcarreleator | "warehouse", 440,000 birr, 150 m² | a house: 18 million bank + 4 million cash; "440,000 birr" is the stated 2% commission |
| 6931 | houseapartmentcarreleator | "warehouse", 740,000 birr, 180 m² | a G+3 house: 25 million bank + 12 million cash; "740,000 birr" is the stated 2% commission |
| 7372 | smartdealers | warehouse, 450 million birr, 200 m² | the plot is 4,500 m²; 200 m² is one part of the property |

Before this scrape none did. On 27 October 34 did. Reading their adverts
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

## Known mistakes in the listings of 1 November

Reading the 336 new usable listings showed these parser mistakes. They are not fixed yet
(a parser change needs the owner's approval and an old-against-new comparison):

- **26 houses and plots are called warehouses.** Many posts of houseapartmentcarreleator
  and hugeAddisababamarket2025 (15 of the 40 read from each), which share the same adverts,
  end with a menu of links, one of them "land and warehouses" (መሬትና መጋዘን). The parser
  reads that menu as the property type. Of the 27 usable "warehouses" from these channels
  only one (6983) is really a warehouse. 16 of the wrong ones are in the sale sample, so its
  26 warehouses are really about 10.
- **5 "rent" listings are construction news** ("Gazebo Skyline current progress"): the
  word "current" contains "rent". They have no price, so they are not in the model samples.
- **72 new usable listings have neither a price nor a size**; 15 of them are only the
  company footer of realityaddisababa, stored as villas. They are counted as usable but
  cannot enter the model samples.
- **Some prices are missed**, for example "8,5 ሚሊየን" (a comma as the decimal point) and a
  bare "18,500,000" with no word for birr.
- **Bank-plus-cash prices in these two channels** can pick up the commission instead (see
  6930 and 6931 above).

## Fitness for a hedonic price model

**Sale sample: 469 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, and has no obvious outlier. By type: apartment 207,
villa 108, condominium 48, shop 36, warehouse 26 (16 of them wrongly typed, see "Known
mistakes"), land 23, office 14, studio 7. Whole buildings are not in it (no built-up size,
see above). 12 look like reposts of the same advert (same type, place, price and size).

| Variable | Known in the sale sample (469) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition) | core variables |
| Map coordinates | 85% | usable (rough, one point per place) |
| Sub-city | 73% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 56% (homes only: 62% of 370) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 32% | too incomplete |
| Bathrooms | 23% (homes: 28%) | too incomplete |
| Posting date | 34% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 17% | too incomplete |
| Finishing | 17% | too incomplete |
| Payment terms | 18% | too incomplete |

Location is thin at the neighbourhood level. The 469 listings fall in 61 places, but only
24 places have 5 or more listings and 14 have 10 or more. Only 23 place-and-type
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

1. Fix the parser mistakes above (26 wrong warehouses first), so the sale sample's types
   can be trusted.
2. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
3. Fetch the real posting dates from Telegram for the 699 undated usable listings (the
   message ids are stored), so the model can include time.
4. Give a sub-city to the places that lack one in `src/locations.py` (286 listings).
