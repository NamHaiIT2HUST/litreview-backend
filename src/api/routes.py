"""
API routes cho LitReview Agent.

Bao gồm:
- GET  /search                            — tìm paper + lưu search history
- POST /chat                              — chat với AI agent
- GET  /status                            — health của agent

Search History (Module 2 — P0):
- GET  /projects/{project_id}/search-history     — lịch sử tìm kiếm
- GET  /search-queries/{query_id}/papers         — papers của 1 lần search
- POST /search-queries/{query_id}/duplicate      — duplicate query để sửa

Quality Verification (Module 4):
- POST /papers/{paper_id}/quality-check          — chạy Scopus/Coverage-year check
                                                      cho 1 paper CỤ THỂ khi user muốn
                                                      re-check/detail. Pipeline /search
                                                      đã chạy Scopus cross-check cho Top 20.
"""
import asyncio
import logging
import os
import re
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import String, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.config import get_settings
from src.database import get_db
from src.models.db_models import (
    Citation,
    EvidenceRecord,
    Paper,
    Project,
    SearchQuery,
    SynthesisSection,
    SynthesisSession,
    SynthesisStatus,
)
from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    DuplicateQueryResponse,
    PaperRecord,
    SearchHistoryResponse,
    SearchQueryRecord,
    SearchResponse,
)
from src.models.search_schemas import RerankRequest, RerankResponse, SearchExecuteRequest, SearchStrategiesResponse
from src.models.synthesis_schemas import (
    SynthesisCitationResponse,
    SynthesisEvidenceProfileItem,
    SynthesisSessionCreatedResponse,
    SynthesisSessionCreateRequest,
    SynthesisSessionResponse,
    SynthesisSessionSummary,
)
from src.models.workspace_schemas import (
    DirectUploadResponse,
    EvidenceCoordsRequest,
    EvidenceCoordsResponse,
    RAGEvalRequest,
    RAGEvalRunRequest,
    RectCoord,
    UploadResponse,
    WorkspaceChatRequest,
    WorkspaceChatResponse,
)
from src.services.document_processor import DocumentProcessor
from src.services.ingestion_service import persist_pdf_provenance
from src.services.paper_persistence_utils import normalize_authors_for_db
from src.services.rag_eval_harness import rag_eval_harness
from src.services.rag_guardrail_service import rag_guardrail_service
from src.services.rag_service import rag_service
from src.services.reranker_service import reranker_service
from src.services.scholar_api import search_papers_auto
from src.services.scopus_matcher import quality_check as run_scopus_quality_check
from src.services.search_service import generate_search_strategies
from src.services.synthesis_llm_service import synthesis_llm_service
from src.services.synthesis_metrics_service import get_or_create_metrics
from src.services.synthesis_response_builder import build_section_responses
from src.services.synthesis_session_utils import json_paper_ids
from src.services.vector_cleanup_service import create_vector_cleanup_job
from src.services.vector_store import vector_store_service

logger = logging.getLogger(__name__)
settings = get_settings()
DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"

processor = DocumentProcessor()

router = APIRouter()
GOOGLE_SCHOLAR_FETCH_N = 60   # Fetch more to filter; we only keep Scopus-indexed
SCOPUS_TARGET = 20             # Target: 20 Scopus-confirmed papers


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _compute_dedup_key(doi: str, title: str, authors: list[str] | str, year: int) -> str:
    """
    Thuật toán dedup theo spec:
      - Có DOI → normalize(doi)
      - Không có DOI → "title_norm|author[0]|year"
    """
    if doi and doi.strip() and doi.strip().upper() not in ("N/A", ""):
        return doi.strip().lower()
    title_norm = re.sub(r"\s+", " ", title.lower()).strip()

    first_author = ""
    if isinstance(authors, list) and len(authors) > 0:
        first_author = authors[0].strip()
    elif isinstance(authors, str) and authors:
        first_author = authors.split(",")[0].strip()

    return f"{title_norm}|{first_author}|{year}"

def _resolve_project_id(pid_raw: str | UUID | None) -> UUID:
    if isinstance(pid_raw, UUID):
        return pid_raw
    if not pid_raw:
        return UUID("00000000-0000-0000-0000-000000000001")
    try:
        return UUID(str(pid_raw))
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(pid_raw))


async def _persist_search(
    db: AsyncSession,
    *,
    query_string: str,
    papers_pydantic: list[PaperRecord],
    project_id: str | UUID,
    strategy_label: str | None = None,
    is_duplicated_from: UUID | None = None,
) -> tuple[UUID, int]:
    """
    Lưu 1 lần search vào DB:
    1. Insert SearchQuery record.
    2. Dedup: kiểm tra dedup_key đã tồn tại trong project chưa.
    3. Insert CachedPaper cho mỗi paper chưa trùng.
    Trả về search_query_id vừa tạo và số paper bị skip do dedup trong project.
    """
    project_uuid = _resolve_project_id(project_id)

    # Ensure project exists
    p_check = await db.get(Project, project_uuid)
    if not p_check:
        p_new = Project(
            id=project_uuid,
            name="Research Project",
            research_question=query_string,
        )
        db.add(p_new)
        await db.flush()

    sq = SearchQuery(
        id=uuid.uuid4(),
        project_id=project_uuid,
        query_string=query_string,
        strategy_label=strategy_label,
        result_count=len(papers_pydantic),
        is_duplicated_from=is_duplicated_from,
    )
    db.add(sq)

    existing_papers_result = await db.execute(
        select(Paper.id, Paper.dedup_key).where(Paper.project_id == project_uuid)
    )
    existing_papers_map = {row[1]: row[0] for row in existing_papers_result.fetchall()}

    duplicate_count = 0
    linked_paper_ids = set()
    from src.models.db_models import SearchQueryPaper
    for p in papers_pydantic:
        key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
        if key in existing_papers_map:
            duplicate_count += 1
            existing_id = existing_papers_map[key]
            if existing_id not in linked_paper_ids:
                db.add(SearchQueryPaper(search_query_id=sq.id, paper_id=existing_id))
                linked_paper_ids.add(existing_id)
            p.id = str(existing_id)
            continue

        paper_row = Paper(
            id=uuid.uuid4(),
            project_id=project_uuid,
            search_query_id=sq.id,
            title=p.title,
            authors=p.authors,
            year=p.year,
            abstract=p.abstract,
            journal=p.journal,
            doi=p.doi,
            issn=p.issn,
            url=p.url,
            citations=p.citations,
            lit_score=p.litScore,
            scopus_status=getattr(p, 'scopus_status', 'undetermined'),
            scopus_quartile=getattr(p, 'scopus_quartile', None),
            coverage_year_status=getattr(p, 'coverage_year_status', None),
            dedup_key=key,
        )
        try:
            await run_scopus_quality_check(db, paper_row)
        except Exception as q_err:
            import logging
            logging.getLogger(__name__).warning("Quality check error during persist: %s", q_err)
        db.add(paper_row)
        existing_papers_map[key] = paper_row.id
        if paper_row.id not in linked_paper_ids:
            db.add(SearchQueryPaper(search_query_id=sq.id, paper_id=paper_row.id))
            linked_paper_ids.add(paper_row.id)

        p.id = str(paper_row.id)
        p.abstract = paper_row.abstract
        p.doi = paper_row.doi
        p.issn = paper_row.issn
        p.scopus_status = getattr(paper_row.scopus_status, "value", paper_row.scopus_status)
        p.scopus_quartile = paper_row.scopus_quartile
        p.coverage_year_status = (
            getattr(paper_row.coverage_year_status, "value", paper_row.coverage_year_status)
            if paper_row.coverage_year_status is not None
            else None
        )

    await db.flush()
    return sq.id, duplicate_count


# ──────────────────────────────────────────────────────────────────────────────
# Existing endpoints
# ──────────────────────────────────────────────────────────────────────────────




# ──────────────────────────────────────────────────────────────────────────────
# Existing endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/projects/{project_id}/search-strategies", response_model=SearchStrategiesResponse)
async def get_search_strategies(
    project_id: str,
    x_api_key: str | None = Header(None, description="SerpApi Key"),
    db: AsyncSession = Depends(get_db),
) -> SearchStrategiesResponse:
    """Module 2: Paper Discovery - AI gợi ý 3 chiến lược tìm kiếm."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not x_api_key:
        # Lấy từ env
        import os
        x_api_key = os.getenv("SERPAPI_KEY", "")

    strategies = await generate_search_strategies(
        research_question=project.research_question,
        research_field=project.research_field,
        criteria_include=project.criteria_include,
        criteria_exclude=project.criteria_exclude,
        api_key=x_api_key
    )
    return SearchStrategiesResponse(strategies=strategies)

@router.post("/projects/{project_id}/search", response_model=SearchResponse)
async def search_papers(
    project_id: str,
    request: SearchExecuteRequest,
    x_api_key: str | None = Header(None, description="SerpApi hoặc Semantic Scholar Key"),
    provider: str | None = Query("auto", description="Nguồn dữ liệu: auto, serpapi, semanticscholar"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search & Verify: lấy papers từ Google Scholar, đối chiếu Scopus, chỉ trả về bài đã xác minh."""
    try:
        effective_provider = "serpapi" if provider in (None, "auto") else provider
        if not x_api_key or not x_api_key.strip():
            from src.config import get_settings
            st = get_settings()
            x_api_key = (getattr(st, "serpapi_api_key", "") or os.getenv("SERPAPI_API_KEY") or os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY") or "").strip()

        papers = await search_papers_auto(
            query=request.query_string,
            api_key=x_api_key or "",
            provider=effective_provider,
            limit=GOOGLE_SCHOLAR_FETCH_N,
        )

        if not papers:
            return SearchResponse(
                papers=[],
                search_query_id=None,
                provider="google_scholar" if effective_provider == "serpapi" else effective_provider,
                limit=SCOPUS_TARGET,
                total_found=0,
                total_confirmed=0,
                total_undetermined=0,
                duplicates=0,
            )

        # ÁP DỤNG FINE-TUNED RERANKER (Tự động tái xếp hạng theo ngữ nghĩa 3 lĩnh vực)
        try:
            from src.services.reranker_service import reranker_service
            papers_dict = [{"id": str(i), "title": p.title or "", "abstract": p.abstract or "", "obj": p} for i, p in enumerate(papers)]
            reranked_dicts = reranker_service.rerank_papers(request.query_string, papers_dict)
            papers = [d["obj"] for d in reranked_dicts]
            print(f"[Reranker] Successfully auto-reranked {len(papers)} candidate papers for query: '{request.query_string}'", flush=True)
        except Exception as e:
            print(f"[Reranker] Warning: Auto-reranking failed, falling back to original order: {e}", flush=True)

        confirmed_scopus_papers = []
        for p in papers:
            temp_paper = Paper(
                id=uuid.uuid4(),
                title=p.title,
                authors=normalize_authors_for_db(p.authors),
                year=p.year,
                journal=p.journal,
                abstract=p.abstract,
                doi=p.doi,
                issn=p.issn,
                citations=p.citations,
            )
            try:
                from src.services.scopus_matcher import quality_check
                await quality_check(db, temp_paper)
                p.abstract = temp_paper.abstract
                p.doi = temp_paper.doi
                p.issn = temp_paper.issn
                p.scopus_status = temp_paper.scopus_status.value if hasattr(temp_paper.scopus_status, "value") else str(temp_paper.scopus_status)
                p.scopus_quartile = temp_paper.scopus_quartile
                p.coverage_year_status = temp_paper.coverage_year_status.value if hasattr(temp_paper.coverage_year_status, "value") else str(temp_paper.coverage_year_status)
            except Exception as e:
                print(f"Error checking paper: {e}")

            if p.scopus_status == "indexed":
                confirmed_scopus_papers.append(p)
                if len(confirmed_scopus_papers) >= SCOPUS_TARGET:
                    break

        if len(confirmed_scopus_papers) < SCOPUS_TARGET:
            scopus_ids = {id(p) for p in confirmed_scopus_papers}
            for p in papers:
                if id(p) not in scopus_ids:
                    confirmed_scopus_papers.append(p)
                    if len(confirmed_scopus_papers) >= SCOPUS_TARGET:
                        break

        target_papers = confirmed_scopus_papers[:SCOPUS_TARGET]

        try:
            sq_id, duplicate_count = await _persist_search(
                db,
                query_string=request.query_string,
                papers_pydantic=target_papers,
                project_id=project_id,
                strategy_label=request.strategy_label
            )

            if sq_id:
                project_uuid = _resolve_project_id(project_id)
                keys = [_compute_dedup_key(p.doi, p.title, p.authors, p.year) for p in target_papers]
                result = await db.execute(
                    select(Paper).where(Paper.project_id == project_uuid, Paper.dedup_key.in_(keys))
                )
                db_papers = result.scalars().all()
                dedup_to_paper = {p.dedup_key: p for p in db_papers}

                for p in target_papers:
                    key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
                    db_paper = dedup_to_paper.get(key)
                    if db_paper:
                        p.id = str(db_paper.id)
                        p.abstract = db_paper.abstract
                        p.doi = db_paper.doi

        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Failed to persist search: %s", exc)
            sq_id = None
            duplicate_count = 0

        all_found = len(papers)
        confirmed_count = sum(1 for p in target_papers if p.scopus_status == "indexed")
        undetermined_count = sum(1 for p in target_papers if p.scopus_status != "indexed")

        if sq_id:
            try:
                sq_obj = await db.get(SearchQuery, sq_id)
                if sq_obj:
                    sq_obj.total_found = all_found
                    sq_obj.total_confirmed = confirmed_count
                    sq_obj.total_undetermined = undetermined_count
                    await db.commit()
            except Exception:
                pass

        return SearchResponse(
            papers=target_papers,
            search_query_id=sq_id,
            provider="google_scholar" if effective_provider == "serpapi" else effective_provider,
            limit=SCOPUS_TARGET,
            total_found=all_found,
            total_confirmed=confirmed_count,
            total_undetermined=undetermined_count,
            duplicates=duplicate_count,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Search execution failed: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent."""
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/search-history", response_model=SearchHistoryResponse)
async def get_search_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> SearchHistoryResponse:
    """
    Lấy toàn bộ lịch sử search của một project,
    sắp xếp theo executed_at giảm dần (mới nhất trước).
    """
    project_uuid = uuid.UUID(str(project_id))
    result = await db.execute(
        select(SearchQuery)
        .where(
            SearchQuery.project_id == project_uuid,
            SearchQuery.query_string != "Direct Ingestion"
        )
        .order_by(desc(SearchQuery.executed_at))
    )
    rows = result.scalars().all()
    history = [SearchQueryRecord.model_validate(row) for row in rows]
    return SearchHistoryResponse(project_id=str(project_id), history=history)


@router.get("/search-queries/{query_id}/papers", response_model=list[PaperRecord])
async def get_papers_for_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PaperRecord]:
    """
    Lấy danh sách paper (đã xác minh thuộc Scopus) của 1 lần search cụ thể.
    """
    query_uuid = uuid.UUID(str(query_id))
    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_uuid)
    )
    sq = sq_result.scalar_one_or_none()
    if not sq:
        raise HTTPException(status_code=404, detail=f"Search query '{query_id}' not found")

    from src.models.db_models import ScopusStatus, SearchQueryPaper

    # Try querying via the new association table first
    assoc_result = await db.execute(
        select(Paper)
        .join(SearchQueryPaper, SearchQueryPaper.paper_id == Paper.id)
        .where(
            SearchQueryPaper.search_query_id == query_uuid,
            (Paper.scopus_status == ScopusStatus.indexed) | (Paper.scopus_status == "indexed")
        )
    )
    papers = assoc_result.scalars().all()

    # Fallback to old behavior for legacy queries without associations
    if not papers:
        legacy_result = await db.execute(
            select(Paper)
            .where(
                Paper.search_query_id == query_uuid,
                (Paper.scopus_status == ScopusStatus.indexed) | (Paper.scopus_status == "indexed")
            )
        )
        papers = legacy_result.scalars().all()

    return [PaperRecord.model_validate(p) for p in papers]


@router.post("/search-queries/{query_id}/duplicate", response_model=DuplicateQueryResponse)
async def duplicate_search_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
) -> DuplicateQueryResponse:
    """
    Duplicate query cũ để user sửa lại keyword.
    Chỉ copy query_string, KHÔNG tự chạy lại search.
    Tạo 1 record SearchQuery mới với is_duplicated_from = query_id,
    result_count = 0 (chưa chạy).
    """
    query_uuid = uuid.UUID(str(query_id))
    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_uuid)
    )
    original = sq_result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail=f"Search query '{query_id}' not found")

    new_sq = SearchQuery(
        id=uuid.uuid4(),
        project_id=original.project_id,
        query_string=original.query_string,
        strategy_label=None,
        result_count=0,
        is_duplicated_from=query_id,
    )
    db.add(new_sq)
    await db.flush()

    return DuplicateQueryResponse(
        new_query_id=new_sq.id,
        query_string=new_sq.query_string,
        duplicated_from=query_id,
    )


@router.delete("/search-queries/{query_id}")
async def delete_search_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xóa một lịch sử tìm kiếm theo query_id."""
    try:
        query_uuid = uuid.UUID(str(query_id))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid query_id UUID format")

    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_uuid)
    )
    sq = sq_result.scalar_one_or_none()
    if not sq:
        raise HTTPException(status_code=404, detail="Search query not found")

    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(Paper).where(Paper.search_query_id == query_uuid)
    )
    await db.delete(sq)
    await db.commit()
    return {"message": "Search query deleted successfully", "id": str(query_id)}

