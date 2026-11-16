# Thesis data check: off-plan apartments in Bole Sub-City

Thesis topic (owner, 16 November 2026): **"Market-implied discount rates and cash-equivalent prices of off-plan apartments in
Bole Sub-City."** This file shows what the stored data can give that topic today. It uses the stored listings only, as the owner
asked: nothing contacted Telegram. Every number comes from `database/thesis_data_check.py` (read-only), which can be run again:

    venv\Scripts\python.exe database\thesis_data_check.py

State of the database on 16 November 2026: 6,304 stored listings, 1,752 usable (see `DATA_QUALITY.md`).

## In short

- **Sub-cities now follow the owner's rules** (16 November 2026, shared with the ollaa-web project): Ayat, CMC, Summit, Figa and
  their neighbours are Lemi Kura, every "Bole…" place but Bole Arabsa is Bole, and Gerji is Bole. Bole is therefore smaller than in
  the first check: **49 of the 265 off-plan apartment adverts are placed in Bole** (83 before), mostly "Bole" itself, Haya Hulet
  and Bole Bulbula. 57 more adverts are unclear.
- **What the 49 Bole off-plan adverts state** (stored fields): total price 59%, down payment % 61%, unit size 37%, a handover date
  10% (a date or a period 29%), an instalment plan 4%, a discount schedule 4%, and 1 advert ties instalments to construction. None
  states more than 4 of the 7 terms; the 5 most complete are shown under "Bole off-plan apartments: what they state".
- **Too few for a discount-rate model from text alone:** 17 Bole off-plan adverts have a unit size and total price, 1 has those and
  a discount schedule, and none states both a price paid at once and a price paid over time. Ready Bole apartments with price and
  size: **69**.
- **The one-row-per-unit table** (`listing_units`, task S38) gives 87 units in 14 Bole off-plan adverts.
- **championallsites is almost all photos (1,043 of 1,090 posts)**: its prices and payment terms are in the pictures. A 30-photo pilot
  from its Bole developers' topics (task S41) is prepared; see "Photo pilot".

## How adverts were sorted (please read: these are word rules, so the counts are estimates)

- **Apartment advert for sale:** text read (not a photo-only post), not for rent, and stored as an apartment or studio, or of unknown
  type with apartment words ("አፓርትመንት", "መኝታ", "bed"). Government condominiums are kept apart.
- **Off-plan:** the advert says the building is under construction ("በግንባታ ላይ", "97% የደረሰ", "under construction"), or gives a
  handover ("መረከቢያ 2 አመት", "የሚረከቡ", "delivery"), or sells on a payment plan (down payment or instalments) and names a
  developer, or sits in a forum topic whose title starts with the building's progress ("90% ሀያሁለት").
- **Ready:** none of that. **Unclear:** off-plan words and also finished-building words ("ግንባታው የተጠናቀቀ", "ካርታ ያለው", "ተከራይቶ",
  a topic titled "100% ያለቀ"); developers also sell finished flats on payment plans.
- **Bole:** the sub-city of the listing's stored place in `src/locations.py`. A developer advert often lists several sites; the stored
  place is the one the parser picked (usually the first), so a second count shows adverts naming any Bole place.
- **Usable** and **sale sample** have the meaning of `DATA_QUALITY.md`. Many off-plan adverts are not in the sale sample because
  they list several units or have no single total price.
- Each field below was found by word patterns in Amharic and English, read on samples of adverts, not checked advert by advert. The
  five examples under each field show what was matched. Contacts are masked.

## Off-plan apartment adverts

