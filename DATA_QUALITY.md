# Ollaa-Telegram: data quality report

State of the `ollaa` database on 28 October 2026, after tasks S12–S14. Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9 and S12). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 423 values that earlier hand repairs set are kept on purpose and win over the
parser; 247 of the usable listings hold at least one of them.

## Summary

- **946 usable listings** out of 4,276 stored listings (5,091 raw Telegram messages from
  34 channels and groups): 765 for sale, 178 for rent, 3 for both.
- **2,860 listings (67%) are photo-only posts** (`MEDIA_PENDING`) whose images have not
  been read yet. They are the largest untapped part of the data.
- **394 sale listings are ready for a hedonic model** (price, size, named place, known
  type, priced in birr, no obvious outlier). Only **23 rent listings** are, so a rent
  model is not possible yet.
- Bedrooms are known for 57% of the model sample (62% of its homes). Floor, bathrooms,
  posting date, building height, finishing and payment terms are known for a third or
  less, too few to use as model variables.
- **No usable listing has an obviously impossible value.** The 34 found on 27 October
  were all parser mistakes, fixed in task S12; the last one left, a flat called a single
  room, was fixed in S14 (see "Obvious outliers").

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
| Stored listings | 4,276 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −2,860 |
| Service or share adverts, inquiries ("looking for"), junk | −420 |
| Property post, but neither sale nor rent could be told | −50 |
| **Usable listings** | **946** |

The 815 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 260 | 47 | 1 | 308 |
| Villa (houses, G+0 to G+4) | 195 | 19 | 1 | 215 |
| Unknown type | 102 | 9 | 1 | 112 |
| Commercial (shop) | 49 | 22 | 0 | 71 |
| Condominium | 45 | 11 | 0 | 56 |
| Office | 30 | 7 | 0 | 37 |
| Commercial building (whole building) | 33 | 3 | 0 | 36 |
| Single room | 0 | 35 | 0 | 35 |
| Studio | 11 | 22 | 0 | 33 |
| Land | 29 | 0 | 0 | 29 |
| Warehouse | 10 | 3 | 0 | 13 |
| Townhouse | 1 | 0 | 0 | 1 |
| **Total** | **765** | **178** | **3** | **946** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 247 | 48 | 1 | 296 |
| Yeka | 55 | 44 | 1 | 100 |
| Kirkos | 56 | 14 | 0 | 70 |
| Arada | 55 | 0 | 0 | 55 |
| Nifas Silk | 26 | 8 | 0 | 34 |
| Kolfe | 25 | 3 | 0 | 28 |
| Akaki | 11 | 3 | 0 | 14 |
| Lideta | 9 | 1 | 0 | 10 |
| Addis Ketema | 2 | 0 | 0 | 2 |
| Gulele | 1 | 1 | 0 | 2 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 14 | 0 | 0 | 14 |
| Gelan, Dukem (counted as Addis Ababa) | 3 | 1 | 0 | 4 |
| Place named, sub-city not in the place table | 184 | 42 | 0 | 226 |
| No place found in the text | 76 | 13 | 1 | 90 |

The 226 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria,
German Square and others) that `src/locations.py` does not yet assign to a sub-city.

81 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 99 | 8 | 0 | 107 |
| Bole | Bole | 62 | 16 | 0 | 78 |
| Summit | — | 50 | 5 | 0 | 55 |
| Piassa | Arada | 49 | 0 | 0 | 49 |
| Kazanchis | Kirkos | 37 | 7 | 0 | 44 |
| CMC | Yeka | 20 | 14 | 1 | 35 |
| Megenagna | Yeka | 29 | 5 | 0 | 34 |
| Bole Bulbula | Bole | 26 | 4 | 0 | 30 |
| Sarbet / Old Airport | Nifas Silk | 19 | 6 | 0 | 25 |
| Gerji | Yeka | 4 | 20 | 0 | 24 |
| Figa | — | 18 | 5 | 0 | 23 |
| Summit 72 | — | 22 | 0 | 0 | 22 |
| Ayat 49 | Bole | 19 | 2 | 0 | 21 |
| Jacros | — | 12 | 8 | 0 | 20 |
| Mexico | Kirkos | 11 | 6 | 0 | 17 |
| Bole Arabsa | Bole | 15 | 2 | 0 | 17 |
| Haya Hulet (22) | Bole | 5 | 8 | 1 | 14 |
| Wello Sefer | Bole | 12 | 1 | 0 | 13 |
| Bulgaria | — | 12 | 0 | 0 | 12 |
| German Square | — | 12 | 0 | 0 | 12 |

