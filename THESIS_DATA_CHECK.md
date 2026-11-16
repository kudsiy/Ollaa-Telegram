# Thesis data check: off-plan apartments in Bole Sub-City

Thesis topic (owner, 16 November 2026): **"Market-implied discount rates and cash-equivalent prices of off-plan apartments in
Bole Sub-City."** This file shows what the stored data can give that topic today. It uses the stored listings only, as the owner
asked: nothing contacted Telegram. Every number comes from `database/thesis_data_check.py` (read-only), which can be run again:

    venv\Scripts\python.exe database\thesis_data_check.py

State of the database on 16 November 2026: 6,304 stored listings, 1,752 usable (see `DATA_QUALITY.md`).

## In short

- **265 stored adverts are off-plan apartments for sale** (being built, or sold on a developer's payment plan); **83 of them are placed
  in Bole**, but 36 of those are at Ayat, whose sub-city must be checked. 57 more adverts are unclear.
- The payment terms the thesis needs are stated **often for the down payment, rarely for the rest**. In Bole, 61% of off-plan adverts give a down
  payment %, 30% a handover period, 17% a cash or early-payment discount, 14% an instalment plan, 10% a schedule of several
  discounts, and 1 advert ties instalments to construction stages.
- **Only 32 off-plan Bole adverts have both a unit size and a total price stored, and only 8 state a discount schedule.** That is too few
  for a market-implied discount rate model from text alone. Ready Bole apartments with price and size: **96**.
- **Since tasks S36 and S37 the parser stores these terms as fields** (down payment %, discount schedule, instalments, interest-free,
  months to handover, construction progress, price per m² as written, and prices by payment option and finish): see "Stored by the
  parser". Only **9 off-plan Bole adverts** have a discount schedule together with a stored size and total price, and only **7
  off-plan adverts (2 in Bole)** state both a price paid at once and a price paid over time.
- **Since task S38 every priced unit of a multi-unit advert has its own row** (`listing_units`): 42 off-plan apartment adverts give
  205 units (15 adverts and 82 units in Bole), where the listings kept one each. 16 units are priced both paid at once and another
  way, none of them in Bole.
- The largest source of developer adverts, **championallsites, is almost all photos (1,043 of 1,090 posts)**: its prices and payment
  terms are in the pictures, which only the photo reader (`media_pilot.py`, Gemini) could read.

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
| Stored place in Bole sub-city | **83** |
| Naming a Bole place anywhere in the text (a developer often lists several sites) | 91 |
| Stored place in another sub-city | 114 |
| Stored place without a sub-city in the place table | 40 |
| No place found | 28 |

Of the 83 off-plan adverts placed in Bole, 36 are at Ayat (Ayat or Ayat 49), whose sub-city should be checked (see the last table); the others: bole_main 26, haya_hulet 10, bole_bulbula 8, bole_adeyabeba 1, bole_michael 1, bole_medhanialem 1.

Off-plan adverts by the sub-city of their stored place: Bole 83, (none) 68, Kirkos 41, Yeka 30, Nifas Silk 20, Arada 20, Sheger 1, Kolfe 1, Akaki 1.

Not counted above: 3,721 photo-only posts, whose words are in the picture; 1,043 of them are in championallsites and 1,488 are in a forum topic or name a developer.

## What the off-plan adverts state

| Field | All off-plan (265) | Off-plan in Bole (83) | Usable off-plan |
|---|---|---|---|
| Developer or project name | 176 (66%) | 41 (49%) | 108 |
| Unit size and total price (both stored) | 87 (33%) | 32 (39%) | 79 |
| …of which the total price is written as a total | 30 (11%) | 7 (8%) | 30 |
| Down payment as a % | 182 (69%) | 51 (61%) | 109 |
| Down payment, any form (% or amount) | 197 (74%) | 55 (66%) | 122 |
| Instalment plan | 54 (20%) | 12 (14%) | 46 |
| Instalments linked to construction stages | 7 (3%) | 1 (1%) | 7 |
| Handover date or period | 71 (27%) | 25 (30%) | 35 |
| Cash or early-payment discount | 50 (19%) | 14 (17%) | 40 |
| Discount schedule (2 or more discount rates) | 17 (6%) | 8 (10%) | 14 |
| Price per m² written in the advert | 67 (25%) | 27 (33%) | 51 |

### Stored by the parser (tasks S36, S37 and S39)

The same terms as fields of `processed_listings`, filled by `src/payment_terms.py` (stricter than the word counts above, which only show that a term is mentioned):

| Field | Column | All off-plan (265) | Off-plan in Bole (83) |
|---|---|---|---|
| Down payment % | `down_payment_pct` | 186 (70%) | 52 (63%) |
| Discount schedule (share paid : discount) | `discount_schedule` | 29 (11%) | 12 (14%) |
| Number of instalments | `instalment_count` | 10 (4%) | 2 (2%) |
| Instalment period, months | `instalment_months` | 19 (7%) | 1 (1%) |
| Instalments follow construction | `instalments_follow_construction` | 7 (3%) | 1 (1%) |
| Interest-free | `interest_free` | 35 (13%) | 7 (8%) |
| Months to handover | `handover_months` | 49 (18%) | 19 (23%) |
| Handover date (S39) | `handover_date` | 17 (6%) | 6 (7%) |
| Construction progress % | `construction_progress_pct` | 64 (24%) | 33 (40%) |
| Price per m² as written | `price_per_sqm_stated` | 55 (21%) | 20 (24%) |
| Prices by payment option or finish (S37) | `price_options` | 26 (10%) | 9 (11%) |
| Price per m² paid at once | `cash_price_per_sqm` | 10 (4%) | 2 (2%) |
| Price per m² paid over time | `instalment_price_per_sqm` | 7 (3%) | 2 (2%) |
| Total of one unit paid at once | `cash_price_birr` | 9 (3%) | 3 (4%) |
| Total of one unit paid over time | `instalment_price_birr` | 5 (2%) | 3 (4%) |

Off-plan Bole adverts with a discount schedule and a stored size and total price: 9.

Off-plan adverts that state a price paid at once and a price paid over time (per m² or for one unit): 7, 2 of them in Bole: 1106 (ayat_zone) 61,750 against 95,000 birr per m²; 1108 (sarbet_old_airport) 75,000 against 115,000 birr per m²; 1110 (sarbet_old_airport) 75,000 against 110,000 birr per m²; 1123 (ayat_zone) 61,000 against 95,000 birr per m²; 1208 (megenagna) 90,000 against 95,000 birr per m²; 2440 (garment) 77,000 against 110,000 birr per m²; 2441 (sarbet_old_airport) 69,000 against 107,000 birr per m².

### One row per unit (task S38)

`listing_units` holds every unit of a multi-unit advert whose total price the advert states, one row per unit and payment option (`src/listing_units.py`). The listing itself keeps only its first unit.

|  | Adverts | Units | Unit rows (unit × payment option) |
|---|---|---|---|
| All adverts with 2 or more priced units | 78 | 342 | 368 |
| Off-plan apartment adverts | 42 | 205 | 228 |
| Off-plan apartment adverts in Bole | 15 | 82 | 88 |

Units priced both paid at once and another way: 16 in 5 adverts (0 units in off-plan Bole adverts). Units priced both under the 65/35 option and paid over time: 8.

### Five real examples of each (masked; the listing number is the stored id)

**Developer or project name**

- 115 (giftrealestateee, ayat_zone): “#Gift Real Estate # ቅናሽ (9- 20%) #45% የባንክ አማራጭ 💸በ5% ቅድመ ክፍያ አድራሻ - legehare (የድሮ ባቡ”
- 220 (brokercom11, bole_main): “መኪኖች ቻርጅ ማድረጊያ ቦታ የተዘጋጀለት ☞የ24 ሰአት የካሜራ አገልግሎት(CCTV Service ) . . . . TEMER PROPERTIES Create / Construct / Deliver #Temerproperties #Temerrealestate #Teme”
- 1015 (jamborealestate, bole_main): “የወደፊት ቤትዎ በመሃል ቦሌ እየጠበቅዎ ነዉ !!! 19ኛው በሆነዉ ከሚሊንየም አዳራሽ ጀርባ በሚገኘዉ የጃምቦ ሪል ስቴት ቦሌ-3 ፕሮጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!!”
- 1106 (TemerApartmentShop, ayat_zone): “የአከባቢ ፀጥታ እና አቀማመጥ የብዙ ሰው የመኖርያ መንደር በሆነው #አያት ላይ ባለ 3 መኝታ አፓርትመንት ከ #ቴምር ሪልስቴት ከ 35% ልዮ ቅናሽ ጋ ይግዙ ። ለበለጠ መረጃ በቀጥታ አልያም በዋሳፕ <contact> የሳይት ዝርዝር”
- 1210 (championrealestate, bole_main): “📢 የሲቲ ሴንተር ሳይት(ቦሌ ጌቱ ኮሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒ”

**Unit size and total price (both stored)**

- 220 (brokercom11, bole_main; stored 80 m², 5,720,000 birr): “ሣር ቤት ላይ 35% ቅናሽ❗️ ✅ መሀል ሣር ቤት ላይ በካሬ 71,500 - 78,000 ብር ብቻ❗️ ✅ የማስታወቂያ ሽያጭ”
- 1106 (TemerApartmentShop, ayat_zone; stored 108 m², 6,600,000 birr): “ምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት 🏧 ዋጋ እና አከፍፈል 🛌 ባለ 3 መኝታ 108 ካሬ 🏦 ጠቅላላ ዋጋ = 6.6 ሚልዮን 100% ለሚከፍል 🏦 ጠቅላላ ዋጋ = 10 ሚልዮን ቀስ እያለ 10% ለሚከፍል ⭐ በካሬ”
- 1210 (championrealestate, bole_main; stored 162 m², 12,960,000 birr): “ለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,2”
- 1316 (Temerproperties2m, ayat_zone; stored 111 m², 7,936,500 birr): “ቤቶች የወጣ ልዩ ቅናሽ #ከቴምርሪልስቴት 📍አያት ሳይት 65/35 የክፍያ አማራጭ 👉3 መኝታ 111 ካሬ ሙሉ ክፍያ 7,936,500ብር 👉3 መኝት 137ካሬ 9,795,500ብር ሙሉ ክፍያ 📍አያት ፈረስ ቤት 👉2 መኝታ 86ካሬ”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula; stored 123 m², 13,267,320 birr): “የተጠናቀቀ 2. አፓርታማዎቹ ግራዉንድ ፕላስ 3 ፡ በወለል 1 አፓርትመንት ባለ ሁለት መኝታ 105 .8 ካሬ ጠቅላላ ዋጋ =13,267,320 ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር ጠቅላላ ዋጋ = 15,436,740 ቅድሚያ ክፍ”

**Down payment as a %**

- 115 (giftrealestateee, ayat_zone): “#Gift Real Estate # ቅናሽ (9- 20%) #45% የባንክ አማራጭ 💸በ5% ቅድመ ክፍያ አድራሻ - legehare (የድሮ ባቡር ጣብያ) 👁 አያት 👁 ሲምሲ 👁 አትላስ 👁 22 ማዞርያ”
- 1015 (jamborealestate, bole_main): “3 ፕሮጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Loc”
- 1106 (TemerApartmentShop, ayat_zone): “መኝታ / 108ካሬ ,110ካሬ 119 ካሬ እና 121ካሬ 🏦 ሙለ ለሚከፍል 35% ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት 🏧 ዋጋ እና አከፍፈል”
- 1210 (championrealestate, bole_main): “ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25%”
- 1316 (Temerproperties2m, ayat_zone): “ሙሉ ክፍያ 6,669,000ብር ሙሉ ክፍያ 📍ቀስ ብሎ መክፈል ለሚፈልግ 🎯አያት ሳይት 👉3 መኝታ 111ካሬ 10% ቅድመ ክፍያ 1,221,000ብር ሙሉ ክፍያ 12,210,000ብር 👉3መኝታ 137 ካሬ 10% ቅድመ ክፍያ 1,507,000ብ”

**Down payment, any form (% or amount)**

- 115 (giftrealestateee, ayat_zone): “#Gift Real Estate # ቅናሽ (9- 20%) #45% የባንክ አማራጭ 💸በ5% ቅድመ ክፍያ አድራሻ - legehare (የድሮ ባቡር ጣብያ) 👁 አያት 👁 ሲምሲ 👁 አትላስ 👁 22 ማዞርያ”
- 1015 (jamborealestate, bole_main): “ጀክት ባለ 3 መኝታ አፓርትመንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Loc”
- 1106 (TemerApartmentShop, ayat_zone): “መኝታ / 108ካሬ ,110ካሬ 119 ካሬ እና 121ካሬ 🏦 ሙለ ለሚከፍል 35% ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት 🏧 ዋጋ እና አከፍፈል”
- 1210 (championrealestate, bole_main): “ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ”
- 1316 (Temerproperties2m, ayat_zone): “ፍያ 6,669,000ብር ሙሉ ክፍያ 📍ቀስ ብሎ መክፈል ለሚፈልግ 🎯አያት ሳይት 👉3 መኝታ 111ካሬ 10% ቅድመ ክፍያ 1,221,000ብር ሙሉ ክፍያ 12,210,000ብር 👉3መኝታ 137 ካሬ 10% ቅድመ ክፍያ 1,507,000ብ”

**Instalment plan**

- 1015 (jamborealestate, bole_main): “መንቶች ብቻ በተለያየ የካሬ አማራጮች ቀርተዉናል! ይፍጠኑ!!! 📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ ለበለጠ መረጃ የሽያጭ ቢሮዎቻችን ይጎብኙን!! 🗺 Sales Office Locations: 👉Meskel”
- 1106 (TemerApartmentShop, ayat_zone): “ረስ ቤት ✅ ባለ 3 መኝታ / 108ካሬ ,110ካሬ 119 ካሬ እና 121ካሬ 🏦 ሙለ ለሚከፍል 35% ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት”
- 1210 (championrealestate, bole_main): “ኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር 6,480,000 ◎ ሁለተኛ ክፍያ 25% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25% ብር 3,240,000 በአራት ወር ውስጥ”
- 1316 (Temerproperties2m, ayat_zone): “10,500ብር ሙሉ ክፍያ 👉3 መኝታ 108ካሬ 6,669,000ብር ሙሉ ክፍያ 6,669,000ብር ሙሉ ክፍያ 📍ቀስ ብሎ መክፈል ለሚፈልግ 🎯አያት ሳይት 👉3 መኝታ 111ካሬ 10% ቅድመ ክፍያ 1,221,000ብር ሙሉ ክፍያ 12,”
- 1327 (ApartmentForYouAyatRealEstate, bole_bulbula): “3,267,320 ባለ ሶስት መኝታ፡ 123.1 ካሬ ሜትር ጠቅላላ ዋጋ = 15,436,740 ቅድሚያ ክፍያ: አከፋፈል በ12 ወር : 5 ጊዜ ክፍያ ይጠናቀቃል 30% 20% 20% 20% 10% 100% ለበለጠ መረጃ 0”

**Instalments linked to construction stages**

- 1106 (TemerApartmentShop, ayat_zone): “ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግንባታ ፍጥነት 🏧 ዋጋ እና አከፍፈል 🛌 ባለ 3 መኝታ 108 ካሬ 🏦 ጠቅላላ ዋጋ = 6.6 ሚልዮን 100% ለ”
- 1143 (TemerApartmentShop, piassa): “ሚልዮን 👉 ቀሪ 90% የሚከፈለው ✅ ከወለድ ነፃ ለ3 አመት ✅ በ16 ዙር ክፍያ 5% እያንዳንዱ ዙር ✅ በግንባታ ሂደት ✅ ያለምንም ጭማሪ በሀገራችን ብር ብቻ ቀድመው በመደወል ቤትዎ ይምረጡ <contact> / 09-83”
- 1534 (TemerApartmentShop, sarbet_old_airport): “scalation – fixed price guarantee ✔️ Interest-free payment ✔️ Payment based on construction progress ✔️ Trusted developer with proven delivery ✔️ Prime locations”
- 2438 (TemerApartmentShop, kality): “ታ = 153ካሬ = 11.4ሚሊዮን ✅ በረጅም ጊዜ ክፍያ ለሚፈልጉ ደምበኞች 🏦 በ20% ቅድመ ክፍያ (በግንባታ ሂደት ለሚከፍሉ) 👉 106ካሬ = ሙሉ ክፍያ = 12.1ሚሊዮን ቅድመ ክፍያ 20% = 2”
- 2619 (Apartments_store, gerji): “ዩ ልዩ ቅናሽ ጋር እና ሌሎች ብዙ አጓጊ እና ምቹ ሁኔታውችን አመቻችተናል። 💥በ12% ቅድመ ክፍያ ቀሪዉን የግንባታውን ሂደት እያዩ የሚከፍሉት💥 👉👉ገርጂ ሜታ መብራት ►ባለ አንድ መኝታ 66.96 ካሬ ጠቅላላ ዋጋ 4,352”

**Handover date or period**

- 220 (brokercom11, bole_main): “ባለ 3 መኝታ ✅ 139.23 ካሬ = 9,954,750 ✅ በኢትዮጵያ ብር ብቻ ተዋውለው ያለምንም ጭማሪ ቤቶን የሚረከቡበት ✅ በወለል 2 ቤት ብቻ በቅናሽ አቅርበናል! ✅ የዲፕሎማት መቀመጫ በሆነችው ሣር ቤት። ☎️ +251972”
- 1139 (TemerApartmentShop, ayat_zone): “ፍያ = 1 ሚልዮን ብር 📦 ሙሉ ለሚከፍል የ 2.6 ሚልዮን ብር ቅናሽ ከ 1 አመት እስከ 2 አመት ባለው ጊዜ የሚረከቡ በብር ውል ብቻ የሚገዙት ያለምንም ጭማሪ አሁኑኑ ይደውሉልን <contact> /<contact>”
- 1210 (championrealestate, bole_main): “% ብር 3,240,000 በሁለት ወር ውስጥ ◎ የመጨረሻ ክፍያ 25% ብር 3,240,000 በአራት ወር ውስጥ ◎ መረከቢያ 3 ወር ◎ የባለቤትነት ካርታ የተዘጋጀለት <contact>”
- 1963 (Apartments_store, ayat_49): “ብድር አሁን ቅድመ ክፍያ:30% 📍በአያት 49 የአየር መንገድ ሰራተኞች መኖሪያ ጎን 97% የደረሱ አሁን የሚረከቡት ባለ 2 መኝታ: 122ካሬ 7,930,000ብር ጠቅላላ ዋጋ ባለ 3 መኝታ: 143ካሬ እና 156ካሬ”
- 2139 (luxury_freelancers, bole_main): “ቦሌ መድኃኒዓለም 148 ካሬ 22.2mil(100%) 8th Floor 6 ወር የሚረከብ”

**Cash or early-payment discount**

- 118 (giftrealestateee, ayat_zone): “#Gift Real Estate #ጊፍትሪልስቴት #realestate # ቅናሽ (20%) #45% የባንክ አማራጭ 🫴ወቅቱን ባገናዘበ ዋጋ ጥራታቸውን የጠበቁ ቤቶችን በተለያዩ ካሬ አማራጮች አቅርበ”
- 1106 (TemerApartmentShop, ayat_zone): “ion= አያት ፈረስ ቤት ✅ ባለ 3 መኝታ / 108ካሬ ,110ካሬ 119 ካሬ እና 121ካሬ 🏦 ሙለ ለሚከፍል 35% ቅናሽ 🏦 ቀስ እያለ ለሚከፍል ቅድመ ክፍያ 10% 🔑 መረከብያ 2 አመት 👉አከፋፈል ያለምንም ወለድ እና ጭማሪ በግን”
- 1332 (ApartmentForYouAyatRealEstate, ayat_zone): “ምኘታ 140,160 ካሬዎች ተጨማሪ የሰራተኛ ምኘታ ቤት አላቸው ልዩ ቅናሽ 100%----ለከፈለ---20% ቅናሽ 85%-----ለከፈለ----17 %ቅናሽ 70%-----ለከፈለ ----14%ቅናሽ 55%----ለከፈለ-------11”
- 1963 (Apartments_store, ayat_49): “እና 156ካሬ 💥ዋጋ: 12,727,000ብር እና 13,884,000ብር 🌟ቅናሽ ቅድመ ክፍያ: 50% ለሚከፍል 2% ቅናሽ ቅድመ ክፍያ: 100% ለሚከፍል 5% ቅናሽ 👌🏾ህንፃው ያካተተው የጂም እና ሙሉ የስፓ አገልግሎት የተሟላለት”
- 2172 (luxury_freelancers, bole_bulbula): “tate ⚡️Discount Update for the apartments !⚡️ For 50% Down payment= 3% Discount from the total amount For 100% Down payment= 6% Discount from the t”

**Discount schedule (2 or more discount rates)**

- 1127 (TemerApartmentShop, ayat_zone): “አልያም በ ዋሳፕ ይደውሉልን 👉 የተለያዩ የክፍያ አማራጭ 1ኛ አከፋፈል 65/35 አከፋፈል 65% ከፍለው 35% ቅናሽ በነፃ 2ኛ አከፋፈል 40% ከፍለው 20% ቅናሽ እና የ 8 ወር እፎይታ ጊዜ 3ተኛ አከፋፈል 10% ቅድመ ክ”
- 1332 (ApartmentForYouAyatRealEstate, ayat_zone): “ምኘታ 140,160 ካሬዎች ተጨማሪ የሰራተኛ ምኘታ ቤት አላቸው ልዩ ቅናሽ 100%----ለከፈለ---20% ቅናሽ 85%-----ለከፈለ----17 %ቅናሽ 70%-----ለከፈለ ----14%ቅናሽ 55%----ለከፈለ-------11”
- 1963 (Apartments_store, ayat_49): “እና 156ካሬ 💥ዋጋ: 12,727,000ብር እና 13,884,000ብር 🌟ቅናሽ ቅድመ ክፍያ: 50% ለሚከፍል 2% ቅናሽ ቅድመ ክፍያ: 100% ለሚከፍል 5% ቅናሽ 👌🏾ህንፃው ያካተተው የጂም እና ሙሉ የስፓ አገልግሎት የተሟላለት”
- 2172 (luxury_freelancers, bole_bulbula): “tate ⚡️Discount Update for the apartments !⚡️ For 50% Down payment= 3% Discount from the total amount For 100% Down payment= 6% Discount from the t”
- 2562 (realityaddisababa, dembel): “ላይ በሚገኘው አዲሱ ፕሮጀክታችን ላይ ልዩ ቅናሽ ይዘን መተናል! እስከ ነሐሴ 5 ድረስ ቅድመ ክፍያ ሲከፍሉ 7% ቅናሽ ያገኛሉ፣ ሙሉ ክፍያ የሚፈጽሙ ከሆነ ደግሞ የ27% ቅናሽ ይኖሮታል። ይህም ማለት በካሬ በ83,950 ብር ብቻ”

**Price per m² written in the advert**

- 220 (brokercom11, bole_main): “ሣር ቤት ላይ 35% ቅናሽ❗️ ✅ መሀል ሣር ቤት ላይ በካሬ 71,500 - 78,000 ብር ብቻ❗️ ✅ የማስታወቂያ ሽያጭ ባለ 1 መኝታ ✅ 80.7ካሬ = 5,770,0”
- 1106 (TemerApartmentShop, ayat_zone): “ዋጋ = 6.6 ሚልዮን 100% ለሚከፍል 🏦 ጠቅላላ ዋጋ = 10 ሚልዮን ቀስ እያለ 10% ለሚከፍል ⭐ በካሬ ዋጋ 95,000 ብር ቀስ እያለ ለሚከፍል ⭐ በካሬ ዋጋ 61,750 ብር 100% ለሚከፍል ለበለጠ መረጃ 09-”
- 1210 (championrealestate, bole_main): “ሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር”
- 1329 (ApartmentForYouAyatRealEstate, ayat_zone): “ንቺስ ➾በ 2017 ዓ.ም 43.5 ትርፍ ያስገኘው አክሲዮን ➾የንግድ ሱቆች ሽያጭ!/ Ground Floor ዋጋ በካሬ 👉119,416 ብር G+1 ዋጋ በካሬ 👉165,186 ብር G+2 ዋጋ በካሬ👉 159,953 ብር G+3 ዋጋ በካሬ”
- 1972 (Apartments_store, ayat_49): “#ቅናሹእንደቀጠለነው 💥ዋጋ: 65,000/በካሬ 💥3,770,000 ብር በ15 ዓመት በድርጅቱ በኩል በተመቻቸ የባንክ ብድር የሚከፈል አሁን ቅድመ ክፍያ:3”

## Ready Bole apartments, for comparison

| Bole apartments for sale | Count | usable | in the sale sample |
|---|---|---|---|
| Ready, any | 143 | 115 | 68 |
| **Ready, with price and size** | **96** | 96 | 68 |
| Off-plan, with price and size | 32 | 27 | 22 |
| Unclear, in Bole | 5 | 4 | 2 |
| Government condominiums with price and size (kept apart) | 54 | 54 | 54 |

- Ready Bole apartments: median asking price 128,713 birr per m² over 96 listings (stored total price ÷ stored size; not cleaned for outliers).
- Off-plan Bole apartments: median asking price 95,000 birr per m² over 32 listings (stored total price ÷ stored size; not cleaned for outliers).

## Channels and forum topics with the most off-plan adverts with payment terms

211 of the 265 off-plan adverts state a down payment, an instalment plan or a discount; 59 of them have their stored place in Bole.

| Channel or group | Off-plan with payment terms | of them in Bole |
|---|---|---|
| TemerApartmentShop | 72 | 10 |
| luxury_freelancers | 38 | 18 |
| giftrealestateee | 26 | 8 |
| ApartmentForYouAyatRealEstate | 19 | 12 |
| menoriarealestatesalesconsultant | 12 | 0 |
| Apartments_store | 10 | 4 |
| jamborealestat | 8 | 3 |
| Temerproperties2m | 5 | 1 |
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
| luxury_freelancers | Ghion Homes ወሎ ሰፈር | 1 | 0 | 6 |
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
| ayat_zone | Ayat | አያት, Ayat, በአያት | Bole | check: a large area at the Bole–Yeka border | 58 | 29 |
| bole_main | Bole | ቦሌ, Bole, bole | Bole | check: may mean the whole sub-city or Bole Road | 48 | 30 |
| cmc_michael | CMC | CMC, በሲኤምሲ, ሲኤምሲ | Yeka | check: near a sub-city border (Yeka–Bole) | 31 | 15 |
| sarbet_old_airport | Sarbet / Old Airport | ሳርቤት, sarbet, Sarbet | Nifas Silk | check: near a sub-city border (Nifas Silk–Kolfe–Kirkos) | 29 | 17 |
| piassa | Piassa | Piassa, ፒያሳ, በፒያሳ | Arada | likely | 28 | 21 |
| kazanchis | Kazanchis | ካዛንቺስ, ካሳንቺስ, በካዛንቺስ | Kirkos | likely | 24 | 15 |
| megenagna | Megenagna | መገናኛ, Megenagna, በመገናኛ | Yeka | check: near a sub-city border (Yeka–Bole) | 20 | 15 |
| awere | Awere | አዋሬ, በአዋሬ | — | **no sub-city in the place table** | 20 | 11 |
| la_gare | La Gare | በለገሃር, ለገሃር, La Gare | Kirkos | likely | 20 | 13 |
| bulgaria | Bulgaria | ቡልጋሪያ, Bulgaria, በቡልጋሪያ | — | **no sub-city in the place table** | 17 | 8 |
| summit | Summit | ሰሚት | — | **no sub-city in the place table** | 17 | 5 |
| haya_hulet | Haya Hulet (22) | 22 ማዞሪያ, ሀያሁለት, ሃያሁለት | Bole | check: near a sub-city border (Bole–Yeka) | 13 | 10 |
| mexico | Mexico | Mexico, ሜክሲኮ, በሜክሲኮ | Kirkos | check: near a sub-city border (Kirkos–Lideta) | 13 | 8 |
| ayat_49 | Ayat 49 | አያት 49, Ayat49, በአያት 49 | Bole | check: Ayat, at the Bole–Yeka border | 13 | 8 |
| garment | Garment | ጋርመንት, Garment | — | **no sub-city in the place table** | 11 | 2 |
| summit_72 | Summit 72 | ሰሚት72, ሰሚት 72 | — | **no sub-city in the place table** | 9 | 15 |
| dembel | Dembel | ደንበል, Dembel, ወደ ደንበል | — | **no sub-city in the place table** | 9 | 1 |
| meskel_flower | Meskel Flower | Meskel Flower, መስቀል ፍላወር, Meskel flower | Kirkos | check: near a sub-city border (Kirkos–Bole) | 8 | 8 |
| tafo | Tafo | Tafo, ጣፎ | Lemi Kura | check: at the city edge (Yeka–Lemi Kura–Sheger) | 8 | 0 |
| yeka | Yeka | የካ, ከየካ, Yeka | Yeka | check: may be a false match inside a longer word | 7 | 1 |
| haile_garment | Haile Garment | Haile Garment, ሀይሌ ጋርመንት, ሃይሌ ጋርመንት | — | **no sub-city in the place table** | 7 | 2 |
| german | German Square | ጀርመን | — | **no sub-city in the place table** | 7 | 8 |
| gelan | Gelan | ገላን, Gelan | Sheger | likely | 6 | 1 |
| figa | Figa | Figa, በፊጋ, ፊጋ | — | **no sub-city in the place table** | 6 | 3 |
| 4kilo | Arat Kilo | አራት ኪሎ, 4 Kilo, 4kilo | Arada | likely | 5 | 2 |
| kality | Kality | ቃሊቲ, Kaliti, Kality | Akaki | likely | 5 | 1 |
| gerji | Gerji | Gerji, ገርጂ | Yeka | check: near a sub-city border (Bole–Yeka) | 4 | 2 |
| imperial | Imperial | Imperial, IMPERIAL, ኢምፔሪያል | Yeka | check: near a sub-city border (Bole–Yeka) | 4 | 2 |
| mekanisa_abo | Mekanisa / Abo Mazoria | mekanisa | Nifas Silk | check: near a sub-city border (Nifas Silk–Kolfe) | 4 | 4 |
| gotera | Gotera | Gotera, ጎተራ | Nifas Silk | check: near a sub-city border (Kirkos–Nifas Silk) | 4 | 1 |
| bole_atlas | Atlas | Atlas | Bole | check: Atlas is near the Bole–Kirkos border | 3 | 0 |
| teklehaimanot | Teklehaimanot | Teklehaimanot | — | **no sub-city in the place table** | 3 | 1 |
| bambis | Bambis | ባምቢስ, በባምቢስ, ከባምቢስ | Kirkos | check: near a sub-city border (Kirkos–Bole) | 3 | 2 |
| lemi_kura | Lemi Kura | በለሚ ኩራ, ለሚኩራ | Lemi Kura | likely | 3 | 0 |
| bole_bulbula | Bole Bulbula | ቦሌ ቡልቡላ | Bole | likely | 2 | 8 |
| sholla | Shola | ሾላ, Shola | Yeka | check: near a sub-city border (Yeka–Bole) | 2 | 1 |
| lebu | Lebu | ለቡ | Kolfe | check: near a sub-city border (Nifas Silk–Kolfe) | 2 | 1 |
| merkato | Merkato | Merkato, መርካቶ | Addis Ketema | likely | 2 | 0 |
| addisu_gebeya | Addisu Gebeya | አዲሱ ገበያ, የአዲሱ ገበያ | — | **no sub-city in the place table** | 2 | 1 |
| bethel | Bethel | Bethel | — | **no sub-city in the place table** | 2 | 2 |
| wello_sefer | Wello Sefer | ወሎ ሰፈር | — | **no sub-city in the place table** | 2 | 3 |
| medhanialem | Medhanialem | መድሃኒዓለም, Medhanialem | — | **no sub-city in the place table** | 2 | 0 |
| salite_mehret | Salite Mehret | Salite Mehret | — | **no sub-city in the place table** | 1 | 1 |
| saris | Saris | saris | Nifas Silk | check: near a sub-city border (Nifas Silk–Akaki) | 1 | 0 |
| kebena | Kebena | kebena | — | **no sub-city in the place table** | 1 | 0 |
| lafto | Lafto | ላፍቶ | Nifas Silk | likely | 1 | 0 |
| atena_tera | Atena Tera | አጠና ተራ | — | **no sub-city in the place table** | 1 | 0 |
| bole_adeyabeba | Bole Adey Abeba | ቦሌ አደይ አበባ | Bole | likely | 1 | 1 |
| hiya | Hiya | Hiya | — | **no sub-city in the place table** | 1 | 8 |
| jacros | Jacros | ጃክሮስ | — | **no sub-city in the place table** | 1 | 0 |
| arada | Arada | Arada | Arada | likely | 1 | 0 |
| bole_medhanialem | Bole Medhanialem | Bole Medhanialem | Bole | likely | 1 | 1 |
| lideta | Lideta | ልደታ | Lideta | likely | 1 | 0 |
| 6kilo | Sidist Kilo | 6ኪሎ | Gulele | check: near a sub-city border (Gulele–Arada) | 1 | 0 |
| figa_mebrat | Figa Mebrat | Figa mebrat | — | **no sub-city in the place table** | 1 | 1 |
| wesen | Wesen | ወሰን | — | **no sub-city in the place table** | 1 | 1 |
| stadium | Stadium | STADIUM | Arada | check: near a sub-city border (Kirkos–Arada) | 1 | 0 |
| bisrate_gabriel | Bisrate Gabriel | (from the topic title) | — | **no sub-city in the place table** | 0 | 1 |
| bole_michael | Bole Michael | (from the topic title) | Bole | likely | 0 | 1 |

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