|  | All stored adverts with text | of them usable listings | in the sale sample |
|---|---|---|---|
| Apartment adverts for sale (text read) | 832 | 621 | 309 |
| **Off-plan** (being built or sold on a developer's plan) | **265** | 169 | 69 |
| Unclear (off-plan words and finished-building words) | 57 | 47 | 19 |
| Ready (no off-plan words) | 510 | 405 | 221 |

| Off-plan adverts | Count |
|---|---|
| Stored place in Bole sub-city | **49** |
| Naming a Bole place anywhere in the text (a developer often lists several sites) | 44 |
| Stored place in another sub-city | 170 |
| Stored place without a sub-city in the place table | 18 |
| No place found | 28 |

The 49 off-plan adverts placed in Bole, by place: Bole 26, Haya Hulet (22) 10, Bole Bulbula 8, Bole Adey Abeba 1, Bole Michael 1, Wello Sefer 1, Gerji 1, Bole Medhanialem 1. Ayat, CMC, Summit and Figa are in Lemi Kura under the owner's rules (16 November 2026).

Off-plan adverts by the sub-city of their stored place: Kirkos 65, Lemi Kura 49, Bole 49, (none) 46, Yeka 29, Arada 20, Nifas Silk 4, Sheger 1, Kolfe 1, Akaki 1.

Not counted above: 3,721 photo-only posts, whose words are in the picture; 1,043 of them are in championallsites and 1,488 are in a forum topic or name a developer.

## Bole off-plan apartments: what they state

Under the owner's sub-city rules (16 November 2026), 49 off-plan apartment adverts are placed in Bole. These counts use the fields the parser stores (tasks S36 to S39):

| Stated | Bole off-plan adverts (49) |
|---|---|
| Total price | 29 (59%) |
| Unit size | 18 (37%) |
| Down payment % | 30 (61%) |
| Instalment plan (number of instalments or their period) | 2 (4%) |
| …with its timing (the period in months) | 1 (2%) |
| Instalments linked to construction stages | 1 (2%) |
| Handover date | 5 (10%) |
| Handover date or period | 14 (29%) |
| Cash or early-payment discount schedule | 2 (4%) |

Number of these 7 terms stated (total price, size, down payment, instalments, construction link, handover date, discount schedule): 4 terms: 3, 3 terms: 12, 2 terms: 13, 1 terms: 13, 0 terms: 8.

The 5 most complete (masked):

- **2184** (luxury_freelancers, bole_bulbula; 4 of 7): 11,000,000 birr; 110 m²; down payment 3%; discounts 50:3; 75:4.5; 100:6 (share paid : discount %). “*General briefing* / -From 26-29......Semi Finished / -From 16-25......Fully Finished / All ground 2Bed room (110 Sqm)and from 1-4 3 Bed room (130Sqm) / *Price* :- 100,000Birr/SQM Semi Finished and 120,000Birr/SQM Fully Finished / *N.B* :- Vat included / -6% D…”
- **2619** (Apartments_store, gerji; 4 of 7): 4,352,400 birr; 66 m²; down payment 12%; tied to construction. “👉ለዘመናዊ አኗኗርዎ የሚመጥን ዘመናዊ መንደር ያሰፈልግዎታል ➥Royal Real Estate / 📍ከ  ገርጂ ወደ  ጃክሮስ በሚወስደው መንገድ ላይ / 💥በ ካሬ 65,000 ብር ብቻ💥 / ➥➥ከ1 እስከ 3 መኝታ  አፓርታማ / 👉👉ከልዩ ልዩ ቅናሽ ጋር እና ሌሎች ብዙ አጓጊ እና ምቹ ሁኔታውችን አመቻችተናል። / 💥በ12% ቅድመ ክፍያ ቀሪዉን የግንባታውን ሂደት እያዩ የሚከፍሉት💥 / 👉👉ገርጂ ሜታ መብራት / ►ባለ አን…”
- **7479** (luxury_freelancers, bole_bulbula; 4 of 7): 14,900,000 birr; 103 m²; down payment 30%; over 12 months. “በቦሌ ቡልብላ ሪፌንቲ / ባለ 4ወለል ህንፃ / -60ሺህ ካሬ ላይ ያረፈ ኮንፖወንድ ጊቢ / -በወለል 1ቤት ብቻ / -ባለ 2መኝታ 103ካሬ(90net) / -ባለ 3መኝታ 125ካሬ(110net) / -30% ቅድመ ክፍያ / -ቀሪው በ1ዓመት ሚከፍሉት / -በቂ የመኪና ማቆሚያ ስፍራ / 🔰ዋጋ በካሬ / Ground 144,720 / 1st Floor 155,000 / 2nd Floor 149,000 / 3rd Floor 141,500…”
- **1210** (championrealestate, bole_main; 3 of 7): 12,960,000 birr; 162 m²; down payment 50%; handover in 3 months. “📢 የሲቲ ሴንተር ሳይት(ቦሌ ጌቱ ኮሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። / ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ / ◎ ጠቅላላ ዋጋ ብር 12,960,000 / ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 / ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ / ◎ የመጨረሻ ክፍያ 25% ብር 3,240,000 በአራት …”
- **1327** (ApartmentForYouAyatRealEstate, bole_bulbula; 3 of 7): 13,267,320 birr; 123 m²; 5 instalments. “መረጃ Temer  Real Estate ዜና ዉጪ / 60,000 ካሬ ላይ ያረፈ አስደማሚ መንደር / ለኑሮ ተስማሚ በሆነው ቦሌ ቡልቡላ / ከ70% በላይ ተገብቶ የተጠናቀቀ / 2. አፓርታማዎቹ / ግራዉንድ ፕላስ 3 ፡ በወለል 1 አፓርትመንት / ባለ ሁለት መኝታ / 105 .8 ካሬ ጠቅላላ  ዋጋ =13,267,320 / ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር / ጠቅላላ ዋጋ = 15,436,740 / ቅድሚያ ክፍያ: አከ…”

## What the off-plan adverts state

| Field | All off-plan (265) | Off-plan in Bole (49) | Usable off-plan |
|---|---|---|---|
| Developer or project name | 176 (66%) | 20 (41%) | 108 |
| Unit size and total price (both stored) | 87 (33%) | 17 (35%) | 79 |
| …of which the total price is written as a total | 30 (11%) | 4 (8%) | 30 |
| Down payment as a % | 182 (69%) | 29 (59%) | 109 |
| Down payment, any form (% or amount) | 197 (74%) | 32 (65%) | 122 |
| Instalment plan | 54 (20%) | 4 (8%) | 46 |
| Instalments linked to construction stages | 7 (3%) | 1 (2%) | 7 |
| Handover date or period | 71 (27%) | 16 (33%) | 35 |
| Cash or early-payment discount | 50 (19%) | 2 (4%) | 40 |
| Discount schedule (2 or more discount rates) | 17 (6%) | 2 (4%) | 14 |
| Price per m² written in the advert | 67 (25%) | 14 (29%) | 51 |

### Stored by the parser (tasks S36, S37 and S39)

The same terms as fields of `processed_listings`, filled by `src/payment_terms.py` (stricter than the word counts above, which only show that a term is mentioned):

| Field | Column | All off-plan (265) | Off-plan in Bole (49) |
|---|---|---|---|
| Down payment % | `down_payment_pct` | 186 (70%) | 30 (61%) |
| Discount schedule (share paid : discount) | `discount_schedule` | 29 (11%) | 2 (4%) |
| Number of instalments | `instalment_count` | 10 (4%) | 1 (2%) |
| Instalment period, months | `instalment_months` | 19 (7%) | 1 (2%) |
| Instalments follow construction | `instalments_follow_construction` | 7 (3%) | 1 (2%) |
| Interest-free | `interest_free` | 35 (13%) | 0 (0%) |
| Months to handover | `handover_months` | 49 (18%) | 12 (24%) |
| Handover date (S39) | `handover_date` | 17 (6%) | 5 (10%) |
| Construction progress % | `construction_progress_pct` | 64 (24%) | 20 (41%) |
| Price per m² as written | `price_per_sqm_stated` | 55 (21%) | 7 (14%) |
| Prices by payment option or finish (S37) | `price_options` | 26 (10%) | 4 (8%) |
| Price per m² paid at once | `cash_price_per_sqm` | 10 (4%) | 0 (0%) |
| Price per m² paid over time | `instalment_price_per_sqm` | 7 (3%) | 0 (0%) |
| Total of one unit paid at once | `cash_price_birr` | 9 (3%) | 1 (2%) |
| Total of one unit paid over time | `instalment_price_birr` | 5 (2%) | 1 (2%) |

Off-plan Bole adverts with a discount schedule and a stored size and total price: 1.

Off-plan adverts that state a price paid at once and a price paid over time (per m² or for one unit): 7, 0 of them in Bole: 1106 (ayat_zone) 61,750 against 95,000 birr per m²; 1108 (sarbet_old_airport) 75,000 against 115,000 birr per m²; 1110 (sarbet_old_airport) 75,000 against 110,000 birr per m²; 1123 (ayat_zone) 61,000 against 95,000 birr per m²; 1208 (megenagna) 90,000 against 95,000 birr per m²; 2440 (garment) 77,000 against 110,000 birr per m²; 2441 (sarbet_old_airport) 69,000 against 107,000 birr per m².

### One row per unit (task S38)

`listing_units` holds every unit of a multi-unit advert whose total price the advert states, one row per unit and payment option (`src/listing_units.py`). The listing itself keeps only its first unit.

|  | Adverts | Units | Unit rows (unit × payment option) |
|---|---|---|---|
| All adverts with 2 or more priced units | 78 | 342 | 368 |
| Off-plan apartment adverts | 42 | 205 | 228 |
| Off-plan apartment adverts in Bole | 14 | 87 | 89 |

Units priced both paid at once and another way: 16 in 5 adverts (0 units in off-plan Bole adverts). Units priced both under the 65/35 option and paid over time: 8.

### Five real examples of each (masked; the listing number is the stored id)

**Developer or project name**

- 220 (brokercom11, bole_main): “መኪኖች ቻርጅ ማድረጊያ ቦታ የተዘጋጀለት ☞የ24 ሰአት የካሜራ አገልግሎት(CCTV Service ) . . . . TEMER PROPERTIES Create / Construct / Deliver #Temerproperties #Temerrealestate #Teme”
- 1015 (jamborealestate, bole_main): “የወደፊት ቤትዎ በመሃል ቦሌ እየጠበቅዎ ነዉ !!! 19ኛው በሆነዉ ከሚሊንየም አዳራሽ ጀርባ በሚገኘዉ የጃምቦ ሪል ስቴት ቦሌ-3 ፕሮጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!!”
- 1210 (championrealestate, bole_main): “📢 የሲቲ ሴንተር ሳይት(ቦሌ ጌቱ ኮሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒ”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula): “መረጃ Temer Real Estate ዜና ዉጪ 60,000 ካሬ ላይ ያረፈ አስደማሚ መንደር ለኑሮ ተስማሚ በሆነው ቦሌ ቡልቡላ ከ70% በላይ”
- 2172 (luxury_freelancers, bole_bulbula): “Metro Realestate ⚡️Discount Update for the apartments !⚡️ For 50% Down payment= 3% D”

**Unit size and total price (both stored)**

- 220 (brokercom11, bole_main; stored 80 m², 5,720,000 birr): “ሣር ቤት ላይ 35% ቅናሽ❗️ ✅ መሀል ሣር ቤት ላይ በካሬ 71,500 - 78,000 ብር ብቻ❗️ ✅ የማስታወቂያ ሽያጭ”
- 1210 (championrealestate, bole_main; stored 162 m², 12,960,000 birr): “ለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,2”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula; stored 123 m², 13,267,320 birr): “የተጠናቀቀ 2. አፓርታማዎቹ ግራዉንድ ፕላስ 3 ፡ በወለል 1 አፓርትመንት ባለ ሁለት መኝታ 105 .8 ካሬ ጠቅላላ ዋጋ =13,267,320 ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር ጠቅላላ ዋጋ = 15,436,740 ቅድሚያ ክፍ”
- 2139 (luxury_freelancers, bole_main; stored 148 m², 22,200,000 birr): “ቦሌ መድኃኒዓለም 148 ካሬ 22.2mil(100%) 8th Floor 6 ወር የሚረከብ”
- 2619 (Apartments_store, gerji; stored 66 m², 4,352,400 birr): “ን የግንባታውን ሂደት እያዩ የሚከፍሉት💥 👉👉ገርጂ ሜታ መብራት ►ባለ አንድ መኝታ 66.96 ካሬ ጠቅላላ ዋጋ 4,352,400 ብር ቅድመ ክፍያ 522,288 ብር ►ባለ አንድ መኝታ 81.84 ካሬ”

**Down payment as a %**

- 1015 (jamborealestate, bole_main): “3 ፕሮጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Loc”
- 1210 (championrealestate, bole_main): “ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25%”
- 2169 (luxury_freelancers, bole_bulbula): “👉Only fullyfinished 👉Ground floor= 2bedroom 30%downpayment=4.4mil Fullpayment=14.8mil 👉1st&2nd floor=3bedroom 30%downpayment=5.”
- 2357 (giftrealestateee, haya_hulet): “ጊፍት ሪል ስቴት በ2% ቅድመ ክፍያ የአፓርትመንትና የንግድ ሱቆችን ለሽያጭ አቀረበ **** ጊፍት”
- 2454 (jamborealestat, bole_main): “ቦሌ - 3 የቀሩን ቤቶች :- ባለ 3 መኝታ -> 169 - 182 ካሬ Down payment : 10% Location : ሚኒሊየም አዳራሽ ጀርባ የማስረከቢያ ቀን : ሚያዚያ 30/2019 ለበለጠ መረጃ 0940”

**Down payment, any form (% or amount)**

- 1015 (jamborealestate, bole_main): “ጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Loc”
- 1210 (championrealestate, bole_main): “ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula): “ቅላላ ዋጋ =13,267,320 ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር ጠቅላላ ዋጋ = 15,436,740 ቅድሚያ ክፍያ: አከፋፈል በ12 ወር : 5 ጊዜ ክፍያ ይጠናቀቃል 30% 20% 20% 20% 10% 100% ለበለጠ”
- 2169 (luxury_freelancers, bole_bulbula): “👉Only fullyfinished 👉Ground floor= 2bedroom 30%downpayment=4.4mil Fullpayment=14.8mil 👉1st&2nd floor=3bedroom 30%downpayment=5.”
- 2357 (giftrealestateee, haya_hulet): “ጊፍት ሪል ስቴት በ2% ቅድመ ክፍያ የአፓርትመንትና የንግድ ሱቆችን ለሽያጭ አቀረበ **** ጊፍት”