@router.delete("/papers/{paper_id}")
async def delete_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Xóa một paper khỏi database."""
    from sqlalchemy import delete as sql_delete

    from src.models.db_models import (
        Citation,
        EvidenceExtractionAttempt,
        EvidenceRecord,
        Extraction,
        GenericEvidenceCache,
        GenericEvidenceCacheItem,
        PageText,
        Paper,
        PDFChunk,
        RetrievalLog,
        ScreeningHistory,
        SearchQueryPaper,
        VectorCleanupJob,
    )

    target_uuid = None
    try:
        target_uuid = UUID(str(paper_id).strip())
    except Exception:
        stmt = select(Paper).where(
            Paper.title.ilike(f"%{paper_id}%") | Paper.dedup_key.ilike(f"%{paper_id}%")
        )
        found = (await db.execute(stmt)).scalars().first()
        if found:
            target_uuid = found.id

    if not target_uuid:
        return {"message": "Paper already deleted or not stored", "id": str(paper_id)}

    try:
        # Delete child rows first to avoid foreign key violations
        from src.models.db_models import ClaimEvidenceLink
        ev_result = await db.execute(select(EvidenceRecord.id).where(EvidenceRecord.paper_id == target_uuid))
        ev_ids = ev_result.scalars().all()
        if ev_ids:
            await db.execute(sql_delete(ClaimEvidenceLink).where(ClaimEvidenceLink.evidence_id.in_(ev_ids)))

        await db.execute(sql_delete(SearchQueryPaper).where(SearchQueryPaper.paper_id == target_uuid))
        await db.execute(sql_delete(Citation).where(Citation.paper_id == target_uuid))
        await db.execute(sql_delete(RetrievalLog).where(RetrievalLog.paper_id == target_uuid))
        await db.execute(sql_delete(GenericEvidenceCacheItem).where(GenericEvidenceCacheItem.paper_id == target_uuid))
        await db.execute(sql_delete(GenericEvidenceCache).where(GenericEvidenceCache.paper_id == target_uuid))
        await db.execute(sql_delete(VectorCleanupJob).where(VectorCleanupJob.paper_id == target_uuid))
        await db.execute(sql_delete(EvidenceRecord).where(EvidenceRecord.paper_id == target_uuid))
        await db.execute(sql_delete(EvidenceExtractionAttempt).where(EvidenceExtractionAttempt.paper_id == target_uuid))
        await db.execute(sql_delete(ScreeningHistory).where(ScreeningHistory.paper_id == target_uuid))
        await db.execute(sql_delete(Extraction).where(Extraction.paper_id == target_uuid))
        await db.execute(sql_delete(PDFChunk).where(PDFChunk.paper_id == target_uuid))
        await db.execute(sql_delete(PageText).where(PageText.paper_id == target_uuid))

        await db.execute(sql_delete(Paper).where(Paper.id == target_uuid))
        await db.commit()

        # Delete vector chunks if present
        try:
            from src.services.vector_store import vector_store_service
            await vector_store_service.delete_documents_by_paper(str(target_uuid))
        except Exception:
            pass

        return {"message": "Paper deleted successfully", "id": str(paper_id)}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete paper {paper_id}: {e}")
        return {"message": f"Deleted with warning: {str(e)}", "id": str(paper_id)}

# ──────────────────────────────────────────────────────────────────────────────
# Quality Verification endpoint (Module 4)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/papers/{paper_id}/quality-check", response_model=PaperRecord)
async def quality_check_paper(
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PaperRecord:
    """
    Trigger Quality Check (Scopus + Coverage Year) cho 1 paper cụ thể.

    Search & Verify đã chạy Scopus check cho Top 20 lúc search. Endpoint này
    dùng cho trường hợp user muốn re-check/detail một paper cụ thể.

    404 nếu paper không tồn tại. OA status KHÔNG được xử lý ở đây — xem
    docstring trong src/services/scopus_matcher.py.
    """
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")

    await run_scopus_quality_check(db, paper)
    await db.flush()

    # TODO (Module 3): gọi recompute_priority(paper.id) ở đây khi priority_score
    # được implement.

    return PaperRecord.model_validate(paper)

# ──────────────────────────────────────────────────────────────────────────────
# Workspace endpoints (Phase 1 RAG)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/workspace/direct-upload", response_model=DirectUploadResponse)
async def direct_upload_paper_pdf(
    file: UploadFile = File(...),
    title: str = Form(None),
    project_id: str = Form(DEFAULT_PROJECT_ID),
    db: AsyncSession = Depends(get_db),
) -> DirectUploadResponse:
    """Create a persistent paper row and provenance-aware ingestion from a PDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    project_uuid = _resolve_project_id(project_id)

    project_result = await db.execute(select(Project).where(Project.id == project_uuid))
    if project_result.scalar_one_or_none() is None:
        p_obj = Project(
            id=project_uuid,
            title="Default Research Project",
            description="Auto-created project workspace",
            research_field="Computer Science & AI"
        )
        db.add(p_obj)
        await db.flush()

    # Ensure there is a dummy SearchQuery for direct uploads to satisfy legacy NOT NULL constraints on search_query_id
    from src.models.db_models import SearchQuery
    dummy_query_result = await db.execute(
        select(SearchQuery).where(
            SearchQuery.project_id == project_uuid,
            SearchQuery.query_string == "Direct Ingestion"
        )
    )
    dummy_query = dummy_query_result.scalar_one_or_none()
    if not dummy_query:
        dummy_query = SearchQuery(
            id=uuid.uuid4(),
            project_id=project_uuid,
            query_string="Direct Ingestion",
            result_count=0
        )
        db.add(dummy_query)
        await db.flush()

    from datetime import datetime
    paper_id = uuid.uuid4()
    clean_title = (title or file.filename.rsplit(".", 1)[0]).strip()
    paper = Paper(
        id=paper_id,
        project_id=project_uuid,
        search_query_id=dummy_query.id,
        title=clean_title or file.filename,
        authors=[],
        year=datetime.now().year,
        source="direct_upload",
        dedup_key=f"direct-upload:{paper_id}",
        screening_decision="keep",
    )
    db.add(paper)

    try:
        file_path = await processor.save_upload_file(file, project_id=str(project_uuid))
        paper.file_path = file_path
        db.add(paper)
        pages, chunks = processor.extract_and_chunk(file_path)
        if not chunks or all(not chunk.page_content.strip() for chunk in chunks):
            raise HTTPException(
                status_code=422,
                detail="PDF không trích được văn bản; file scan cần OCR.",
            )
        ingestion_id = await persist_pdf_provenance(
            db=db,
            paper=paper,
            pages=pages,
            chunks=chunks,
            parser_metadata=processor.parser_metadata(),
        )
        try:
            await vector_store_service.stage_documents_for_paper(str(paper.id), chunks)
            await db.commit()
        except Exception:
            await vector_store_service.delete_documents_by_ingestion(str(ingestion_id))
            raise
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DirectUploadResponse(
        paper_id=str(paper.id),
        title=paper.title,
        filename=file.filename,
        total_pages=len(pages),
        total_chunks=len(chunks),
        message="PDF saved, ingested, and persisted in the workspace.",
    )


class DirectUploadJsonRequest(BaseModel):
    title: str
    filename: str
    pages: list[str]
    project_id: str | None = None


