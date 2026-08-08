from uuid import UUID
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
    authors: list[str]
    year: int
    abstract: str
    journal: str
    doi: str
    issn: str | None = None  # cần cho Module 4 Quality Check — có thể null nếu nguồn không trả về
    url: str
    citations: int
    litScore: int  # noqa: N815
    tldr: str | None = None
    scopus_status: str | None = "undetermined"
    scopus_quartile: str | None = None
    coverage_year_status: str | None = None

class SearchResponse(BaseModel):
    papers: list[Paper]
    search_query_id: UUID | None = None  # ID của record vừa lưu, dùng cho frontend


# ──────────────────────────────────────────────────
# Search History schemas (Module 2 — Search History)
# ──────────────────────────────────────────────────

class PaperRecord(BaseModel):
    """Paper đã được lưu vào DB (trả về từ GET /search-queries/{id}/papers
    và POST /papers/{id}/quality-check)."""
    id: UUID               # UUID trong DB
    external_id: str | None = None      # id gốc từ API, dùng để render trên FE
    title: str
    authors: list[str]
    year: int
    abstract: str | None = None
    journal: str | None = None
    doi: str | None = None
    issn: str | None = None
    url: str | None = None
    citations: int
    lit_score: int
    tldr: str | None = None
    dedup_key: str

    # Module 4 — Quality Verification
    scopus_status: str        # indexed | not_indexed | undetermined
    scopus_quartile: str | None = None
    coverage_year_status: str | None = None  # ok | out_of_coverage | not_applicable | None
    oa_status: str             # gold | hybrid | bronze | green | closed | undetermined

    model_config = {"from_attributes": True}


class SearchQueryRecord(BaseModel):
    """1 record trong lịch sử search."""
    id: UUID
    project_id: UUID
    query_string: str
    strategy_label: str | None = None
    result_count: int
    executed_at: datetime
    is_duplicated_from: UUID | None = None

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
