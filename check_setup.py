"""
check_setup.py
--------------
Checks that .env is filled in, the database login works and the Gemini key works.
Prints OK / PROBLEM lines and never prints the secrets themselves.

Usage:
    venv\\Scripts\\python.exe check_setup.py
    venv\\Scripts\\python.exe check_setup.py --skip-gemini
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))

problems = 0


def report(ok: bool, label: str, detail: str = "") -> None:
    global problems
    if not ok:
        problems += 1
    print(f"{'OK     ' if ok else 'PROBLEM'}  {label}{': ' + detail if detail else ''}")


report((BASE_DIR / ".env").exists(), ".env file exists")

try:
    import settings
except RuntimeError as e:
    report(False, "settings", str(e))
    sys.exit(1)

# ── Database ──────────────────────────────────────────────────────
try:
    from sqlalchemy import create_engine, text

    engine = create_engine(settings.DB_URL)
    with engine.connect() as conn:
        user = conn.execute(text("SELECT current_user")).scalar()
        rows = conn.execute(text("SELECT COUNT(*) FROM telegram_listings")).scalar()
    report(True, "database login", f"connected as {user}, telegram_listings has {rows:,} rows")
except Exception as e:
    report(False, "database login", type(e).__name__)

# ── Telegram (only checks the values are present) ─────────────────
for name in ("TG_API_ID", "TG_API_HASH", "TG_PHONE"):
    report(bool(getattr(settings, name)), f"{name} is set")

# ── Gemini ────────────────────────────────────────────────────────
if "--skip-gemini" not in sys.argv:
    if not settings.GEMINI_API_KEY:
        report(False, "GEMINI_API_KEY", "empty in .env")
    else:
        # Test with the model extract_images.py actually uses.
        source = (BASE_DIR / "extract_images.py").read_text(encoding="utf-8")
        model_id = re.search(r'^MODEL_ID = "([^"]+)"', source, re.M).group(1)
        try:
            from google import genai

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            names = [m.name for m in client.models.list()]
            report(True, "Gemini key accepted", f"{len(names)} models available")
            reply = client.models.generate_content(model=model_id, contents="Reply with the word OK.")
            report(bool(reply.text), f"Gemini answers with {model_id}")
        except Exception as e:
            # Error text from Google never contains the key, but keep it short.
            report(False, "Gemini", f"{type(e).__name__}: {str(e)[:160]}")

print()
print("All checks passed." if problems == 0 else f"{problems} problem(s) found.")
sys.exit(1 if problems else 0)
