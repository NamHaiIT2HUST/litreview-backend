from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """State schema cho LangGraph agent (flow: retrieve -> draft).

    Mỗi node đọc và ghi vào state này.
    total=False cho phép tất cả fields là optional.
    """

    query: str
    chunks: list  # list[Document] lấy từ vector_store_service
    blocked_sources: list  # nguồn bị Integrity Guard chặn (retracted)
    citations: list[dict]  # list of citation metadata dictionaries
    response: str  # câu trả lời dạng text đầy đủ (ghép từ citations)
    error: str
