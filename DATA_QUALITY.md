# Ollaa-Telegram: data quality report

State of the `ollaa` database on 27 October 2026. Every number below comes from
`database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9). Re-processing every stored
listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 749 values that earlier hand repairs set are kept on purpose and win over the
parser; 301 of the usable listings hold at least one of them.

## Summary

- **779 usable listings** out of 4,276 stored listings (5,091 raw Telegram messages from
  34 channels and groups): 493 for sale, 233 for rent, 53 for both.
- **2,860 listings (67%) are photo-only posts** (`MEDIA_PENDING`) whose images have not
  been read yet. They are the largest untapped part of the data.
- **266 sale listings are ready for a hedonic model** (price, size, named place, known
  type, priced in birr, no obvious outlier). Only **23 rent listings** are, so a rent
  model is not possible yet.
- Bedrooms are known for under half of the model sample. Bathrooms, floor, finishing,
  payment terms, building height and posting date are known for under a third, too few
  to use as model variables.
- **34 usable listings have obviously impossible values** and are left out of the model
  samples.

## Definitions

- **Usable listing**: a post offering a property for sale, rent or both, whose text was
  read. Excluded: photo-only posts (`MEDIA_PENDING`), service adverts, inquiries
  ("looking for…"), junk, and property posts whose sale/rent intent could not be told.
- **Prices** are asking prices taken from adverts, not transaction prices, in birr.
  Sizes are in m².
- **Named place**: one of the places in `src/locations.py`. **Sub-city** comes from the
  same table.

## From stored listings to usable listings

| Step | Listings |
|---|---|
| Stored listings | 4,276 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −2,860 |
| Service adverts, inquiries ("looking for"), junk | −534 |
| Property post, but neither sale nor rent could be told | −103 |
| **Usable listings** | **779** |

The 815 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 131 | 46 | 22 | 199 |
| Villa | 148 | 24 | 5 | 177 |
| Commercial building | 42 | 36 | 10 | 88 |
| Unknown type | 49 | 10 | 2 | 61 |
| Single room | 1 | 54 | 1 | 56 |
| Condominium | 38 | 12 | 1 | 51 |
| Commercial (shop) | 23 | 14 | 3 | 40 |
| Office | 25 | 6 | 1 | 32 |
| Studio | 6 | 24 | 0 | 30 |
| Warehouse | 11 | 7 | 8 | 26 |
| Land | 18 | 0 | 0 | 18 |
| Townhouse | 1 | 0 | 0 | 1 |
| **Total** | **493** | **233** | **53** | **779** |

## Where the listings are

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Bole | 179 | 65 | 22 | 266 |
| Yeka | 32 | 45 | 10 | 87 |
| Kirkos | 24 | 24 | 6 | 54 |
| Arada | 29 | 7 | 0 | 36 |
| Nifas Silk | 15 | 11 | 1 | 27 |
| Kolfe | 12 | 10 | 0 | 22 |
| Akaki | 7 | 4 | 1 | 12 |
| Lideta | 8 | 2 | 0 | 10 |
| Gulele | 0 | 1 | 1 | 2 |
| Addis Ketema | 1 | 1 | 0 | 2 |
| Lemi Kura | 1 | 0 | 0 | 1 |
| Sheger City (outside Addis Ababa) | 14 | 0 | 0 | 14 |
| Gelan, Dukem (counted as Addis Ababa) | 3 | 1 | 0 | 4 |
| Place named, sub-city not in the place table | 121 | 48 | 8 | 177 |
| No place found in the text | 47 | 14 | 4 | 65 |

The 177 listings without a sub-city name a real place (Summit, Figa, Jacros, Bulgaria and
others) that `src/locations.py` does not yet assign to a sub-city.

76 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Bole | 92 | 8 | 0 | 100 |
| Bole | Bole | 33 | 27 | 12 | 72 |
| Summit | — | 40 | 12 | 1 | 53 |
| Kazanchis | Kirkos | 17 | 15 | 1 | 33 |
| CMC | Yeka | 16 | 13 | 4 | 33 |
| Piassa | Arada | 27 | 6 | 0 | 33 |
| Megenagna | Yeka | 13 | 8 | 6 | 27 |
| Figa | — | 16 | 6 | 0 | 22 |
| Gerji | Yeka | 1 | 20 | 0 | 21 |
| Bole Bulbula | Bole | 14 | 6 | 1 | 21 |
| Sarbet / Old Airport | Nifas Silk | 11 | 8 | 1 | 20 |
| Bole Arabsa | Bole | 14 | 2 | 0 | 16 |
| Ayat 49 | Bole | 12 | 2 | 2 | 16 |
| Haya Hulet (22) | Bole | 0 | 9 | 5 | 14 |
| Mexico | Kirkos | 6 | 7 | 1 | 14 |
| Jacros | — | 9 | 4 | 0 | 13 |
| Summit 72 | — | 12 | 0 | 0 | 12 |
| Wello Sefer | Bole | 9 | 2 | 1 | 12 |
| Bulgaria | — | 6 | 1 | 4 | 11 |
| Jemo | Kolfe | 3 | 7 | 0 | 10 |

## How complete each field is (usable listings)

| Field | Sale (493) | Rent (233) | Both (53) | All (779) |
|---|---|---|---|---|
| Price (sale or rent) | 71% | 71% | 43% | 69% |
| Size (built-up or plot) | 77% | 41% | 79% | 66% |
| Bedrooms | 42% | 28% | 68% | 40% |
| Bathrooms | 15% | 17% | 64% | 19% |
| Named place | 90% | 94% | 92% | 92% |
| Sub-city | 66% | 73% | 77% | 69% |
| Map coordinates (from the place table) | 78% | 79% | 75% | 79% |
| Property type | 90% | 96% | 96% | 92% |
| Floor | 23% | 30% | 30% | 26% |
| Finishing | 12% | 13% | 57% | 15% |
| Payment terms | 13% | 15% | 23% | 15% |
| Building height (G+n) | 26% | 23% | 21% | 25% |
| Posting date | 22% | 42% | 32% | 28% |

**Price, size, bedrooms and place all known: 180 listings (23%)**: 137 sale, 26 rent,
17 both.

Known problems in these fields:

- **Rent and sale prices mixed up**: 70 rent listings carry a sale price (50 of them have
  no rent). Some are sales filed as rentals, others store the monthly rent in the
  sale-price field. They are left out of both model samples.
- **US dollar prices**: 29 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for only 221 usable listings (10 in 2025, 211 in 2026). The
  other 558 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
  an upper bound, not the posting date.
- **Coordinates** are one point per place (neighbourhood centre), and some are rough. They
  suit distance-to-centre variables, not exact positions.

## Photo-only posts (`MEDIA_PENDING`)

2,860 listings (67% of all stored listings) are photos or files without readable text.
850 of them get a place from their forum topic; everything else about them is unknown.
3,333 images wait in `media_queue`, none read yet (`extract_images.py`, Gemini). Reading
them is the largest possible gain in sample size.

## Obvious outliers

A value is flagged when it cannot be right for Addis Ababa in 2025–2026. 34 usable
listings break at least one rule. They stay in the database but are left out of the
model samples.

| Rule | Listings |
|---|---|
| Sale price under 500,000 birr (12) | 1021, 1040, 1042, 1323, 1324, 1340, 1341, 2127, 2307, 2442, 2618, 2872 |
| Under 20,000 birr per m², not already above (3) | 1271 (3,333), 1726 (7,857), 5328 (17,442) |
| Over 1,000,000 birr per m² (4) | 1276 (1.60 M), 2098 (1.82 M), 2857 (1.43 M), 2858 (1.52 M) |
| Rent outside 1,000–2,000,000 birr a month (2) | 1991 (29,999,000), 5651 (5,500,000: a sale advert misread as a rental) |
| Flat, studio or room size impossible (5) | 2100 (930 m² apartment), 4174 (633 m²), 2827 (572 m²), 2096 and 5938 (200 m² single rooms) |
| Flat with more than 6 bedrooms (8) | 1256, 1733, 1735, 1758, 1984, 2483, 5587, 6286 |

Price per m² uses built-up size (plot size for land). The adverts behind 20 of these were
read by hand. Every one is a parser mistake, not a real price:

- a rent or a rental income read as the sale price (1021, 1040, 1042, 1271, 2307, 2618);
- a price per m² read as the total (2127, 2442);
- a whole building's price paired with one unit's size or its footprint (1276, 2098,
  2857), or a plot size read as a flat's size (2096, 2100, 4174);
- share offers, not property at all (1323, 1340);
- a remaining balance or the cash part read as the price (1726, 5328), and "6,400 000"
  read as 6,400 (2872);
- a 10-bedroom G+3 house filed as an apartment (1733).

## Fitness for a hedonic price model

**Sale sample: 266 listings.** Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, and has no obvious outlier. By type: villa 94, apartment
71, condominium 34, commercial building 22, shop 12, land 12, office 10, warehouse 9,
studio 2. Only 3 look like reposts of the same advert (same type, place, price and size).

| Variable | Known in the sale sample (266) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition) | core variables |
| Map coordinates | 85% | usable (rough, one point per place) |
| Sub-city | 73% | usable once the place table assigns the missing sub-cities |
| Bedrooms | 45% (homes only: 47% of 201) | borderline: dropping listings without it halves the sample |
| Building height (G+n) | 30% | too incomplete |
| Floor | 28% | too incomplete |
| Posting date | 23% | too incomplete: no time trend can be estimated |
| Bathrooms | 13% (homes: 10%) | too incomplete |
| Payment terms | 11% | too incomplete |
| Finishing | 9% | too incomplete |

Location is thin at the neighbourhood level. The 266 listings fall in 46 places, but only
19 places have 5 or more listings and 6 have 10 or more. Only 9 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 23 listings** with rent, size, place and type, so a rent model is not
possible. Without requiring size there are 111 (single room 52, studio 20, apartment 16,
shop 10, others 13), mostly rooms and studios. That is enough to describe rents, not to
model them.

## What would improve the data most

1. Read the 3,333 waiting images (`MEDIA_PENDING`, 67% of listings).
2. Fetch the real posting dates from Telegram for the 558 undated usable listings (the
   message ids are stored), so the model can include time.
3. Fix in the parser the rent/sale price mix-up (70 listings) and the causes of the
   outliers above; then re-process and re-run `database/data_quality.py`.
4. Give a sub-city to the places that lack one in `src/locations.py` (177 listings).
