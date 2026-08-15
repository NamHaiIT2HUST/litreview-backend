import asyncio
import json
import os
import time
import uuid

os.environ.setdefault("PYTHONWARNINGS", "ignore")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

from sqlalchemy import delete, select

from src.database import session_scope
from src.models.db_models import (
    GenericEvidenceCache,
    LLMCallLog,
    Paper,
    Project,
    SynthesisMetrics,
    SynthesisSession,
    SynthesisStatus,
)
from src.services.research_question_policy import GENERAL_LITERATURE_REVIEW_OBJECTIVE
from src.services.synthesis_llm_service import synthesis_llm_service
from src.synthesis.graph import build_synthesis_graph
from src.services.synthesis_service import synthesis_service


async def run_one(label: str, paper_ids: list[uuid.UUID], project_id: uuid.UUID):
    async with session_scope() as db:
        session = SynthesisSession(
            project_id=project_id,
            paper_ids=[str(item) for item in paper_ids],
            research_question=GENERAL_LITERATURE_REVIEW_OBJECTIVE,
            status=SynthesisStatus.processing,
        )
        db.add(session)
        await db.flush()
        session_id = session.id
    started = time.perf_counter()
    error = None
    try:
        await build_synthesis_graph().ainvoke({"session_id": str(session_id)})
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        # Graph branches may still be unwinding after a SQLite lock; status is
        # reported from the persisted row without introducing another write.
    wall_ms = int((time.perf_counter() - started) * 1000)
    async with session_scope() as db:
        logs = list((await db.execute(select(LLMCallLog).where(LLMCallLog.session_id == session_id))).scalars())
        metrics = (await db.execute(select(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id))).scalar_one_or_none()
        row = (await db.execute(select(SynthesisSession).where(SynthesisSession.id == session_id))).scalar_one()
    by_stage = {}
    for log in logs:
        item = by_stage.setdefault(log.step_name, {"calls": 0, "duration_ms": 0, "prompt_chars": [], "response_chars": []})
        item["calls"] += 1
        item["duration_ms"] += int(log.duration_ms or 0)
        item["prompt_chars"].append(len(json.dumps(log.prompt_json or {}, ensure_ascii=False)))
        item["response_chars"].append(len(json.dumps(log.response_json or {}, ensure_ascii=False)))
    print(json.dumps({
        "label": label, "session_id": str(session_id), "status": row.status.value,
        "error": error, "wall_ms": wall_ms, "llm_calls": len(logs), "by_stage": by_stage,
        "metrics": ({
            "duration_ms": metrics.synthesis_duration_ms, "input_tokens": metrics.total_input_tokens,
            "output_tokens": metrics.total_output_tokens, "cache_hits": metrics.cache_hits,
            "cache_misses": metrics.cache_misses, "grounding_retries": metrics.grounding_retry_count,
            "claim_verification_count": metrics.claim_verification_count, "final_word_count": metrics.final_word_count,
            "citation_coverage": metrics.citation_coverage, "section_metrics": metrics.section_metrics,
        } if metrics else None),
        "concurrency": synthesis_llm_service.concurrency_snapshot(),
    }, default=str))
    return session_id


async def main():
    async with session_scope() as db:
        reference = (await db.execute(select(SynthesisSession).where(
            SynthesisSession.id == uuid.UUID("9fa6e30c-268b-4031-895c-be040002b98f")
        ))).scalar_one()
        paper_ids = [uuid.UUID(value) for value in reference.paper_ids]
        papers = list((await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))).scalars())
        project_id = papers[0].project_id
        if os.getenv("BENCHMARK_WARM_ONLY") != "1":
            await db.execute(delete(GenericEvidenceCache))
            await db.commit()
    if os.getenv("BENCHMARK_WARM_ONLY") != "1":
        await run_one("cold", paper_ids, project_id)
    await run_one("warm", paper_ids, project_id)


if __name__ == "__main__":
    asyncio.run(main())