**Instalment plan**

- 1015 (jamborealestate, bole_main): “መንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Locations: 👉Meskel”
- 1210 (championrealestate, bole_main): “ኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25% ብር 3,240,000 በአራት ወር ውስጥ”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula): “3,267,320 ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር ጠቅላላ ዋጋ = 15,436,740 ቅድሚያ ክፍያ: አከፋፈል በ12 ወር : 5 ጊዜ ክፍያ ይጠናቀቃል 30% 20% 20% 20% 10% 100% ለበለጠ መረጃ 0”
- 2236 (luxury_freelancers, wello_sefer): “📌Block 4 10% ቅድመ ክፍያ በ2አመት ከ4ወር በግማሽ ግንባታ የሚረከቡት 🔰1st Floor ካሬ 115ሺ 👉1መኝታ 93.97ካሬ=10.8mil 👉2”
- 22 (ETHIOhouseagents, meskel_flower): “1, Around 22 plot 200 m² Built-up 130 m² G+4 Guesthouse 500,000 birr monthly income price 65 million negotiable 2, Around Meskel flower 600 m² B”

**Instalments linked to construction stages**

- 2619 (Apartments_store, gerji): “ዩ ልዩ ቅናሽ ጋር እና ሌሎች ብዙ አጓጊ እና ምቹ ሁኔታውችን አመቻችተናል። 💥በ12% ቅድመ ክፍያ ቀሪዉን የግንባታውን ሂደት እያዩ የሚከፍሉት💥 👉👉ገርጂ ሜታ መብራት ►ባለ አንድ መኝታ 66.96 ካሬ ጠቅላላ ዋጋ 4,352”
- 1106 (TemerApartmentShop, ayat_zone): “ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት 🏧 ዋጋ እና አከፍፈል 🛌 ባለ 3 መኝታ 108 ካሬ 🏦 ጠቅላላ ዋጋ = 6.6 ሚልዮን 100% ለ”
- 1143 (TemerApartmentShop, piassa): “ሚልዮን 👉 ቀሪ 90% የሚከፈለው ✅ ከወለድ ነፃ ለ3 አመት ✅ በ16 ዙር ክፍያ 5% እያንዳንዱ ዙር ✅ በግንባታ ሂደት ✅ ያለምንም ጭማሪ በሀገራችን ብር ብቻ ቀድመው በመደወል ቤትዎ ይምረጡ <contact> / 09-83”
- 1534 (TemerApartmentShop, sarbet_old_airport): “scalation – fixed price guarantee ✔️ Interest-free payment ✔️ Payment based on construction progress ✔️ Trusted developer with proven delivery ✔️ Prime locations”
- 2438 (TemerApartmentShop, kality): “ታ = 153ካሬ = 11.4ሚሊዮን ✅ በረጅም ጊዜ ክፍያ ለሚፈልጉ ደምበኞች 🏦 በ20% ቅድመ ክፍያ (በግንባታ ሂደት ለሚከፍሉ) 👉 106ካሬ = ሙሉ ክፍያ = 12.1ሚሊዮን ቅድመ ክፍያ 20% = 2”

