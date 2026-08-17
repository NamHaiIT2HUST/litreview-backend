"""Ports (giao diện phụ thuộc) của SLR Swarm.

Các agent không import trực tiếp service thật. Chúng nhận `SwarmDeps` được inject,
nên có thể chạy end-to-end với stub (test, demo offline) hoặc với adapter thật
(SerpApi / OpenAlex / vLLM local) mà không phải sửa graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from src.agents.slr_swarm.contracts import PaperRecord


@runtime_checkable
class LLMPort(Protocol):
    """Một model sinh văn bản. `schema` khác None nghĩa là cần JSON đúng schema."""

    async def complete(self, prompt: str, *, schema: dict[str, Any] | None = None) -> str: ...


@runtime_checkable
class SearchPort(Protocol):
    """Tìm kiếm bài báo theo chuỗi Boolean query."""

    async def search(self, query: str, *, limit: int = 20) -> list[PaperRecord]: ...


@runtime_checkable
class CitationPort(Protocol):
    """Đồ thị trích dẫn 2 chiều dùng cho Snowballing."""

    async def references(self, paper_id: str) -> list[PaperRecord]: ...   # backward
    async def citations(self, paper_id: str) -> list[PaperRecord]: ...    # forward


class PageText:
    """Một trang full-text đã tách dòng, phục vụ Live PDF Anchor."""

    __slots__ = ("page", "lines")

    def __init__(self, page: int, lines: list[str]):
        self.page = page
        self.lines = lines


@runtime_checkable
class CorpusPort(Protocol):
    """Nguồn full-text để verifier đối chiếu claim với tài liệu gốc."""

    async def pages(self, paper_id: str) -> list[PageText]: ...


@dataclass
class ModelRouter:
    """§6 Master Plan: đẩy screening/extraction về model local, chỉ gọi cloud khi cần.

    Đếm luôn số lần *tránh* được cloud call để Dashboard KPI báo cáo tiền tiết kiệm.
    """

    local: LLMPort
    cloud: LLMPort | None = None
    local_calls: int = 0
    cloud_calls: int = 0

    def pick(self, task: str) -> LLMPort:
        """`screening` và `extraction` luôn chạy local (rẻ, nhanh, <100ms/abstract)."""
        if task in ("screening", "extraction") or self.cloud is None:
            self.local_calls += 1
            return self.local
        self.cloud_calls += 1
        return self.cloud


@dataclass
class SwarmDeps:
    """Túi phụ thuộc được truyền vào mọi node của graph."""

    router: ModelRouter
    search: SearchPort
    citations: CitationPort
    corpus: CorpusPort
    grounding_threshold: float = 0.80
    min_papers: int = 5
    snowball_depth: int = 1
    max_papers: int = 200
    baseline_minutes: float = 14 * 8 * 60  # 14 ngày làm tay × 8h (§7.3)
    extras: dict[str, Any] = field(default_factory=dict)
