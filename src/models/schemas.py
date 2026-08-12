from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")

class Paper(BaseModel):
    id: str
    # Canonical UUID assigned by our database after search persistence. The
    # provider ID remains in ``id`` so no search metadata is lost.
    db_id: str | None = None
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
    search_query_id: UUID | None = None  # canonical DB UUID; JSON serializes as string
    provider: str = "google_scholar"
    limit: int = 20
    total_found: int = 0
    total_confirmed: int = 0
    total_undetermined: int = 0
    duplicates: int = 0


# ──────────────────────────────────────────────────
# Search History schemas (Module 2 — Search History)
# ──────────────────────────────────────────────────

class PaperRecord(BaseModel):
    """Canonical paper row returned from our database."""
    id: UUID
    external_id: str | None = None
    title: str
    authors: list[str] | str | None = None
    year: int | None = None
    abstract: str | None = None
    journal: str | None = None
    doi: str | None = None
    issn: str | None = None
    # These provider-only fields are not yet persisted by the legacy schema.
    url: str = "#"
    citations: int = 0
    lit_score: int = 0
    tldr: str | None = None
    dedup_key: str

    # Module 4 — Quality Verification
    scopus_status: str = "undetermined"
    scopus_quartile: str | None = None
    coverage_year_status: str | None = None
    oa_status: str = "undetermined"

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
    project_id: UUID
    history: list[SearchQueryRecord]


class DuplicateQueryResponse(BaseModel):
    """Response cho POST /search-queries/{id}/duplicate."""
    new_query_id: UUID
    query_string: str
    duplicated_from: UUID