**Handover date or period**

- 220 (brokercom11, bole_main): “ባለ 3 መኝታ ✅ 139.23 ካሬ = 9,954,750 ✅ በኢትዮጵያ ብር ብቻ ተዋውለው ያለምንም ጭማሪ ቤቶን የሚረከቡበት ✅ በወለል 2 ቤት ብቻ በቅናሽ አቅርበናል! ✅ የዲፕሎማት መቀመጫ በሆነችው ሣር ቤት። ☎️ +251972”
- 1210 (championrealestate, bole_main): “% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25% ብር 3,240,000 በአራት ወር ውስጥ ◎ መረከቢያ 3 ወር ◎ የባለቤትነት ካርታ የተዘጋጀለት <contact>”
- 2139 (luxury_freelancers, bole_main): “ቦሌ መድኃኒዓለም 148 ካሬ 22.2mil(100%) 8th Floor 6 ወር የሚረከብ”
- 2454 (jamborealestat, bole_main): “ኝታ -> 169 - 182 ካሬ Down payment : 10% Location : ሚኒሊየም አዳራሽ ጀርባ የማስረከቢያ ቀን : ሚያዚያ 30/2019 ለበለጠ መረጃ <contact>”
- 2582 (realityaddisababa, bole_main): “artments located at Bole Dembel. 📍Prime Location 🏠Elegant Finishes 🗓 Handover: Q4 2025 𝐂𝐎𝐌𝐄 𝐇𝐎𝐌𝐄 𝐓𝐎 𝐖𝐇𝐀𝐓 𝐌𝐀𝐓𝐓𝐄𝐑𝐒! 📲 Contact Us: 📞 <contact> 📞 0”

**Cash or early-payment discount**

- 2172 (luxury_freelancers, bole_bulbula): “tate ⚡️Discount Update for the apartments !⚡️ For 50% Down payment= 3% Discount from the total amount For 100% Down payment= 6% Discount from the t”
- 109 (giftrealestateee, cmc_michael): “እና የንግድ ሱቆችን ለሽያጭ አቅርቧል። 💥ከ341,962 ብር ቅድመ ክፍያ ጀምሮ የቤት ባለቤት ይሁኑ። 👉 20% ቅናሽ ከሙሉ ዋጋ ላይ እሚቀነስ 👉 ቅድመ ክፍያ ከ 5% ጀምሮ 👉 45% የባንክ አማራጭ የተመቻቸላቸዉ 👉 ሙሉ በሙሉ”
- 1099 (TemerApartmentShop, piassa): “ላይ 2 ሳይት በጥራት እና በታማኝነት ያስረከበው #ቴምር ሪልስቴት አሁን ላይ #ፒያሳ ቸርችል ጎዳና አጠገብ ከ30% ልዩ ቅናሽጋ ባለ 3 እና ባለ 2 መኝታ ቤቶች አቅርቦላቹሀል። በቀጥታ አልያም ውጪ ሁኖው በዋሳፕ ያነጋግሩን። 09-83”
- 1167 (Bamaconrealestateplc, other_addis): “🏠130.94 sq.m2 ➣2 bedroom 💵Total price =12,963,060ETB 💵(100%) payment 15% discount=12,242,890ETB 💵(30%) down payment =3,888,918ETB”
- 1309 (Temerproperties2m, sarbet_old_airport): “ቃዎች ጭማሪ ፤ በኢትዮጵያ ብር ከፍለው የሚጨርሱት * 3ዐ% እና ከዚያ በላይ ለሚከፍሉ፣ ከከፈሉት ላይ 15%_25% ቅናሽ አዘጋጅተናል”

