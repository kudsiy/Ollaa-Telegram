# Thesis data check: off-plan apartments in Bole Sub-City

Thesis topic (owner, 16 November 2026): **"Market-implied discount rates and cash-equivalent prices of off-plan apartments in
Bole Sub-City."** This file shows what the stored data can give that topic today. It uses the stored listings only, as the owner
asked: nothing contacted Telegram. Every number comes from `database/thesis_data_check.py` (read-only), which can be run again:

    venv\Scripts\python.exe database\thesis_data_check.py

State of the database on 16 November 2026: 6,304 stored listings, 1,752 usable (see `DATA_QUALITY.md`).

## In short

- **261 stored adverts are off-plan apartments for sale** (being built, or sold on a developer's payment plan); **85 of them are placed
  in Bole**, but 39 of those are at Ayat, whose sub-city must be checked. 61 more adverts are unclear.
- The payment terms the thesis needs are stated **often for the down payment, rarely for the rest**. In Bole, 62% of off-plan adverts give a down
  payment %, 29% a handover period, 16% a cash or early-payment discount, 14% an instalment plan, 9% a schedule of several
  discounts, and 1 advert ties instalments to construction stages.
- **Only 33 off-plan Bole adverts have both a unit size and a total price stored, and only 8 state a discount schedule.** That is too few
  for a market-implied discount rate model from text alone. Ready Bole apartments with price and size: **92**.
- **None of these payment terms is stored as a field yet** except a down payment % and a bank-loan %, which the parser fills for
  some listings. The parser should start extracting them (see the end).
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
| **Off-plan** (being built or sold on a developer's plan) | **261** | 166 | 69 |
| Unclear (off-plan words and finished-building words) | 61 | 51 | 25 |
| Ready (no off-plan words) | 510 | 404 | 215 |

| Off-plan adverts | Count |
|---|---|
| Stored place in Bole sub-city | **85** |
| Naming a Bole place anywhere in the text (a developer often lists several sites) | 92 |
| Stored place in another sub-city | 112 |
| Stored place without a sub-city in the place table | 39 |
| No place found | 25 |

Of the 85 off-plan adverts placed in Bole, 39 are at Ayat (Ayat or Ayat 49), whose sub-city should be checked (see the last table); the others: bole_main 25, haya_hulet 10, bole_bulbula 8, bole_adeyabeba 1, bole_michael 1, bole_medhanialem 1.

Off-plan adverts by the sub-city of their stored place: Bole 85, (none) 64, Kirkos 39, Yeka 30, Nifas Silk 20, Arada 20, Sheger 1, Kolfe 1, Akaki 1.

Not counted above: 3,721 photo-only posts, whose words are in the picture; 1,043 of them are in championallsites and 1,254 are in a forum topic or name a developer.

## What the off-plan adverts state

| Field | All off-plan (261) | Off-plan in Bole (85) | Usable off-plan |
|---|---|---|---|
| Developer or project name | 170 (65%) | 39 (46%) | 103 |
| Unit size and total price (both stored) | 86 (33%) | 33 (39%) | 78 |
| …of which the total price is written as a total | 29 (11%) | 7 (8%) | 29 |
| Down payment as a % | 179 (69%) | 53 (62%) | 107 |
| Down payment, any form (% or amount) | 193 (74%) | 57 (67%) | 119 |
| Instalment plan | 54 (21%) | 12 (14%) | 46 |
| Instalments linked to construction stages | 7 (3%) | 1 (1%) | 7 |
| Handover date or period | 71 (27%) | 25 (29%) | 35 |
| Cash or early-payment discount | 48 (18%) | 14 (16%) | 38 |
| Discount schedule (2 or more discount rates) | 16 (6%) | 8 (9%) | 13 |
| Price per m² written in the advert | 66 (25%) | 28 (33%) | 50 |

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

**Price per m² written in the advert**

- 220 (brokercom11, bole_main): “ሣር ቤት ላይ 35% ቅናሽ❗️ ✅ መሀል ሣር ቤት ላይ በካሬ 71,500 - 78,000 ብር ብቻ❗️ ✅ የማስታወቂያ ሽያጭ ባለ 1 መኝታ ✅ 80.7ካሬ = 5,770,0”
- 1106 (TemerApartmentShop, ayat_zone): “ዋጋ = 6.6 ሚልዮን 100% ለሚከፍል 🏦 ጠቅላላ ዋጋ = 10 ሚልዮን ቀስ እያለ 10% ለሚከፍል ⭐ በካሬ ዋጋ 95,000 ብር ቀስ እያለ ለሚከፍል ⭐ በካሬ ዋጋ 61,750 ብር 100% ለሚከፍል ለበለጠ መረጃ 09-”
- 1210 (championrealestate, bole_main): “ሜርሻል ጀርባ) ዩኒት ኤ 162 ካሬ ሜትር ባለ ሶስት መኝታ 2ኛ እና 6ኛ ፎቅ ለሽያጭ ክፍት ሆነዋል። ◎ ዋጋ በካ.ሜ ብር 80,000 ፊኒሺንግን ጨምሮ ◎ ጠቅላላ ዋጋ ብር 12,960,000 ◎ የመጀመሪያ ቅድመ ክፍያ 50% ብር”
- 1329 (ApartmentForYouAyatRealEstate, ayat_zone): “ንቺስ ➾በ 2017 ዓ.ም 43.5 ትርፍ ያስገኘው አክሲዮን ➾የንግድ ሱቆች ሽያጭ!/ Ground Floor ዋጋ በካሬ 👉119,416 ብር G+1 ዋጋ በካሬ 👉165,186 ብር G+2 ዋጋ በካሬ👉 159,953 ብር G+3 ዋጋ በካሬ”
- 1967 (Apartments_store, ayat_zone): “ና ማቆሚያ ያለው 🌴 2 መኝታ - 96.75, 102, 107, 112 ካሬ 🌴 3 መኝታ - 172 ካሬ 💰በካሬ 68,000 🤝15% ቅድመ ክፍያ 💰በካሬ 63,920 🤝30% ቅድመ ክፍያ ለበለጠ፡ ☎<contact>”

## Ready Bole apartments, for comparison

| Bole apartments for sale | Count | usable | in the sale sample |
|---|---|---|---|
| Ready, any | 138 | 111 | 64 |
| **Ready, with price and size** | **92** | 92 | 64 |
| Off-plan, with price and size | 33 | 28 | 23 |
| Unclear, in Bole | 8 | 7 | 5 |
| Government condominiums with price and size (kept apart) | 54 | 54 | 54 |

- Ready Bole apartments: median asking price 130,000 birr per m² over 92 listings (stored total price ÷ stored size; not cleaned for outliers).
- Off-plan Bole apartments: median asking price 95,000 birr per m² over 33 listings (stored total price ÷ stored size; not cleaned for outliers).

## Channels and forum topics with the most off-plan adverts with payment terms

207 of the 261 off-plan adverts state a down payment, an instalment plan or a discount; 61 of them have their stored place in Bole.

| Channel or group | Off-plan with payment terms | of them in Bole |
|---|---|---|
| TemerApartmentShop | 72 | 10 |
| luxury_freelancers | 38 | 18 |
| giftrealestateee | 25 | 8 |
| ApartmentForYouAyatRealEstate | 19 | 12 |
| Apartments_store | 13 | 7 |
| menoriarealestatesalesconsultant | 12 | 0 |
| jamborealestat | 7 | 2 |
| Temerproperties2m | 5 | 1 |
| championrealestate | 5 | 1 |
| brokercom11 | 4 | 1 |
| dmcrealestateofficial | 2 | 0 |
| jamborealestate | 2 | 1 |
| ETHIOhouseagents | 1 | 0 |
| Bamaconrealestateplc | 1 | 0 |
| condoaddis | 1 | 0 |

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
| ayat_zone | Ayat | አያት, Ayat, በአያት | Bole | check: a large area at the Bole–Yeka border | 63 | 33 |
| bole_main | Bole | ቦሌ, Bole, bole | Bole | check: may mean the whole sub-city or Bole Road | 46 | 29 |
| cmc_michael | CMC | CMC, በሲኤምሲ, ሲኤምሲ | Yeka | check: near a sub-city border (Yeka–Bole) | 31 | 15 |
| piassa | Piassa | Piassa, ፒያሳ, በፒያሳ | Arada | likely | 29 | 22 |
| sarbet_old_airport | Sarbet / Old Airport | ሳርቤት, sarbet, Sarbet | Nifas Silk | check: near a sub-city border (Nifas Silk–Kolfe–Kirkos) | 28 | 16 |
| kazanchis | Kazanchis | ካዛንቺስ, ካሳንቺስ, በካዛንቺስ | Kirkos | likely | 24 | 15 |
| megenagna | Megenagna | መገናኛ, Megenagna, በመገናኛ | Yeka | check: near a sub-city border (Yeka–Bole) | 21 | 16 |
| awere | Awere | አዋሬ, በአዋሬ | — | **no sub-city in the place table** | 20 | 11 |
| la_gare | La Gare | በለገሃር, ለገሃር, La Gare | Kirkos | likely | 19 | 12 |
| bulgaria | Bulgaria | ቡልጋሪያ, Bulgaria, በቡልጋሪያ | — | **no sub-city in the place table** | 17 | 8 |
| summit | Summit | ሰሚት | — | **no sub-city in the place table** | 17 | 5 |
| ayat_49 | Ayat 49 | አያት 49, በአያት 49, Ayat49 | Bole | check: Ayat, at the Bole–Yeka border | 15 | 9 |
| haya_hulet | Haya Hulet (22) | 22 ማዞሪያ, ሀያሁለት, ሃያሁለት | Bole | check: near a sub-city border (Bole–Yeka) | 13 | 10 |
| mexico | Mexico | Mexico, ሜክሲኮ, በሜክሲኮ | Kirkos | check: near a sub-city border (Kirkos–Lideta) | 13 | 8 |
| garment | Garment | ጋርመንት, Garment | — | **no sub-city in the place table** | 11 | 2 |
| summit_72 | Summit 72 | ሰሚት72, ሰሚት 72 | — | **no sub-city in the place table** | 9 | 15 |
| tafo | Tafo | Tafo, ጣፎ | Lemi Kura | check: at the city edge (Yeka–Lemi Kura–Sheger) | 8 | 0 |
| dembel | Dembel | ደንበል, Dembel, ወደ ደንበል | — | **no sub-city in the place table** | 8 | 0 |
| meskel_flower | Meskel Flower | Meskel Flower, Meskel flower, መስቀል ፍላወር | Kirkos | check: near a sub-city border (Kirkos–Bole) | 7 | 8 |
| yeka | Yeka | የካ, ከየካ, Yeka | Yeka | check: may be a false match inside a longer word | 7 | 1 |
| haile_garment | Haile Garment | Haile Garment, ሀይሌ ጋርመንት, ሃይሌ ጋርመንት | — | **no sub-city in the place table** | 7 | 2 |
| german | German Square | ጀርመን | — | **no sub-city in the place table** | 7 | 8 |
| gelan | Gelan | ገላን, Gelan | Sheger | likely | 6 | 1 |
| figa | Figa | Figa, በፊጋ, ፊጋ | — | **no sub-city in the place table** | 6 | 3 |
| 4kilo | Arat Kilo | አራት ኪሎ, 4 Kilo, 4kilo | Arada | likely | 5 | 2 |
| kality | Kality | ቃሊቲ, Kaliti, Kality | Akaki | likely | 5 | 1 |
| gerji | Gerji | Gerji, ገርጂ | Yeka | check: near a sub-city border (Bole–Yeka) | 4 | 2 |
| bole_atlas | Atlas | Atlas | Bole | check: Atlas is near the Bole–Kirkos border | 4 | 1 |
| imperial | Imperial | Imperial, IMPERIAL, ኢምፔሪያል | Yeka | check: near a sub-city border (Bole–Yeka) | 4 | 2 |
| mekanisa_abo | Mekanisa / Abo Mazoria | mekanisa | Nifas Silk | check: near a sub-city border (Nifas Silk–Kolfe) | 4 | 4 |
| teklehaimanot | Teklehaimanot | Teklehaimanot | — | **no sub-city in the place table** | 3 | 1 |
| lemi_kura | Lemi Kura | በለሚ ኩራ, ለሚኩራ | Lemi Kura | likely | 3 | 0 |
| gotera | Gotera | Gotera, ጎተራ | Nifas Silk | check: near a sub-city border (Kirkos–Nifas Silk) | 3 | 1 |
| bole_bulbula | Bole Bulbula | ቦሌ ቡልቡላ | Bole | likely | 2 | 8 |
| sholla | Shola | ሾላ, Shola | Yeka | check: near a sub-city border (Yeka–Bole) | 2 | 1 |
| lebu | Lebu | ለቡ | Kolfe | check: near a sub-city border (Nifas Silk–Kolfe) | 2 | 1 |
| merkato | Merkato | Merkato, መርካቶ | Addis Ketema | likely | 2 | 0 |
| bambis | Bambis | በባምቢስ, ከባምቢስ | Kirkos | check: near a sub-city border (Kirkos–Bole) | 2 | 1 |
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

"Adverts naming it" counts off-plan and unclear adverts that name the place anywhere; "Stored as the listing's place" counts those
whose stored place it is (it can come from a hashtag or the forum topic's title, so it can be larger). "Sure?" is Claude's own reading
of Addis Ababa's map, not an official source: "likely" places look well inside their sub-city, "check" places are near a border or
wide, and places "with no sub-city in the place table" need one. To correct a sub-city, tell Claude the right one, or change it in
`src/locations.py` (then run `tests/test_locations.py`); the Bole counts change with it, Ayat most of all.

## What the parser should start extracting

For a market-implied discount rate, each advert must give the price of one unit under at least two payment options (for example the
cash price and the instalment price), and when each payment is due. Today the stored fields hold one price and one size per advert.
In order of value for the thesis:

1. **Discount schedule:** pairs of "share paid now → discount", for example "65% ለከፈለ 35% ቅናሽ", "100% ለሚከፍል 20%, 85% 17%,
   70% …", "For 50% down payment 3%, for 100% 6%". This is the most direct measure of the developer's implied rate. New field: a list
   of (paid %, discount %).
2. **Down payment %** (`down_payment_pct` exists but is filled for few listings): read "ቅድመ ክፍያ 20%", "ከ 10% ቅድሚያ ክፍያ ጀምሮ",
   "10% downpayment", and the amount when only an amount is given.
3. **Instalment plan:** number of instalments ("16 ዙር", "14 ዙር ክፍያ"), the period ("እስከ 3 አመት", "በ12 ወር"), the size of each
   ("5% እያንዳንዱ ዙር"), interest-free ("ያለምንም ወለድ"), and whether payments follow construction ("በግንባታ ሂደት", "payment
   based on construction progress"). New fields: count, period in months, linked to construction (yes/no).
4. **Handover period or date:** "መረከቢያ 2 አመት", "በ 18 ወር ቁልፍ የሚረከቡት", "6 ወር የሚረከብ", dates in the Ethiopian calendar
   ("2018 ዓ.ም"), converted to months from the posting date. New field: months to handover.
5. **Price per m², by payment option and finish:** "በካሬ 95,000 ብር ቀስ እያለ ለሚከፍል", "Semi finished 127,000 / full finished
   144,000". New fields: price per m², payment option, finishing level.
6. **Construction progress %:** from the text ("97% የደረሱ") and from luxury_freelancers' topic titles ("85% ቦሌ ደንበል").
7. **One row per unit:** a developer advert usually lists several units (studio 40 m², 2 bedrooms 90 m², 3 bedrooms 121 m², each with
   a total price). Storing each unit with its own size and prices would multiply the usable observations; today only the first is kept.
8. **Developer and project name, normalized:** the `developer` field holds several spellings of one developer ("ሪያሊቲ ሪልእስቴት reality",
   "ሪያሊቲ ሪልስቴት reality", "at reality"); the forum topic title often names the project.

Before the thesis relies on these fields, the photo-only developer posts matter most: championallsites alone holds 1,043, one topic per
project. Reading them with `media_pilot.py` (Gemini, free tier) needs the owner's approval for a full run (`CLAUDE.md`), and would
need the same new fields.
