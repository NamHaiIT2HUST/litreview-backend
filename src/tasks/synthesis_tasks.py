"""Celery entry point for long-running synthesis sessions."""
from __future__ import annotations

import asyncio
import time
import uuid

from src.database import DATABASE_URL, session_scope
from src.services.synthesis_service import synthesis_service
from src.services.synthesis_metrics_service import get_or_create_metrics
from src.synthesis.graph import build_synthesis_graph
from src.tasks.celery_app import celery_app
from src.tasks.retry_policy import should_retry_synthesis

MAX_SYNTHESIS_RETRIES = 2


def _checkpoint_connection_string(database_url: str) -> str | None:
    """Convert SQLAlchemy async Postgres URL to psycopg-compatible DSN."""
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + database_url[len("postgresql+asyncpg://") :]
    if database_url.startswith("postgresql://"):
        return database_url
    return None


async def run_synthesis_session(session_id: str) -> None:
    """Run one graph attempt.

    This function intentionally does *not* mark the session failed.  A transient
    exception may still be retried by Celery, so terminal status belongs to the
    outer task after the retry budget is exhausted.
    """
    started = time.perf_counter()
    checkpoint_dsn = _checkpoint_connection_string(DATABASE_URL)

    if checkpoint_dsn:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(checkpoint_dsn) as checkpointer:
            # setup() is idempotent and ensures checkpoint migrations exist.
            await checkpointer.setup()
            graph = build_synthesis_graph(checkpointer=checkpointer)
            await graph.ainvoke(
                {"session_id": session_id},
                {"configurable": {"thread_id": session_id}},
            )
    else:
        # SQLite/dev fallback: run without production checkpointer.
        graph = build_synthesis_graph()
        await graph.ainvoke({"session_id": session_id})

    async with session_scope() as db:
        metrics = await get_or_create_metrics(db, uuid.UUID(session_id))
        metrics.synthesis_duration_ms = int((time.perf_counter() - started) * 1000)
        await db.flush()


async def _mark_terminal_failure(session_id: str, exc: BaseException) -> None:
    async with session_scope() as db:
        await synthesis_service.mark_failed(db, uuid.UUID(session_id), exc)


@celery_app.task(
    bind=True,
    name="litreview.run_synthesis",
    max_retries=MAX_SYNTHESIS_RETRIES,
    acks_late=True,
)
def run_synthesis_task(self, session_id: str) -> None:
    try:
        asyncio.run(run_synthesis_session(session_id))
    except Exception as exc:
        retries = int(getattr(self.request, "retries", 0))
        if should_retry_synthesis(
            exc,
            retries=retries,
            max_retries=MAX_SYNTHESIS_RETRIES,
        ):
            # Keep DB status=processing while Celery owns a retry.  Marking it
            # failed here would make the frontend stop polling before recovery.
            raise self.retry(exc=exc, countdown=2 ** retries)

        asyncio.run(_mark_terminal_failure(session_id, exc))
        raise