**Discount schedule (2 or more discount rates)**

- 2172 (luxury_freelancers, bole_bulbula): “tate ⚡️Discount Update for the apartments !⚡️ For 50% Down payment= 3% Discount from the total amount For 100% Down payment= 6% Discount from the t”
- 1101 (TemerApartmentShop, awere): “አዲስ ሳይት በሴቶች አደባባይ #አዋሬ ላይ በትልቅ ቅናሽ 35% ባለ 1 መኝታ እና ባለ 3 መኝታ ከታማኙ #ቴምር ሪልስቴት ይግዙ። <contact> በቀጥታ ወይም ዋሳፕ”
- 1330 (ApartmentForYouAyatRealEstate, kazanchis): “አከከፋፈል 10% ቅድመ ክፍያ 15% 15% 15% 15% 15% 5% 5% 5% የቅንሽ መጠን 100% ለከፈለ 20% ቅናሽ 85% ለከፈለ 17% ቅናሽ 70% ለከፈለ 14% ቅናሽ 55% ለከፈለ 11% ቅናሽ 40% ለከፈለ 8% ቅናሽ”
- 1963 (Apartments_store, ayat_49): “እና 156ካሬ 💥ዋጋ: 12,727,000ብር እና 13,884,000ብር 🌟ቅናሽ ቅድመ ክፍያ: 50% ለሚከፍል 2% ቅናሽ ቅድመ ክፍያ: 100% ለሚከፍል 5% ቅናሽ 👌🏾ህንፃው ያካተተው የጂም እና ሙሉ የስፓ አገልግሎት የተሟላለት”
- 2562 (realityaddisababa, dembel): “ላይ በሚገኘው አዲሱ ፕሮጀክታችን ላይ ልዩ ቅናሽ ይዘን መተናል! እስከ ነሐሴ 5 ድረስ ቅድመ ክፍያ ሲከፍሉ 7% ቅናሽ ያገኛሉ፣ ሙሉ ክፍያ የሚፈጽሙ ከሆነ ደግሞ የ27% ቅናሽ ይኖሮታል። ይህም ማለት በካሬ በ83,950 ብር ብቻ”

**Price per m² written in the advert**

- 220 (brokercom11, bole_main): “ሣር ቤት ላይ 35% ቅናሽ❗️ ✅ መሀል ሣር ቤት ላይ በካሬ 71,500 - 78,000 ብር ብቻ❗️ ✅ የማስታወቂያ ሽያጭ ባለ 1 መኝታ ✅ 80.7ካሬ = 5,770,0”
- 1210 (championrealestate, bole_main): “ሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር”
- 2184 (luxury_freelancers, bole_bulbula): “oom (110 Sqm)and from 1-4 3 Bed room (130Sqm) *Price* :- 100,000Birr/SQM Semi Finished and 120,000Birr/SQM Fully Finished *N.B* :- Vat inclu”
- 2628 (Apartments_store, bole_main): “ስቴት(Palm Real Estate) 💥ከተረጋገጠ የባንክ ብድር ጋር 🧩 40% የ ባንክ ብድር የተመቻቸለት 💰 በካሬ 99,000 ብር 📍ቦሌ ደምበል(Dembel site)💥💥✅ 👉 ባለ 1 መኝታ: 70.85 & 73.94ካሬ 👉 ባለ”
- 6726 (ApartmentForYouAyatRealEstate, bole_main): “ፃ ከ3ኛ እስከ 5ኛ ፎቅ የሚገኙ የንግድ ቦታዎች! • ስፋት: ከ 20 ካሬ ሜትር ጀምሮ የዋጋ አማራጮች (በካሬ)፦ 🔹 100% ሙሉ ክፍያ ለሚፈፅሙ: • 3ኛ ፎቅ ➡️ 250,000 ብር • 4ኛ ፎቅ ➡️ 215,000 ብር •”

## Ready Bole apartments, for comparison

| Bole apartments for sale | Count | usable | in the sale sample |
|---|---|---|---|
| Ready, any | 112 | 86 | 33 |
| **Ready, with price and size** | **69** | 69 | 33 |
| Off-plan, with price and size | 17 | 17 | 14 |
| Unclear, in Bole | 7 | 6 | 4 |
| Government condominiums with price and size (kept apart) | 4 | 4 | 4 |

- Ready Bole apartments: median asking price 151,515 birr per m² over 69 listings (stored total price ÷ stored size; not cleaned for outliers).
- Off-plan Bole apartments: median asking price 105,000 birr per m² over 17 listings (stored total price ÷ stored size; not cleaned for outliers).

## Channels and forum topics with the most off-plan adverts with payment terms

211 of the 265 off-plan adverts state a down payment, an instalment plan or a discount; 33 of them have their stored place in Bole.

| Channel or group | Off-plan with payment terms | of them in Bole |
|---|---|---|
| TemerApartmentShop | 72 | 0 |
| luxury_freelancers | 38 | 19 |
| giftrealestateee | 26 | 5 |
| ApartmentForYouAyatRealEstate | 19 | 2 |
| menoriarealestatesalesconsultant | 12 | 0 |
| Apartments_store | 10 | 2 |
| jamborealestat | 8 | 2 |
| Temerproperties2m | 5 | 0 |
| championrealestate | 5 | 1 |
| Bamaconrealestateplc | 4 | 0 |
| brokercom11 | 4 | 1 |
| dmcrealestateofficial | 2 | 0 |
| jamborealestate | 2 | 1 |
| realityaddisababa | 2 | 0 |
| ETHIOhouseagents | 1 | 0 |

Forum topics (each topic is usually one developer project):

