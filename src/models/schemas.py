from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")

class Paper(BaseModel):
    id: str
    title: str
    authors: str
    year: int
    abstract: str
    journal: str
    doi: str
    url: str
    citations: int
    litScore: int  # noqa: N815
    tldr: str | None = None

class SearchResponse(BaseModel):
    papers: list[Paper]
    search_query_id: str | None = None  # ID của record vừa lưu, dùng cho frontend


# ──────────────────────────────────────────────────
# Search History schemas (Module 2 — Search History)
# ──────────────────────────────────────────────────

class PaperRecord(BaseModel):
    """Paper đã được lưu vào DB (trả về từ GET /search-queries/{id}/papers)."""
    id: str               # UUID trong DB
    external_id: str      # id gốc từ API, dùng để render trên FE
    title: str
    authors: str
    year: int
    abstract: str
    journal: str
    doi: str
    url: str
    citations: int
    lit_score: int
    tldr: str | None = None
    dedup_key: str

    model_config = {"from_attributes": True}


class SearchQueryRecord(BaseModel):
    """1 record trong lịch sử search."""
    id: str
    project_id: str
    query_string: str
    strategy_label: str | None = None
    result_count: int
    executed_at: datetime
    is_duplicated_from: str | None = None

    model_config = {"from_attributes": True}


class SearchHistoryResponse(BaseModel):
    """Response cho GET /projects/{id}/search-history."""
    project_id: str
    history: list[SearchQueryRecord]


class DuplicateQueryResponse(BaseModel):
    """Response cho POST /search-queries/{id}/duplicate."""
    new_query_id: str
    query_string: str
    duplicated_from: str