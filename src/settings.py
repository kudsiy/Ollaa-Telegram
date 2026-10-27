"""
settings.py
-----------
The one place where passwords, keys and connection details are read.

Values come from the .env file in the project root, which is never committed.
.env.example lists every setting. Scripts import what they need, e.g.:

    from settings import DB_URL       # SQLAlchemy
    from settings import DB_CONFIG    # psycopg2.connect(**DB_CONFIG)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is missing. Add it to {ENV_FILE} "
            f"(copy .env.example to .env if the file does not exist)."
        )
    return value


# ── PostgreSQL ────────────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "ollaa")
# The everyday login: owns the Ollaa tables but is not a superuser (task S9).
DB_USER = os.getenv("DB_USER", "ollaa_user")
DB_PASSWORD = require_env("DB_PASSWORD")
# The administrator login: only for backups and database/export_schema.py.
DB_ADMIN_USER = os.getenv("DB_ADMIN_USER", "postgres")
DB_ADMIN_PASSWORD = os.getenv("DB_ADMIN_PASSWORD", "").strip() or None
# The running script's name, so the database can tell who changed a listing
# (shown in listing_overrides and processing_exclusions reasons).
DB_APP_NAME = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "python"

# Explicit psycopg2 driver: SQLAlchemy 2.1 switched the default to psycopg (v3).
DB_URL = (
    f"postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?application_name={quote_plus(DB_APP_NAME)}"
)

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "host": DB_HOST,
    "port": DB_PORT,
    "application_name": DB_APP_NAME,
}


def admin_config(dbname: str = DB_NAME) -> dict:
    """psycopg2 settings for the administrator login (backups, creating test databases)."""
    password = DB_ADMIN_PASSWORD or (DB_PASSWORD if DB_USER == DB_ADMIN_USER else None)
    if not password:
        raise RuntimeError(f"DB_ADMIN_PASSWORD is missing. Add it to {ENV_FILE}.")
    return dict(DB_CONFIG, dbname=dbname, user=DB_ADMIN_USER, password=password)


# ── Telegram ──────────────────────────────────────────────────────
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_PHONE = os.getenv("TG_PHONE")

# ── Gemini (image text extraction) ────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or None
