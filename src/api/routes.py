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

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.config import get_settings
from src.database import get_db
from src.models.db_models import Citation, Paper, Project, SearchQuery, SynthesisSession, SynthesisStatus

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
    SynthesisSessionCreateRequest,
    SynthesisSessionCreatedResponse,
    SynthesisSessionResponse,
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

    existing_keys_result = await db.execute(
        select(Paper.dedup_key).where(Paper.project_id == project_uuid)
    )
    existing_keys = {row[0] for row in existing_keys_result.fetchall()}

    duplicate_count = 0
    for p in papers_pydantic:
        key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
        if key in existing_keys:
            duplicate_count += 1
            continue  # bỏ qua bản trùng, không insert (đúng thuật toán dedup spec)

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
        await run_scopus_quality_check(db, paper_row)
        db.add(paper_row)
        existing_keys.add(key)
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
    effective_provider = "serpapi" if provider in (None, "auto") else provider
    if not x_api_key or not x_api_key.strip():
        from src.config import get_settings
        settings = get_settings()
        x_api_key = (settings.serpapi_api_key or os.getenv("SERPAPI_API_KEY") or os.getenv("SERP_API_KEY") or "").strip()

    if effective_provider == "serpapi" and not x_api_key:
        raise HTTPException(status_code=401, detail="SerpApi key is required for Google Scholar Top 20 search")
    if effective_provider != "serpapi" and not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is missing")

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

    try:
        sq_id, duplicate_count = await _persist_search(
            db, 
            query_string=request.query_string, 
            papers_pydantic=papers, 
            project_id=project_id,
            strategy_label=request.strategy_label
        )
        
        if sq_id:
            project_uuid = uuid.UUID(str(project_id))
            keys = [_compute_dedup_key(p.doi, p.title, p.authors, p.year) for p in papers]
            result = await db.execute(
                select(Paper).where(Paper.project_id == project_uuid, Paper.dedup_key.in_(keys))
            )
            db_papers = result.scalars().all()
            dedup_to_paper = {p.dedup_key: p for p in db_papers}
            
            for p in papers:
                key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
                db_paper = dedup_to_paper.get(key)
                if db_paper:
                    p.id = str(db_paper.id)
                    p.issn = db_paper.issn
                    p.scopus_status = db_paper.scopus_status.value if hasattr(db_paper.scopus_status, "value") else db_paper.scopus_status
                    p.scopus_quartile = db_paper.scopus_quartile
                    p.coverage_year_status = db_paper.coverage_year_status.value if hasattr(db_paper.coverage_year_status, "value") else db_paper.coverage_year_status
            
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Failed to persist search: %s", exc)
        sq_id = None
        duplicate_count = 0

    # --- Filter: chỉ giữ bài đã xác minh Scopus, tối đa SCOPUS_TARGET ---
    all_found = len(papers)
    scopus_papers = [p for p in papers if p.scopus_status == "indexed"]
    scopus_papers = scopus_papers[:SCOPUS_TARGET]

    # Cập nhật số lượng bài Scopus thực tế vào SearchQuery record trong DB
    if sq_id:
        try:
            sq_obj = await db.get(SearchQuery, sq_id)
            if sq_obj:
                sq_obj.result_count = len(scopus_papers)
                await db.commit()
        except Exception:
            pass

    return SearchResponse(
        papers=scopus_papers,
        search_query_id=sq_id,
        provider="google_scholar" if effective_provider == "serpapi" else effective_provider,
        limit=SCOPUS_TARGET,
        total_found=all_found,
        total_confirmed=len(scopus_papers),
        total_undetermined=sum(1 for p in papers if p.scopus_status == "undetermined"),
        duplicates=duplicate_count,
    )


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
        .where(SearchQuery.project_id == project_uuid)
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

    from src.models.db_models import ScopusStatusEnum
    result = await db.execute(
        select(Paper)
        .where(
            Paper.search_query_id == query_uuid,
            (Paper.scopus_status == ScopusStatusEnum.INDEXED) | (Paper.scopus_status == "indexed")
        )
    )
    papers = result.scalars().all()
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

        file_path = await processor.save_upload_file(file)
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