| Group | Topic | Off-plan with payment terms | of them in Bole | All stored posts in the topic |
|---|---|---|---|---|
| luxury_freelancers | Janbo Realestate | 7 | 4 | 41 |
| luxury_freelancers | Metro ቡልቡላ compund | 5 | 5 | 41 |
| luxury_freelancers | 97% ካዛንቺስ Joberg | 5 | 0 | 31 |
| luxury_freelancers | 85% ቦሌ ደንበል Palm Realestate 40%Bank | 4 | 4 | 19 |
| luxury_freelancers | 95% መገናኛ እግዚያራብ | 4 | 0 | 8 |
| luxury_freelancers | 90% ሀያሁለት | 2 | 2 | 12 |
| luxury_freelancers | Compass property | 2 | 2 | 5 |
| luxury_freelancers | 90% መስቀል ፍላወር 50%Bank | 1 | 0 | 11 |
| luxury_freelancers | ብስራተ ገብርኤል Aman Property | 1 | 0 | 14 |
| luxury_freelancers | 90% ሜክሲኮ ሰንጋተራ | 1 | 0 | 6 |
| luxury_freelancers | Eniy Realestate ቡልቡላ compund | 1 | 1 | 11 |
| luxury_freelancers | Abay Homes ሜክሲኮ | 1 | 0 | 11 |
| luxury_freelancers | 90% hiya 50% bank | 1 | 0 | 13 |
| luxury_freelancers | Ghion Homes ወሎ ሰፈር | 1 | 1 | 6 |
| luxury_freelancers | Merit Realestate 4ኪሎ | 1 | 0 | 8 |
| luxury_freelancers | Dream builders Realestate | 1 | 0 | 7 |

**championallsites** (a forum group, one topic per developer project): 1,090 stored posts in 46 topics; 1,043 are photo-only, so their prices and payment terms are in the pictures, which the text parser cannot read. Of the 47 with text, 9 are construction-progress updates, and 0 is read as an off-plan apartment advert. Its busiest topics:

| Topic (project) | Stored posts | Photo-only | With text |
|---|---|---|---|
| Nor Sheger_Arada Grand Mall (ፒያሳ) | 51 | 50 | 1 |
| #Champion_Site Gazebo Skyline | 50 | 45 | 5 |
| Visco_BoleMeskelFlower(መስቀልፍላወር) | 40 | 40 | 0 |
| 3NASeyoum_Sholla(ሾላ) | 39 | 37 | 2 |
| Star_Properties_Grove Apartment Sarbet | 35 | 35 | 0 |
| Nexus_Sunset (ለቡ ቫርኔሮ) | 35 | 33 | 2 |
| Laphto_Life_Real Estate (Biserat Gbreal) | 31 | 30 | 1 |
| Tekas_TheUrbanTower(ሜክሲኮ የቀድሞ ሜቴክ ጀርባ) | 31 | 28 | 3 |
| AMESCO_GreenlandVillage(ለቡ ሙዚቃ ሰፈር) | 31 | 30 | 1 |
| Zaramba Real estate- UPTOWN ADDIS | 30 | 28 | 2 |
| Zeramba_Peaceful(ወሎ ሰፈር ከኢንሳ ፊትለፊት) | 29 | 28 | 1 |
| (Sold Out) Prime_Millinneium Plaza (ሚሊንየም አዳራሽ ሰባተኛ በር) | 29 | 28 | 1 |
| (Sold Out) Estifanos_EastHorizon2(ወሰን) | 29 | 29 | 0 |
| Amifa_Green Garden (ካዛንቺስ) | 28 | 26 | 2 |
| MetroHomes_Bole_Harmony Loft (ቦሌ ሚካኤል) | 28 | 27 | 1 |

## Places named in the off-plan adverts

