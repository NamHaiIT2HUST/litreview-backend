from src.agents.state import AgentState
from src.services.integrity_service import check_retraction


async def guard_node(state: AgentState) -> dict:
    """
    Integrity Guard: đối chiếu real-time với Crossref trước khi cho phép
    1 chunk được dùng làm nguồn trong Draft.

    - Chunk có doi bị retracted -> loại khỏi danh sách, ghi vào blocked_sources.
    - Chunk không có doi, hoặc Crossref không xác định được -> giữ lại
      (unknown != retracted, không mặc định là xấu).
    - Nếu sau khi lọc không còn chunk nào -> trả error, dừng pipeline
      (không gọi LLM trên tập rỗng).
    """
    if state.get("error"):
        return {}

    chunks = state.get("chunks", [])
    if not chunks:
        return {"error": "Không có chunk nào để kiểm tra."}

    doi_cache: dict[str, dict] = {}  # tránh gọi Crossref trùng DOI trong 1 request
    kept_chunks = []
    blocked_sources = []

    for doc in chunks:
        doi = doc.metadata.get("doi")

        if not doi:
            kept_chunks.append(doc)
            continue

        if doi not in doi_cache:
            doi_cache[doi] = await check_retraction(doi)

        result = doi_cache[doi]
        if result["status"] == "retracted":
            blocked_sources.append({"doi": doi, "detail": result["detail"]})
            continue  # loại chunk này, không đưa vào draft

        kept_chunks.append(doc)

    if not kept_chunks:
        return {
            "error": "Tất cả nguồn liên quan đã bị Integrity Guard chặn (retracted).",
            "blocked_sources": blocked_sources,
        }

    return {"chunks": kept_chunks, "blocked_sources": blocked_sources}