@router.post("/workspace/direct-upload", response_model=DirectUploadResponse)
async def direct_upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> DirectUploadResponse:
    """Upload a PDF directly from Workspace without a prior paper search result."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        project_uuid = uuid.UUID(DEFAULT_PROJECT_ID)
        paper_uuid = uuid.uuid4()
        
        # Create a new Paper record for this direct upload
        paper = Paper(
            id=paper_uuid,
            project_id=project_uuid,
            title=title,
            authors="Direct Upload",
            year=2024,
            abstract="",
            source="direct_upload",
            dedup_key=f"direct_upload_{paper_uuid}"
        )
        db.add(paper)
        await db.flush()

        file_path = await processor.save_upload_file(file)
        pages, chunks = processor.extract_and_chunk(file_path, paper_title=paper.title)
        
        if not chunks or all(not chunk.page_content.strip() for chunk in chunks):
            raise HTTPException(
                status_code=422,
                detail="PDF không trích được văn bản — có thể là file scan/ảnh."
            )

        ingestion_id = await persist_pdf_provenance(
            db=db,
            paper=paper,
            pages=pages,
            chunks=chunks,
            parser_metadata=processor.parser_metadata(),
        )

        old_vector_ids = []
        cleanup_job = None
        try:
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
        except Exception as e:
            await vector_store_service.delete_documents_by_ingestion(str(ingestion_id))
            await db.rollback()
            import traceback
            with open("upload_error.log", "w") as f:
                traceback.print_exc(file=f)
            raise

        if cleanup_job is not None:
            try:
                from src.tasks.vector_cleanup_tasks import run_vector_cleanup_job
                run_vector_cleanup_job.delay(str(cleanup_job.id))
            except Exception as cleanup_enqueue_exc:
                import logging
                logging.getLogger(__name__).warning("Vector cleanup enqueue failed: %s", cleanup_enqueue_exc)

        return DirectUploadResponse(
            paper_id=str(paper.id),
            title=title,
            filename=file.filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            message="Direct upload successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        with open("upload_error_outer.log", "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
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
    
    file_path = os.path.join("uploads", "papers", request.filename)
    if not os.path.exists(file_path):
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
        
        # Searching the snippet
        # If snippet has newlines or variations, search_for can be tricky. We might just search for the first 30-50 chars to locate the bounding box, or use the whole snippet.
        search_text = request.snippet.strip()
        
        # We might need to split by newline if the text is multi-line
        instances = page.search_for(search_text)
        
        if not instances:
            # For long chunks, search_for with the whole text might fail due to hyphens/newlines.
            # Fallback: search for the first 50 chars and last 50 chars, or split into words.
            # A simple approach is to just search for the first few words to at least highlight the start.
            first_part = search_text[:60].strip()
            if first_part:
                instances = page.search_for(first_part)
                
            # Try to get the end of the chunk too
            last_part = search_text[-60:].strip()
            if last_part:
                instances.extend(page.search_for(last_part))
                
        # If still empty, try even shorter
        if not instances and len(search_text) > 20:
            instances = page.search_for(search_text[:20])

        rects = []
        for inst in instances:
            rects.append(RectCoord(
                x=inst.x0 / page_width,
                y=inst.y0 / page_height,
                width=(inst.x1 - inst.x0) / page_width,
                height=(inst.y1 - inst.y0) / page_height
            ))

            
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
    db: AsyncSession = Depends(get_db),
) -> SynthesisSessionCreatedResponse:
    """Create and enqueue a long-running evidence-first synthesis session."""
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

    # Enqueue synthesis job
    session = SynthesisSession(
        id=uuid.uuid4(),
        project_id=request.project_id,
        paper_ids=paper_ids,
        status=SynthesisStatus.PENDING,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    try:
        from src.tasks.synthesis_tasks import run_synthesis_session
        run_synthesis_session.delay(str(session.id))
    except Exception as enqueue_exc:
        import logging
        logging.getLogger(__name__).warning(
            "Synthesis session %s created but could not be enqueued: %s",
            session.id, enqueue_exc,
        )

    return SynthesisSessionCreatedResponse(session_id=session.id, status=session.status.value)


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
    )
