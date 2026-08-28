"""Compare the live Postgres schema against the current SQLAlchemy models and
report any drift (create_all() only creates missing tables -- it never ALTERs
an existing one, so a shared dev DB silently falls behind model changes).

For each drifted table, also prints its row count so you know whether it's
safe to drop-and-let-create_all()-rebuild (0 rows) or needs a real ALTER
migration written by hand (has data).

Usage: .venv/Scripts/python.exe -m scripts.check_schema_drift [DATABASE_URL]
Defaults to the local docker-compose Postgres on port 5434 if no URL is given.
Must run as a module (-m) from the repo root so `src` is importable.
"""
import asyncio
import sys

import asyncpg

from src.database import Base
import src.models.db_models  # noqa: F401 -- registers all models on Base.metadata

DEFAULT_URL = "postgresql://postgres:password@127.0.0.1:5434/litreview"


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    con = await asyncpg.connect(url)
    try:
        found_drift = False
        for table in Base.metadata.sorted_tables:
            tname = table.name
            exists = await con.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=$1)",
                tname,
            )
            if not exists:
                print(f"{tname}: TABLE MISSING (create_all() will add it on next startup)")
                found_drift = True
                continue

            live_cols = {
                r["column_name"]
                for r in await con.fetch(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=$1",
                    tname,
                )
            }
            model_cols = {c.name for c in table.columns}
            missing_in_db = sorted(model_cols - live_cols)
            extra_in_db = sorted(live_cols - model_cols)
            if missing_in_db or extra_in_db:
                found_drift = True
                count = await con.fetchval(f"SELECT count(*) FROM {tname}")
                safety = "SAFE to drop+recreate" if count == 0 else "HAS DATA -- needs a real ALTER migration"
                print(f"{tname}: rows={count} ({safety})")
                if missing_in_db:
                    print(f"  missing columns (in model, not in DB): {missing_in_db}")
                if extra_in_db:
                    print(f"  extra columns (in DB, not in model): {extra_in_db} -- harmless, SQLAlchemy ignores them")

        if not found_drift:
            print("No schema drift found.")
    finally:
        await con.close()


if __name__ == "__main__":
    asyncio.run(main())
