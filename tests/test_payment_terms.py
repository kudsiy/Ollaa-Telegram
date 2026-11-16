r"""
test_payment_terms.py
---------------------
Checks src/payment_terms.py (task S36) on wordings taken from real developer adverts. Never
touches the database.

Usage:
    venv\Scripts\python.exe tests\test_payment_terms.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import payment_terms as pt  # noqa: E402

failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got!r}" + ("" if ok else f" (expected {expected!r})"))


# Down payment: the smallest share below 100%.
check("ቅድመ ክፍያ 20%", pt.down_payment_pct("🏦 ቅድመ ክፍያ 20% = 2.1 ሚልዮን ብር"), 20)
check("ቅድመ ክፍያ (20%) =", pt.down_payment_pct("ቅድመ ክፍያ (20%) = 1,564,000ብር"), 20)
check("ከ 10% ቅድሚያ ክፍያ ጀምሮ", pt.down_payment_pct("📌 ከ 10% ቅድሚያ ክፍያ ጀምሮ በምቹ የአከፋፈል አማራጭ"), 10)
check("በ30% ቅድመክፍያ", pt.down_payment_pct("👉በ30% ቅድመክፍያ"), 30)
check("10% downpayment", pt.down_payment_pct("🔰10% downpayment"), 10)
check("the smallest of several", pt.down_payment_pct("💰በካሬ 68,000 🤝15% ቅድመ ክፍያ\n💰በካሬ 63,920 🤝30% ቅድመ ክፍያ"), 15)
check("100% is a full payment, not a down payment",
      pt.down_payment_pct("ቅድመ ክፍያ: 50% ለሚከፍል 2% ቅናሽ\nቅድመ ክፍያ: 100% ለሚከፍል 5% ቅናሽ"), 50)
check("an amount only", pt.down_payment_pct("👉 ቅድመ ክፍያ = 2.8 ሚልዮን ብር"), None)
check("a rent advance in months", pt.down_payment_pct("🔵 ቅድሚያ ክፍያ: የ3 ወር"), None)

# Discount schedule: share paid -> discount.
check("65% ከፍለው 35% ቅናሽ", pt.discount_schedule("1ኛ አከፋፈል 65/35 አከፋፈል 65% ከፍለው 35% ቅናሽ በነፃ"), "65:35")
check("a ladder", pt.discount_schedule("ልዩ ቅናሽ\n100%----ለከፈለ---20% ቅናሽ\n85%-----ለከፈለ----17 %ቅናሽ\n70%-----ለከፈለ----14% ቅናሽ"),
      "70:14; 85:17; 100:20")
check("English", pt.discount_schedule("For 50% Down payment= 3% Discount from the total amount\nFor 100% Down payment= 6% Discount"),
      "50:3; 100:6")
check("full payment without a %", pt.discount_schedule("🏦 ሙለ ለሚከፍል 35% ቅናሽ"), "100:35")
check("100% ለከፈለ", pt.discount_schedule("🏦 100% ለከፈለ 35% ቅናሽ = 7ሚልዮን ሙሉ ክፍያ"), "100:35")
check("a discount without a share paid", pt.discount_schedule("👉ከ5% - 12% ቅናሽ"), None)
check("a bank share is not a discount", pt.discount_schedule("#45% የባንክ አማራጭ 💸በ5% ቅድመ ክፍያ"), None)

# Instalments.
check("በ16 ዙር ክፍያ", pt.instalment_count("✅ በ16 ዙር ክፍያ 5% እያንዳንዱ ዙር"), 16)
check("5 ጊዜ ክፍያ", pt.instalment_count("አከፋፈል በ12 ወር : 5 ጊዜ ክፍያ ይጠናቀቃል"), 5)
check("an ordinal round is not a count", pt.instalment_count("9ኛ ዙር የመሬት ሊዝ ጨረታ"), None)
check("ቀሪውን ክፍያ እስከ 3 ዓመት", pt.instalment_months("💳 20% ቅድመ ክፍያ\n📆 ቀሪውን ክፍያ እስከ 3 ዓመት"), 36)
check("አከፋፈል በ12 ወር", pt.instalment_months("አከፋፈል በ12 ወር : 5 ጊዜ ክፍያ ይጠናቀቃል"), 12)
check("14 ዙር ክፍያ እስከ 3 አመት", pt.instalment_months("14 ዙር ክፍያ እስከ 3 አመት ድረስ ምንም ዋጋ ጭማሪ"), 36)
check("a handover period is not an instalment period", pt.instalment_months("☑️ መረከብያ 3 አመት\n☑️ ቅድመ ክፍያ = 20%"), None)
check("payments follow construction (Amharic)", pt.instalments_follow_construction("🏦 በ20% ቅድመ ክፍያ (በግንባታ ሂደት ለሚከፍሉ)"), True)
check("payments follow construction (English)", pt.instalments_follow_construction("✔️ Payment based on construction progress"), True)
check("construction alone is not a payment plan", pt.instalments_follow_construction("#Gazebo Skyline current progress"), False)
check("ያለምንም ወለድ", pt.interest_free("👉አከፋፈል ያለምንም ወለድ እና ጭማሪ"), True)
check("ወለድም ሆነ ዋጋ ጭማሪ የለውም", pt.interest_free("* ወለድም ሆነ ዋጋ ጭማሪ የለውም"), True)
check("interest-free", pt.interest_free("✔️ Interest-free payment"), True)
check("a bank loan is not interest-free", pt.interest_free("40% የ ባንክ ብድር የተመቻቸለት"), False)

# Handover.
check("መረከብያ 2 አመት", pt.handover_months("🔑 መረከብያ 2 አመት"), 24)
check("በ 18 ወር ቁልፍ የሚረከቡት", pt.handover_months("👉 መረከብያ = በ 18 ወር ቁልፍ የሚረከቡት"), 18)
check("6 ወር የሚረከብ", pt.handover_months("ቦሌ መድኃኒዓለም 148 ካሬ 22.2mil(100%) 8th Floor 6 ወር የሚረከብ"), 6)
check("from 1 to 2 years", pt.handover_months("ከ 1 አመት እስከ 2 አመት ባለው ጊዜ የሚረከቡ"), 24)
check("handover now", pt.handover_months("97% የደረሱ አሁን የሚረከቡት ባለ 2 መኝታ"), 0)
check("2 years and 4 months", pt.handover_months("10% ቅድመ ክፍያ\nበ2አመት ከ4ወር በግማሽ ግንባታ የሚረከቡት"), 28)
check("Delivery: 18 Months", pt.handover_months("🔑 Down Payment: 40%\n⏳ Delivery: 18 Months"), 18)
check("no handover", pt.handover_months("ቅድመ ክፍያ 20%"), None)

# Construction progress.
check("97% የደረሱ", pt.construction_progress_pct("በአያት 49 97% የደረሱ አሁን የሚረከቡት"), 97)
check("a forum topic", pt.construction_progress_pct("ባለ 3 መኝታ", "85% ቦሌ ደንበል Palm Realestate 40%Bank"), 85)
check("100% ያለቀ topic", pt.construction_progress_pct("", "100% ያለቀ ሰሚት Golden"), 100)
check("a down payment is not progress", pt.construction_progress_pct("20% ቅድመ ክፍያ"), None)

# All together, on one Temer advert.
temer = ("🏦 ቅድመ ክፍያ 20% = 2.1 ሚልዮን ብር\n🏦 100% ለከፈለ 35% ቅናሽ = 7ሚልዮን ሙሉ ክፍያ\n☑️ መረከብያ 3 አመት\n"
         "☑️ ቀሪ ክፍያ ያለምንም ወለድ እና ዋጋ ጭማሪ ይክፈሉ\n14 ዙር ክፍያ እስከ 3 አመት ድረስ ግንባታ እያያቹ የምትከፍሉበት")
check("all terms", pt.extract_terms(temer), {
    "price_options": "100: 7,000,000", "cash_price_per_sqm": None, "instalment_price_per_sqm": None,
    "cash_price_birr": 7000000, "instalment_price_birr": None, "discount_schedule": "100:35", "instalment_count": 14, "instalment_months": 36, "instalments_follow_construction": True,
    "interest_free": True, "handover_months": 36, "handover_date": None, "construction_progress_pct": None})

# Handover dates (S39): the Ethiopian calendar turned into the Gregorian one.
from datetime import date  # noqa: E402

check("Meskerem 1, 2018 is the new year of 2025", pt.ethiopian_to_gregorian(2018, 1, 1), date(2025, 9, 11))
check("before a leap year it falls on 12 September", pt.ethiopian_to_gregorian(2016, 1, 1), date(2023, 9, 12))
check("Timket, Tir 11, 2018", pt.ethiopian_to_gregorian(2018, 5, 11), date(2026, 1, 19))
check("Sene 30, 2019, as the advert converts it", pt.handover_date("📦 Delivery: ሰኔ 30/2019 EC (July 7, 2027 GC)"), date(2027, 7, 7))
check("the Ethiopian date wins over a wrong conversion", pt.handover_date("📦 Delivery: ሚያዝያ 30/2018 (April 8, 2026 GC)"), date(2026, 5, 8))
check("on the line after a handover word", pt.handover_date("-Delivery time for Imperial\nሚያዝያ -30/2018"), date(2026, 5, 8))
check("የማስረከቢያ ቀን and another spelling", pt.handover_date("የማስረከቢያ ቀን :  ሚያዚያ 30/2019"), date(2027, 5, 8))
check("a Gregorian date", pt.handover_date("-Delivery time for semi finished March 09/2028 GC"), date(2028, 3, 9))
check("a tender's dates are not a handover", pt.handover_date("የጨረታ ሰነዱን ማስረከቢያ ከጥር 13/2018 እስከ ጥር 20/2018"), None)
check("an expo's dates are not a handover", pt.handover_date("#ታላቅ የገና ቅናሽ ኤክስፖ (ታህሳስ 15-28/2018)\nየሚረከቡ ቤቶች"), None)
check("a date without a handover word", pt.handover_date("ታህሳስ 15/2018 ጊፍት ሪል ስቴት"), None)

# The months to handover from the posting date, when the advert gives a date and no period (no database used).
from datetime import datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from etl_runner import build_processed_values  # noqa: E402
from run_pipeline import ValuationPipeline as _Pipeline  # noqa: E402

dated = SimpleNamespace(id=1, text="የሚሸጥ አፓርትመንት ከቴምር ሪልስቴት\nቅድመ ክፍያ 20%\n📦 Delivery: ሰኔ 30/2019 EC (July 7, 2027 GC)",
                        channel="https://t.me/x", posted_at=datetime(2026, 11, 16, 10, 0), reply_to_top_id=None, topic_title=None)
values, _, _ = build_processed_values(_Pipeline(), dated)
check("months from the posting date", (values["handover_date"], values["handover_months"]), (date(2027, 7, 7), 8))
values, _, _ = build_processed_values(_Pipeline(), SimpleNamespace(**{**dated.__dict__, "posted_at": None}))
check("no posting date: no months", values["handover_months"], None)

# Prices by payment option and finish (S37).
po = pt.price_options("💰 Special Pricing\n✔️ 75,000 Birr/sqm — for 100% cash payers\n✔️ 115,000 Birr/sqm — for long-term payers")
check("price per m²: cash and long-term", (po["cash_price_per_sqm"], po["instalment_price_per_sqm"]), (75000, 115000))
po = pt.price_options("✅ ባለ 3 መኝታ / 108ካሬ\n🏦 ጠቅላላ ዋጋ = 6.6 ሚልዮን 100% ለሚከፍል\n🏦 ጠቅላላ ዋጋ = 10 ሚልዮን ቀስ እያለ 10% ለሚከፍል\n"
                      "⭐ በካሬ ዋጋ 95,000 ብር ቀስ እያለ ለሚከፍል", 108)
check("totals of one unit, paid at once and over time", (po["cash_price_birr"], po["instalment_price_birr"], po["instalment_price_per_sqm"]),
      (6600000, 10000000, 95000))
temer_65 = ("65/35 አከፍፈል\n👉 2መኝታ 81 ካሬ ሙሉ ክፍያ 5.7ሚሊዮን\n👉2መኝታ 1ዐ6ካሬ ሙሉ ክፍያ 7.9ሚሊዮን 👉3መኝታ 139ካሬሙሉ ክፍያ 1ዐ.3ሚሊዮን\n"
            "ቀስ ብሎ ለሚከፍል\n2መኝታ 81 ካሬ\n20%ቅድመ ክፍያ 1.86ሚሊዮን\nሙሉ ክፍያ 9.3ሚሊዮን")
po = pt.price_options(temer_65, 81)
check("“ሙሉ ክፍያ” under a heading is a total, not cash", (po["cash_price_birr"], po["instalment_price_birr"]), (None, 9300000))
check("two units on one line keep their own sizes", "65: 10,300,000 (139 m²)" in po["price_options"], True)
check("a down payment is not a price", "1,860,000" in po["price_options"], False)
po = pt.price_options("🔰100% በካሬ 86ሺ\n🔰50% በካሬ 90ሺ ቀሪውን በ1አመት")
check("100% በካሬ and 50% በካሬ", (po["cash_price_per_sqm"], po["instalment_price_per_sqm"]), (86000, 90000))
po = pt.price_options("✅  በከፊል ግንባታ በካሬ 99,935 ብር\nበሙሉ ግንባታ በካሬ 132,825 ብር")
check("finish levels", po["price_options"], "list semi-finished: 99,935/m²; list fully finished: 132,825/m²")
check("a resale's cash part beside a bank debt is not a cash price",
      pt.price_options("ጠቅላላ ዋጋ፦ 26,000,000 ብር\nበጥሬ ገንዘብ (Cash)፦ 13.5 ሚሊዮን ብር ብቻ\nየባንክ ዕዳ፦ 12.5 ሚሊዮን ብር")["price_options"], None)
check("one price without an option or finish is not stored", pt.price_options("💰 Price: 115,000 Birr per sqm")["price_options"], None)
check("one finish level alone is not stored", pt.price_options("only Fully Finished Apartment\n137 sqm • 26,999,000 ETB")["price_options"], None)
check("“in cash” beside a bank loan is not a cash price", pt.price_options("30 million total, 5 million in cash, rest bank loan")["price_options"], None)
po = pt.price_options("✅ 100% ለሚከፍል 30% ቅናሽ\n💰 Price: 115,000 Birr per sqm\n👉 1 መኝታ 69 ካሬ\n° ጠቅላላ ዋጋ = 7.9 ሚልዮን ብር\n"
                      "° 100% ሲከፍሉ = 2.3 ሚልዮን ብር ቅናሽ ያገኛሉ")
check("a discount is neither a heading nor a price", (po["price_options"], po["cash_price_birr"]), (None, None))
po = pt.price_options("👉 በአንዴ ለሚከፍል 35% ቅናሽ አግኝተው በካሬ 75ሺ መግዛት ይችላሉ አልያም ቀስ እያሉ በ 3 አመት በካሬ 110ሺ")
check("two options on one line", (po["cash_price_per_sqm"], po["instalment_price_per_sqm"]), (75000, 110000))

# Through the parser: a rent's advance is not a payment plan; a sale keeps its terms.
from run_pipeline import ValuationPipeline  # noqa: E402

pipeline = ValuationPipeline()
rent = pipeline.process({"id": "r", "text": "🔥የሚከራይ የንግድ ቦታ🔥\n🔵 ኪራይ: 50ሺ ብር\n🔵 ቅድሚያ ክፍያ: የ3 ወር + ሲለቀቅ የሚመለስ (የ1 ወር ክፍያ)"})
check("rent: no instalment period", (rent["intent"], rent["instalment_months"]), ("RENT", None))
sale = pipeline.process({"id": "s", "text": "የሚሸጥ አፓርትመንት ከቴምር ሪልስቴት\n" + temer, "topic_title": "90% ሀያሁለት"})
check("sale: terms and the topic's progress", (sale["discount_schedule"], sale["handover_months"], sale["construction_progress_pct"]),
      ("100:35", 36, 90))
check("a stated bank share, no 100% − down payment", (sale["down_payment_pct"], sale["bank_loan_pct"]), (20, None))

print(f"\n{'PASS' if not failures else f'FAILED: {failures} check(s)'}")
sys.exit(1 if failures else 0)
