# Ollaa-Telegram: data quality report

State of the `ollaa` database on 19 November 2026, after the first scrape with the new
login (S18), parser fixes (S19), duplicate removal and an accuracy check (S20), and the return of
listings the old duplicate steps had removed (S22, S24), the clearing of copied built-up sizes (S25), parser fixes
from the accuracy check (S26), the owner's corrections after it (S27 to S29), and the scrapes of 3 November (S30), 15 November (S32) and 19 November (S43). Every number below
comes from `database/data_quality.py` (read-only), which can be run again at any time:

    venv\Scripts\python.exe database\data_quality.py

The listings were produced by the fixed parser (tasks S5–S9, S12, S19 and S26). Re-processing every
stored listing with today's code changes nothing (`src/reprocess.py`: "Listings that would
change: 0"). 315 values that earlier hand repairs set are kept on purpose and win over the
parser; 157 of the usable listings hold at least one of them (5 were retired in task S40 when the parser came to agree).

## Summary

- **1,819 usable listings** out of 6,500 stored listings (6,894 raw Telegram messages from
  34 channels and groups): 1,498 for sale, 316 for rent, 5 for both.
- **3,839 listings (59%) are photo-only posts** (`MEDIA_PENDING`). The photo pilot
  (`MEDIA_PILOT.md`) found they rarely carry a price or a size.
- **544 sale listings are ready for a hedonic model** (price, size, named place, known type, priced
  in birr, no obvious outlier). Some may be a property re-advertised (see "Duplicates"); read it as
  about 529 to 544 different properties. Only **36 rent
  listings** are ready, so a rent model is not possible yet.
- **Accuracy improved, by Claude's reading: 20 of 60 random listings (33%) had a value the advert
  contradicts before the parser fixes of task S26, 6 of a new random 60 (10%, likely 5% to 20%) after
  them, and 7 of a third random 60 (12%, likely 6% to 22%) on 3 November.** The third round confirms the
  second; 10% and 12% are the same within the margin of error. The owner has not yet checked any of the
  three sets (see "Accuracy check").
- **Only 17 houses are in the sale sample; 293 more have a plot size only.** A model using plot size
  as its own variable could use them; the sample as defined today needs a built-up size for a house.
- Bedrooms are known for 74% of the model sample (88% of its homes). Floor, bathrooms, posting date,
  building height, finishing and payment terms are known for 45% or less, too few to use as model
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
| Stored listings | 6,500 |
| Photo or file only, text not read yet (`MEDIA_PENDING`) | −3,839 |
| Service or share adverts, inquiries ("looking for"), junk | −775 |
| Property post, but neither sale nor rent could be told | −67 |
| **Usable listings** | **1,819** |

The 394 raw messages without a listing are deleted duplicates and junk; the database keeps
them out permanently (`processing_exclusions`).

## Sale and rent, property types

| Type | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Apartment | 509 | 102 | 2 | 613 |
| Villa (houses, G+0 to G+4) | 439 | 30 | 1 | 470 |
| Unknown type | 163 | 5 | 1 | 169 |
| Condominium | 130 | 21 | 0 | 151 |
| Land | 87 | 6 | 0 | 93 |
| Single room | 0 | 75 | 0 | 75 |
| Commercial building (whole building) | 65 | 6 | 0 | 71 |
| Commercial (shop) | 47 | 22 | 0 | 69 |
| Studio | 19 | 38 | 1 | 58 |
| Office | 21 | 8 | 0 | 29 |
| Warehouse | 14 | 3 | 0 | 17 |
| Townhouse | 4 | 0 | 0 | 4 |
| **Total** | **1,498** | **316** | **5** | **1,819** |

## Where the listings are

Sub-cities follow the owner's rules (16 November 2026, shared with the ollaa-web project; see `src/locations.py`): every place whose
name starts with Bole is in Bole except Bole Arabsa, and Gerji is Bole; Ayat, CMC, Summit, Figa, Wesen, Yetebaberut, Feyel Bet,
Safari and Gurd Shola are Lemi Kura; Sarbet and Bulgaria are Kirkos, Awere is Yeka. Lemi Kura is therefore the largest sub-city
here, and Bole much smaller than before (549 listings before the rules, 302 now).

| Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|
| Lemi Kura | 510 | 74 | 1 | 585 |
| Bole | 204 | 97 | 1 | 302 |
| Kirkos | 150 | 30 | 1 | 181 |
| Yeka | 97 | 14 | 0 | 111 |
| Kolfe | 76 | 13 | 0 | 89 |
| Arada | 71 | 0 | 0 | 71 |
| Akaki | 27 | 4 | 0 | 31 |
| Sheger City (outside Addis Ababa) | 28 | 0 | 0 | 28 |
| Nifas Silk | 18 | 3 | 0 | 21 |
| Lideta | 14 | 1 | 0 | 15 |
| Gelan, Dukem (counted as Addis Ababa) | 9 | 1 | 0 | 10 |
| Addis Ketema | 3 | 1 | 0 | 4 |
| Gulele | 1 | 2 | 0 | 3 |
| No place found in the text | 174 | 31 | 2 | 207 |
| Place named, sub-city not in the place table | 116 | 45 | 0 | 161 |

The 161 listings without a sub-city name a real place (Jacros, German Square, Addisu Gebeya, Addis Sefer, Gofa and others)
that `src/locations.py` does not yet assign to a sub-city.

89 different places are named. The 20 most frequent:

| Place | Sub-city | Sale | Rent | Both | Total |
|---|---|---|---|---|---|
| Ayat | Lemi Kura | 208 | 15 | 1 | 224 |
| Bole | Bole | 99 | 35 | 0 | 134 |
| Summit | Lemi Kura | 89 | 6 | 0 | 95 |
| Megenagna | Yeka | 73 | 9 | 0 | 82 |
| CMC | Lemi Kura | 35 | 35 | 0 | 70 |
| Piassa | Arada | 61 | 0 | 0 | 61 |
| Kazanchis | Kirkos | 47 | 12 | 1 | 60 |
| Figa | Lemi Kura | 54 | 5 | 0 | 59 |
| Bole Bulbula | Bole | 41 | 10 | 0 | 51 |
| Jemo | Kolfe | 44 | 5 | 0 | 49 |
| Sarbet / Old Airport | Kirkos | 38 | 10 | 0 | 48 |
| Ayat 49 | Lemi Kura | 38 | 3 | 0 | 41 |
| Mexico | Kirkos | 28 | 5 | 0 | 33 |
| Gerji | Bole | 7 | 26 | 0 | 33 |
| Summit 72 | Lemi Kura | 32 | 0 | 0 | 32 |
| Haya Hulet (22) | Bole | 14 | 15 | 1 | 30 |
| Jacros | — | 17 | 13 | 0 | 30 |
| Kality | Akaki | 23 | 4 | 0 | 27 |
| Bole Arabsa | Lemi Kura | 23 | 3 | 0 | 26 |
| Wello Sefer | Bole | 22 | 2 | 0 | 24 |

## How complete each field is (usable listings)

| Field | Sale (1,498) | Rent (316) | Both (5) | All (1,819) |
|---|---|---|---|---|
| Price (sale or rent) | 85% | 75% | 0% | 83% |
| Size (built-up or plot) | 80% | 20% | 40% | 69% |
| Bedrooms | 52% | 48% | 60% | 51% |
| Bathrooms | 17% | 4% | 20% | 15% |
| Named place | 88% | 90% | 60% | 89% |
| Sub-city | 81% | 76% | 60% | 80% |
| Map coordinates (from the place table) | 75% | 73% | 60% | 75% |
| Property type | 89% | 98% | 80% | 91% |
| Floor | 20% | 25% | 20% | 21% |
| Finishing | 16% | 12% | 0% | 15% |
| Payment terms | 16% | 5% | 0% | 14% |
| Building height (G+n) | 20% | 5% | 0% | 17% |
| Posting date | 49% | 72% | 20% | 53% |

**Price, size, bedrooms and place all known: 639 listings (35%)**: 604 sale, 35 rent.

Things to know about these fields:

- **Rent and sale prices are no longer mixed up.** Before S12, 70 "rent" listings carried
  a sale price; most were sale adverts that mention their rental income, the rest stored
  the monthly rent in the sale-price field. Now no rent listing has a sale price and no
  sale listing has a rent.
- **US dollar prices**: 71 usable listings quote US dollars, often per m² or per month.
  They are not converted and are left out of the model samples.
- **Posting dates**: known for 961 usable listings (11 in 2025, 950 in 2026). The
  other 858 only have the date they were collected (28 Dec 2025 – 15 Apr 2026), which is
  an upper bound, not the posting date.
