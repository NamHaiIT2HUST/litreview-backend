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
import os
import re
import uuid
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.config import get_settings
settings = get_settings()
from src.database import get_db
from src.models.db_models import Citation, EvidenceRecord, Paper, Project, SearchQuery, SynthesisSection, SynthesisSession, SynthesisStatus

DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"

from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    DuplicateQueryResponse,
    PaperRecord,
    SearchHistoryResponse,
    SearchQueryRecord,
    SearchResponse,
)
from src.models.workspace_schemas import UploadResponse, DirectUploadResponse, WorkspaceChatRequest, WorkspaceChatResponse, EvidenceCoordsRequest, EvidenceCoordsResponse, RectCoord
from src.models.search_schemas import SearchExecuteRequest, SearchStrategiesResponse
from src.models.synthesis_schemas import (
    SynthesisCitationResponse,
    SynthesisEvidenceProfileItem,
    SynthesisSessionCreateRequest,
    SynthesisSessionCreatedResponse,
    SynthesisSessionResponse,
    SynthesisSessionSummary,
)
from src.services.search_service import generate_search_strategies
from src.services.scholar_api import search_papers_auto
from src.services.scopus_matcher import quality_check as run_scopus_quality_check
from src.services.document_processor import DocumentProcessor
from src.services.ingestion_service import persist_pdf_provenance
from src.services.paper_persistence_utils import normalize_authors_for_db
from src.services.vector_cleanup_service import create_vector_cleanup_job
from src.services.vector_store import vector_store_service
from src.services.rag_service import rag_service
from src.services.synthesis_response_builder import build_section_responses
from src.services.synthesis_llm_service import synthesis_llm_service
from src.services.synthesis_session_utils import json_paper_ids

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

async def _persist_search(
    db: AsyncSession,
    query_string: str,
    papers_pydantic,
    project_id: str | UUID = DEFAULT_PROJECT_ID,
    strategy_label: str | None = None,
    is_duplicated_from: str | None = None,
) -> tuple[UUID, int]:
    """
    Lưu 1 lần search vào DB:
    1. Insert SearchQuery record.
    2. Dedup: kiểm tra dedup_key đã tồn tại trong project chưa.
    3. Insert CachedPaper cho mỗi paper chưa trùng.
    Trả về search_query_id vừa tạo và số paper bị skip do dedup trong project.

    Search & Verify P0: paper mới được đối chiếu Scopus ngay trong pipeline này
    để UI render kết quả Top 20 đã xác minh. Endpoint quality-check chỉ còn là
    re-check/detail cho từng paper.
    """
    project_uuid = uuid.UUID(str(project_id)) if isinstance(project_id, (str, UUID)) else project_id
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
        await run_scopus_quality_check(db, paper_row, enrich_abstract=False)
        db.add(paper_row)
        existing_papers_map[key] = paper_row.id
        if paper_row.id not in linked_paper_ids:
            db.add(SearchQueryPaper(search_query_id=sq.id, paper_id=paper_row.id))
            linked_paper_ids.add(paper_row.id)

        p.id = str(paper_row.id)
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

from src.models.db_models import Project



# ──────────────────────────────────────────────────────────────────────────────
# Existing endpoints
# ──────────────────────────────────────────────────────────────────────────────

