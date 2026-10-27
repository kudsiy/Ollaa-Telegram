"""
2026_10_27_s9_app_login.py
--------------------------
One-time change for task S9: the scripts stop using the superuser login.

Makes ollaa_user (not a superuser, cannot create databases or logins) the owner
of every table, view, materialized view, sequence and function in the ollaa
database's public schema, and lets it create tables there. The scripts then log
in as ollaa_user (DB_USER in .env); the postgres login (DB_ADMIN_USER) is only
needed for backups and for database/export_schema.py.

Must run as the postgres login. Take a backup first (see CLAUDE.md).

Usage:
    venv\\Scripts\\python.exe database\\migrations\\2026_10_27_s9_app_login.py          # dry run
    venv\\Scripts\\python.exe database\\migrations\\2026_10_27_s9_app_login.py --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import psycopg2  # noqa: E402
from psycopg2 import sql  # noqa: E402

import settings  # noqa: E402

APP_USER = "ollaa_user"


def main(apply: bool) -> None:
    conn = psycopg2.connect(**settings.admin_config())
    cur = conn.cursor()
    cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    if not cur.fetchone()[0]:
        sys.exit("Run this as the postgres (superuser) login.")
    cur.execute("SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = %s", (APP_USER,))
    if cur.fetchone() != (False, False, False):
        sys.exit(f"{APP_USER} must be an ordinary login (no superuser, createdb or createrole).")

    cur.execute("""
        SELECT c.relkind, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'm')
          AND pg_get_userbyid(c.relowner) <> %s
        ORDER BY c.relkind, c.relname
    """, (APP_USER,))
    kinds = {"r": "TABLE", "v": "VIEW", "m": "MATERIALIZED VIEW"}
    relations = cur.fetchall()
    for kind, name in relations:
        # A table's sequences and indexes change owner with it.
        cur.execute(sql.SQL("ALTER {} public.{} OWNER TO {}").format(
            sql.SQL(kinds[kind]), sql.Identifier(name), sql.Identifier(APP_USER)))
    cur.execute("""
        SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND pg_get_userbyid(p.proowner) <> %s
    """, (APP_USER,))
    functions = [r[0] for r in cur.fetchall()]
    for signature in functions:
        cur.execute(sql.SQL("ALTER FUNCTION {} OWNER TO {}").format(sql.SQL(signature), sql.Identifier(APP_USER)))
    # Scripts run "CREATE TABLE IF NOT EXISTS", which needs this.
    cur.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(sql.Identifier(APP_USER)))

    cur.execute("""
        SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'm', 'S') AND pg_get_userbyid(c.relowner) <> %s
    """, (APP_USER,))
    left = cur.fetchone()[0]
    print(f"new owner {APP_USER}: {len(relations)} tables/views, {len(functions)} functions "
          f"(sequences and indexes follow their tables); objects still owned by someone else: {left}")

    if apply and left == 0:
        conn.commit()
        print("COMMITTED")
    else:
        conn.rollback()
        print("DRY RUN: nothing was changed (use --apply)" if not apply else "ROLLED BACK")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