- **Coordinates** are one point per place (neighbourhood centre), and some are rough. They
  suit distance-to-centre variables, not exact positions.
- **Whole buildings** (`COMMERCIAL_BUILDING`) are stored with the land they stand on as
  their plot and no built-up size, because adverts give the land or footprint, not the
  floor area. Their price per built-up m² is therefore unknown.
- **Posts listing several properties** (a broker's list of buildings, a developer's unit
  options) are stored once, with the first property's price and size.

## Photo-only posts (`MEDIA_PENDING`)

3,839 listings (59% of all stored listings) are photos or files without readable text.
965 of them get a place from their forum topic; everything else about them is unknown.
5,052 images wait in `media_queue`, none read yet. The photo pilot (`MEDIA_PILOT.md`) found
that of 45 photos, 3 carried the words of an offer and none had a price and a size, so
reading them is not advised.

## Obvious outliers

A value is flagged when it cannot be right for Addis Ababa in 2025–2026: a sale price under
500,000 birr; under 20,000 or over 1,000,000 birr per m² (built-up; plot for land); a rent
outside 1,000–2,000,000 birr a month; a flat, studio or room under 15 m² or over 500 m²
(studios and rooms over 100 m²); a flat with more than 6 bedrooms.

**8 usable listings break a rule today**, and are left out of the model samples:

| Listing | Stored | What the advert says |
|---|---|---|
| 6726 | 250,000 birr for 20 m² | shops from 20 m²; 250,000 birr is the price per m² |
| 2022 | flat, 20,000 birr for 161 m² | a price written "32,20,000" |
| 2868 | house, 12,500 birr | a price written "12,500..ሚሊየን" |
| 3597 | building for rent, 500 million birr a month | for sale at 500 million, "also available for rent" |
| 2600 | building for rent, 2.5 million birr a month | a G+6 building for rent: over the rule's limit, possibly right |
| 8360 | flat with 14 bedrooms, 300 m², 95 million birr | a whole G+5 apartment building at Tulu Dimtu (scrape of 19 Nov), stored as one flat |
| 8366 | flat of 404 m², 520 million birr (1.29 million per m²) | a whole B+G+8 apartment building at Meskel Flower with 15 flats (scrape of 19 Nov), stored as one flat |
| 8382 | flat of 560 m², priced in US dollars | a G+1 duplex at Megenagna, 54,999,000 **birr**; the advert's "$2,000" rental income made the parser call the price dollars (scrape of 19 Nov) |

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

