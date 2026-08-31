"""Celery tasks for durable stale-vector garbage collection."""
from __future__ import annotations

import asyncio
import logging
import uuid

from src.database import session_scope
from src.services.vector_cleanup_service import (
    claim_pending_cleanup_job_ids,
    load_cleanup_job,
    mark_cleanup_attempt,
    mark_cleanup_completed,
    mark_cleanup_failed,
    reset_cleanup_job_to_pending,
)
from src.services.vector_store import vector_store_service
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def process_vector_cleanup_job(job_id: str) -> bool:
    parsed_job_id = uuid.UUID(job_id)

    # Commit the attempt counter before touching Chroma. If the process dies
    # during the external delete, the job remains pending and is retried later.
    async with session_scope() as db:
        job = await load_cleanup_job(db, parsed_job_id)
        if job is None or job.status == "completed":
            return False
        vector_ids = list(job.vector_ids or [])
        await mark_cleanup_attempt(db, parsed_job_id)

    try:
        await vector_store_service.delete_document_ids(vector_ids)
    except Exception as exc:
        async with session_scope() as db:
            await mark_cleanup_failed(db, parsed_job_id, exc)
        return False

    async with session_scope() as db:
        await mark_cleanup_completed(db, parsed_job_id)
    return True


async def load_cleanup_batch(limit: int = 10) -> list[str]:
    async with session_scope() as db:
        job_ids = await claim_pending_cleanup_job_ids(db, limit=limit)
    return [str(job_id) for job_id in job_ids]


async def reset_job_status_on_dispatch_error(job_id: str) -> None:
    async with session_scope() as db:
        await reset_cleanup_job_to_pending(db, uuid.UUID(job_id))


@celery_app.task(name="litreview.cleanup_vectors")
def run_vector_cleanup_job(job_id: str) -> bool:
    return asyncio.run(process_vector_cleanup_job(job_id))


@celery_app.task(name="litreview.drain_vector_cleanup_jobs")
def drain_vector_cleanup_jobs() -> int:
    job_ids = asyncio.run(load_cleanup_batch(limit=10))

    dispatched = 0
    for job_id in job_ids:
        try:
            run_vector_cleanup_job.delay(job_id)
            dispatched += 1
        except Exception:
            asyncio.run(reset_job_status_on_dispatch_error(job_id))
            raise

    return dispatched
