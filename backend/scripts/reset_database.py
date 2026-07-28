#!/usr/bin/env python
"""
Reset production database: drop and rebuild from migrations + seeds.

WARNING: This is destructive and removes all data. Only safe when production
has no real users.

Usage:
  CONFIRM_RESET=yes uv run python -m scripts.reset_database
"""

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from alembic.command import upgrade
from alembic.config import Config

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import async_session
from app.db.seed.seed_exercises import upsert_exercises
from app.db.seed.seed_program_templates import seed_program_templates

DROP_RETRY_ATTEMPTS = 5
DROP_RETRY_DELAY_SECONDS = 2


def get_db_connection_details():
    """Parse database URL to extract host, port, database, user, password."""
    parsed = urlparse(settings.DATABASE_URL)
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
    }


def drop_and_recreate_database():
    """Drop and recreate the database, retrying if a live service (ECS task,
    local docker-compose backend, etc.) reconnects between the terminate and
    the drop."""
    details = get_db_connection_details()

    # Connect to postgres default database to drop/create target database
    pg_url = f"postgresql://{details['user']}:{details['password']}@{details['host']}:{details['port']}/postgres"
    engine = create_engine(pg_url, isolation_level="AUTOCOMMIT")

    try:
        last_error: OperationalError | None = None
        for attempt in range(1, DROP_RETRY_ATTEMPTS + 1):
            try:
                with engine.connect() as conn:
                    # Terminate existing connections to the target database
                    conn.execute(
                        text(
                            """
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = :database
                            AND pid <> pg_backend_pid();
                            """
                        ),
                        {"database": details["database"]},
                    )

                    conn.execute(text(f'DROP DATABASE IF EXISTS "{details["database"]}";'))
                    conn.execute(text(f'CREATE DATABASE "{details["database"]}";'))
                    print(f"✓ Database '{details['database']}' dropped and recreated")
                    return
            except OperationalError as e:
                last_error = e
                if attempt < DROP_RETRY_ATTEMPTS:
                    print(
                        f"  Drop attempt {attempt}/{DROP_RETRY_ATTEMPTS} failed "
                        f"(likely a live connection racing the drop), retrying in "
                        f"{DROP_RETRY_DELAY_SECONDS}s..."
                    )
                    time.sleep(DROP_RETRY_DELAY_SECONDS)

        assert last_error is not None
        raise last_error
    finally:
        engine.dispose()


def run_migrations():
    """Run Alembic migrations."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    )
    upgrade(alembic_cfg, "head")
    print("✓ Migrations applied")


async def run_seeds():
    """Run database seeds."""
    async with async_session() as db:
        await upsert_exercises(db)
        print("✓ Exercise seed data upserted")

        await seed_program_templates(db)
        print("✓ Program template seed data upserted")


def require_confirmation():
    """Second, independent confirmation gate — the GitHub workflow's prompt only
    covers runs triggered through it. Anyone running this script directly
    (e.g. locally with prod env vars loaded) must also opt in explicitly."""
    details = get_db_connection_details()
    print("⚠️  This will DROP and rebuild the following database:")
    print(f"    host:     {details['host']}")
    print(f"    database: {details['database']}\n")

    if os.environ.get("CONFIRM_RESET") != "yes":
        print(
            "❌ Refusing to proceed. Set CONFIRM_RESET=yes to confirm you want to " "drop this database.",
            file=sys.stderr,
        )
        sys.exit(1)


async def main():
    """Execute the full reset."""
    require_confirmation()

    try:
        print("Resetting database...\n")

        drop_and_recreate_database()
        run_migrations()
        await run_seeds()

        print("\n✅ Database reset complete!")
    except Exception:
        print("\n❌ Database reset failed:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
