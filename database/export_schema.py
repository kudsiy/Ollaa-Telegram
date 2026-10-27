"""
export_schema.py
----------------
Writes database/schema.sql from the live database, and checks that it works.

schema.sql holds the structure only (tables, views, functions, indexes), no data
and no passwords. It is made by pg_dump, so never edit it by hand: change the
live database, then run this script again.

Usage (from the project root):
    venv\\Scripts\\python.exe database\\export_schema.py           # rewrite schema.sql
    venv\\Scripts\\python.exe database\\export_schema.py --check   # prove it rebuilds the live structure
    venv\\Scripts\\python.exe database\\export_schema.py --check --keep   # ...and keep the test database

--check builds a temporary empty database (ollaa_schema_check) from schema.sql,
compares its structure with the live database, and deletes it again.

It uses the administrator login (DB_ADMIN_USER / DB_ADMIN_PASSWORD in .env),
because creating and deleting databases is an admin job.
"""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import psycopg2  # noqa: E402

import settings  # noqa: E402

SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
CHECK_DB = "ollaa_schema_check"
PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")

HEADER = """\
-- ============================================================
-- schema.sql: creates every table, view, materialized view,
-- function, index and constraint of the Ollaa database, empty.
--
-- Made by database/export_schema.py from the live database on {today}.
-- Do not edit by hand. Change the live database, then run
--     venv\\Scripts\\python.exe database\\export_schema.py
-- and prove the result with
--     venv\\Scripts\\python.exe database\\export_schema.py --check
--
-- Use it on a NEW, empty database, for example:
--     createdb -U postgres ollaa_new
--     psql -U postgres -d ollaa_new -v ON_ERROR_STOP=1 -f database\\schema.sql
-- then make ollaa_user (the scripts' login) the owner, with DB_NAME=ollaa_new in .env:
--     venv\\Scripts\\python.exe database\\migrations\\2026_10_27_s9_app_login.py --apply
-- It runs as one transaction: if anything goes wrong, nothing is created.
-- It holds structure only: no data and no passwords.
--
-- Columns that scripts add the first time they run, not yet in the live database:
--   telegram_listings.has_attachment, attachment_type          (src/listener.py)
--   processed_listings.lat, lon, geocode_method,
--     geocode_confidence, geocode_matched_name                 (src/geocoder.py)
--   processed_listings.is_duplicate, duplicate_of              (src/dedup_fast.py)
-- ============================================================
"""


def pg_tool(name: str) -> str:
    exe = PG_BIN / f"{name}.exe"
    return str(exe) if exe.exists() else (shutil.which(name) or name)


def pg_env() -> dict:
    return dict(os.environ, PGPASSWORD=settings.admin_config()["password"])


def dump_structure(dbname: str) -> str:
    result = subprocess.run(
        [pg_tool("pg_dump"), "-h", settings.DB_HOST, "-p", str(settings.DB_PORT), "-U", settings.DB_ADMIN_USER,
         "--schema-only", "--no-owner", "--no-privileges", dbname],
        env=pg_env(), capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"pg_dump failed for {dbname}: {result.stderr.decode(errors='replace').strip()}")
    # On Windows pg_dump turns every \n into \r\n, including inside function bodies
    # that already had \r\n. Undo that once, so the bodies keep their own \r.
    text = result.stdout.decode("utf-8").replace("\r\n", "\n")
    # pg_dump 18 adds \restrict lines with a random key that changes on every run.
    return "\n".join(line for line in text.split("\n")
                     if not line.startswith(("\\restrict", "\\unrestrict")))


def materialized_views(structure: str) -> list[str]:
    return [line.split()[3] for line in structure.split("\n")
            if line.startswith("CREATE MATERIALIZED VIEW ")]


def build_schema_file(structure: str) -> str:
    lines = structure.split("\n")
    # Drop pg_dump's own banner and version lines; the header replaces them.
    while lines and (lines[0].startswith("--") or not lines[0].strip()):
        lines.pop(0)
    body = "\n".join(line.replace("; Owner: -", "") for line in lines)
    body = body.replace("SET row_security = off;\n", "SET row_security = off;\n\nBEGIN;\n", 1)
    refresh = "".join(f"REFRESH MATERIALIZED VIEW {mv};\n" for mv in materialized_views(structure))
    body = body.replace("-- PostgreSQL database dump complete\n--\n",
                        "-- Fill the materialized views (empty until data is loaded)\n--\n\n"
                        + refresh + "\nCOMMIT;\n", 1)
    assert "BEGIN;" in body and "COMMIT;" in body, "pg_dump output changed shape; update build_schema_file"
    return HEADER.format(today=date.today().isoformat()) + "\n" + body.rstrip("\n") + "\n"


def maintenance_connection():
    conn = psycopg2.connect(**settings.admin_config("postgres"))
    conn.autocommit = True
    return conn


def check(keep: bool) -> bool:
    assert CHECK_DB != settings.DB_NAME, "the check database must never be the live one"
    conn = maintenance_connection()
    cur = conn.cursor()
    cur.execute("SELECT datcollate, datctype FROM pg_database WHERE datname = %s", (settings.DB_NAME,))
    collate, ctype = cur.fetchone()
    cur.execute(f'DROP DATABASE IF EXISTS "{CHECK_DB}"')
    cur.execute(f"CREATE DATABASE \"{CHECK_DB}\" TEMPLATE template0 ENCODING 'UTF8' "
                f"LC_COLLATE '{collate}' LC_CTYPE '{ctype}'")
    try:
        load = subprocess.run(
            [pg_tool("psql"), "-h", settings.DB_HOST, "-p", str(settings.DB_PORT), "-U", settings.DB_ADMIN_USER,
             "-d", CHECK_DB, "-q", "-v", "ON_ERROR_STOP=1", "-f", str(SCHEMA_FILE)],
            env=pg_env(), capture_output=True, text=True, encoding="utf-8",
        )
        if load.returncode != 0:
            print(f"FAILED: schema.sql did not load into an empty database:\n{load.stderr.strip()}")
            return False
        print("OK      schema.sql loads into an empty database without errors")

        live, rebuilt = dump_structure(settings.DB_NAME), dump_structure(CHECK_DB)
        if live != rebuilt:
            diff = difflib.unified_diff(live.split("\n"), rebuilt.split("\n"), "live", "rebuilt", lineterm="")
            print("FAILED: the rebuilt structure differs from the live database:")
            print("\n".join(list(diff)[:80]))
            return False
        counts = {kind: sum(1 for line in live.split("\n") if line.startswith(f"CREATE {kind} "))
                  for kind in ("TABLE", "VIEW", "MATERIALIZED VIEW", "FUNCTION", "INDEX", "SEQUENCE")}
        print("OK      rebuilt structure is identical to the live database "
              f"({', '.join(f'{n} {k.lower()}' for k, n in counts.items())})")
        return True
    finally:
        if keep:
            print(f"kept test database {CHECK_DB}")
        else:
            cur.execute(f'DROP DATABASE IF EXISTS "{CHECK_DB}"')
            print(f"removed test database {CHECK_DB}")
        conn.close()


def main() -> None:
    if "--check" in sys.argv:
        sys.exit(0 if check(keep="--keep" in sys.argv) else 1)
    # Bytes, not text: keep the \r inside function bodies exactly as in the database.
    SCHEMA_FILE.write_bytes(build_schema_file(dump_structure(settings.DB_NAME)).encode("utf-8"))
    print(f"wrote {SCHEMA_FILE.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