| Code | Place | Written in the adverts as | Sub-city now | Sure? | Adverts naming it | Stored as the listing's place |
|---|---|---|---|---|---|---|
| ayat_zone | Ayat | አያት, Ayat, በአያት | Lemi Kura | owner's rule (16 Nov 2026) | 58 | 29 |
| bole_main | Bole | ቦሌ, Bole, bole | Bole | owner's rule (16 Nov 2026) | 48 | 30 |
| cmc_michael | CMC | CMC, በሲኤምሲ, ሲኤምሲ | Lemi Kura | owner's rule (16 Nov 2026) | 31 | 13 |
| sarbet_old_airport | Sarbet / Old Airport | ሳርቤት, sarbet, Sarbet | Kirkos | owner's rule (16 Nov 2026) | 29 | 17 |
| piassa | Piassa | Piassa, ፒያሳ, በፒያሳ | Arada | likely | 28 | 21 |
| kazanchis | Kazanchis | ካዛንቺስ, ካሳንቺስ, በካዛንቺስ | Kirkos | likely | 24 | 15 |
| megenagna | Megenagna | መገናኛ, Megenagna, በመገናኛ | Yeka | check: near a sub-city border (Yeka–Bole) | 20 | 15 |
| awere | Awere | አዋሬ, በአዋሬ | Yeka | owner's rule (16 Nov 2026) | 20 | 11 |
| la_gare | La Gare | በለገሃር, ለገሃር, La Gare | Kirkos | likely | 20 | 13 |
| bulgaria | Bulgaria | ቡልጋሪያ, Bulgaria, በቡልጋሪያ | Kirkos | owner's rule (16 Nov 2026) | 17 | 8 |
| summit | Summit | ሰሚት | Lemi Kura | owner's rule (16 Nov 2026) | 17 | 5 |
| haya_hulet | Haya Hulet (22) | 22 ማዞሪያ, ሀያሁለት, ሃያሁለት | Bole | owner's rule (16 Nov 2026) | 13 | 10 |
| mexico | Mexico | Mexico, ሜክሲኮ, በሜክሲኮ | Kirkos | check: near a sub-city border (Kirkos–Lideta) | 13 | 8 |
| ayat_49 | Ayat 49 | አያት 49, Ayat49, በአያት 49 | Lemi Kura | owner's rule (16 Nov 2026) | 13 | 8 |
| garment | Garment | ጋርመንት, Garment | — | **no sub-city in the place table** | 11 | 2 |
| summit_72 | Summit 72 | ሰሚት72, ሰሚት 72 | Lemi Kura | owner's rule (16 Nov 2026) | 9 | 15 |
| dembel | Dembel | ደንበል, Dembel, ወደ ደንበል | — | **no sub-city in the place table** | 9 | 1 |
| meskel_flower | Meskel Flower | Meskel Flower, መስቀል ፍላወር, Meskel flower | Kirkos | check: near a sub-city border (Kirkos–Bole) | 8 | 8 |
| tafo | Tafo | Tafo, ጣፎ | Lemi Kura | check: at the city edge (Yeka–Lemi Kura–Sheger) | 8 | 0 |
| yeka | Yeka | የካ, ከየካ, Yeka | Yeka | check: may be a false match inside a longer word | 7 | 1 |
| haile_garment | Haile Garment | Haile Garment, ሀይሌ ጋርመንት, ሃይሌ ጋርመንት | — | **no sub-city in the place table** | 7 | 2 |
| german | German Square | ጀርመን | — | **no sub-city in the place table** | 7 | 8 |
| gelan | Gelan | ገላን, Gelan | Sheger | likely | 6 | 1 |
| figa | Figa | Figa, በፊጋ, ፊጋ | Lemi Kura | owner's rule (16 Nov 2026) | 6 | 3 |
| 4kilo | Arat Kilo | አራት ኪሎ, 4 Kilo, 4kilo | Arada | likely | 5 | 2 |
| kality | Kality | ቃሊቲ, Kaliti, Kality | Akaki | likely | 5 | 1 |
| gerji | Gerji | Gerji, ገርጂ | Bole | owner's rule (16 Nov 2026) | 4 | 2 |
| yetebaberut | Yetebaberut | የተባበሩት | Lemi Kura | owner's rule (16 Nov 2026) | 4 | 2 |
| imperial | Imperial | Imperial, IMPERIAL, ኢምፔሪያል | Yeka | check: near a sub-city border (Bole–Yeka) | 4 | 2 |
| mekanisa_abo | Mekanisa / Abo Mazoria | mekanisa | Nifas Silk | check: near a sub-city border (Nifas Silk–Kolfe) | 4 | 4 |
| gotera | Gotera | Gotera, ጎተራ | Nifas Silk | check: near a sub-city border (Kirkos–Nifas Silk) | 4 | 1 |
| bole_atlas | Atlas | Atlas | Bole | check: Atlas is near the Bole–Kirkos border | 3 | 0 |
| teklehaimanot | Teklehaimanot | Teklehaimanot | — | **no sub-city in the place table** | 3 | 1 |
| bambis | Bambis | ባምቢስ, በባምቢስ, ከባምቢስ | Kirkos | check: near a sub-city border (Kirkos–Bole) | 3 | 2 |
| lemi_kura | Lemi Kura | በለሚ ኩራ, ለሚኩራ | Lemi Kura | likely | 3 | 0 |
| bole_bulbula | Bole Bulbula | ቦሌ ቡልቡላ | Bole | owner's rule (16 Nov 2026) | 2 | 8 |
| sholla | Shola | ሾላ, Shola | Yeka | check: near a sub-city border (Yeka–Bole) | 2 | 1 |
| lebu | Lebu | ለቡ | Kolfe | check: near a sub-city border (Nifas Silk–Kolfe) | 2 | 1 |
| merkato | Merkato | Merkato, መርካቶ | Addis Ketema | likely | 2 | 0 |
| addisu_gebeya | Addisu Gebeya | አዲሱ ገበያ, የአዲሱ ገበያ | — | **no sub-city in the place table** | 2 | 1 |
| bethel | Bethel | Bethel | — | **no sub-city in the place table** | 2 | 2 |
| wello_sefer | Wello Sefer | ወሎ ሰፈር | Bole | likely | 2 | 3 |
| medhanialem | Medhanialem | መድሃኒዓለም, Medhanialem | — | **no sub-city in the place table** | 2 | 0 |
| salite_mehret | Salite Mehret | Salite Mehret | — | **no sub-city in the place table** | 1 | 1 |
| saris | Saris | saris | Nifas Silk | check: near a sub-city border (Nifas Silk–Akaki) | 1 | 0 |
| kebena | Kebena | kebena | — | **no sub-city in the place table** | 1 | 0 |
| lafto | Lafto | ላፍቶ | Nifas Silk | likely | 1 | 0 |
| atena_tera | Atena Tera | አጠና ተራ | — | **no sub-city in the place table** | 1 | 0 |
| bole_adeyabeba | Bole Adey Abeba | ቦሌ አደይ አበባ | Bole | owner's rule (16 Nov 2026) | 1 | 1 |
| hiya | Hiya | Hiya | — | **no sub-city in the place table** | 1 | 8 |
| jacros | Jacros | ጃክሮስ | — | **no sub-city in the place table** | 1 | 0 |
| arada | Arada | Arada | Arada | likely | 1 | 0 |
| bole_medhanialem | Bole Medhanialem | Bole Medhanialem | Bole | owner's rule (16 Nov 2026) | 1 | 1 |
| lideta | Lideta | ልደታ | Lideta | likely | 1 | 0 |
| 6kilo | Sidist Kilo | 6ኪሎ | Gulele | check: near a sub-city border (Gulele–Arada) | 1 | 0 |
| figa_mebrat | Figa Mebrat | Figa mebrat | Lemi Kura | owner's rule (16 Nov 2026) | 1 | 1 |
| wesen | Wesen | ወሰን | Lemi Kura | owner's rule (16 Nov 2026) | 1 | 1 |
| stadium | Stadium | STADIUM | Arada | check: near a sub-city border (Kirkos–Arada) | 1 | 0 |
| bisrate_gabriel | Bisrate Gabriel | (from the topic title) | — | **no sub-city in the place table** | 0 | 1 |
| bole_michael | Bole Michael | (from the topic title) | Bole | owner's rule (16 Nov 2026) | 0 | 1 |

## Photo pilot (task S41)

The owner decided on 16 November 2026 to read 30 photos from championallsites through the existing Telegram login, with `src/telegram_photo_pilot.py` and its limits (see `CLAUDE.md`). The 30 are chosen evenly from the 7 topics of developers with projects in Bole (Metro's Harmony Loft, Prime's Bole Japan and Wello Sefer, Zeramba's Peaceful, Solta's CityLux, Tewabech's Bole Japan project, Samuel's Flight Deck). Today, 16 November, is a day of the scheduled scrape, so the download waits for 17 November; the results will be added here.

