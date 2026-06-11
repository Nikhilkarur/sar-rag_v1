"""
clean_db_for_prod.py — wipe the database to a clean slate and rebuild the
schema from Alembic migrations.

    python clean_db_for_prod.py --yes [--seed]

What it does, in order:
  1. Confirms you really mean it (--yes, or interactive y/N prompt).
  2. DROP SCHEMA public CASCADE  — removes every table, index, constraint,
     and the alembic_version bookkeeping row in one shot.
  3. CREATE SCHEMA public        — fresh, empty schema.
  4. alembic upgrade head        — the migrations are the single source of
     truth for the schema; create_all() is never used here.
  5. (--seed) runs seed.py       — minimal login-able state, zero dummy data.

Safety rails:
  * Refuses to run when ENVIRONMENT == "production" unless
    AEGIS_ALLOW_PROD_WIPE=1 is also set.
  * Prints the target database (host/name only, no password) before acting.
"""
import argparse
import os
import subprocess
import sys
from urllib.parse import urlparse

from sqlalchemy import create_engine, text

from app.config import settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Wipe DB and rebuild from Alembic migrations")
    parser.add_argument("--yes", action="store_true", help="skip the interactive confirmation")
    parser.add_argument("--seed", action="store_true", help="run seed.py after rebuilding")
    args = parser.parse_args()

    url = urlparse(settings.DATABASE_URL)
    target = f"{url.hostname}:{url.port or 5432}/{url.path.lstrip('/')}"

    if settings.ENVIRONMENT == "production" and os.environ.get("AEGIS_ALLOW_PROD_WIPE") != "1":
        print("REFUSED: ENVIRONMENT=production. Set AEGIS_ALLOW_PROD_WIPE=1 to override.")
        return 2

    print(f"Target database : {target}")
    print("This will DESTROY every table and row in the 'public' schema.")
    if not args.yes:
        answer = input("Type 'yes' to continue: ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            return 1

    # Use a dedicated engine (no pool reuse) so the DDL runs on a clean connection
    engine = create_engine(settings.DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            print("Dropping schema 'public' ...")
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            print("Schema recreated.")
    finally:
        engine.dispose()

    print("Running alembic upgrade head ...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    if result.returncode != 0:
        print("alembic upgrade FAILED — the database is empty but has no schema.")
        return result.returncode
    print("Schema is at head.")

    if args.seed:
        print("Seeding minimal data ...")
        result = subprocess.run(
            [sys.executable, "seed.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode != 0:
            print("seed.py FAILED.")
            return result.returncode

    print("Done. Database is clean and migration-true.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
