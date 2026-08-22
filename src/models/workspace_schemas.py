"""Pydantic schemas for Workspace endpoints.

PaperQA2-inspired improvements (2026-08):
  - WorkspaceChatRequest: optional paper_id filter to scope retrieval to one paper.
  - WorkspaceChatResponse: structured context_used (list[dict] with citation metadata)
    and citations (traceable source list, mirroring PaperQA2's bib dict).
"""
from typing import Any

from pydantic import BaseModel


class EvidenceCoordsRequest(BaseModel):
    filename: str
    page: int
    snippet: str


class RectCoord(BaseModel):
    x: float
    y: float
    width: float
    height: float


class EvidenceCoordsResponse(BaseModel):
    rects: list[RectCoord]


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    total_pages: int
    total_chunks: int
    message: str


class DirectUploadResponse(BaseModel):
    paper_id: str
    title: str
    filename: str
    total_pages: int
    total_chunks: int
    source: str = "direct_upload"
    message: str


class WorkspaceChatRequest(BaseModel):
    message: str
    # Optional: scope retrieval to a specific paper (PaperQA2-inspired scoping).
    # If None, search across all papers in the workspace collection.
    paper_id: str | None = None
    paper_ids: list[str] | None = None


class CitationEntry(BaseModel):
    """Traceable citation entry — mirrors PaperQA2's bib dict entry.

    Each entry links a citation key (as it appears in the answer text, e.g. 'paper_p3')
    back to its source paper, page, and paper DB id so the UI can render clickable
    source cards rather than opaque "Nguồn #N" labels.
    """
    key: str
    paper_title: str
    page: Any  # int or "?" for unknown
    paper_id: str
    filename: str
    cited_in_answer: bool = False  # True if key actually appears in the answer text


class ContextEntry(BaseModel):
    """Structured context chunk shown in the 'Sources Used' panel.

    Replaces the old flat list[str] of raw page_content so the UI has enough
    metadata to display a meaningful source card with title, page, and a summary
    snippet instead of the raw extracted text.
    """
    key: str
    paper_title: str
    page_display: str  # human-readable (1-indexed), e.g. "4" or "?"
    paper_id: str
    snippet: str       # First ~250 chars of the MAP-generated summary (not raw chunk text)
    score: int         # MAP relevance score (0-10)


class WorkspaceChatResponse(BaseModel):
    answer: str
    # Structured context entries (replaces raw list[str] of page_content)
    context_used: list[dict]  # list[ContextEntry] — kept as dict for API compatibility
    # Traceable citations: one entry per unique citation key used/considered
    citations: list[dict] = []  # list[CitationEntry] — kept as dict for API compatibility
    # RAG Guardrail & Hallucination verification result
    guardrail: dict | None = None


class RAGEvalRequest(BaseModel):
    question: str
    answer: str
    context_chunks: list[dict] = []


class RAGEvalRunRequest(BaseModel):
    paper_ids: list[str] = []
    max_questions_per_paper: int = 2