## How complete each field is (usable listings)

| Field | Sale (765) | Rent (178) | Both (3) | All (946) |
|---|---|---|---|---|
| Price (sale or rent) | 83% | 72% | 0% | 81% |
| Size (built-up or plot) | 78% | 24% | 67% | 68% |
| Bedrooms | 49% | 14% | 67% | 43% |
| Bathrooms | 18% | 5% | 33% | 16% |
| Named place | 90% | 93% | 67% | 90% |
| Sub-city | 66% | 69% | 67% | 67% |
| Map coordinates (from the place table) | 76% | 73% | 67% | 76% |
| Property type | 87% | 95% | 67% | 88% |
| Floor | 24% | 25% | 33% | 24% |
| Finishing | 17% | 10% | 0% | 15% |
| Payment terms | 17% | 5% | 0% | 15% |
| Building height (G+n) | 20% | 8% | 0% | 18% |
| Posting date | 19% | 55% | 0% | 26% |

**Price, size, bedrooms and place all known: 311 listings (33%)**: 310 sale, 1 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 29 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for only 247 usable listings (11 in 2025, 236 in 2026). The
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

2,860 listings (67% of all stored listings) are photos or files without readable text.
850 of them get a place from their forum topic; everything else about them is unknown.
3,333 images wait in `media_queue`, none read yet (`extract_images.py`, Gemini). Reading
them is the largest possible gain in sample size.

## Obvious outliers

A value is flagged when it cannot be right for Addis Ababa in 2025–2026: a sale price under
500,000 birr; under 20,000 or over 1,000,000 birr per m² (built-up; plot for land); a rent
outside 1,000–2,000,000 birr a month; a flat, studio or room under 15 m² or over 500 m²
(studios and rooms over 100 m²); a flat with more than 6 bedrooms.

**No usable listing breaks a rule today.** On 27 October 34 did. Reading their adverts
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

## Fitness for a hedonic price model

**Sale sample: 394 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, and has no obvious outlier. By type: apartment 175,
villa 104, condominium 41, shop 27, land 18, office 14, warehouse 8, studio 7. Whole
buildings are not in it (no built-up size, see above). 7 look like reposts of the same
advert (same type, place, price and size).

| Variable | Known in the sale sample (394) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition) | core variables |
| Map coordinates | 86% | usable (rough, one point per place) |
| Sub-city | 74% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 57% (homes only: 62% of 327) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 35% | too incomplete |
| Bathrooms | 24% (homes: 28%) | too incomplete |
| Posting date | 21% | too incomplete: no time trend can be estimated |
| Building height (G+n) | 18% | too incomplete |
| Finishing | 18% | too incomplete |
| Payment terms | 17% | too incomplete |

Location is thin at the neighbourhood level. The 394 listings fall in 56 places, but only
23 places have 5 or more listings and 12 have 10 or more. Only 20 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 23 listings** with rent, size, place and type (condominium 10, apartment 6,
villa 3, others 4), so a rent model is not possible. Without requiring size there are 126
(apartment 37, single room 34, studio 21, villa 12, condominium 10, others 12), mostly
flats, rooms and studios. That is enough to describe rents, not to model them. `rental_listings` (rebuilt in task S13) has one row for every rent or
mixed listing with a rent: 129 rows, the 128 usable rentals with a rent plus listing 2046,
whose kept "advert" class keeps it out of the usable listings.

## What would improve the data most

1. Read the 3,333 waiting images (`MEDIA_PENDING`, 67% of listings).
2. Fetch the real posting dates from Telegram for the 699 undated usable listings (the
   message ids are stored), so the model can include time.
3. Give a sub-city to the places that lack one in `src/locations.py` (226 listings).