## What the parser extracts now (tasks S36 to S40), and what is left

Task S36 added these fields to `processed_listings`, filled by `src/payment_terms.py` and checked by `tests/test_payment_terms.py`
(wordings from real adverts). They are protected like other parser fields: a value corrected by hand is kept.

| Field | Column | What it holds |
|---|---|---|
| Discount schedule | `discount_schedule` | share paid now : discount, "65:35; 100:20" ("65% ከፍለው 35% ቅናሽ", "For 50% Down payment = 3% Discount") |
| Down payment % | `down_payment_pct` (existing, now read far more often) | the smallest down payment offered below 100% |
| Instalments | `instalment_count`, `instalment_months` | "በ16 ዙር ክፍያ" = 16; "ቀሪውን ክፍያ እስከ 3 ዓመት" = 36 months |
| Payments follow construction | `instalments_follow_construction` | "በግንባታ ሂደት", "payment based on construction progress" (no means not stated) |
| Interest-free | `interest_free` | "ያለምንም ወለድ", "ከወለድ ነፃ", "interest-free" (no means not stated) |
| Months to handover | `handover_months` | "መረከቢያ 2 አመት" = 24, "በ2አመት ከ4ወር ... የሚረከቡት" = 28, "አሁን የሚረከቡት" = 0 |
| Construction progress | `construction_progress_pct` | "97% የደረሱ", or the forum topic's title ("85% ቦሌ ደንበል") |
| Price per m² as written | `price_per_sqm_stated` | "በካሬ 95,000 ብር" |
| Prices by payment option and finish (S37) | `price_options` | every price tied to a way of paying or to two finish levels: "100: 75,000/m²; slow: 115,000/m²; 65: 5,700,000 (81 m²)"; the option is the share paid at once (100 = cash), "slow" (paid over time) or "list" (no option given) |
| Paid at once (S37) | `cash_price_per_sqm`, `cash_price_birr` | "75,000 Birr/sqm — for 100% cash payers", "100% ለሚከፍል ጠቅላላ ዋጋ = 5.3 ሚልዮን" |
| Paid over time (S37) | `instalment_price_per_sqm`, `instalment_price_birr` | "115,000 Birr/sqm — for long-term payers"; the option with the smallest share paid at once; totals are of one unit size |

Rent adverts get none of these (their "ቅድሚያ ክፍያ: የ3 ወር" is a rent advance). "ሙሉ ክፍያ" alone is not read as cash: under a heading
"ቀስ ብሎ ለሚከፍል" it means the total ("ሙሉ ክፍያ 9.3ሚሊዮን"). A discount ("100% ሲከፍሉ = 2.3 ሚልዮን ብር ቅናሽ") is not a price, "5 million in cash"
beside a bank loan is not a cash price, and a single finish level ("only Fully Finished Apartment") is not stored. One correction came with them: the parser used to
treat a down payment and a bank loan as adding up to 100%, so a developer's "5% ቅድመ ክፍያ" became a 95% bank loan. Each is now kept
only as stated; `bank_loan_pct` also reads "45% የባንክ አማራጭ". Comparing the old and new parser on all 6,304 listings: 232 down payments
and 160 bank-loan shares changed (208 down payments were found where the old rule found none), 14 developer flags followed the bank
loan, and no other field changed.

Prices by payment option (S37): comparing old and new parser on all 6,304 listings, no existing field changed; 41 listings got
`price_options` (13 a price per m² paid at once, 8 one paid over time, 17 and 8 such totals of one unit).

One row per unit (S38): `src/listing_units.py` fills the table `listing_units` (listing, unit number, size, bedrooms, payment
option, finish, total price, price per m²) with every unit whose total the advert states, in adverts with 2 or more priced units
(checked by `tests/test_units.py`). It is rebuilt from the stored listings after each scrape (`run_all.py` and the scheduled task
run it). A size times the advert's price per m² is not used: in an advert for several sites the sizes of one site met the price per
m² of another. An old price ("የበፊት ዋጋ = 8.1 ሚልዮን") is not read as a price. The listings themselves did not change.

Handover dates (S39): `handover_date` holds the date an advert states for handover, in the Gregorian calendar, read from the
Ethiopian one ("ሰኔ 30/2019" = 7 July 2027; Meskerem 1 falls on 11 September, or 12 September before a Gregorian leap year) or
from a Gregorian date ("Delivery time … March 09/2028 GC"). The Ethiopian date is used even when the advert adds a conversion,
because one advert converts "ሚያዝያ 30/2018" to 8 April 2026 instead of 8 May. Only dates on a line with a handover word (or the
line after it) count; a tender's or an expo's dates do not. 19 listings have one, between May 2025 and May 2028. A year alone
("2018 ዓ.ም") is not read. When an advert gives a date but no period, `handover_months` is the months from the posting date, if
the post's date is known; none of the 19 has one (they were collected before posting dates were saved), so their months stay
empty until the thesis decides which date to count from.

Developer names (S40): `src/developers.py` holds one name per developer and the spellings that mean it ("ቴምር", "Temer
Properties" and "ተመር" are Temer Real Estate; "ሪያሊቲ ሪልእስቴት" and "reality real estate" are Reality Real Estate). A developer's own
channel names it (TemerApartmentShop), then a forum topic (championallsites' "Legacy_Green Valley" is Legacy), then the post's words.
A name that is also a place or a word counts only beside "real estate" or a project word, so "አያት 49" is no longer Ayat Real Estate
(267 listings lost that wrong name) and "Prime Hotel" is not Prime Real Estate. The old rule's fragments ("everyone has an opinion
about") are gone. Comparing old and new parser on all 6,304 listings: the developer changed on 2,121 (89 spellings on 1,334
listings became 76 names on 2,247), the developer flag on 299, the listing class on 14 (a promotion or not) and the valuation flag
on 5; usable listings and the sale sample did not change. `tests/test_developers.py` checks the rules.

**Still left:**

1. **The photo-only developer posts:** championallsites alone holds 1,043, one topic per project. Reading them with `media_pilot.py`
   (Gemini, free tier) needs the owner's approval for a full run (`CLAUDE.md`).
