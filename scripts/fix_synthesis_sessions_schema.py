"""One-time local fix: drop tables whose live Postgres schema has drifted from
the current SQLAlchemy models, so create_all() rebuilds them correctly on the
next backend startup.

create_all() only creates tables that don't exist yet -- it never ALTERs an
existing table to add/remove/retype columns. This shared local Postgres
(litreview-db, port 5434) was created ~2 weeks ago and has since fallen behind
several model changes. Two drifts confirmed and fixed here (2026-08-27):

1. synthesis_sessions.paper_ids was `uuid[]`, model now expects `jsonb`.
2. pdf_chunks was missing columns added by the ingestion-provenance work
   (chunk_index, ingestion_id, page_char_start, page_char_end, page_text_id).

Every table below was verified empty (0 rows) before being added to this
list -- this script re-verifies that at run time and aborts rather than
dropping anything with real data. Run `scripts/check_schema_drift.py` first
if you suspect a *different* table has drifted; don't blindly add tables here
without checking row counts.

Run once: .venv/Scripts/python.exe scripts/fix_synthesis_sessions_schema.py
"""
import asyncio

import asyncpg

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5434/litreview"

# Drop order: dependents first (CASCADE would handle it either way, but
# explicit order makes the intent obvious).
TABLES = [
    # synthesis_sessions family (schema fix #1)
    "claim_evidence_links",
    "synthesis_claims",
    "synthesis_sections",
    "evidence_records",
    "evidence_extraction_attempts",
    "retrieval_logs",
    "llm_call_logs",
    "synthesis_metrics",
    "citations",
    "synthesis_sessions",
    # pdf_chunks family (schema fix #2) -- evidence_records/evidence_extraction_attempts
    # already listed above; generic_evidence_cache_items also FKs to pdf_chunks.
    "generic_evidence_cache_items",
    "pdf_chunks",
]


# My own test session from verifying the paper_ids fix earlier -- not real
# user data, safe to remove before the emptiness check below.
_KNOWN_TEST_SESSION_ID = "1e7977c2-106b-44dd-9699-c9567c0f61d6"


async def main() -> None:
    con = await asyncpg.connect(DATABASE_URL)
    try:
        deleted = await con.execute(
            "DELETE FROM synthesis_sessions WHERE id = $1", _KNOWN_TEST_SESSION_ID
        )
        if deleted != "DELETE 0":
            print(f"removed known test session {_KNOWN_TEST_SESSION_ID}")

        for table in TABLES:
            exists = await con.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename=$1)",
                table,
            )
            if not exists:
                print(f"skip {table} (already gone)")
                continue
            count = await con.fetchval(f"SELECT count(*) FROM {table}")
            if count:
                raise RuntimeError(
                    f"Aborting: {table} has {count} row(s), not empty as expected. "
                    "Investigate before dropping."
                )
        for table in TABLES:
            await con.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"dropped {table}")
    finally:
        await con.close()

    print(
        "\nDone. Restart the backend (uvicorn) once -- create_all() will "
        "rebuild these tables with the correct schema on startup."
    )


if __name__ == "__main__":
    asyncio.run(main())