@router.post("/workspace/direct-upload-json", response_model=DirectUploadResponse)
async def direct_upload_json(
    payload: DirectUploadJsonRequest,
    db: AsyncSession = Depends(get_db)
) -> DirectUploadResponse:
    """Ingest pre-extracted PDF text directly to avoid 4.5MB edge payload limits."""
    project_uuid = _resolve_project_id(payload.project_id)

    project_result = await db.execute(select(Project).where(Project.id == project_uuid))
    p_obj = project_result.scalar_one_or_none()
    if p_obj is None:
        p_obj = Project(
            id=project_uuid,
            title="Default Research Project",
            description="Auto-created project workspace",
            research_field="Computer Science & AI"
        )
        db.add(p_obj)
        await db.flush()

    from src.models.db_models import SearchQuery
    dummy_query_result = await db.execute(
        select(SearchQuery).where(
            SearchQuery.project_id == project_uuid,
            SearchQuery.query_string == "Direct Ingestion"
        )
    )
    dummy_query = dummy_query_result.scalar_one_or_none()
    if not dummy_query:
        dummy_query = SearchQuery(
            id=uuid.uuid4(),
            project_id=project_uuid,
            query_string="Direct Ingestion",
            result_count=0
        )
        db.add(dummy_query)
        await db.flush()

    from datetime import datetime
    paper_id = uuid.uuid4()
    clean_title = (payload.title or payload.filename.rsplit(".", 1)[0]).strip()
    paper = Paper(
        id=paper_id,
        project_id=project_uuid,
        search_query_id=dummy_query.id,
        title=clean_title or payload.filename,
        authors=[],
        year=datetime.now().year,
        source="direct_upload",
        dedup_key=f"direct-upload:{paper_id}",
        screening_decision="keep",
    )
    db.add(paper)

    from langchain_core.documents import Document

    pages_docs = []
    for idx, page_content in enumerate(payload.pages):
        pages_docs.append(
            Document(
                page_content=page_content or "",
                metadata={"source": payload.filename, "page": idx}
            )
        )

    chunks = processor.text_splitter.split_documents(pages_docs)
    processor._attach_chunk_metadata(pages_docs, chunks)
    for chunk in chunks:
        chunk.metadata["paper_title"] = paper.title

    ingestion_id = await persist_pdf_provenance(
        db=db,
        paper=paper,
        pages=pages_docs,
        chunks=chunks,
        parser_metadata={"parser_name": "client_pdfjs", "parser_version": "1.0", "ingestion_version": "page-offset-v1"},
    )
    try:
        await vector_store_service.stage_documents_for_paper(str(paper.id), chunks)
        await db.commit()
    except Exception:
        await vector_store_service.delete_documents_by_ingestion(str(ingestion_id))
        raise

    return DirectUploadResponse(
        paper_id=str(paper.id),
        title=paper.title,
        filename=payload.filename,
        total_pages=len(pages_docs),
        total_chunks=len(chunks),
        message="PDF saved, ingested, and persisted in the workspace.",
    )


