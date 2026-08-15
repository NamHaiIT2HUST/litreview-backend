import asyncio
import json
import os
import shutil
import time
import uuid
from pathlib import Path

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

from sqlalchemy import select, text

from src.database import Base, engine, session_scope
from src.models.db_models import (
    GenericEvidenceCache,
    LLMCallLog,
    PageText,
    Paper,
    PDFChunk,
    Project,
    SynthesisClaim,
    SynthesisMetrics,
    SynthesisSection,
    SynthesisSession,
    SynthesisStatus,
)
from src.services.document_processor import DocumentProcessor
from src.services.generic_evidence_cache_service import precompute_generic_evidence
from src.services.ingestion_service import persist_pdf_provenance
from src.services.synthesis_service import synthesis_service
from src.services.synthesis_llm_service import synthesis_llm_service
from src.synthesis.graph import build_synthesis_graph

DESKTOP = Path(r"C:\Users\Hp\Desktop")
RQ = "How have algorithms for the Split Feasibility Problem evolved in terms of problem assumptions, projection mechanisms, convergence guarantees, and computational requirements?"
FILES = [
    "2.-li2012.pdf",
    "3.-2010.04504v1_-SFP-không-lồi.pdf",
    "4.-byrne2002.pdf",
    "5.-xu2010.pdf",
    "6.-xu2018.pdf",
]


async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.get_backend_name() == "sqlite":
            columns = await conn.run_sync(lambda c: [row[1] for row in c.exec_driver_sql("PRAGMA table_info(evidence_records)").fetchall()])
            if "applies_to" not in columns:
                await conn.execute(text("ALTER TABLE evidence_records ADD COLUMN applies_to VARCHAR(80) NOT NULL DEFAULT 'study'"))


async def ingest():
    processor = DocumentProcessor()
    async with session_scope() as db:
        project = Project(id=uuid.uuid4(), name="Set B SFP benchmark", research_question=RQ, research_field="optimization")
        db.add(project)
        await db.flush()
        paper_ids = []
        for filename in FILES:
            source = DESKTOP / filename
            if not source.exists():
                raise FileNotFoundError(source)
            paper = Paper(
                id=uuid.uuid4(), project_id=project.id, title=filename[:-4],
                authors=[], source="direct_upload", dedup_key=f"set-b:{filename}:{uuid.uuid4()}",
                screening_decision="keep",
            )
            db.add(paper)
            await db.flush()
            pages, chunks = processor.extract_and_chunk(str(source))
            ingestion_id = await persist_pdf_provenance(
                db=db, paper=paper, pages=pages, chunks=chunks,
                parser_metadata=processor.parser_metadata(),
            )
            await db.commit()
            # The production vector service is imported separately to keep the same staging path.
            from src.services.vector_store import vector_store_service
            await vector_store_service.stage_documents_for_paper(str(paper.id), chunks)
            paper_ids.append(paper.id)
            print(json.dumps({"ingested": filename, "paper_id": str(paper.id), "pages": len(pages), "chunks": len(chunks), "ingestion_id": str(ingestion_id)}))
    return project.id, paper_ids


async def precompute(paper_ids):
    for paper_id in paper_ids:
        async with session_scope() as db:
            paper = (await db.execute(select(Paper).where(Paper.id == paper_id))).scalar_one()
            started = time.perf_counter()
            await precompute_generic_evidence(db, paper=paper)
            print(json.dumps({"precompute_paper_id": str(paper_id), "duration_ms": int((time.perf_counter()-started)*1000)}))


async def synthesize(project_id, paper_ids):
    async with session_scope() as db:
        session = SynthesisSession(
            id=uuid.uuid4(), project_id=project_id,
            paper_ids=[str(value) for value in paper_ids], research_question=RQ,
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
    wall_ms = int((time.perf_counter()-started)*1000)
    async with session_scope() as db:
        logs = list((await db.execute(select(LLMCallLog).where(LLMCallLog.session_id == session_id))).scalars())
        metrics = (await db.execute(select(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id))).scalar_one_or_none()
        row = (await db.execute(select(SynthesisSession).where(SynthesisSession.id == session_id))).scalar_one()
        claims = list((await db.execute(select(SynthesisClaim).where(SynthesisClaim.synthesis_session_id == session_id))).scalars())
        sections = list((await db.execute(select(SynthesisSection).where(SynthesisSection.synthesis_session_id == session_id).order_by(SynthesisSection.position))).scalars())
        caches = list((await db.execute(select(GenericEvidenceCache).where(GenericEvidenceCache.paper_id.in_(paper_ids)))).scalars())
    by_stage = {}
    for log in logs:
        stage = by_stage.setdefault(log.step_name, {"calls": 0, "duration_ms": 0, "durations_ms": []})
        stage["calls"] += 1; stage["duration_ms"] += int(log.duration_ms or 0); stage["durations_ms"].append(int(log.duration_ms or 0))
    print(json.dumps({
        "session_id": str(session_id), "status": row.status.value, "error": error, "wall_ms": wall_ms,
        "llm_calls": len(logs), "by_stage": by_stage,
        "cache_statuses": [cache.status.value for cache in caches],
        "metrics": ({"cache_hits": metrics.cache_hits, "cache_misses": metrics.cache_misses, "grounding_retries": metrics.grounding_retry_count, "final_word_count": metrics.final_word_count, "citation_coverage": metrics.citation_coverage, "section_metrics": metrics.section_metrics} if metrics else None),
        "claims": [{"id": str(c.id), "status": c.verification_status.value, "statement": c.statement} for c in claims],
        "sections": [{"title": s.title, "draft": s.draft} for s in sections],
        "concurrency": synthesis_llm_service.concurrency_snapshot(),
    }, ensure_ascii=False, default=str))


async def main():
    await prepare_db()
    project_id, paper_ids = await ingest()
    await precompute(paper_ids)
    await synthesize(project_id, paper_ids)


if __name__ == "__main__":
    asyncio.run(main())
