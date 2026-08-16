"""Small aggregate metrics layer built on the existing synthesis audit logs."""
from __future__ import annotations

import uuid
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.models.db_models import Citation, LLMCallLog, SynthesisMetrics


async def get_or_create_metrics(db, session_id: uuid.UUID) -> SynthesisMetrics:
    result = await db.execute(select(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id))
    metrics = result.scalar_one_or_none()
    if metrics is None:
        values = {"id": uuid.uuid4(), "session_id": session_id}
        dialect = db.bind.dialect.name
        if dialect == "postgresql":
            statement = pg_insert(SynthesisMetrics).values(**values).on_conflict_do_nothing(
                index_elements=[SynthesisMetrics.session_id]
            )
        elif dialect == "sqlite":
            statement = sqlite_insert(SynthesisMetrics).values(**values).on_conflict_do_nothing(
                index_elements=[SynthesisMetrics.session_id]
            )
        else:
            # Keep a sensible fallback for other SQLAlchemy dialects.
            db.add(SynthesisMetrics(**values))
            await db.flush()
            return await get_or_create_metrics(db, session_id)

        await db.execute(statement)
        result = await db.execute(select(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id))
        metrics = result.scalar_one()
    return metrics


async def increment_metric(db, session_id: uuid.UUID, field: str, amount: int = 1) -> None:
    metrics = await get_or_create_metrics(db, session_id)
    setattr(metrics, field, int(getattr(metrics, field) or 0) + amount)


async def finalize_metrics(
    db, *, session_id: uuid.UUID, duration_ms: int | None, review_markdown: str,
    factual_sentence_count: int, section_metrics: list[dict] | None = None,
) -> None:
    metrics = await get_or_create_metrics(db, session_id)
    calls = await db.execute(select(func.count()).select_from(LLMCallLog).where(LLMCallLog.session_id == session_id))
    citations = await db.execute(select(func.count()).select_from(Citation).where(Citation.synthesis_session_id == session_id))
    metrics.total_llm_calls = int(calls.scalar_one())
    metrics.synthesis_duration_ms = duration_ms
    metrics.final_word_count = len(review_markdown.split())
    citation_count = int(citations.scalar_one())
    metrics.citation_coverage = (
        min(1.0, citation_count / factual_sentence_count)
        if factual_sentence_count else None
    )
    if section_metrics is not None:
        metrics.section_metrics = section_metrics
    await db.flush()