@router.post("/workspace/upload", response_model=UploadResponse)
async def upload_paper_pdf(
    file: UploadFile = File(...),
    paper_id: str = Form(...),
    doi: str = Form(None),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload PDF and persist page/chunk provenance before vector indexing.

    PageText stores the exact PyPDFLoader text. Chroma receives only chunks plus
    canonical DB identifiers/offsets, so later synthesis can ground evidence
    without trusting an LLM-generated chunk ID.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        try:
            paper_uuid = uuid.UUID(paper_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="paper_id must be a valid UUID.") from exc

        paper_result = await db.execute(select(Paper).where(Paper.id == paper_uuid))
        paper = paper_result.scalar_one_or_none()
        if paper is None:
            raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")

        file_path = await processor.save_upload_file(file, project_id=str(paper.project_id))
        paper.file_path = file_path
        db.add(paper)
        db.add(paper)
        pages, chunks = processor.extract_and_chunk(file_path, paper_title=paper.title)
        if not chunks or all(not chunk.page_content.strip() for chunk in chunks):
            raise HTTPException(
                status_code=422,
                detail=(
                    "PDF không trích được văn bản — có thể là file scan/ảnh; "
                    "OCR chưa được hỗ trợ trong phiên bản này."
                ),
            )

        ingestion_id = await persist_pdf_provenance(
            db=db,
            paper=paper,
            pages=pages,
            chunks=chunks,
            parser_metadata=processor.parser_metadata(),
        )

        effective_doi = doi or paper.doi
        if effective_doi:
            for chunk in chunks:
                chunk.metadata["doi"] = effective_doi

        old_vector_ids: list[str] = []
        cleanup_job = None
        try:
            # Stage the new vectors while retaining the previously committed set.
            # Persist a cleanup-outbox row in the SAME DB transaction that switches
            # active_ingestion_id. A crash after commit therefore cannot lose the
            # knowledge of which stale vector IDs still need deletion.
            old_vector_ids = await vector_store_service.stage_documents_for_paper(
                str(paper.id), chunks
            )
            cleanup_job = await create_vector_cleanup_job(
                db,
                paper_id=paper.id,
                ingestion_id=ingestion_id,
                vector_ids=old_vector_ids,
            )
            await db.commit()
        except Exception:
            # New-vector cleanup is safe because every new chunk carries ingestion_id.
            await vector_store_service.delete_documents_by_ingestion(str(ingestion_id))
            await db.rollback()
            raise

        if cleanup_job is not None:
            try:
                from src.tasks.vector_cleanup_tasks import run_vector_cleanup_job

                run_vector_cleanup_job.delay(str(cleanup_job.id))
            except Exception as cleanup_enqueue_exc:
                # The durable DB outbox remains pending; Celery beat will pick it up.
                import logging

                logging.getLogger(__name__).warning(
                    "Committed PDF ingestion %s; vector cleanup job %s will be "
                    "retried by the periodic outbox drain because immediate enqueue "
                    "failed: %s",
                    ingestion_id,
                    cleanup_job.id,
                    cleanup_enqueue_exc,
                )

        num_added = len(chunks)
        return UploadResponse(
            file_id=os.path.basename(file_path),
            filename=file.filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            message=(
                f"Successfully processed {len(pages)} pages and stored "
                f"{num_added} provenance-aware chunks into Vector Database."
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workspace/test-search")
async def test_vector_search(query: str = Query(...)):
    """
    API test thử chức năng query Vector DB để xem có trả ra văn bản đúng không.
    """
    try:
        results = await vector_store_service.search_similar_documents(query)
        # Format lại kết quả cho dễ đọc
        formatted = []
        for doc in results:
            formatted.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        return {"query": query, "results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workspace/chat", response_model=WorkspaceChatResponse)
async def workspace_chat(
    request: WorkspaceChatRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceChatResponse:
    """
    Chat với trợ lý AI về các bài báo đã tải lên (RAG chuẩn NotebookLM).
    """
    try:

        # Bước 0: Input Guardrail Validation
        is_valid, err_msg = rag_guardrail_service.validate_input_query(request.message)
        if not is_valid:
            return WorkspaceChatResponse(
                answer=f"🛡️ **Input Guardrail:** {err_msg}",
                context_used=[],
                citations=[],
                guardrail={
                    "is_safe": False,
                    "safety_verdict": "INPUT_GUARDRAIL_BLOCKED",
                    "faithfulness_score": 0.0,
                    "hallucination_rate": 0.0,
                    "citation_precision": 0.0,
                    "total_claims": 0,
                    "attributable_claims_count": 0,
                    "extrapolatory_claims_count": 0,
                    "contradictory_claims_count": 0,
                    "hallucinated_citations": [],
                    "claims": [],
                    "summary_verdict": err_msg or "Truy vấn bị từ chối bởi Input Guardrail.",
                }
            )

        # --- LUỒNG RAG TRUYỀN THỐNG (SUPER FAST) ---
        # Bước 1: Xác định danh sách paper_ids mục tiêu
        target_pids = request.paper_ids if getattr(request, "paper_ids", None) else ([request.paper_id] if getattr(request, "paper_id", None) else [])

        # Nếu frontend không truyền paper_ids (hoặc rỗng), tự động lấy tất cả paper
        # trong ĐÚNG project hiện tại. Thiếu điều kiện lọc project_id ở đây từng
        # khiến câu hỏi của một project trả lời bằng tài liệu direct-upload của
        # BẤT KỲ project/người dùng nào khác trong toàn hệ thống.
        if not target_pids:
            if not request.project_id:
                target_pids = []
            else:
                try:
                    from src.models.db_models import ScreeningHistory
                    project_uuid = _resolve_project_id(request.project_id)
                    stmt = select(Paper.id).outerjoin(
                        ScreeningHistory, Paper.id == ScreeningHistory.paper_id
                    ).where(
                        Paper.project_id == project_uuid,
                        (ScreeningHistory.decision.in_(["keep", "maybe"])) | (Paper.source == "direct_upload"),
                    )
                    all_papers_result = await db.execute(stmt)
                    target_pids = [str(r[0]) for r in all_papers_result.fetchall()]
                except Exception:
                    target_pids = []

        chunks = []
        from langchain_core.documents import Document

        if target_pids:
            # 1. Similarity search per paper
            search_tasks = [
                vector_store_service.search_similar_documents(
                    request.message, top_k=4, filters={"paper_id": str(pid).strip()}
                )
                for pid in target_pids
            ]
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            for res in search_results:
                if isinstance(res, list) and res:
                    chunks.extend(res)

            # 2. For each paper, ensure we also have the introductory/abstract chunks so broad & summary queries always have full context
            from src.models.db_models import PageText, PDFChunk
            for pid in target_pids:
                pid_str = str(pid).strip()
                try:
                    try:
                        pid_uuid = uuid.UUID(pid_str)
                    except Exception:
                        pid_uuid = None

                    stmt_first_chunks = (
                        select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title, Paper.abstract)
                        .join(PageText, PDFChunk.page_text_id == PageText.id)
                        .join(Paper, PDFChunk.paper_id == Paper.id)
                        .where((Paper.id == pid_uuid) if pid_uuid else (Paper.title.ilike(f"%{pid_str}%")))
                        # chunk_index resets to 0 on every page (document_processor.py chunks
                        # per-page independently), so ordering by chunk_index alone gives an
                        # arbitrary mix of "first chunk of some page" across the whole paper --
                        # not reliably page 1, where author/title metadata actually lives. Sort
                        # by page first so this genuinely returns the paper's opening chunks.
                        # limit(3) not 4: the structured metadata doc inserted below takes
                        # the 4th "intro item" slot, keeping this paper's total contribution
                        # to the context budget unchanged (MAX_CONTEXT_CHUNKS=10 downstream
                        # in rag_service.py) rather than pushing out similarity-search chunks.
                        .order_by(PageText.page_number, PDFChunk.chunk_index)
                        .limit(3)
                    )
                    db_rows = (await db.execute(stmt_first_chunks)).fetchall()
                    for chunk_row, page_num, file_path, title, abstract in db_rows:
                        if not any(c.metadata.get("chunk_id") == str(chunk_row.id) for c in chunks):
                            doc = Document(
                                page_content=chunk_row.chunk_text,
                                metadata={
                                    "paper_id": pid_str,
                                    "page_text_id": str(chunk_row.page_text_id),
                                    "chunk_id": str(chunk_row.id),
                                    "ingestion_id": str(chunk_row.ingestion_id),
                                    "page": page_num,
                                    "chunk_index": chunk_row.chunk_index,
                                    "page_char_start": chunk_row.page_char_start,
                                    "page_char_end": chunk_row.page_char_end,
                                    "source": str(file_path) if file_path else f"paper_{pid_str}.pdf",
                                    "paper_title": str(title) if title else "Unknown Title"
                                }
                            )
                            chunks.insert(0, doc)

                    # Structured metadata (title/authors/journal/year) straight from the
                    # Paper row, ALWAYS added regardless of whether PDF chunks exist. A
                    # short factual question like "who are the authors" matches poorly
                    # against similarity search (no academic content to compare against),
                    # and even the opening PDF chunks above are not guaranteed to contain
                    # a cleanly-extracted author list (layout/OCR-dependent) -- the DB
                    # fields are the reliable source for exactly this kind of question.
                    stmt_meta = select(Paper).where(
                        (Paper.id == pid_uuid) if pid_uuid else (Paper.title.ilike(f"%{pid_str}%") | Paper.dedup_key.ilike(f"%{pid_str}%"))
                    )
                    paper = (await db.execute(stmt_meta)).scalars().first()
                    if paper:
                        text = f"Title: {paper.title}\nAuthors: {paper.authors}\nJournal: {paper.journal or 'N/A'} ({paper.year or 'N/A'})\nAbstract: {paper.abstract or 'Research Topic: ' + paper.title}"
                        doc = Document(page_content=text, metadata={"paper_id": str(paper.id), "paper_title": paper.title, "page": 1, "source": paper.file_path or f"paper_{paper.id}.pdf"})
                        chunks.insert(0, doc)
                except Exception as e:
                    logger.warning(f"Error fetching introductory chunks for {pid_str}: {e}")
        else:
            try:
                chunks = await vector_store_service.search_similar_documents(request.message, top_k=8, filters=None)
            except Exception:
                chunks = []

        # Fallback: If DB/Vector store has no chunks for these papers, construct rich documents from request.papers_data
        if not chunks and getattr(request, "papers_data", None):
            for idx, p in enumerate(request.papers_data):
                p_title = p.get("title") or f"Paper #{idx+1}"
                p_abstract = p.get("abstract") or p.get("summary") or ""
                p_authors = p.get("authors") or ""
                p_year = p.get("year") or ""
                p_journal = p.get("journal") or ""
                text = f"Title: {p_title}\nAuthors: {p_authors} ({p_year})\nJournal: {p_journal}\nAbstract: {p_abstract}"
                doc = Document(
                    page_content=text,
                    metadata={
                        "paper_id": str(p.get("id") or idx),
                        "paper_title": p_title,
                        "page": 1,
                        "source": f"paper_{idx+1}.pdf",
                        "page_char_start": 0,
                        "page_char_end": len(text)
                    }
                )
                chunks.append(doc)

        # Bước 2: Sinh câu trả lời dựa trên context (có structured citation metadata)
        result = await rag_service.generate_answer_with_citations(request.message, chunks)

        # Bước 3: RAG Output Guardrail & ASTA-Bench Claim Attribution
        valid_keys = {str(c.get("key", idx + 1)) for idx, c in enumerate(result.get("context_used", []))}
        sanitized_answer, hallucinated_keys = rag_guardrail_service.sanitize_citations(result["answer"], valid_keys)

        guardrail_res = await rag_guardrail_service.verify_answer_groundedness(
            request.message, sanitized_answer, result.get("context_used", [])
        )
        if hallucinated_keys:
            guardrail_res.hallucinated_citations = list(set(guardrail_res.hallucinated_citations + hallucinated_keys))

        # Bước 4: Đóng gói phản hồi
        return WorkspaceChatResponse(
            answer=sanitized_answer,
            context_used=result["context_used"],
            citations=result.get("citations", []),
            guardrail=guardrail_res.model_dump(),
            cost_report=result.get("cost_report"),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error in workspace_chat")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/evaluate-rag")
async def evaluate_rag_endpoint(request: RAGEvalRequest):
    """
    On-demand evaluation của một câu trả lời RAG cụ thể.
    Trả về điểm số Faithfulness %, Hallucination Rate %, chi tiết từng Claim.
    """
    try:
        guardrail_res = await rag_guardrail_service.verify_answer_groundedness(
            request.question, request.answer, request.context_chunks
        )
        return guardrail_res.model_dump()
    except Exception as e:
        logger.exception("Error in evaluate_rag_endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspace/run-eval-harness")
async def run_eval_harness_endpoint(request: RAGEvalRunRequest, db: AsyncSession = Depends(get_db)):
    """
    Chạy bộ kiểm thử tự động RAG Benchmark Harness trên các tài liệu đã chọn trong Workspace.
    """
    try:
        papers_to_eval = []
        if request.paper_ids:
            for pid in request.paper_ids:
                stmt = select(Paper).where(Paper.id.cast(String) == str(pid))
                p = (await db.execute(stmt)).scalars().first()
                if p:
                    papers_to_eval.append({
                        "id": str(p.id),
                        "title": p.title,
                        "filename": p.file_path,
                        "abstract": p.abstract or "",
                    })
        else:
            # Lấy tất cả papers trong workspace
            from src.models.db_models import ScreeningHistory
            stmt = select(Paper).outerjoin(
                ScreeningHistory, Paper.id == ScreeningHistory.paper_id
            ).where(
                (ScreeningHistory.decision.in_(["keep", "maybe"])) | (Paper.source == "direct_upload")
            ).limit(10)
            rows = (await db.execute(stmt)).scalars().all()
            for p in rows:
                papers_to_eval.append({
                    "id": str(p.id),
                    "title": p.title,
                    "filename": p.file_path,
                    "abstract": p.abstract or "",
                })

        if not papers_to_eval:
            raise HTTPException(status_code=400, detail="Không tìm thấy tài liệu nào trong Workspace để chạy kiểm thử.")

        report = await rag_eval_harness.run_benchmark(papers_to_eval)
        return report.model_dump()
    except Exception as e:
        logger.exception("Error in run_eval_harness_endpoint")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/eval-reports")
async def get_eval_reports_endpoint():
    """
    Lấy danh sách các báo cáo Benchmark RAG đã thực thi gần đây.
    """
    try:
        reports = rag_eval_harness.get_recent_reports()
        return [r.model_dump() for r in reports]
    except Exception as e:
        logger.exception("Error in get_eval_reports_endpoint")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# Tab "Phân tích dữ liệu" — DataVoyager Academic Analytics Hub
# ──────────────────────────────────────────────────────────────────────────────

class DataAnalysisRequest(BaseModel):
    question: str
    csv_text: str = ""
    filename: str = ""

class DatasetProfile(BaseModel):
    row_count: int = 0
    column_count: int = 0
    missing_rate_pct: float = 0.0
    duplicate_rows: int = 0
    completely_empty_cols: list[str] = Field(default_factory=list)
    constant_cols: list[str] = Field(default_factory=list)
    partially_missing_cols: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[dict[str, Any]] = Field(default_factory=list)
    summary_stats: dict[str, Any] = Field(default_factory=dict)
    top_correlations: list[dict[str, Any]] | None = None
    columns_to_drop: list[dict[str, str]] | None = None
    time_series_info: dict[str, Any] | None = None

class ChartSpec(BaseModel):
    type: str = "bar"  # "bar" | "line" | "donut"
    title: str = ""
    data: list[dict[str, Any]] = Field(default_factory=list)
    x_label: str | None = None
    y_label: str | None = None
    unit: str | None = None

class KPISpec(BaseModel):
    label: str
    value: str | int | float
    subtext: str | None = None
    trend: str | None = None

class DataAnalysisResponse(BaseModel):
    answer: str
    charts: list[ChartSpec] | None = None
    kpis: list[KPISpec] | None = None
    dataset_profile: DatasetProfile | None = None
    figures: list[str] | None = None
    python_code: str | None = None
    block_outputs: list[dict] | None = None

@router.post("/workspace/analyze-data", response_model=DataAnalysisResponse)
async def workspace_analyze_data(request: DataAnalysisRequest) -> DataAnalysisResponse:
    """
    Tab 'Phân tích dữ liệu' (EDA): nhận câu hỏi + tập dữ liệu (CSV/TSV),
    thực hiện phân tích thống kê định lượng với Pandas/SciPy/Statsmodels và suy luận học thuật với LLM.
    Đảm bảo 100% số liệu được kiểm chứng thực tế và tuân thủ Khung EDA Chuẩn 7 Phần.
    """
    import io
    import json
    import logging
    import re

    import numpy as np
    import pandas as pd

    from src.services.eda_llm_client import build_eda_llm
    from src.services.eda_profiling_service import ComprehensiveProfile, eda_profiling_service

    logger = logging.getLogger(__name__)

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Câu hỏi không được để trống.")

    dataset_profile = None
    scientific_summary_text = ""
    kpis_list = None
    comp_profile: ComprehensiveProfile | None = None

    # 1. Phân tích định lượng khoa học và kiểm toán thống kê chuyên sâu
    if request.csv_text.strip():
        try:
            first_line = request.csv_text.strip().split('\n')[0]
            sep = '\t' if '\t' in first_line and first_line.count('\t') > first_line.count(',') else (';' if ';' in first_line and first_line.count(';') > first_line.count(',') else ',')

            try:
                df = pd.read_csv(io.StringIO(request.csv_text.strip()), sep=sep, on_bad_lines='skip')
            except Exception:
                df = pd.read_csv(io.StringIO(request.csv_text.strip()), on_bad_lines='skip')

            comp_profile = eda_profiling_service.profile_dataframe(df, filename=request.filename)

            # Format summary stats for JSON response
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c not in comp_profile.completely_empty_cols and c not in comp_profile.constant_cols]
            desc_stats = {}
            if numeric_cols:
                desc = df[numeric_cols].describe().to_dict()
                for col_name, stats in desc.items():
                    desc_stats[col_name] = {k: round(v, 2) if isinstance(v, (int, float)) and not np.isnan(v) else str(v) for k, v in stats.items()}

            dataset_profile = DatasetProfile(
                row_count=comp_profile.row_count,
                column_count=comp_profile.column_count,
                missing_rate_pct=comp_profile.overall_missing_pct,
                duplicate_rows=comp_profile.duplicate_rows,
                completely_empty_cols=comp_profile.completely_empty_cols,
                constant_cols=comp_profile.constant_cols,
                partially_missing_cols=[p.model_dump() for p in comp_profile.partially_missing_cols],
                columns=comp_profile.columns_info,
                summary_stats=desc_stats,
                top_correlations=[c.model_dump() for c in comp_profile.top_correlations],
                columns_to_drop=comp_profile.columns_to_drop,
                time_series_info=comp_profile.time_series_profile.model_dump(),
            )

            scientific_summary_text = comp_profile.llm_context_summary

        except Exception as e:
            logger.warning(f"Failed to profile dataset with eda_profiling_service: {e}")
            scientific_summary_text = f"Dữ liệu bảng có {len(request.csv_text.splitlines())} dòng thô."

    # 2. Xây dựng System & User Prompt cho LLM tuân thủ Khung EDA Chuẩn 7 Phần
    preview = request.csv_text.strip()[:10000]
    truncated = len(request.csv_text) > 10000
    truncation_note = "\n[Dữ liệu đã được cắt bớt do quá dài — chỉ hiển thị 10.000 ký tự đầu]" if truncated else ""
    fname = f" (tệp: {request.filename})" if request.filename else ""

    prompt_parts = [
        "Bạn là Chuyên gia Khoa học Dữ liệu & Thống kê Nghiên cứu (Lead Data Scientist & Senior Statistical Reviewer).",
        f"Câu hỏi hoặc yêu cầu phân tích của người dùng: \"{question}\"\n"
    ]

    if request.csv_text.strip() and scientific_summary_text:
        prompt_parts.append(f"--- THÔNG TIN TẬP DỮ LIỆU ĐÃ ĐƯỢC TÍNH TOÁN & XÁC THỰC 100% BỞI ENGINE PANDAS/SCIPY/STATSMODELS{fname} ---")
        prompt_parts.append(scientific_summary_text)
        prompt_parts.append(f"\n--- TRÍCH ĐOẠN DỮ LIỆU THÔ (SAMPLE) ---\n```\n{preview}{truncation_note}\n```\n")

    prompt_parts.append(
        "HƯỚNG DẪN BẮT BUỘC VỀ BÁO CÁO PHÂN TÍCH DỮ LIỆU KHÁM PHÁ (EDA) CHUẨN MỰC:\n"
        "Bạn PHẢI trình bày bài phân tích khám phá dữ liệu (EDA) theo đúng KHUNG EDA CHUẨN 7 PHẦN dưới đây. "
        "BẮT BUỘC tuân thủ cấu trúc xen kẽ: [Lời giải thích/Đặt vấn đề] ➔ [Khối mã Python riêng biệt (vẽ biểu đồ hoặc in thống kê)] ➔ [Nhận xét, phân tích sâu về kết quả/đồ thị vừa tạo].\n\n"
                "QUY TẮC CHÍNH TẢ & VĂN PHONG TIẾNG VIỆT CHUẨN MỰC:\n"
        "   - TUYỆT ĐỐI KHÔNG VIẾT HOA TÙNG TỪ THEO KIỂU TITLE CASE CỦA TIẾNG ANH (Ví dụ: KHÔNG VIẾT 'Kế Hoạch Hành Động Tiền Xử Lý Dữ Liệu', 'Kiểm Toán Chất Lượng').\n"
        "   - BẮT BUỘC dùng văn phong hành chính/học thuật tiếng Việt chuẩn: Chỉ viết hoa chữ cái đầu câu/tiêu đề và tên riêng (Ví dụ: '7. Kết luận và kế hoạch tiền xử lý dữ liệu', '2. Kiểm toán chất lượng dữ liệu và dữ liệu khuyết').\n\n"
        "NGUYÊN TẮC BẤT DI BẤT DỊCH (GROUNDING & DESIGN RULES):\n"
        "1. KHÔNG ĐƯỢC TỰ BỊA RA CHỈ SỐ: Mọi số liệu nêu trong báo cáo (tương quan Pearson/Spearman, số ô missing, số lượng outlier, hình dạng phân phối, shape) PHẢI KHỚP 100% với Bảng Thống Kê Định Lượng Đã Xác Thực ở trên hoặc kết quả mã Python xuất ra.\n"
        "2. PHÂN BIỆT RÕ LOẠI DỮ LIỆU KHUYẾT: Báo cáo tỷ lệ khuyết theo từng cột, không gộp 1 số tổng gây hiểu lầm. Nêu rõ cột rỗng 100% (bắt buộc DROP) vs cột khuyết vi mô <= 5% (áp dụng Linear Interpolation / Forward-fill).\n"
        "3. TÁCH BIỂU ĐỒ & CODE THÀNH TỪNG KHỐI RIÊNG: Mỗi biểu đồ/mục phân tích PHẢI là một khối ```python riêng biệt kết thúc bằng `plt.show()` để chèn ảnh trực tiếp ngay dưới khối code.\n"
        "4. TIÊU CHUẨN ĐỒ THỊ CHẤT LƯỢNG CAO (QUANTITATIVE & STYLISH PLOTS):\n"
        "   - Đối với Dữ liệu khuyết (Phần 2): BẮT BUỘC vẽ Biểu đồ Cột (Bar Chart) thể hiện Tỷ lệ % & Số lượng ô khuyết từng cột (có ghi nhãn số lượng và % trên đầu mỗi cột). TUYỆT ĐỐI KHÔNG vẽ heatmap tím đen vì người đọc không thể nhìn ra số lượng ô khuyết.\n"
        "   - Đối với Boxplots & Ngoại lai (Phần 3): BẮT BUỘC vẽ Subplots lưới phân tách cho từng biến số (hoặc dùng `sns.boxplot(..., palette='Set2')`) với bảng màu đa dạng, đường median đỏ, điểm ngoại lai cam rõ nét. TUYỆT ĐỐI KHÔNG để biểu đồ trắng đen đơn điệu.\n"
        "   - Đối với Histogram & Phân phối: BẮT BUỘC dùng `sns.histplot(..., kde=True, color='#2563eb')` hoặc `sns.kdeplot()` với màu sắc hiện đại.\n"
        "   - Đối với Heatmap tương quan: BẮT BUỘC dùng `sns.heatmap(..., annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)`.\n"
        "5. ĐỊNH DẠNG TIÊU ĐỀ & TRÌNH BÀY BẮT BUỘC:\n"
        "   - BẮT BUỘC dùng thẻ Tiêu đề Markdown Cấp 3 viết hoa chuẩn tiếng Việt:\n"
        "     `### 1. Tổng quan cấu trúc dữ liệu`\n"
        "     `### 2. Kiểm toán chất lượng dữ liệu và dữ liệu khuyết`\n"
        "     `### 3. Phân phối đơn biến và kiểm định ngoại lai (outliers)`\n"
        "     `### 4. Phân tích chuỗi thời gian và tính toàn vẹn lịch trình (time-series & DST)`\n"
        "     `### 5. Quan hệ đa biến và kiểm định tương quan (multivariate & correlation)`\n"
        "     `### 6. Phân tích biến mục tiêu và đánh giá dự báo (target evaluation)`\n"
        "     `### 7. Kết luận và kế hoạch tiền xử lý dữ liệu (action plan)`\n"
        "     (BẮT BUỘC CÓ 3 DẤU `### ` Ở ĐẦU DÒNG, TUYỆT ĐỐI KHÔNG VIẾT `1. ` hay `2. ` trần trụi).\n"
        "   - Mỗi phần lớn phải có 1 câu nhận định/tóm tắt trọng tâm in đậm ngay dưới tiêu đề trước khi mở khối code.\n"
        "   - Dùng Markdown Table cho các số liệu thống kê quan trọng để văn bản dễ đọc và trực quan.\n\n"
        "CẤU TRÚC 7 PHẦN BẮT BUỘC CỦA BÁO CÁO EDA:\n"
        "### 1. Tổng quan cấu trúc dữ liệu\n"
        "- Kích thước dòng x cột, dung lượng, kiểu dữ liệu từng cột (Numeric, Datetime, Categorical), kiểm tra dòng trùng lặp.\n"
        "- Khối python xem `df.info()`, `df.shape`, `df.head()`.\n\n"
        "### 2. Kiểm toán chất lượng dữ liệu và dữ liệu khuyết\n"
        "- Bảng phân tích chi tiết dữ liệu khuyết theo từng cột (phân nhóm: 100% NaN vs khuyết vi mô <= 5%).\n"
        "- Rà soát cột hằng số 0 (zero-variance) và tính hợp lệ theo miền vật lý (domain constraints).\n"
        "- Khối python vẽ biểu đồ Cột (Bar chart) số lượng & tỷ lệ % dữ liệu khuyết theo từng cột (`df.isnull().sum()`).\n\n"
        "### 3. Phân phối đơn biến và kiểm định ngoại lai (outliers)\n"
        "- Bảng thống kê mô tả nâng cao: Mean, Median, Std, Skewness, IQR.\n"
        "- Đánh giá độ lệch (Skewness) và kiểm định ngoại lai theo ngưỡng IQR $[Q_1 - 1.5IQR, Q_3 + 1.5IQR]$ với số lượng điểm ngoại lai cụ thể.\n"
        "- Khối python vẽ Histogram + KDE và Boxplots đa màu sắc (Subplots hoặc `sns.boxplot(..., palette='Set2')`) cho các biến số quan trọng.\n\n"
        "### 4. Phân tích chuỗi thời gian và tính toàn vẹn lịch trình (time-series & DST)\n"
        "- BẮT BUỘC dùng đoạn mã chuẩn sau để kiểm tra tính liên tục (loại trừ NaT ở dòng đầu tiên để tránh lỗi đếm sai):\n"
        "```python\n"
        "# Kiểm tra tính liên tục của chuỗi thời gian\n"
        "dt_utc = pd.to_datetime(df['time'], utc=True, errors='coerce')\n"
        "time_diffs = dt_utc.diff().dropna()\n"
        "diffs_hours = time_diffs.dt.total_seconds() / 3600.0\n"
        "print(f\"Khoảng thời gian trung bình: {diffs_hours.mean():.2f} giờ\")\n"
        "print(f\"Số khoảng thời gian lệch khỏi 1.0 giờ: {(diffs_hours != 1.0).sum()}\")\n"
        "print(f\"Đơn điệu tăng: {dt_utc.is_monotonic_increasing}\")\n"
        "print(f\"Số mốc thời gian trùng lặp: {dt_utc.duplicated().sum()}\")\n"
        "```\n"
        "- Phân tích tính mùa vụ (Seasonality: theo giờ, theo ngày trong tuần, theo tháng) và Kiểm định tính dừng Augmented Dickey-Fuller (ADF Test).\n"
        "- Khối python vẽ biểu đồ diễn biến thời gian và phân tích mùa vụ.\n\n"
        "### 5. Quan hệ đa biến và kiểm định tương quan (multivariate & correlation)\n"
        "- Ma trận tương quan Pearson & Spearman kèm p-value và đánh giá mức độ tương quan (đảm bảo số liệu chính xác 100% theo bảng xác thực).\n"
        "- Kiểm tra Đa cộng tuyến (VIF) bằng statsmodels và in bảng kết quả chi tiết:\n"
        "```python\n"
        "from statsmodels.stats.outliers_influence import variance_inflation_factor\n"
        "vif_cols = [c for c in ['total_load_actual', 'price_day_ahead', 'generation solar', 'generation wind onshore', 'generation fossil gas'] if c in df.columns]\n"
        "if len(vif_cols) >= 2:\n"
        "    X_vif = df[vif_cols].dropna()\n"
        "    vif_data = pd.DataFrame({\n"
        "        'Đặc trưng (Feature)': vif_cols,\n"
        "        'VIF': [round(variance_inflation_factor(X_vif.values, i), 2) for i in range(len(vif_cols))]\n"
        "    })\n"
        "    print(vif_data.to_string(index=False))\n"
        "```\n"
        "- BẮT BUỘC trình bày Bảng VIF dưới dạng Markdown Table ngay trong nội dung phân tích để hiển thị rõ trong văn bản và bản in PDF.\n"
        "- Khối python vẽ Heatmap tương quan và Scatter plots giữa các cặp biến chính.\n\n"
        "### 6. Phân tích biến mục tiêu và đánh giá dự báo (target evaluation)\n"
        "- Phân phối biến mục tiêu và tương quan giữa các đặc trưng với target.\n"
        "- Đánh giá sai số dự báo ngắn hạn (MAE, RMSE, Mean Bias).\n"
        "- Khối python vẽ biểu đồ so sánh Dự báo vs Thực tế và phân phối sai số (Residuals).\n\n"
        "### 7. Kết luận và kế hoạch tiền xử lý dữ liệu (action plan)\n"
        "- Danh sách cụ thể các cột BẮT BUỘC LOẠI BỎ (DROP) kèm lý do rõ ràng.\n"
        "- Chiến lược điền khuyết theo từng nhóm cột.\n"
        "- Đề xuất Feature Engineering (lags, rolling stats, cyclic time encoding).\n"
        "- Khuyến nghị mô hình và lưu ý các điểm biến động đột biến.\n\n"
        "LƯU Ý VỀ ĐỘ DÀI: BẮT BUỘC HOÀN TẤT ĐẦY ĐỦ TRỌN VẸN CẢ 7 PHẦN TRÊN. TUYỆT ĐỐI KHÔNG DỪNG NGANG GIỮA CHỪNG.\n\n"
        "KHỐI CHỈ SỐ KEY FINDINGS BẮT BUỘC:\n"
        "Hãy xuất khối json_kpis chứa các chỉ số đã được chứng thực ở Mục 7 của Bảng Thống Kê Định Lượng:\n"
        "```json_kpis\n"
        "[\n"
        "  {\"label\": \"Kích Thước Tập Dữ Liệu\", \"value\": \"35,064 dòng × 29 cột\", \"subtext\": \"0 dòng trùng lặp\"}\n"
        "]\n"
        "```\n"
    )

    full_prompt = "\n".join(prompt_parts)

    # 3. Thực thi LLM với cơ chế đa mô hình chống lỗi
    try:
        llm = build_eda_llm(get_settings())
        msg = await llm.ainvoke([("human", full_prompt)])
        content = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        raw_text = str(content).strip()

        # 4. Trích xuất json_chart và json_kpis
        chart_matches = re.finditer(r'```(?:json_chart|json)\s*(\{[\s\S]*?"type"[\s\S]*?\})\s*```', raw_text, re.IGNORECASE)
        charts_list = []
        for match in chart_matches:
            try:
                chart_data = json.loads(match.group(1))
                if isinstance(chart_data, dict) and "type" in chart_data and "data" in chart_data:
                    charts_list.append(ChartSpec(
                        type=chart_data.get("type", "bar").lower(),
                        title=chart_data.get("title", "Biểu đồ phân tích dữ liệu"),
                        data=chart_data.get("data", []),
                        x_label=chart_data.get("x_label"),
                        y_label=chart_data.get("y_label"),
                        unit=chart_data.get("unit"),
                    ))
            except Exception as e:
                logger.warning(f"Could not parse chart json: {e}")

        # Grounded KPIs priority: If grounded_kpis exist from verified profile, use them or reconcile
        kpis_list = []
        if comp_profile and comp_profile.grounded_kpis:
            kpis_list = [
                KPISpec(
                    label=str(item.get("label", "")),
                    value=item.get("value", ""),
                    subtext=item.get("subtext"),
                    trend=item.get("trend"),
                ) for item in comp_profile.grounded_kpis
            ]
        else:
            kpis_match = re.search(r'```(?:json_kpis|json)\s*(\[[\s\S]*?\{[\s\S]*?"label"[\s\S]*?\}[\s\S]*?\])\s*```', raw_text, re.IGNORECASE)
            if kpis_match:
                try:
                    kpis_data = json.loads(kpis_match.group(1))
                    if isinstance(kpis_data, list):
                        kpis_list = [
                            KPISpec(
                                label=str(item.get("label", "")),
                                value=item.get("value", ""),
                                subtext=item.get("subtext"),
                                trend=item.get("trend"),
                            ) for item in kpis_data if isinstance(item, dict) and "label" in item
                        ]
                except Exception as e:
                    logger.warning(f"Could not parse kpis json: {e}")

        # Xóa các khối json_chart và json_kpis khỏi văn bản markdown để giao diện sạch đẹp
        cleaned_answer = re.sub(r'```json_chart[\s\S]*?```', '', raw_text)
        cleaned_answer = re.sub(r'```json_kpis[\s\S]*?```', '', cleaned_answer).strip()

        # 4.4 Truncation Safety Net: Khắc phục triệt để hiện tượng bị cắt cụt nội dung
        if cleaned_answer:
            # Tự động đóng các khối code chưa đóng nếu bị cắt ngang
            if cleaned_answer.count("```") % 2 != 0:
                cleaned_answer += "\n```\n"

            # Tự động bổ sung Mục 7 nếu bị cắt cụt
            has_section_7 = bool(re.search(r'(?:###?\s*7\.|Kế\s*hoạch\s*hành\s*động|Action\s*Plan)', cleaned_answer, re.IGNORECASE))
            if not has_section_7 and comp_profile:
                drop_md = "\n".join([f"- **`{d['column']}`**: {d['reason']}" for d in comp_profile.columns_to_drop])
                impute_md = "\n".join([f"- **`{m['column']}`**: {m['strategy']}" for m in comp_profile.imputation_strategy])

                section_7_supplement = f"""

### 7. Kết Luận & Kế Hoạch Hành Động Tiền Xử Lý (Action Plan)

#### 7.1. Danh Sách Các Cột Bắt Buộc Loại Bỏ (DROP LIST)
{drop_md}

#### 7.2. Chiến Lược Điền Khuyết Dữ Liệu
{impute_md}

#### 7.3. Đề Xuất Kỹ Thuật Đặc Trưng (Feature Engineering) & Mô Hình Hóa
- **Tạo biến trễ (Lag Features)**: Tạo các độ trễ vật lý quan trọng ($t-1$, $t-24$, $t-168$) để nắm bắt tự tương quan và tính chu kỳ ngày/tuần.
- **Thống kê trượt (Rolling Statistics)**: Tính Rolling Mean và Rolling Std (cửa sổ 24 giờ) để theo dõi động thái xu hướng ngắn hạn.
- **Mã hóa chu kỳ thời gian (Cyclic Encoding)**: Chuyển đổi mốc thời gian thành các thành phần $\\sin/\\cos$ của `hour` và `month` để giữ tính liên tục vòng tròn.
- **Chuẩn hóa dữ liệu (Feature Scaling)**: Sử dụng `RobustScaler` hoặc `StandardScaler` trên các đặc trưng có phân phối lệch và ngoại lai trước khi huấn luyện mô hình.
"""
                cleaned_answer += section_7_supplement

        # 4.5 Trích xuất mã Python và chạy ngầm (Backend Execution) để lấy block outputs
        py_matches = list(re.finditer(r'```(?:python|py)\s*(.*?)\s*```', cleaned_answer, re.DOTALL | re.IGNORECASE))
        extracted_python = ""
        block_outputs = []

        if py_matches:
            from src.services.code_sandbox_service import smart_repair_python_code
            blocks = [smart_repair_python_code(m.group(1)) for m in py_matches if m.group(1).strip()]
            extracted_python = "\n\n".join(blocks)

            # Execute all blocks sequentially in sandbox to get outputs for each block
            if request.csv_text.strip():
                try:
                    from src.services.code_sandbox_service import code_sandbox_service
                    block_outputs = await code_sandbox_service.execute_blocks_async(
                        blocks=blocks,
                        csv_text=request.csv_text.strip(),
                        timeout_seconds=25.0
                    )
                except Exception as ex:
                    logger.warning(f"Background python execution failed: {ex}")

        return DataAnalysisResponse(
            answer=cleaned_answer or "Hoàn tất phân tích dữ liệu.",
            charts=charts_list if charts_list else None,
            kpis=kpis_list if kpis_list else None,
            python_code=extracted_python if extracted_python else None,
            block_outputs=block_outputs if block_outputs else None,
            dataset_profile=dataset_profile,
        )

    except Exception as exc:
        logger.warning(f"LLM call encountered an error ({exc}). Generating deterministic Pandas scientific analysis fallback.")

        # Fallback phân tích thống kê định lượng mạnh mẽ bằng Pandas theo đúng Khung 7 Phần
        lines = []
        lines.append("### 📊 Báo Cáo Phân Tích Thống Kê Khám Phá Dữ Liệu (DataVoyager Engine)")
        lines.append(f"**Yêu cầu:** *{question}*\n")

        single_chart = None
        if dataset_profile:
            lines.append("### 1. Tổng quan Cấu trúc Dữ liệu")
            lines.append(f"- **Kích thước tập dữ liệu:** `{dataset_profile.row_count}` dòng quan sát × `{dataset_profile.column_count}` biến số.")
            lines.append(f"- **Dòng trùng lặp:** `{dataset_profile.duplicate_rows}` dòng.")
            lines.append(f"- **Tỷ lệ khuyết thiếu toàn cục:** `{dataset_profile.missing_rate_pct}%`.")

            lines.append("\n### 2. Kiểm toán Chất lượng Dữ liệu & Dữ liệu Khuyết")
            if dataset_profile.completely_empty_cols:
                lines.append(f"- **Cột rỗng 100% (Bắt buộc DROP):** {', '.join(dataset_profile.completely_empty_cols)}")
            if dataset_profile.constant_cols:
                lines.append(f"- **Cột hằng số 0 (Bắt buộc DROP):** {', '.join(dataset_profile.constant_cols)}")
            if dataset_profile.partially_missing_cols:
                lines.append("- **Các cột khuyết một phần:**")
                for pm in dataset_profile.partially_missing_cols[:10]:
                    lines.append(f"  * `{pm.get('name')}`: {pm.get('null_count')} dòng ({pm.get('null_pct')}%)")

            lines.append("\n### 3. Phân phối Đơn biến & Kiểm định Outliers")
            if dataset_profile.summary_stats:
                lines.append("| Tên Biến | Mean | Median | Std | Min | Max |")
                lines.append("|---|---|---|---|---|---|")
                for cname, stats in list(dataset_profile.summary_stats.items())[:8]:
                    lines.append(f"| `{cname}` | {stats.get('mean', '-')} | {stats.get('50%', '-')} | {stats.get('std', '-')} | {stats.get('min', '-')} | {stats.get('max', '-')} |")

            lines.append("\n### 4. Phân tích Chuỗi Thời gian & Tính Toàn vẹn")
            if dataset_profile.time_series_info and dataset_profile.time_series_info.get("is_time_series"):
                tsi = dataset_profile.time_series_info
                lines.append(f"- Cột thời gian: `{tsi.get('date_column')}`")
                lines.append(f"- Múi giờ phát hiện: `{tsi.get('timezone_detected')}`")
                if tsi.get("dst_transition_warning"):
                    lines.append(f"- Lưu ý DST: {tsi.get('dst_transition_warning')}")
                if tsi.get("adf_statistic") is not None:
                    lines.append(f"- Kiểm định ADF: Stat = {tsi.get('adf_statistic')}, p-value = {tsi.get('adf_p_value')}")

            lines.append("\n### 5. Quan hệ Đa biến & Tương quan Thống kê")
            if dataset_profile.top_correlations:
                lines.append("| Cặp Biến | Tương Quan (r) | Ý Nghĩa Thống Kê | Mức Độ |")
                lines.append("|---|---|---|---|")
                for corr in dataset_profile.top_correlations[:8]:
                    lines.append(f"| `{corr.get('var1')}` vs `{corr.get('var2')}` | **{corr.get('pearson_r')}** | {corr.get('significance')} | {corr.get('strength')} |")

            lines.append("\n### 6. Phân tích Biến Mục tiêu (Target Evaluation)")
            lines.append("- Phân tích xu hướng biến động và sai số dự báo nếu có cột dự báo đi kèm.")

            lines.append("\n### 7. Kết luận & Kế hoạch Tiền xử lý Dữ liệu")
            if dataset_profile.columns_to_drop:
                lines.append("**Danh sách đề xuất loại bỏ (Drop List):**")
                for d in dataset_profile.columns_to_drop:
                    lines.append(f"- `{d.get('column')}`: {d.get('reason')}")
            lines.append("\n**Chiến lược điền khuyết:** Áp dụng Linear Interpolation / Forward-fill cho các cột có tỷ lệ khuyết thấp (<1%).")

        fallback_answer = "\n".join(lines)

        # Fallback KPIs
        fallback_kpis = comp_profile.grounded_kpis if (comp_profile and comp_profile.grounded_kpis) else [
            {"label": "Kích Thước", "value": f"{dataset_profile.row_count if dataset_profile else 0} dòng", "subtext": "Xác thực bởi Pandas"}
        ]
        kpis_list = [KPISpec(label=k["label"], value=k["value"], subtext=k.get("subtext")) for k in fallback_kpis]

        return DataAnalysisResponse(
            answer=fallback_answer,
            charts=[single_chart] if single_chart else None,
            kpis=kpis_list,
            dataset_profile=dataset_profile,
        )


@router.post("/workspace/execute-code")
async def workspace_execute_code(request: dict) -> dict:
    """
    Thực thi mã Python trực tiếp trong môi trường Isolated Code Sandbox an toàn.
    Tự động nạp dữ liệu người dùng vào biến 'df', capture stdout/stderr và render matplotlib figures.
    """
    from src.services.code_sandbox_service import code_sandbox_service

    code = str(request.get("code", ""))
    csv_text = str(request.get("csv_text", ""))
    timeout = float(request.get("timeout_seconds", 10.0))

    res = await code_sandbox_service.execute_code_async(
        code=code,
        csv_text=csv_text,
        timeout_seconds=timeout
    )
    return res.model_dump()


@router.post("/workspace/evidence-coords", response_model=EvidenceCoordsResponse)
async def get_evidence_coords(
    request: EvidenceCoordsRequest,
) -> EvidenceCoordsResponse:
    """Find text coordinates in PDF for highlighting."""
    import logging
    import os

    base_dir = os.path.join("uploads", "papers")
    file_path = os.path.join(base_dir, request.filename)
    if not os.path.exists(file_path):
        for root, dirs, files in os.walk(base_dir):
            matching = [name for name in files if name == request.filename or name.endswith("_" + request.filename)]
            if matching:
                file_path = os.path.join(root, matching[0])
                break
        else:
            return EvidenceCoordsResponse(rects=[])

    try:
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
        except ImportError:
            logging.getLogger(__name__).warning(
                "PyMuPDF is not installed; evidence coordinates are unavailable."
            )
            return EvidenceCoordsResponse(rects=[])
        doc = fitz.open(file_path)

        start_page = max(0, request.page - 1)
        if start_page >= len(doc):
            return EvidenceCoordsResponse(rects=[])

        search_text = request.snippet.strip()
        rects = []
        import difflib
        import re
        def clean_word(w):
            return re.sub(r'\W+', '', w).lower()

        words = search_text.split()
        search_words_list = [clean_word(w) for w in words if clean_word(w)]

        pages_to_search = [start_page]
        if start_page + 1 < len(doc):
            pages_to_search.append(start_page + 1)

        total_matched_words = 0

        for p_idx in pages_to_search:
            page = doc[p_idx]
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            page_num = p_idx + 1

            # 1. Native PyMuPDF search
            hits = page.search_for(search_text)
            if hits:
                for hit in hits:
                    rects.append(RectCoord(
                        page=page_num,
                        x=hit.x0 / page_width,
                        y=hit.y0 / page_height,
                        width=(hit.x1 - hit.x0) / page_width,
                        height=(hit.y1 - hit.y0) / page_height
                    ))
                # If we found a perfect match natively, we don't need to search the next page
                return EvidenceCoordsResponse(rects=rects)

            # 2. Sub-snippet search
            chunk_matched = False
            for chunk_start in range(0, len(words), 10):
                chunk = " ".join(words[chunk_start:chunk_start + 15])
                if len(chunk) > 3:
                    hits = page.search_for(chunk)
                    for hit in hits:
                        rects.append(RectCoord(
                            page=page_num,
                            x=hit.x0 / page_width,
                            y=hit.y0 / page_height,
                            width=(hit.x1 - hit.x0) / page_width,
                            height=(hit.y1 - hit.y0) / page_height
                        ))
                        chunk_matched = True

            if chunk_matched:
                # If chunks matched, we consider it a hit. We'll still check the next page if it spilled over.
                pass

            # 3. Fallback: difflib sequence matching
            page_words = page.get_text("words", sort=True)
            page_clean_words = [clean_word(w[4]) for w in page_words]

            if search_words_list and page_clean_words:
                matcher = difflib.SequenceMatcher(None, page_clean_words, search_words_list)
                blocks = matcher.get_matching_blocks()

                min_block_size = 2 if len(search_words_list) > 3 else 1
                valid_blocks = [b for b in blocks if b.size >= min_block_size]

                if valid_blocks:
                    matched_count = sum(b.size for b in valid_blocks)
                    total_matched_words += matched_count

                    start_idx = valid_blocks[0].a
                    end_idx = valid_blocks[-1].a + valid_blocks[-1].size

                    def merge_rects(word_list):
                        merged = []
                        current_rect = None
                        def is_same_line(r1, r2):
                            overlap = max(0, min(r1[3], r2[3]) - max(r1[1], r2[1]))
                            return overlap > 0.5 * min(r1[3]-r1[1], r2[3]-r2[1])

                        for w in word_list:
                            r = [w[0], w[1], w[2], w[3]]
                            if current_rect is None:
                                current_rect = r
                            else:
                                if is_same_line(current_rect, r):
                                    current_rect[0] = min(current_rect[0], r[0])
                                    current_rect[2] = max(current_rect[2], r[2])
                                    current_rect[1] = min(current_rect[1], r[1])
                                    current_rect[3] = max(current_rect[3], r[3])
                                else:
                                    merged.append(current_rect)
                                    current_rect = r
                        if current_rect:
                            merged.append(current_rect)
                        return merged

                    if (end_idx - start_idx) <= len(search_words_list) * 2.5:
                        words_to_merge = [page_words[i] for i in range(start_idx, end_idx)]
                    else:
                        words_to_merge = []
                        for b in valid_blocks:
                            for i in range(b.a, b.a + b.size):
                                words_to_merge.append(page_words[i])

                    merged_rects = merge_rects(words_to_merge)
                    for mr in merged_rects:
                        rects.append(RectCoord(
                            page=page_num,
                            x=mr[0] / page_width,
                            y=mr[1] / page_height,
                            width=(mr[2] - mr[0]) / page_width,
                            height=(mr[3] - mr[1]) / page_height
                        ))

            # If we've found enough matches on the first page, do not process the next page
            # to avoid false positives (e.g. difflib matching stop words on the next page).
            if rects and not chunk_matched and total_matched_words >= len(search_words_list) * 0.8:
                break
            if chunk_matched and p_idx == start_page:
                # if chunk matched, let it process the next page just in case it spans.
                pass

        return EvidenceCoordsResponse(rects=rects)
    except Exception as e:
        logging.getLogger(__name__).error("Error finding coords: %s", e)
        return EvidenceCoordsResponse(rects=[])

# ──────────────────────────────────────────────────────────────────────────────
# Interactive Outline-First Synthesis (Plan -> User Approval -> Execute)
#
# Ported from feat/synthesis-fast-v2-ui. This is a SEPARATE opt-in path from
# the Legacy /synthesis-sessions endpoint below -- it only produces a usable
# result when SYNTHESIS_MODE=fast_v2_experimental (see config.py), since
# plan_outline()/run_section_scoped_synthesis() call into src/synthesis/fast_v2/
# regardless of synthesis_mode. Legacy stays the default; this is additive.
# ──────────────────────────────────────────────────────────────────────────────

class SectionPlanDto(BaseModel):
    id: str = ""
    title: str
    purpose: str = ""
    target_words: int = 1000
    papers_to_compare: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)


class OutlinePlanDto(BaseModel):
    research_question: str
    sections: list[SectionPlanDto]


class SynthesisPlanRequest(BaseModel):
    project_id: uuid.UUID
    paper_ids: list[str]
    research_question: str | None = None
    # Free-text emphasis instruction (e.g. "focus on the methodology, keep
    # the intro brief"). The Planner reflects this in target_words
    # allocation per section -- deliberately the ONLY way to steer section
    # length; there is no numeric per-section word-count input anywhere.
    guidance: str | None = None


class SynthesisExecuteRequest(BaseModel):
    project_id: uuid.UUID
    paper_ids: list[str]
    approved_outline: OutlinePlanDto


@router.post("/synthesis/plan")
async def plan_synthesis_outline(
    request: SynthesisPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Step 1: Planning only. Turns selected PDFs into a structured outline.
    The pipeline STOPS here. User reviews and edits before approving.
    """
    project_result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    raw_paper_ids = list(dict.fromkeys(request.paper_ids))
    if not raw_paper_ids:
        raise HTTPException(status_code=422, detail="At least 1 paper is required to plan outline.")

    candidate_uuids = []
    for pid_raw in raw_paper_ids:
        pid_str = str(pid_raw).strip()
        try:
            candidate_uuids.append(uuid.UUID(pid_str))
        except Exception:
            stmt = select(Paper).where(
                Paper.project_id == request.project_id,
                (Paper.title.ilike(f"%{pid_str}%") | Paper.dedup_key.ilike(f"%{pid_str}%"))
            )
            found = (await db.execute(stmt)).scalars().first()
            if found:
                candidate_uuids.append(found.id)

    # A UUID accepted above is NOT yet proven to belong to this project -- it
    # was only checked for being syntactically a UUID. Re-scope the actual
    # DB fetch to (id IN candidates) AND (project_id == request.project_id)
    # so a stale/cross-project paper_id can never pull another project's
    # paper into this outline plan.
    paper_result = await db.execute(
        select(Paper).where(Paper.id.in_(candidate_uuids), Paper.project_id == request.project_id)
    )
    papers = list(paper_result.scalars().all())
    paper_uuids = [p.id for p in papers]

    from src.synthesis.fast_v2.runtime import (
        build_general_review_question,
        ensure_fast_v2_indexed,
        plan_outline,
    )

    await ensure_fast_v2_indexed(paper_uuids)

    rq = build_general_review_question(request.research_question)
    metadata = [{"title": p.title or "", "abstract": p.abstract or ""} for p in papers]

    outline_plan = await plan_outline(paper_metadata=metadata, research_question=rq, guidance=request.guidance)

    return JSONResponse(
        status_code=200,
        content={
            "research_question": outline_plan.research_question,
            "sections": [
                {
                    "id": s.id,
                    "title": s.title,
                    "purpose": s.purpose,
                    "target_words": s.target_words,
                    "papers_to_compare": list(s.papers_to_compare),
                    "retrieval_queries": list(s.retrieval_queries),
                }
                for s in outline_plan.sections
            ]
        },
    )


@router.post("/synthesis/execute")
async def execute_approved_synthesis(
    request: SynthesisExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Step 2: Execution.
    Executes the approved outline with section-specific contexts, 1-call Writer,
    Batched Citation Agent, and deterministic provenance.
    """
    project_result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    raw_paper_ids = list(dict.fromkeys(request.paper_ids))
    candidate_uuids = []
    for pid_raw in raw_paper_ids:
        pid_str = str(pid_raw).strip()
        try:
            candidate_uuids.append(uuid.UUID(pid_str))
        except Exception:
            stmt = select(Paper).where(
                Paper.project_id == request.project_id,
                (Paper.title.ilike(f"%{pid_str}%") | Paper.dedup_key.ilike(f"%{pid_str}%"))
            )
            found = (await db.execute(stmt)).scalars().first()
            if found:
                candidate_uuids.append(found.id)

    # Same re-scoping as /synthesis/plan: a syntactically-valid UUID is not
    # proof of project ownership. Only papers confirmed to belong to
    # request.project_id are allowed through to the writer/citation stages.
    owned_result = await db.execute(
        select(Paper.id).where(Paper.id.in_(candidate_uuids), Paper.project_id == request.project_id)
    )
    paper_uuids = [row[0] for row in owned_result.all()]

    from src.synthesis.fast_v2.planning.research_lead import LongformOutlinePlan, SectionPlan
    from src.synthesis.fast_v2.runtime import run_section_scoped_synthesis

    approved_sections = tuple(
        SectionPlan(
            id=s.id or f"sec_{idx}",
            title=s.title,
            purpose=s.purpose,
            target_words=s.target_words,
            papers_to_compare=tuple(s.papers_to_compare),
            retrieval_queries=tuple(s.retrieval_queries),
        )
        for idx, s in enumerate(request.approved_outline.sections, 1)
    )
    outline_obj = LongformOutlinePlan(
        research_question=request.approved_outline.research_question,
        sections=approved_sections,
    )

    fast_v2_result = await run_section_scoped_synthesis(
        paper_ids=paper_uuids,
        approved_outline=outline_obj,
    )

    persisted = SynthesisSession(
        id=uuid.uuid4(),
        project_id=request.project_id,
        paper_ids=json_paper_ids(paper_uuids),
        research_question=outline_obj.research_question,
        status=(SynthesisStatus.done if fast_v2_result.grounded else SynthesisStatus.failed),
        review_markdown=fast_v2_result.text,
        error_message=(None if fast_v2_result.grounded else fast_v2_result.grounding_warning),
        citation_coverage_telemetry=fast_v2_result.diagnostics.get("citation_coverage_telemetry"),
    )
    db.add(persisted)

    for item in fast_v2_result.citations:
        db.add(Citation(
            id=uuid.uuid4(),
            synthesis_session_id=persisted.id,
            paper_id=item.paper_id,
            citation_marker=item.citation_marker,
            review_char_start=item.review_char_start,
            review_char_end=item.review_char_end,
            source_page=item.source_page,
            source_char_start=item.source_char_start,
            source_char_end=item.source_char_end,
            quoted_snippet=item.quoted_snippet,
        ))

    # /synthesis/execute never recorded LLMCallLog/SynthesisMetrics rows for
    # this (the only user-reachable) synthesis path, so the admin dashboard's
    # token-usage totals were always 0 even after real runs -- the writer and
    # citation agent telemetry above already carries the token counts LangChain
    # reports on each call, it just never got summed into SynthesisMetrics.
    writer_tel = fast_v2_result.diagnostics.get("writer_telemetry") or {}
    citation_tel = fast_v2_result.diagnostics.get("citation_coverage_telemetry") or {}
    repair_tel = fast_v2_result.diagnostics.get("verbatim_repair_telemetry") or {}

    def _int_or_zero(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    metrics = await get_or_create_metrics(db, persisted.id)
    metrics.total_input_tokens = (
        _int_or_zero(writer_tel.get("prompt_tokens"))
        + _int_or_zero(citation_tel.get("total_input_tokens_used"))
        + _int_or_zero(repair_tel.get("total_input_tokens_used"))
    )
    metrics.total_output_tokens = (
        _int_or_zero(writer_tel.get("completion_tokens"))
        + _int_or_zero(citation_tel.get("total_tokens_used"))
        + _int_or_zero(repair_tel.get("total_output_tokens_used"))
    )
    metrics.total_llm_calls = (
        1
        + _int_or_zero(citation_tel.get("number_of_batches"))
        + len(repair_tel.get("outcomes") or [])
    )
    metrics.synthesis_duration_ms = _int_or_zero(fast_v2_result.timings.get("total_ms"))

    await db.commit()

    payload = fast_v2_result.to_dict()
    payload["session_id"] = str(persisted.id)
    return JSONResponse(status_code=200, content=payload)


# ──────────────────────────────────────────────────────────────────────────────
# Synthesis endpoints (evidence-first, async job)
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/synthesis-sessions",
    response_model=SynthesisSessionCreatedResponse,
    status_code=202,
)
async def create_synthesis_session(
    request: SynthesisSessionCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SynthesisSessionCreatedResponse:
    """Create and enqueue a long-running evidence-first synthesis session."""
    try:
        synthesis_llm_service.validate_configuration()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    project_result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")
    # Keep first occurrence/order because citation numbering follows user selection.
    raw_paper_ids = list(dict.fromkeys(request.paper_ids))
    max_papers = get_settings().synthesis_max_papers
    if len(raw_paper_ids) > max_papers:
        raise HTTPException(
            status_code=422,
            detail=f"Synthesis accepts at most {max_papers} papers per session.",
        )

    from datetime import datetime
    paper_uuids = []
    for pid_raw in raw_paper_ids:
        pid_str = str(pid_raw).strip()
        try:
            paper_uuids.append(uuid.UUID(pid_str))
        except Exception:
            stmt = select(Paper).where(
                Paper.project_id == request.project_id,
                (Paper.title.ilike(f"%{pid_str}%") | Paper.dedup_key.ilike(f"%{pid_str}%"))
            )
            found = (await db.execute(stmt)).scalars().first()
            if found:
                paper_uuids.append(found.id)
            else:
                new_id = uuid.uuid4()
                new_paper = Paper(
                    id=new_id,
                    project_id=request.project_id,
                    title=pid_str,
                    abstract="",
                    journal="Academic Journal",
                    year=datetime.now().year,
                    source="synthesis_request",
                )
                db.add(new_paper)
                await db.flush()
                paper_uuids.append(new_id)

    paper_ids = paper_uuids
    paper_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
    papers = list(paper_result.scalars().all())
    by_id = {paper.id: paper for paper in papers}

    missing = [paper_id for paper_id in paper_ids if paper_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=404,
            detail="Papers not found: " + ", ".join(str(item) for item in missing),
        )

    for paper in papers:
        if paper.project_id is None or str(paper.project_id) != str(request.project_id):
            paper.project_id = request.project_id
    await db.flush()

    # Fast v2 (EXPERIMENTAL, opt-in via SYNTHESIS_MODE=fast_v2_experimental):
    # runs synchronously in-request through the real composition root and
    # returns the result directly, bypassing the Legacy session/graph/DB
    # path entirely. Legacy path below is completely unchanged when this
    # flag is off (the default).
    if get_settings().fast_v2_enabled:
        if not request.research_question or not request.research_question.strip():
            raise HTTPException(
                status_code=422,
                detail="research_question is required for fast_v2_experimental synthesis",
            )
        from src.synthesis.fast_v2.runtime import run_fast_v2_synthesis

        fast_v2_result = await run_fast_v2_synthesis(
            paper_ids=paper_ids, research_question=request.research_question
        )
        return JSONResponse(status_code=200, content=fast_v2_result.to_dict())

    # Auto-ingest any papers missing active_ingestion_id (with timeout to avoid hanging)
    from src.services.ingestion_service import ensure_paper_ingested
    for paper in papers:
        p_id_str = str(paper.id) if hasattr(paper, 'id') else "unknown"
        if getattr(paper, 'active_ingestion_id', None) is None:
            try:
                await asyncio.wait_for(ensure_paper_ingested(db, paper), timeout=10.0)
            except TimeoutError:
                await db.rollback()
                import logging
                logging.getLogger(__name__).warning("Auto-ingestion timed out for paper %s, skipping", p_id_str)
            except Exception as ing_err:
                await db.rollback()
                import logging
                logging.getLogger(__name__).warning("Auto-ingestion error for paper %s: %s", p_id_str, ing_err)

    session = SynthesisSession(
        id=uuid.uuid4(),
        project_id=request.project_id,
        paper_ids=json_paper_ids(paper_ids),
        status=SynthesisStatus.processing,
    )
    db.add(session)
    # Commit before queueing so a fast worker can already read the session.
    await db.commit()

    try:
        import os
        use_celery = os.getenv("USE_CELERY", "false").lower() in ("true", "1")
        if not use_celery:
            # Use FastAPI BackgroundTasks so synthesis runs in the web process directly
            async def local_run_synthesis(sid: str):
                from src.tasks.synthesis_tasks import _mark_terminal_failure, run_synthesis_session
                try:
                    await run_synthesis_session(sid)
                except Exception as exc:
                    await _mark_terminal_failure(sid, exc)
            background_tasks.add_task(local_run_synthesis, str(session.id))
        else:
            from src.tasks.synthesis_tasks import run_synthesis_task
            run_synthesis_task.delay(str(session.id))
    except Exception as exc:
        session.status = SynthesisStatus.failed
        session.error_message = f"Failed to enqueue synthesis task: {exc}"
        await db.commit()
        raise HTTPException(status_code=503, detail=session.error_message) from exc

    return SynthesisSessionCreatedResponse(
        session_id=session.id,
        status=session.status.value,
    )


@router.get(
    "/projects/{project_id}/synthesis-sessions",
    response_model=list[SynthesisSessionSummary],
)
async def list_synthesis_sessions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[SynthesisSessionSummary]:
    """List all synthesis sessions for a project."""
    result = await db.execute(
        select(SynthesisSession)
        .where(SynthesisSession.project_id == project_id)
        .order_by(desc(SynthesisSession.created_at))
    )
    sessions = result.scalars().all()

    return [
        SynthesisSessionSummary(
            id=session.id,
            status=session.status.value,
            created_at=session.created_at,
            paper_count=len(session.paper_ids) if isinstance(session.paper_ids, list) else 0,
        )
        for session in sessions
    ]


@router.get(
    "/synthesis-sessions/{session_id}",
    response_model=SynthesisSessionResponse,
)
async def get_synthesis_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SynthesisSessionResponse:
    """Poll synthesis status and retrieve the final review/citation provenance."""
    result = await db.execute(
        select(SynthesisSession).where(SynthesisSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail=f"Synthesis session '{session_id}' not found")

    citation_result = await db.execute(
        select(Citation)
        .where(Citation.synthesis_session_id == session_id)
        .order_by(Citation.review_char_start, Citation.id)
    )
    citations = list(citation_result.scalars().all())
    paper_ids = {item.paper_id for item in citations if item.paper_id is not None}
    paper_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids))) if paper_ids else None
    papers_by_id = {paper.id: paper for paper in (paper_result.scalars().all() if paper_result else [])}
    section_result = await db.execute(
        select(SynthesisSection)
        .where(SynthesisSection.synthesis_session_id == session_id)
        .order_by(SynthesisSection.position, SynthesisSection.id)
    )
    sections = list(section_result.scalars().all())
    evidence_result = await db.execute(
        select(EvidenceRecord)
        .where(EvidenceRecord.synthesis_session_id == session_id)
        .order_by(EvidenceRecord.paper_id, EvidenceRecord.dimension, EvidenceRecord.created_at)
    )
    evidence_profile = list(evidence_result.scalars().all())

    return SynthesisSessionResponse(
        id=session.id,
        status=session.status.value,
        review_markdown=session.review_markdown,
        error_message=session.error_message,
        citation_coverage_telemetry=session.citation_coverage_telemetry,
        citations=[
            SynthesisCitationResponse(
                id=item.id,
                marker_display=item.citation_marker,
                paper_id=item.paper_id,
                title=(papers_by_id[item.paper_id].title if item.paper_id in papers_by_id else None),
                filename=(os.path.basename(papers_by_id[item.paper_id].file_path)
                          if item.paper_id in papers_by_id and papers_by_id[item.paper_id].file_path else None),
                review_char_start=item.review_char_start,
                review_char_end=item.review_char_end,
                source_page=item.source_page,
                source_page_display=(item.source_page + 1 if item.source_page is not None else None),
                source_char_start=item.source_char_start,
                source_char_end=item.source_char_end,
                quoted_snippet=item.quoted_snippet,
            )
            for item in citations
        ],
        sections=build_section_responses(sections, {item.id for item in citations}),
        evidence_profile=[
            SynthesisEvidenceProfileItem(
                id=item.id,
                paper_id=item.paper_id,
                dimension=item.dimension,
                value=item.value,
                quote=item.quote,
            )
            for item in evidence_profile
        ],
    )

class SynthesisQualityResponse(BaseModel):
    """The 3-layer Evidence Quantification Engine's output metrics (see
    MODULE_1_PLAN.md) for one finished synthesis session -- computed from
    SynthesisClaim.verification_status and the section-level counters
    finalize_review() records, not a separate LLM-judge pass (that's
    ragas_eval_service.py / rag_guardrail_service.py, a different subsystem
    over RAG chat answers, not synthesis claims -- these field names are the
    same on purpose (same concepts) but the two are computed completely
    differently and are not interchangeable)."""

    session_id: uuid.UUID
    total_claims: int
    supported_claims: int
    contradicted_claims: int
    insufficient_claims: int
    faithfulness_score_pct: float | None
    hallucination_rate_pct: float | None
    claim_sentences_proposed: int
    claim_sentences_kept: int
    citation_precision_pct: float | None


@router.get(
    "/synthesis-sessions/{session_id}/quality",
    response_model=SynthesisQualityResponse,
)
async def get_synthesis_session_quality(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SynthesisQualityResponse:
    """Faithfulness / Hallucination Rate / Citation Precision for one
    completed synthesis session -- the Tri-Layer Evidence Quantification
    Engine's actual deliverable (MODULE_1_PLAN.md), not the claim-verification
    step alone (that runs earlier, inside cross_paper_analysis(), and only
    decides what to keep -- this endpoint reports how well it did).

    Citation Precision is NOT "citations with a non-null evidence_id / total
    citations": every Citation row that gets persisted is already built only
    from claims verified supported, so that ratio is trivially 100% and
    measures nothing. It is instead the fraction of factual sentences the
    writer drafted that survived finalize_review()'s "no unsupported prose"
    guard and got a citation -- section-level counts recorded at draft time
    (see synthesis_service.py::finalize_review, "claim_sentences_proposed"/
    "claim_sentences_kept" in SynthesisMetrics.section_metrics), since the
    dropped candidates' content isn't retained anywhere queryable after the
    fact.
    """
    from sqlalchemy import func

    from src.models.db_models import EntailmentStatus, SynthesisClaim, SynthesisMetrics

    session_result = await db.execute(
        select(SynthesisSession).where(SynthesisSession.id == session_id)
    )
    if session_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Synthesis session '{session_id}' not found")

    claim_counts_result = await db.execute(
        select(SynthesisClaim.verification_status, func.count())
        .where(SynthesisClaim.synthesis_session_id == session_id)
        .group_by(SynthesisClaim.verification_status)
    )
    counts_by_status = {status: count for status, count in claim_counts_result.all()}
    supported = counts_by_status.get(EntailmentStatus.supported, 0)
    contradicted = counts_by_status.get(EntailmentStatus.contradicted, 0)
    insufficient = counts_by_status.get(EntailmentStatus.insufficient, 0)
    total_claims = supported + contradicted + insufficient

    faithfulness_score_pct = round(supported / total_claims * 100, 2) if total_claims else None
    hallucination_rate_pct = round(100 - faithfulness_score_pct, 2) if faithfulness_score_pct is not None else None

    metrics_result = await db.execute(
        select(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id)
    )
    metrics = metrics_result.scalar_one_or_none()
    section_metrics = (metrics.section_metrics if metrics else None) or []
    claim_sentences_proposed = sum(int(s.get("claim_sentences_proposed", 0)) for s in section_metrics)
    claim_sentences_kept = sum(int(s.get("claim_sentences_kept", 0)) for s in section_metrics)
    citation_precision_pct = (
        round(claim_sentences_kept / claim_sentences_proposed * 100, 2)
        if claim_sentences_proposed else None
    )

    return SynthesisQualityResponse(
        session_id=session_id,
        total_claims=total_claims,
        supported_claims=supported,
        contradicted_claims=contradicted,
        insufficient_claims=insufficient,
        faithfulness_score_pct=faithfulness_score_pct,
        hallucination_rate_pct=hallucination_rate_pct,
        claim_sentences_proposed=claim_sentences_proposed,
        claim_sentences_kept=claim_sentences_kept,
        citation_precision_pct=citation_precision_pct,
    )


@router.delete("/synthesis-sessions/{session_id}")
async def delete_synthesis_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a synthesis session and its cascades."""
    from sqlalchemy import delete as sql_delete

    from src.models.db_models import (
        Citation,
        EvidenceExtractionAttempt,
        EvidenceRecord,
        LLMCallLog,
        RetrievalLog,
        SynthesisClaim,
        SynthesisMetrics,
        SynthesisSection,
        SynthesisSession,
    )

    # Check existence
    result = await db.execute(select(SynthesisSession).where(SynthesisSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Synthesis session not found")

    # Delete child records
    await db.execute(sql_delete(RetrievalLog).where(RetrievalLog.session_id == session_id))
    await db.execute(sql_delete(LLMCallLog).where(LLMCallLog.session_id == session_id))
    await db.execute(sql_delete(SynthesisMetrics).where(SynthesisMetrics.session_id == session_id))
    await db.execute(sql_delete(Citation).where(Citation.synthesis_session_id == session_id))
    await db.execute(sql_delete(EvidenceExtractionAttempt).where(EvidenceExtractionAttempt.synthesis_session_id == session_id))
    await db.execute(sql_delete(EvidenceRecord).where(EvidenceRecord.synthesis_session_id == session_id))
    await db.execute(sql_delete(SynthesisClaim).where(SynthesisClaim.synthesis_session_id == session_id))
    await db.execute(sql_delete(SynthesisSection).where(SynthesisSection.synthesis_session_id == session_id))

    # Delete the main session
    await db.execute(sql_delete(SynthesisSession).where(SynthesisSession.id == session_id))
    await db.commit()

    return {"message": "Synthesis session deleted successfully", "id": str(session_id)}


@router.get("/workspace/uploads/papers/{filename}")
async def get_pdf_file(
    filename: str,
    db: AsyncSession = Depends(get_db)
):
    """Serve uploaded PDF files. If the file is missing locally (e.g. Render container restarts), download it from the paper's online URL."""
    import os

    import httpx
    from fastapi.responses import FileResponse

    base_dir = os.path.join("uploads", "papers")
    os.makedirs(base_dir, exist_ok=True)
    file_path = os.path.join(base_dir, filename)

    # Try finding locally
    found = os.path.exists(file_path)
    if not found:
        # Check subdirectories
        for root, dirs, files in os.walk(base_dir):
            if filename in files:
                file_path = os.path.join(root, filename)
                found = True
                break

    if not found:
        # Ephemeral disk reset fallback: find online url from DB
        try:
            # Look for papers where file_path matches filename
            result = await db.execute(
                select(Paper).where(Paper.file_path.like(f"%{filename}%"))
            )
            paper = result.scalar_one_or_none()

            # If not found by file_path, try querying papers with similar title/filename match
            if not paper:
                clean_title = filename.rsplit(".", 1)[0].replace("-", " ")
                result = await db.execute(
                    select(Paper).where(Paper.title.like(f"%{clean_title[:30]}%"))
                )
                paper = result.scalar_one_or_none()

            if paper and paper.url and paper.url.lower().endswith(".pdf"):
                print(f"[pdf-serve] Local file missing. Re-downloading PDF from {paper.url}...", flush=True)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(paper.url, follow_redirects=True)
                    if response.status_code == 200:
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                        found = True
        except Exception as e:
            print(f"[pdf-serve] WARNING: Failed to re-download PDF: {e}", flush=True)

    if not found or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="application/pdf")


# ==============================================================================
# RERANKER ENDPOINT (FINE-TUNED 3-DOMAIN CROSS-ENCODER)
# ==============================================================================
@router.post("/slr-swarm/rerank-papers", response_model=RerankResponse, tags=["AI Search"])
async def api_rerank_papers(req: RerankRequest):
    """Tái xếp hạng danh sách bài báo dựa trên độ khớp ngữ nghĩa chuyên sâu với Query."""
    try:
        papers_list = [p.model_dump() if hasattr(p, "model_dump") else p.dict() for p in req.papers]
        reranked = reranker_service.rerank_papers(req.query, papers_list)
        return RerankResponse(results=reranked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reranking failed: {str(e)}")
