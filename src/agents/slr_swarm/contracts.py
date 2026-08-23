"""Hợp đồng dữ liệu (data contracts) trao đổi giữa các agent trong SLR Swarm.

Mọi agent chỉ nói chuyện với nhau qua các model ở file này, không truyền dict tự do.
Nhờ vậy Master Orchestrator có thể validate output từng chặng trước khi cho đi tiếp.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Agent 1: PICO & Research Gap
# --------------------------------------------------------------------------- #
class PICOFrame(BaseModel):
    """Khung PICO chuẩn hoá từ ý tưởng thô của nghiên cứu viên."""

    population: str = ""
    intervention: str = ""
    comparison: str = ""
    outcome: str = ""
    boolean_query: str = ""
    search_keywords: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)


class GapSaturation(str, Enum):
    EMPTY = "empty"        # chưa có bài nào -> khoảng trống rõ rệt
    SPARSE = "sparse"      # ít bài -> còn dư địa
    SATURATED = "saturated"  # đã bão hoà -> tính mới thấp


class GapCell(BaseModel):
    """Một ô trong Research Gap Heatmap (trục X × trục Y)."""

    dimension_x: str
    dimension_y: str
    paper_count: int = 0
    saturation: GapSaturation = GapSaturation.EMPTY

    @staticmethod
    def classify(paper_count: int, sparse_threshold: int = 3, saturated_threshold: int = 10) -> GapSaturation:
        if paper_count <= 0:
            return GapSaturation.EMPTY
        if paper_count < sparse_threshold:
            return GapSaturation.SPARSE
        if paper_count >= saturated_threshold:
            return GapSaturation.SATURATED
        return GapSaturation.SPARSE


class GapMap(BaseModel):
    axis_x: list[str] = Field(default_factory=list)
    axis_y: list[str] = Field(default_factory=list)
    cells: list[GapCell] = Field(default_factory=list)

    def empty_cells(self) -> list[GapCell]:
        return [c for c in self.cells if c.saturation is GapSaturation.EMPTY]


# --------------------------------------------------------------------------- #
# Agent 2: Citation Snowball
# --------------------------------------------------------------------------- #
class PaperRecord(BaseModel):
    """Một bài báo trong corpus đang xử lý."""

    paper_id: str
    title: str = ""
    abstract: str = ""
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    source: str = "query"  # query | forward_snowball | backward_snowball
    seed_distance: int = 0  # 0 = seed, 1 = hàng xóm bậc 1, ...
    pdf_available: bool = False


# --------------------------------------------------------------------------- #
# Agent 3: Peer Screener & Grounded Verifier
# --------------------------------------------------------------------------- #
class GroundedSpan(BaseModel):
    """Toạ độ chứng minh cho một khẳng định — dùng cho Live PDF Anchor."""

    paper_id: str
    page: int
    line_start: int
    line_end: int
    quote: str
    score: float = 0.0  # [0,1] mức khớp giữa claim và đoạn trích


Decision = Literal["keep", "reject", "unsure"]


class ReviewerOpinion(BaseModel):
    """Ý kiến của một reviewer trong cặp Dual-Agent Peer Screener."""

    reviewer: str  # "inclusive" | "strict" | "adjudicator"
    decision: Decision
    reason: str = ""
    confidence: float = 0.0


class ScreeningVerdict(BaseModel):
    """Kết luận sàng lọc cuối cùng cho một bài báo."""

    paper_id: str
    decision: Decision
    reason: str = ""
    confidence: float = 0.0
    grounding_score: float = 0.0
    spans: list[GroundedSpan] = Field(default_factory=list)
    opinions: list[ReviewerOpinion] = Field(default_factory=list)
    disagreed: bool = False


# --------------------------------------------------------------------------- #
# Agent 4: PRISMA Matrix & Drafter
# --------------------------------------------------------------------------- #
class PrismaRow(BaseModel):
    """Một dòng trong bảng ma trận so sánh PRISMA."""

    paper_id: str
    design: str = ""
    sample_size: str = ""
    method: str = ""
    outcome: str = ""
    limitation: str = ""
    evidence: list[GroundedSpan] = Field(default_factory=list)


class ReviewDraft(BaseModel):
    latex: str = ""
    bibtex: str = ""
    claim_count: int = 0
    grounded_claim_count: int = 0


# --------------------------------------------------------------------------- #
# Agent 5: Methodology & Code Copilot
# --------------------------------------------------------------------------- #
class DatasetProfile(BaseModel):
    rows: int = 0
    columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    missing_ratio: dict[str, float] = Field(default_factory=dict)


class AnalysisPlan(BaseModel):
    methods: list[str] = Field(default_factory=list)
    rationale: str = ""
    code: str = ""
    interpretation: str = ""


# --------------------------------------------------------------------------- #
# KPI (§7.3 Master Plan)
# --------------------------------------------------------------------------- #
class KpiSnapshot(BaseModel):
    grounding_precision: float = 0.0   # mục tiêu >= 0.80
    time_saved_ratio: float = 0.0      # mục tiêu >= 0.50
    papers_processed: int = 0
    elapsed_minutes: float = 0.0
    baseline_minutes: float = 0.0
    llm_calls_saved: int = 0

    @property
    def meets_btc(self) -> bool:
        return self.grounding_precision >= 0.80 and self.time_saved_ratio >= 0.50
