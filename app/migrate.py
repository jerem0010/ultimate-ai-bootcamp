"""Apply versioned SQL migrations to an existing Day 04 database."""
import argparse
import asyncio
import hashlib
import os
from pathlib import Path
import asyncpg

MIGRATIONS = Path(__file__).resolve().parents[1] / "infrastructure/postgres/migrations"


async def migrate(dsn: str):
    conn = await asyncpg.connect(dsn)
    try:
        # Serialize migration runners on this database.
        await conn.execute("SELECT pg_advisory_lock(420005)")
        if not await conn.fetchval("SELECT to_regclass('public.tasks') IS NOT NULL"):
            raise RuntimeError("Missing tasks table: initialize the Day 02 schema first")
        await conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            raw = path.read_bytes()
            checksum = hashlib.sha256(raw).hexdigest()
            previous = await conn.fetchval(
                "SELECT checksum FROM schema_migrations WHERE version=$1", path.name)
            if previous is not None:
                if previous != checksum:
                    raise RuntimeError(f"Applied migration changed: {path.name}")
                print(f"Already applied: {path.name}")
                continue
            sql = raw.decode().strip()
            # Day 04 legacy migration contains its own transaction wrapper.
            if path.name == "004_production_backend.sql":
                if not (sql.startswith("BEGIN;") and sql.endswith("COMMIT;")):
                    raise RuntimeError("Unexpected Day 04 migration format")
                sql = sql[len("BEGIN;"):-len("COMMIT;")].strip()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations(version, checksum) VALUES($1,$2)",
                    path.name, checksum)
            print(f"Applied: {path.name}")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    dsn = os.environ["TEST_DATABASE_URL" if args.test else "DATABASE_URL"]
    if args.test and dsn == os.environ.get("DATABASE_URL"):
        raise RuntimeError("Test database must be separate")
    asyncio.run(migrate(dsn))


if __name__ == "__main__":
    main()