**Task S27 (the owner's decision).** The parser fixes of S26 corrected types, and `dedup_strict.py` then
reported 9 more repeats (6 in the sale sample), for example 1103 and 1309 (Sarbet, 81 m², 5.7 million). Each was
read next to the listing kept, and all 9 were removed (backup `backups/ollaa_2026-11-01_before_S27.dump`): 5627, 1103,
1315, 1354, 1214, 2389, 1854, 2439, 269. Stored listings went from 5,774 to 5,765.

**Task S28 (the owner's decision).** Correcting the types in S27 showed one more repeat: 1744 repeats 1745 (Bulgaria,
68 m², 7,820,000 birr). It was removed (backup `backups/ollaa_2026-11-02_before_S28.dump`). Stored listings went to 5,764.

**Standing rule (the owner's decision, 2 November 2026).** When two listings are clearly the same advert (same channel or same
agent, same property, place, price and size, only small wording differences), the newer copy is removed without asking and the one
with the most complete details stays. The owner is asked only when the price or size differs. Every removal is listed here:

| Removed | Kept | Date | Why |
|---|---|---|---|
| 2625 | 2628 | 2 Nov 2026 | one channel: Palm Real Estate, Bole Dembel, 73 m², 7,227,000 birr; 2625 adds a Christmas discount line |
| 7697 | 7730 | 3 Nov 2026 | one agent, two channels, code 2731, same words: Tulu Dimtu, 2 bedrooms, 76 m², 6,300,000 birr |
| 7731 | 6947 | 3 Nov 2026 | one agent, same words but a new code (812, was 802): Addis Sefer, 160 m², 10 million birr |
| 7716 | 6947 | 3 Nov 2026 | the same advert with code 812 in the agent's other channel |
| 7717 | 7732 | 3 Nov 2026 | one agent, two channels, code 811, same words: Haile Garment, G+3, 72 m², 24 million birr |
| 7725 | 7733 | 3 Nov 2026 | one agent, two channels, code 808, same words: Sheger City, 150 m², 9.5 million birr |
| 7726 | 7734 | 3 Nov 2026 | one agent, two channels, code 807, same words: Lebu, 250 m², 43 million birr |
| 7728 | 7736 | 3 Nov 2026 | one agent, two channels, code 806, same words: land at Ayat, 250 m², 14 million birr |
| 7714 | 7724 | 3 Nov 2026 | one channel, new code (813, was 809), one phrase less: Sheger City, 160 m², 10 million birr |
| 7790 | 7797 | 3 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 212, same words: Addisu Gebeya, 3 bedrooms, rent 70,000 birr |
| 7793 | 7799 | 3 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 211, same words: Addisu Gebeya, 2 bedrooms, rent 60,000 birr |
| 7696 | 3313 | 3 Nov 2026 | one channel, same words: a broker's list of services, no property |
| 7737 | 7008 | 3 Nov 2026 | one channel, same words: realityaddisababa's name and contacts, no property |
| 7967 | 7008 | 15 Nov 2026 | one channel, same words: realityaddisababa's name and contacts, no property |
| 7968 | 7008 | 15 Nov 2026 | the same, posted again |
| 7969 | 7008 | 15 Nov 2026 | the same, posted again |
| 7966 | 7012 | 15 Nov 2026 | one channel, same words: the name of realityaddisababa's Palace View project and contacts, no details |
| 8119 | 7325 | 15 Nov 2026 | one channel (ETHIOhouseagents), same words: Summit, 3 bedrooms, 115 m², 5.7 million birr (was in the sale sample) |
| 7905 | 3313 | 15 Nov 2026 | one channel, same words: a broker's list of services, no property |
| 1896 | 7916 | 15 Nov 2026 | one channel, same words: "write to the admin" caption, no property (the copy with a posting date stays) |
| 7924 | 7956 | 15 Nov 2026 | one agent, two channels, code 829, same words: house at Shegole, 164 m², 16 million birr |
| 7926 | 7957 | 15 Nov 2026 | one agent, two channels, code 827, same words: house behind Garment, 90 m², 5 million birr |
| 7937 | 7961 | 15 Nov 2026 | one agent, code AP0104, same words: flats of 103, 138 and 175 m² (stored: 103 m², 9,785,000 birr) |
| 7928 | 7961 | 15 Nov 2026 | the same advert, posted again |
| 7940 | 7961 | 15 Nov 2026 | the same advert, posted again |
| 7958 | 7961 | 15 Nov 2026 | the same advert, posted again in the same channel |
| 7939 | 7960 | 15 Nov 2026 | one agent, two channels, code 823, same words: G+3 at Gelan, 72 m², 18 million birr |
| 7947 | 7962 | 15 Nov 2026 | one agent, two channels, code 817, same words: house at Sheger City, 200 m², 8 million birr |
| 7954 | 7963 | 15 Nov 2026 | one agent, two channels, code 0024, same words: Wingate condominium, 2 bedrooms, 71 m², 8 million birr (was in the sale sample) |
| 8036 | 8040 | 15 Nov 2026 | one channel (AddisBrokerageNetworking), same words: Addisu Gebeya, 2 bedrooms, 83 m², 12,499,000 birr (was in the sale sample) |
| 8057 | 8090 | 15 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 214, same words: Shola condominium, 2 bedrooms, rent 55,000 birr |
| 8071 | 8097 | 15 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 213, same words: CMC, 2 bedrooms, rent 50,000 birr |
| 7941 | 6931 | 15 Nov 2026 | one channel, new code (822, was 795), other wording: G+3 at Ayat, 180 m², 37 million birr (25 million bank and 12 million cash) |
| 8327 | 7008 | 19 Nov 2026 | one channel, same words: realityaddisababa's name and contacts, no property |
| 8329 | 7008 | 19 Nov 2026 | the same, posted again |
| 8403 | 8088 | 19 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 215, same words: Summit condominium, 2 bedrooms, 76 m², rent 50,000 birr (8403 posted 4 days later) |
| 8394 | 8405 | 19 Nov 2026 | one agent, Bet_afri and Betafrivip, code VBT 216, same words: Kazanchis, 1 bedroom, 11th floor, rent 50,000 birr (8394 posted 24 minutes later) |
| 8301 | 7686 | 19 Nov 2026 | one channel (Roya_King4102), same phone, same words but "cmc" left out: villa at Figa, 200 m², 22 million birr |
| 8317 | 8325 | 19 Nov 2026 | one agent (same phone and username), houseapartmentcarreleator and hugeAddisababamarket2025, code 834, the same words posted 16 seconds apart: Dembel (Gazebo roundabout), 152 m², 15.5 million birr (in the sale sample); the copies are identical, so the one `dedup_strict.py` ranks first stays |
| 8341 | 7077 | 19 Nov 2026 | different agents (livingethio, Apartments_for_rent_Addis_Ababa), one property: house at CMC, 250 m², 110 million birr; the parsed details are the same, the older post stays (8341 adds only "modern G+2") |

The removal of 2625 was named by the owner; its backup is `backups/ollaa_2026-11-02_2226_before_dedup.dump`. Stored listings went
to 5,763. The scrape of 3 November (task S30) added 163, to 5,926; each of the 16 repeats reported was then read side by side and the
12 above were removed with `dedup_strict.py --apply --same-source --only ...` (backup
`backups/ollaa_2026-11-03_2231_before_dedup.dump`). Stored listings went to 5,914; 11 of the 12 were usable, 1 was in the sale sample.
The scrape of 15 November (task S32) added 413, to 6,327. `dedup_strict.py` listed 27 repeats; each was read side by side.
The 20 above dated 15 November were removed with `dedup_strict.py --apply --same-source --only ...` (backup
`backups/ollaa_2026-11-15_2305_before_dedup.dump`). Stored listings went to 6,307; 15 of the 20 were usable, 3 were in the sale
sample. The other 7 were left: the 4 of task S30 below (7655, 7812, 7668, 7694) and the 3 of task S32 below.

**The owner's decisions on the repeats left over (task S33, 16 November 2026).** The owner widened the standing rule: the same
property posted by different agents (same place, size, price and floor) is one property, and the most complete copy stays; different
floors are different units, so both stay; unclear cases keep both. Each of the 7 pairs below was read again side by side. 3 were
removed with `dedup_strict.py --apply --only 7655 7812 7668` (backup `backups/ollaa_2026-11-16_1937_before_dedup.dump`); stored
listings went from 6,307 to 6,304, usable from 1,755 to 1,752 and the sale sample from 525 to 523. In each removed pair the two copies
held the same details, so the copy kept is the one `dedup_strict.py` ranks first.

| Pair | Decision | Why |
|---|---|---|
| 7655 and 6907 | **7655 removed**, 6907 kept | different agents, one property: land at Ayat 49, 90 m², 8 million birr, the same words |
| 7812 and 7736 | **7812 removed**, 7736 kept | different agents, one property: land at Ayat (near the power office), 250 m², 14 million birr |
| 7668 and 7715 | **7668 removed**, 7715 kept | different agents, one property: studio condominium at Lideta, 37 m², 9th floor, 5.2 million birr |
| 7856 and 7656 | both kept | different floors (ground and 1st), so different units |
| 7694 and 6757 | both kept | unclear: only 7694 names a penthouse at Bole Atlas |
| 7899 and 6776 | both kept | unclear: only 7899 names a shop; 6776 is the channel's contacts only |
| 7938 and 7959 | both kept | not a property: one government press release on a land lease auction (127 plots), with no single place, size or price |

The 11 pairs of Bet_afri rooms with different prices stay as they are (owner's decision).

**Left for the owner (task S30), not removed** (as written then; see the decisions above):

| Listing | Same as | Why it was left |
|---|---|---|
| 7655 (mygojo1) | 6907 (houseapartmentcarreleator) | different agents: land at Ayat 49, 90 m², 8 million birr (7655 is in the sale sample) |
| 7812 (Ethiodelala2) | 7736 (hugeAddisababamarket2025) | different agents: land at Ayat, 250 m², 14 million birr (7812 is in the sale sample) |
| 7668 (mygojo1) | 7715 (houseapartmentcarreleator) | different agents: studio at Lideta, 37 m², 9th floor, 5.2 million birr |
| 7694 | 6757, same channel | not clearly one property: the same slogan, but only 7694 names a penthouse at Bole Atlas; neither is a usable listing |
| 7692 | 6677, same channel | the price differs: villa at Summit, 150 m², 17.5 million on 31 October and 23 million on 1 November (neither is in the sale sample) |
| 7797 | 7242, same channel | the price and the code differ: Addisu Gebeya, 3 bedrooms, rent 80,000 against 70,000 birr; maybe two flats |

**Left for the owner (task S32), not removed** (as written then; see the decisions above):

| Listing | Same as | Why it was left |
|---|---|---|
| 7938 (houseapartmentcarreleator) | 7959 (hugeAddisababamarket2025) | no phone or username in common, so not covered by the rule, although these two channels share one code system; both are the same government press release on a land lease auction, not a property, which the parser wrongly reads as an office for sale (neither is in the sale sample) |
| 7856 | 7656, same channel (mygojo1) | not clearly one flat: Mexico/Lideta, 1 bedroom, 52 m², 7.5 million birr, but 7856 says ground floor and 7656 says 1st floor, with other codes (4016, 3986) and other details (neither is in the sale sample) |
| 7899 | 6776, same channel (giftrealestateee) | not clearly one property: only 7899 names a roadside shop for sale; 6776 is the channel's contacts only (neither is a usable listing) |

The scrape added 11 pairs whose price differs. All 11 were read: they are different rooms and flats for rent on Bet_afri's
template (other codes and room sizes, for example BT 1465, a 3×3.5 m room for 11,000 birr, and BT 1488, a 3×3 m room for
10,000 birr), not repeats.

`dedup_strict.py` now lists 71 pairs whose price differs (58 before S32): the 11 new ones above, and 2 more among older listings that were not read.

**The scrape of 19 November (task S43)** added 203 listings, to 6,507. `dedup_strict.py` listed 13 repeats. 4 were pairs already
decided above (7694 and 6757, 7899 and 6776, 7938 and 7959, 7856 and 7656: both kept). The other 9 were read side by side, and 7
copies were removed (in the table above) with `dedup_strict.py --apply --only ...` (backup
`backups/ollaa_2026-11-19_2322_before_dedup.dump`; the scrape's own backup is `backups/ollaa_2026-11-19_before_S43.dump`). Stored
listings went from 6,507 to 6,500; 5 of the 7 were usable, 1 was in the sale sample. Two pairs were kept:

| Pair | Decision | Why |
|---|---|---|
| 8258 and 7656 | both kept | one channel (mygojo1), Mexico/Lideta, 1 bedroom, 52 m², 7.5 million birr, but 8258 says 4th floor and 7656 1st floor, with other codes (4035, 3986): different units |
| 8260 and 7847 | both kept | unclear: one channel (mygojo1), Jemo 1 condominium, 31 m², 3rd floor, 4.5 million birr, but other codes (4033, 4019) and other details (only 8260 names a gypsum ceiling, an asphalt compound and an empty flat); a block holds many such flats (8260 is in the sale sample) |

`dedup_strict.py` now lists 76 pairs whose price differs (77 before the removals). 5 involve the new listings; none was removed:

| Listing | Same as | Why it is left for the owner |
|---|---|---|
| 8378 | 8377, same channel (AddisBrokerageNetworking) | Megenagna flat, 111 m², 15,540,000 against 13,500,000 birr, posted the same day; both in the sale sample |
| 8387 | 3786, same channel (AddisBrokerageNetworking) | Bulgaria flat, 92 m², 14,499,000 now against 11,999,999 birr earlier; both in the sale sample (maybe a price rise) |
| 8389 | 8079, same channel (Bet_afri) | studio at Bole, rent 30,000 (3rd floor) against 35,000 birr (1st floor): different floors, so different units |
| 8390 | 8054 and 8058, same channel (Bet_afri) | rooms at Ayat, rent 20,000 against 15,000 and 14,000 birr: Bet_afri's room template, as the 11 pairs above |

**What is still not certain.** In the sample, 17 listings in 8 groups look like one property whose
price changed and were kept, so up to 9 of the 544 may not be different properties (for example 7150
and 2704, and 8377 and 8378); 6 more are extra copies that share type, place, price and size but were kept
(different floors, or unclear, as 8260 and 7847). More extra copies share type, place, price and size but differ in floor, bedrooms or second
size, or hold protected values, and 6 of the listings returned in S24 are uncertain (below). A property
advertised by two brokers with different prices or wording cannot always be detected, and different units
at one price can look alike, so read 544 as about 529 to 544 different properties.

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

**Sale sample: 544 listings** (493 before the scrape of 15 November, 525 after it; 2 repeats removed in S33; 523 before the scrape of
19 November, 545 after it, 1 repeat removed in S43). Each has a price, a size (plot for land), a named place and
a known type, is priced in birr, has no obvious outlier and repeats no other listing. By type:
apartment 314, condominium 114, land 64, shop 18, villa 17, studio 8, warehouse 6, office 3.
Whole buildings and houses with a plot size only are not in it (no built-up size).

**Left out by the owner's decision (1 November 2026):**

- **6930**: 22 million birr for 150 m²; the advert does not say whether it is land or a house.
- **6726**: 250,000 birr is the price per m², read as the total; the unit's total is not stated.

| Variable | Known in the sale sample (544) | Use in a model |
|---|---|---|
| Price, size, type, named place | 100% (by definition; see "Accuracy check") | core variables |
| Map coordinates | 84% | usable (rough, one point per place) |
| Sub-city | 92% | usable (the owner's sub-city rules, 16 November 2026) |
| Bedrooms | 74% (homes only: 88% of 453) | usable for homes, with the missing ones handled (a "not stated" category or a smaller sample) |
| Floor | 40% | too incomplete |
| Bathrooms | 25% (homes: 30%) | too incomplete |
| Posting date | 47% | too incomplete for a time trend so far; it grows with each scrape |
| Building height (G+n) | 4% | too incomplete |
| Finishing | 20% | too incomplete |
| Payment terms | 17% | too incomplete |

Location is thin at the neighbourhood level. The 544 listings fall in 68 places, but only
28 places have 5 or more listings and 15 have 10 or more. Only 29 place-and-type
combinations have 5 or more. Sub-city fixed effects, or distance from coordinates, are
more realistic than one dummy per neighbourhood.

**Rent sample: 36 listings** with rent, size, place and type (condominium 17, apartment 12,
shop 3, villa 2, others 2), so a rent model is not possible. Without requiring size there
are 230 (apartment 78, single room 70, studio 37, condominium 18, villa 16, others 11),
mostly flats, rooms and studios. That is enough to describe rents, not to model them.
`rental_listings` (rebuilt in task S13) has one row for every rent or mixed listing with a
rent: 241 rows, the 237 usable rentals with a rent plus 4 whose class keeps them out of the
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

| Houses (villas, townhouses) | Before S25 | After S25 | After S26 | After S27 | After S30 | After S32 | After S43 |
|---|---|---|---|---|---|---|---|
| In the sale sample, with a built-up and a different plot size | 27 | 27 | 15 | 15 | 15 | 16 | 17 |
| In the sale sample, with the same number stored as both | 91 | 0 | 0 | 0 | 0 | 0 | 0 |
| **All houses in the sale sample** | **118** | **27** | **15** | **15** | **15** | **16** | **17** |
| Outside the sample, otherwise fit, with a plot size only | 150 | 241 | 248 | 245 | 260 | 284 | 293 |

In S26, houses whose two sizes are the land on the title deed and the land held ("በካርታ 120 ካሬ, በይዞታ 160 ካሬ")
lost a built-up size that was never stated. Of the 15 left then, some built-up sizes are the house's footprint ("300 ካሬ ላይ
ያረፈ", for a G+3), not its floor area.

19 other houses outside the sample (no price or no named place) still hold the same kind of copied size. They
are protected and were not part of the owner's decision.

## Accuracy check

**These are Claude's counts from reading the adverts; the owner has not confirmed them.** The owner asked to
go ahead on them on 1 November 2026, and can still check any of the files: `database/accuracy_check.py` writes
`data/accuracy_check/accuracy_check_60.html` (round 1, with the values as they then were),
`accuracy_check_60_round2.html` and `accuracy_check_60_round3.html` (not committed). A listing counts as wrong when the advert contradicts a stored
type, place, price, size or bedrooms.

| | Round 1, before the fixes | Round 2, after the fixes | Round 3, 3 November |
|---|---|---|---|
| Listings drawn at random from the sale sample | 60 of 457 | 60 of 492, none from round 1 | 60 of 391 (the sample of 493 without rounds 1 and 2) |
| **With at least one wrong value** | **20 (33%)** | **6 (10%)** | **7 (12%)** |
| Likely true share (95% interval, Wilson) | 23% to 46% | 5% to 20% | 6% to 22% |
| Type wrong | 12 | 3 | 2 |
| Size wrong | 9 | 4 | 1 |
| Place wrong | 4 | 1 | 2 |
| Price wrong | 2 | 1 | 2 |
| Bedrooms wrong | 3 | 0 | 1 |
| Bedrooms stated but not stored | 10 | 1 | 0 |

**Round 3 (task S30).** `random.Random(20261104).sample(pool, 60)`; every advert was read in full, and the draw was not changed
after reading. It says accuracy has held at about the level of round 2: 10% and 12% cannot be told apart with 60 listings each, and
both stay below round 1. No parser rule was changed and nothing was corrected.

| Listing | What the advert contradicts |
|---|---|
| 1199 | bedrooms: 56.5 m² is the studio; 1 bedroom belongs to the 77.2 m² unit |
| 1330 | size: 5,624,190 birr is for 45 m², not 60 m² |
| 2438 | place: Awarre, not Kality (a protected value); price: 78 m² is 5.4 million, 8.5 million is the long-payment price of 80 m² |
| 2610 | type: apartments at Bole Dembel, not a villa |
| 2623 | price: 9.1 million is the top of the range, about 114 m²; 106 m² at 80,000 birr per m² is about 8.5 million |
| 5596 | place: Gelan, opposite Robik Hotel, not Kality |
| 7319 | type: 40 shops, 2 warehouses and a house, not a warehouse |

6 of the 7 (all but 7319) are adverts offering several units, and in 4 of them (1199, 1330, 2438, 2623) one unit's value is paired with
another's. Not counted as wrong, as in round 2, and listed under "My reading" in the file: built-up sizes stored for 3 land listings
(1742, 2112, 2869), whose model size is the plot; another unit's size stored as the plot of 3 flats (1199, 1309, 2610). 2 of those are
already among the 7, so counting them as well would make 11 of 60 (18%). 2112 and 2869 are also one piece of land at two prices.

Cautions for round 3: one reader, Claude, who knows the rules, made this count; the owner has not checked it; and 60 listings is a
small sample. Rounds 1 and 2 read about the first 620 characters of each advert and round 3 read everything, but all 7 mistakes show
early in their adverts, so that did not raise the count.

**Rounds 1 and 2.**

Three cautions. One reader made both counts, knowing the rules. That reader read about the first 620 characters of each
advert, and long ones run past that. And 2 of round 2's 6 (2836, 2841) showed the title-deed-and-holding mistake, which was
then fixed; they left the sample and 2 random listings replaced them, so the file shows 4 wrong. 10% is the fair figure, because
that rule was written after seeing them.

**The 4 still in the file:** 1099 and 1744 are flats called offices, because the wrong type was a protected value. The owner
released those and 2625 (a flat called a shop) in task S27 (`database/migrations/2026_11_01_s27_release_wrong_types.py`), and
the parser now reads all 3 as apartments; protected values went from 324 to 321. Round 2's file still shows the old values, as
the owner received it. In task S28 the owner also released the protected built-up size of 2625 (94 m², not in its advert, which
lists 70.85 and 73.94 m²), and the parser now reads 73 m², which fits its price at 99,000 birr per m²; protected values went to 320. 2342 and 2887 are adverts for several sites or projects, with
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

Usable listings stayed 1,577 in S26. Bedrooms known in them went from 655 to 832.

Other things seen, not counted as wrong:

(Round 1, before the fixes.)

- **13 of 60:** houses with one size stored as both plot and built-up, cleared in S25.
- **10 of 60:** bedrooms stated but not stored, fixed in S26.
- **4 of 60:** a right but less exact place (Ayat for Ayat 49, Bole for Bole 22).
- **2 of 60:** a plot size stored for a flat, not in the advert.
- Size conventions differ: 155(145) m² stores the gross size in 1809 and the net size in 5552.
- 1260 is a list of many properties and should not be one listing; 1893 says it was sold.

## What would improve the data most

1. The owner's own check of the round 2 and round 3 files, to confirm the 10% and the 12%.
2. Decide how to model houses: 284 with a plot size only are outside the sample, against 16 inside it.
3. Keep scraping regularly: posts now come with their real dates, and the busiest channels
   post 40 messages in about two days, so a run at least every two days avoids new gaps.
4. Fetch the real posting dates from Telegram for the 858 undated usable listings (the
   message ids are stored), so the model can include time.
5. Give a sub-city to the places that lack one in `src/locations.py` (151 listings).
