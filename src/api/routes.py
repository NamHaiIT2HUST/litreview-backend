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
                                                      cho 1 paper CỤ THỂ (đã Keep),
                                                      KHÔNG chạy hàng loạt trên /search
                                                      (xem Flow Module 4 trong spec:
                                                      "Keep Paper → Quality Check").
"""
import re
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.database import get_db
from src.models.db_models import Paper, SearchQuery

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
from src.models.workspace_schemas import UploadResponse, WorkspaceChatRequest, WorkspaceChatResponse
from src.models.search_schemas import SearchExecuteRequest, SearchStrategiesResponse
from src.services.search_service import generate_search_strategies
from src.services.scholar_api import search_papers_auto
from src.services.scopus_matcher import quality_check as run_scopus_quality_check
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import vector_store_service
from src.services.rag_service import rag_service

processor = DocumentProcessor()

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _compute_dedup_key(doi: str, title: str, authors: str, year: int) -> str:
    """
    Thuật toán dedup theo spec:
      - Có DOI → normalize(doi)
      - Không có DOI → "title_norm|author[0]|year"
    """
    if doi and doi.strip() and doi.strip().upper() not in ("N/A", ""):
        return doi.strip().lower()
    title_norm = re.sub(r"\s+", " ", title.lower()).strip()
    first_author = authors.split(",")[0].strip() if authors else ""
    return f"{title_norm}|{first_author}|{year}"


async def _persist_search(
    db: AsyncSession,
    query_string: str,
    papers_pydantic,
    project_id: str = DEFAULT_PROJECT_ID,
    strategy_label: str | None = None,
    is_duplicated_from: str | None = None,
) -> str:
    """
    Lưu 1 lần search vào DB:
    1. Insert SearchQuery record.
    2. Dedup: kiểm tra dedup_key đã tồn tại trong project chưa.
    3. Insert CachedPaper cho mỗi paper chưa trùng.
    Trả về search_query_id vừa tạo.

    Lưu ý: scopus_status/oa_status của paper mới GIỮ NGUYÊN default "undetermined"
    của DB tại bước này — Quality Check (Module 4) chỉ chạy sau khi user Keep,
    qua POST /papers/{id}/quality-check, KHÔNG chạy ở đây.
    """
    sq = SearchQuery(
        id=str(uuid.uuid4()),
        project_id=project_id,
        query_string=query_string,
        strategy_label=strategy_label,
        result_count=len(papers_pydantic),
        is_duplicated_from=is_duplicated_from,
    )
    db.add(sq)

    existing_keys_result = await db.execute(
        select(Paper.dedup_key).where(Paper.project_id == project_id)
    )
    existing_keys = {row[0] for row in existing_keys_result.fetchall()}

    for p in papers_pydantic:
        key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
        if key in existing_keys:
            continue  # bỏ qua bản trùng, không insert (đúng thuật toán dedup spec)

        paper_row = Paper(
            id=str(uuid.uuid4()),
            project_id=project_id,
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
        db.add(paper_row)
        existing_keys.add(key)

    await db.flush()
    return sq.id


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
    """Module 2: Paper Discovery - Tra cứu bài báo học thuật và lưu vào Search History."""
    if not x_api_key and provider != "auto":
        raise HTTPException(status_code=401, detail="X-API-Key header is missing")

    papers = await search_papers_auto(query=request.query_string, api_key=x_api_key or "", provider=provider, limit=10)

    if not papers:
        return SearchResponse(papers=[], search_query_id=None)

    # Đã gỡ bỏ tự động đối chiếu Scopus để tối ưu, chỉ chạy Quality Check ở Module 4 khi Keep Paper.

    try:
        sq_id = await _persist_search(
            db, 
            query_string=request.query_string, 
            papers_pydantic=papers, 
            project_id=project_id,
            strategy_label=request.strategy_label
        )
        
        if sq_id:
            keys = [_compute_dedup_key(p.doi, p.title, p.authors, p.year) for p in papers]
            result = await db.execute(
                select(Paper).where(Paper.project_id == project_id, Paper.dedup_key.in_(keys))
            )
            db_papers = result.scalars().all()
            dedup_to_id = {p.dedup_key: str(p.id) for p in db_papers}
            
            for p in papers:
                key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
                if key in dedup_to_id:
                    p.id = dedup_to_id[key]
            
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Failed to persist search: %s", exc)
        sq_id = None

    return SearchResponse(papers=papers, search_query_id=sq_id)


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


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}


# ──────────────────────────────────────────────────────────────────────────────
# Search History endpoints (Module 2 — P0)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/search-history", response_model=SearchHistoryResponse)
async def get_search_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> SearchHistoryResponse:
    """
    Lấy toàn bộ lịch sử search của một project,
    sắp xếp theo executed_at giảm dần (mới nhất trước).
    """
    result = await db.execute(
        select(SearchQuery)
        .where(SearchQuery.project_id == project_id)
        .order_by(desc(SearchQuery.executed_at))
    )
    rows = result.scalars().all()
    history = [SearchQueryRecord.model_validate(row) for row in rows]
    return SearchHistoryResponse(project_id=project_id, history=history)


@router.get("/search-queries/{query_id}/papers", response_model=list[PaperRecord])
async def get_papers_for_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PaperRecord]:
    """
    Lấy danh sách paper (đã dedup) của 1 lần search cụ thể.
    """
    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_id)
    )
    sq = sq_result.scalar_one_or_none()
    if not sq:
        raise HTTPException(status_code=404, detail=f"Search query '{query_id}' not found")

    result = await db.execute(
        select(Paper)
        .where(Paper.search_query_id == query_id)
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
    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_id)
    )
    original = sq_result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail=f"Search query '{query_id}' not found")

    new_sq = SearchQuery(
        id=str(uuid.uuid4()),
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


# ──────────────────────────────────────────────────────────────────────────────
# Quality Verification endpoint (Module 4)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/papers/{paper_id}/quality-check", response_model=PaperRecord)
async def quality_check_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
) -> PaperRecord:
    """
    Trigger Quality Check (Scopus + Coverage Year) cho 1 paper cụ thể.

    Theo Flow Module 4: chỉ chạy cho paper user đã Keep, KHÔNG chạy hàng loạt
    trên toàn bộ kết quả /search.

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
    paper_id: str = Form(...)
) -> UploadResponse:
    """
    Nhận file PDF do user upload, lưu xuống disk và cắt thành các chunk (chuẩn bị cho Vector DB).
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    try:
        # Bước 1: Lưu file vật lý
        file_path = await processor.save_upload_file(file)
        
        # Bước 2: Bóc tách và cắt chunk
        pages, chunks = processor.extract_and_chunk(file_path)
        
        # Bước 3: Lưu chunk vào Vector Database
        num_added = await vector_store_service.add_documents(chunks)
        
        return UploadResponse(
            file_id=file_path.split("/")[-1].split("\\")[-1],
            filename=file.filename,
            total_pages=len(pages),
            total_chunks=len(chunks),
            message=f"Successfully processed and stored {num_added} chunks into Vector Database."
        )
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
    Chat với trợ lý AI về các bài báo đã tải lên (RAG).
    """
    try:
        # Bước 1: Tìm kiếm tài liệu liên quan trong ChromaDB
        chunks = await vector_store_service.search_similar_documents(request.message, top_k=4)
        
        # Bước 2: Sinh câu trả lời dựa trên context
        answer = await rag_service.generate_answer(request.message, chunks)
        
        # Bước 3: Đóng gói phản hồi
        context_used = [doc.page_content for doc in chunks]
        return WorkspaceChatResponse(answer=answer, context_used=context_used)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
