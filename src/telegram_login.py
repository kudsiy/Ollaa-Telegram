r"""
telegram_login.py
-----------------
The one careful Telegram login, made by hand by the owner (owner's decision, 30 October
2026). Only the owner runs it, in a terminal; never a script or an assistant.

It asks for the phone number (twice), the code Telegram sends to the Telegram app, and the
two-step password if the account has one. Everything is typed hidden: nothing shows on
the screen, and nothing typed is printed or saved. It creates only the login file the
scraper and the listener use (data/sessions/ollaa_session.session) and does nothing
else: no messages are read, no channels joined. The only requests are Telethon's own
login steps.

Safety (see "Telegram account safety" in CLAUDE.md):
- it refuses if a login file already exists, while the scraper or the listener runs
  (same lock), or while Telegram use is blocked after a warning;
- the number must be typed the same twice and match TG_PHONE in .env, so a code is never
  sent to someone else's phone;
- the login is made under a temporary name and becomes the login file only once it has
  fully worked, so a failed attempt leaves nothing behind;
- any warning from Telegram stops it and blocks Telegram use, as for the scraper;
- afterwards Telegram use is blocked until the next midnight and for at least 12 hours,
  so the scraper and the listener cannot start on the day of the login.
tests/test_telegram_login.py checks all of this without connecting to Telegram.

Usage (the owner, in CMD):
    cd /d C:\Projects\Ollaa-Telegram
    venv\Scripts\python.exe src\telegram_login.py
"""

import asyncio
import getpass
import logging
import re
import sys

from telethon import TelegramClient
from telethon.errors import (PasswordHashInvalidError, PhoneCodeExpiredError, PhoneCodeInvalidError,
                             PhoneNumberInvalidError, PhoneNumberUnoccupiedError, RPCError,
                             SessionPasswordNeededError)

import telegram_safety as safety
from settings import TG_PHONE

TRIES = 3                 # wrong codes or passwords allowed before stopping
AFTER_LOGIN_HOURS = 12    # no scraper or listener for at least this long after the login

ask = getpass.getpass     # hidden typing (the tests replace it)
logging.getLogger("telethon").setLevel(logging.ERROR)


def digits(text) -> str:
    return re.sub(r"\D", "", text or "")


def in_progress_file():
    return safety.STATE_DIR / "login_in_progress.session"


def remove(path) -> None:
    for p in (path, path.with_name(path.name + "-journal")):
        p.unlink(missing_ok=True)


def ask_phone() -> str:
    phone = ask("Your phone number with country code, for example +2519...  (hidden): ").strip()
    again = ask("The same number again (hidden): ").strip()
    if digits(phone) != digits(again):
        raise safety.SafetyStop("The two numbers are not the same. Nothing was sent to Telegram; run the login again.")
    if not phone.startswith("+") or len(digits(phone)) < 10:
        raise safety.SafetyStop("Type the number with its country code, starting with + (for example +2519...). "
                                "Nothing was sent to Telegram.")
    if TG_PHONE and digits(phone)[-9:] != digits(TG_PHONE)[-9:]:
        raise safety.SafetyStop("This is not the number in .env (TG_PHONE). Nothing was sent to Telegram.")
    return "+" + digits(phone)


async def sign_in(client, phone: str) -> None:
    """Code, then the two-step password if the account has one. Only Telethon's login requests."""
    await client.connect()
    await client.send_code_request(phone)
    print("Telegram has sent a login code to your Telegram app (or by SMS).")
    for attempt in range(1, TRIES + 1):
        code = digits(ask("The login code (hidden): "))
        try:
            await client.sign_in(phone=phone, code=code)
            return
        except PhoneCodeInvalidError:
            print("That code is not right." + (" Try again." if attempt < TRIES else ""))
        except SessionPasswordNeededError:
            break
    else:
        raise safety.SafetyStop(f"The code was wrong {TRIES} times. Nothing was saved; try again tomorrow.")

    print("Your account has two-step verification.")
    for attempt in range(1, TRIES + 1):
        password = ask("Your two-step password (hidden): ")
        try:
            await client.sign_in(password=password)
            return
        except PasswordHashInvalidError:
            print("That password is not right." + (" Try again." if attempt < TRIES else ""))
    raise safety.SafetyStop(f"The password was wrong {TRIES} times. Nothing was saved; try again tomorrow.")


async def main() -> int:
    try:
        target = safety.session_file()
        if target.exists():
            raise safety.SafetyStop(f"A Telegram login file already exists ({target}). Nothing was done: there is "
                                    "only ever one login (see CLAUDE.md).")
        api_id, api_hash = safety.api_credentials()
        with safety.TelegramLock("login"):
            budget = safety.DailyBudget()
            budget.check_not_blocked()
            phone = ask_phone()
            temp = in_progress_file()
            remove(temp)
            client = TelegramClient(str(temp.with_suffix("")), api_id, api_hash,
                                    flood_sleep_threshold=safety.FLOOD_SLEEP_THRESHOLD)
            done = False
            try:
                await sign_in(client, phone)
                done = True
            except PhoneCodeExpiredError:
                raise safety.SafetyStop("The code has expired. Nothing was saved; try again later.")
            except (PhoneNumberInvalidError, PhoneNumberUnoccupiedError):
                raise safety.SafetyStop("Telegram does not know this number. Nothing was saved.")
            except RPCError as e:
                raise safety.stop_after_warning(budget, e, "during the login")
            except (OSError, asyncio.TimeoutError) as e:
                raise safety.SafetyStop(f"Could not reach Telegram ({type(e).__name__}). Nothing was saved; "
                                        "try again later.")
            finally:
                await client.disconnect()   # also closes the file
                if not done:
                    remove(temp)
            target.parent.mkdir(parents=True, exist_ok=True)
            temp.replace(target)
            # 11 hours plus the usual extra hour: at least 12 hours, and at least until midnight
            until = budget.block("a new login was just made: no scraping on the day of the login",
                                 (AFTER_LOGIN_HOURS - 1) * 3600)
    except safety.SafetyStop as e:
        print(f"\nSTOPPED: {e}")
        return 2
    print(f"\nLOGGED IN. The login file is saved as {target}.")
    print("Telegram will show a message about a new login in your app: that is this one.")
    print(f"The scraper and the listener will not use Telegram before {until:%Y-%m-%d %H:%M} (Addis Ababa time).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nLogin cancelled (Ctrl+C). Nothing was saved.")