from src.models.db_models import Project

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
                project_uuid = uuid.UUID(str(project_id))
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
    paper_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Xóa một paper khỏi database."""
    from sqlalchemy import delete as sql_delete
    from src.models.db_models import (
        Paper, PageText, PDFChunk, Extraction, ScreeningHistory,
        EvidenceRecord, EvidenceExtractionAttempt, VectorCleanupJob,
        GenericEvidenceCache, GenericEvidenceCacheItem, RetrievalLog, Citation
    )
    
    # Delete child rows first to avoid foreign key violations
    await db.execute(sql_delete(Citation).where(Citation.paper_id == paper_id))
    await db.execute(sql_delete(RetrievalLog).where(RetrievalLog.paper_id == paper_id))
    await db.execute(sql_delete(GenericEvidenceCacheItem).where(GenericEvidenceCacheItem.paper_id == paper_id))
    await db.execute(sql_delete(GenericEvidenceCache).where(GenericEvidenceCache.paper_id == paper_id))
    await db.execute(sql_delete(VectorCleanupJob).where(VectorCleanupJob.paper_id == paper_id))
    await db.execute(sql_delete(EvidenceRecord).where(EvidenceRecord.paper_id == paper_id))
    await db.execute(sql_delete(EvidenceExtractionAttempt).where(EvidenceExtractionAttempt.paper_id == paper_id))
    await db.execute(sql_delete(ScreeningHistory).where(ScreeningHistory.paper_id == paper_id))
    await db.execute(sql_delete(Extraction).where(Extraction.paper_id == paper_id))
    await db.execute(sql_delete(PDFChunk).where(PDFChunk.paper_id == paper_id))
    await db.execute(sql_delete(PageText).where(PageText.paper_id == paper_id))
    
    result = await db.execute(sql_delete(Paper).where(Paper.id == paper_id))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"message": "Paper deleted successfully", "id": str(paper_id)}

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
    try:
        project_uuid = uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="project_id must be a valid UUID.") from exc

    project_result = await db.execute(select(Project).where(Project.id == project_uuid))
    if project_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

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
async def workspace_chat(request: WorkspaceChatRequest) -> WorkspaceChatResponse:
    """
    Chat với trợ lý AI về các bài báo đã tải lên (RAG chuẩn NotebookLM).
    """
    try:

        # --- LUỒNG RAG TRUYỀN THỐNG (SUPER FAST) ---
        # Bước 1: Tìm kiếm tài liệu liên quan trong ChromaDB
        # Lấy context riêng cho từng paper để đảm bảo phân bổ đều khi query chung chung
        chunks = []
        if getattr(request, "paper_ids", None) and len(request.paper_ids) > 0:
            if len(request.paper_ids) == 1:
                # Nếu chỉ chat với 1 tài liệu, lấy 8 chunks cho sâu
                chunks = await vector_store_service.search_similar_documents(
                    request.message, 
                    top_k=8,
                    filters={"paper_id": request.paper_ids[0]}
                )
            else:
                # Nếu chat với nhiều tài liệu, lấy 4 chunks mỗi tài liệu để đảm bảo tài liệu nào cũng có cơ hội (tránh bị nuốt bởi 1 tài liệu)
                for pid in request.paper_ids:
                    paper_chunks = await vector_store_service.search_similar_documents(
                        request.message,
                        top_k=4,
                        filters={"paper_id": pid}
                    )
                    chunks.extend(paper_chunks)
        elif getattr(request, "paper_id", None):
            chunks = await vector_store_service.search_similar_documents(
                request.message, 
                top_k=8,
                filters={"paper_id": request.paper_id}
            )
        else:
            chunks = await vector_store_service.search_similar_documents(
                request.message, 
                top_k=8,
                filters=None
            )

        # Bước 2: Sinh câu trả lời dựa trên context (có structured citation metadata)
        result = await rag_service.generate_answer_with_citations(request.message, chunks)
        
        # Bước 3: Đóng gói phản hồi
        return WorkspaceChatResponse(
            answer=result["answer"],
            context_used=result["context_used"],
            citations=result.get("citations", [])
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error in workspace_chat")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workspace/evidence-coords", response_model=EvidenceCoordsResponse)
async def get_evidence_coords(
    request: EvidenceCoordsRequest,
) -> EvidenceCoordsResponse:
    """Find text coordinates in PDF for highlighting."""
    import os
    import fitz  # PyMuPDF
    import logging
    
    base_dir = os.path.join("uploads", "papers")
    file_path = os.path.join(base_dir, request.filename)
    if not os.path.exists(file_path):
        for root, dirs, files in os.walk(base_dir):
            if request.filename in files:
                file_path = os.path.join(root, request.filename)
                break
        else:
            return EvidenceCoordsResponse(rects=[])
    
    try:
        doc = fitz.open(file_path)
        # fitz is 0-indexed, UI is 1-indexed (usually, though the UI sends the actual page number from the source)
        page_index = max(0, request.page - 1)
        if page_index >= len(doc):
            return EvidenceCoordsResponse(rects=[])
            
        page = doc[page_index]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        search_text = request.snippet.strip()
        rects = []
        
        # Robust word-level matching
        import re
        def clean_word(w):
            return re.sub(r'\W+', '', w).lower()

        search_words = [clean_word(w) for w in search_text.split() if clean_word(w)]
        page_words = page.get_text("words")
        
        if search_words and page_words:
            best_start = 0
            best_end = 0
            max_matches = -1
            
            window_size = min(len(search_words) + 15, len(page_words))
            
            for i in range(len(page_words) - window_size + 1):
                p_ptr = i
                s_ptr = 0
                matches = 0
                while p_ptr < i + window_size and s_ptr < len(search_words):
                    cw = clean_word(page_words[p_ptr][4])
                    if not cw:
                        p_ptr += 1
                        continue
                        
                    # look ahead in search_words
                    for lookahead in range(4):
                        if s_ptr + lookahead < len(search_words) and cw == search_words[s_ptr + lookahead]:
                            matches += 1
                            s_ptr += lookahead + 1
                            break
                    p_ptr += 1
                
                if matches > max_matches:
                    max_matches = matches
                    best_start = i
                    best_end = p_ptr - 1

            if max_matches > 0 and max_matches >= len(search_words) * 0.2:
                # Collect bounding boxes for these words
                for i in range(best_start, best_end + 1):
                    w = page_words[i]
                    rects.append(RectCoord(
                        x=w[0] / page_width,
                        y=w[1] / page_height,
                        width=(w[2] - w[0]) / page_width,
                        height=(w[3] - w[1]) / page_height
                    ))
                    
                return EvidenceCoordsResponse(rects=rects)


            
        return EvidenceCoordsResponse(rects=rects)
    except Exception as e:
        logging.getLogger(__name__).error("Error finding coords: %s", e)
        return EvidenceCoordsResponse(rects=[])

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
    paper_ids = list(dict.fromkeys(request.paper_ids))
    max_papers = get_settings().synthesis_max_papers
    if len(paper_ids) > max_papers:
        raise HTTPException(
            status_code=422,
            detail=f"Synthesis accepts at most {max_papers} papers per session.",
        )
    paper_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
    papers = list(paper_result.scalars().all())
    by_id = {paper.id: paper for paper in papers}

    missing = [paper_id for paper_id in paper_ids if paper_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=404,
            detail="Papers not found: " + ", ".join(str(item) for item in missing),
        )

    foreign_project = [
        paper.id for paper in papers if paper.project_id != request.project_id
    ]
    if foreign_project:
        raise HTTPException(
            status_code=409,
            detail="Papers do not belong to the selected project: "
            + ", ".join(str(item) for item in foreign_project),
        )

    not_ingested = [paper.id for paper in papers if paper.active_ingestion_id is None]
    if not_ingested:
        raise HTTPException(
            status_code=409,
            detail=(
                "PDF provenance ingestion is required before synthesis for papers: "
                + ", ".join(str(item) for item in not_ingested)
            ),
        )

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
        redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_TLS_URL")
        
        if get_settings().app_env == "development" or not redis_url:
            # Local/Fallback mode: use FastAPI BackgroundTasks so we don't need Redis/Celery on Render Free Tier
            async def local_run_synthesis(sid: str):
                from src.tasks.synthesis_tasks import run_synthesis_session, _mark_terminal_failure
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
        citations=[
            SynthesisCitationResponse(
                id=item.id,
                marker_display=item.citation_marker,
                paper_id=item.paper_id,
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

@router.delete("/synthesis-sessions/{session_id}")
async def delete_synthesis_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a synthesis session and its cascades."""
    from sqlalchemy import delete as sql_delete
    from src.models.db_models import (
        SynthesisSession, Citation, EvidenceExtractionAttempt, EvidenceRecord,
        SynthesisClaim, SynthesisSection, RetrievalLog, LLMCallLog, SynthesisMetrics
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
    from fastapi.responses import FileResponse
    import os
    import httpx
    
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
