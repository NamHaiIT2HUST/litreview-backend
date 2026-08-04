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
"""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph import agent
from src.database import get_db
from src.models.db_models import CachedPaper, SearchQuery, DEFAULT_PROJECT_ID
from src.models.schemas import (
    ChatRequest, ChatResponse,
    DuplicateQueryResponse, PaperRecord,
    SearchHistoryResponse, SearchQueryRecord,
    SearchResponse,
)
from src.services.scholar_api import search_papers_auto

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
    strategy_label: Optional[str] = None,
    is_duplicated_from: Optional[str] = None,
) -> str:
    """
    Lưu 1 lần search vào DB:
    1. Insert SearchQuery record.
    2. Dedup: kiểm tra dedup_key đã tồn tại trong project chưa.
    3. Insert CachedPaper cho mỗi paper chưa trùng.
    Trả về search_query_id vừa tạo.
    """
    # 1. Tạo SearchQuery record
    sq = SearchQuery(
        id=str(uuid.uuid4()),
        project_id=project_id,
        query_string=query_string,
        strategy_label=strategy_label,
        result_count=len(papers_pydantic),
        is_duplicated_from=is_duplicated_from,
    )
    db.add(sq)

    # 2. Lấy tất cả dedup_key đã tồn tại trong project
    existing_keys_result = await db.execute(
        select(CachedPaper.dedup_key).where(CachedPaper.project_id == project_id)
    )
    existing_keys = {row[0] for row in existing_keys_result.fetchall()}

    # 3. Insert paper chưa trùng
    for p in papers_pydantic:
        key = _compute_dedup_key(p.doi, p.title, p.authors, p.year)
        paper_row = CachedPaper(
            id=str(uuid.uuid4()),
            project_id=project_id,
            search_query_id=sq.id,
            external_id=p.id,
            title=p.title,
            authors=p.authors,
            year=p.year,
            abstract=p.abstract,
            journal=p.journal,
            doi=p.doi,
            url=p.url,
            citations=p.citations,
            lit_score=p.litScore,
            tldr=p.tldr,
            dedup_key=key,
        )
        db.add(paper_row)
        existing_keys.add(key)  # tránh trùng trong cùng batch này

    await db.flush()
    return sq.id


# ──────────────────────────────────────────────────────────────────────────────
# Existing endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResponse)
async def search_papers(
    query: str = Query(..., description="Từ khóa tìm kiếm"),
    x_api_key: Optional[str] = Header(None, description="SerpApi hoặc Semantic Scholar Key"),
    provider: Optional[str] = Query("auto", description="Nguồn dữ liệu: auto, serpapi, semanticscholar"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Tra cứu bài báo học thuật và lưu vào Search History."""
    if not x_api_key and provider != "auto":
        raise HTTPException(status_code=401, detail="X-API-Key header is missing")

    papers = await search_papers_auto(query=query, api_key=x_api_key or "", provider=provider, limit=10)

    if not papers:
        return SearchResponse(papers=[], search_query_id=None)

    # Lưu vào DB TRƯỚC khi trả về (spec yêu cầu)
    try:
        sq_id = await _persist_search(db, query_string=query, papers_pydantic=papers)
    except Exception as exc:
        # Không để lỗi DB chặn kết quả search trả về user
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
    # Kiểm tra search query tồn tại
    sq_result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_id)
    )
    sq = sq_result.scalar_one_or_none()
    if not sq:
        raise HTTPException(status_code=404, detail=f"Search query '{query_id}' not found")

    result = await db.execute(
        select(CachedPaper)
        .where(CachedPaper.search_query_id == query_id)
        .order_by(desc(CachedPaper.citations))
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
    # Lấy query gốc
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
