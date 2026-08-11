"""Durable garbage collection for stale vector-store records."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db_models import VectorCleanupJob


def _now_utc() -> datetime:
    return datetime.now(UTC)


async def create_vector_cleanup_job(
    db: AsyncSession,
    *,
    paper_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    vector_ids: list[str],
) -> VectorCleanupJob | None:
    """Persist stale vector IDs in the same transaction as ingestion commit."""
    clean_ids = list(dict.fromkeys(vector_ids or []))
    if not clean_ids:
        return None
    job = VectorCleanupJob(
        id=uuid.uuid4(),
        paper_id=paper_id,
        ingestion_id=ingestion_id,
        vector_ids=clean_ids,
        status="pending",
    )
    db.add(job)
    await db.flush()
    return job


async def list_pending_cleanup_job_ids(
    db: AsyncSession,
    *,
    limit: int = 100,
) -> list[uuid.UUID]:
    result = await db.execute(
        select(VectorCleanupJob.id)
        .where(VectorCleanupJob.status == "pending")
        .order_by(VectorCleanupJob.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def load_cleanup_job(db: AsyncSession, job_id: uuid.UUID) -> VectorCleanupJob | None:
    return await db.get(VectorCleanupJob, job_id)


async def mark_cleanup_attempt(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await db.get(VectorCleanupJob, job_id)
    if job is None or job.status == "completed":
        return
    job.attempt_count += 1
    job.last_error = None
    await db.flush()


async def mark_cleanup_completed(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await db.get(VectorCleanupJob, job_id)
    if job is None:
        return
    job.status = "completed"
    job.last_error = None
    job.completed_at = _now_utc()
    await db.flush()


async def mark_cleanup_failed(db: AsyncSession, job_id: uuid.UUID, exc: BaseException) -> None:
    job = await db.get(VectorCleanupJob, job_id)
    if job is None or job.status == "completed":
        return
    # Keep the job pending so periodic draining can retry it later.
    job.status = "pending"
    job.last_error = f"{type(exc).__name__}: {exc}"[:4000]
    await db.flush()
