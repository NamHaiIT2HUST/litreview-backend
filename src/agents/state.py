from __future__ import annotations

from typing import TypedDict


class Citation(TypedDict):
    """1 câu trong answer, kèm chunk nào làm bằng chứng."""

    sentence: str
    chunk_id: str
    source: str  # tên file / paper_id của chunk đó


class AgentState(TypedDict, total=False):
    """State schema cho LangGraph agent (flow: retrieve -> draft).

    Mỗi node đọc và ghi vào state này.
    total=False cho phép tất cả fields là optional.
    """

    query: str
    chunks: list  # list[Document] lấy từ vector_store_service
    blocked_sources: list  # nguồn bị Integrity Guard chặn (retracted)
    citations: list[Citation]  # output có cấu trúc: câu nào bám nguồn nào
    response: str  # câu trả lời dạng text đầy đủ (ghép từ citations)
    error: str
