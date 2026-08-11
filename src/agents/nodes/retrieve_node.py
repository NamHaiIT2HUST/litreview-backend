from src.agents.state import AgentState
from src.services.vector_store import vector_store_service


async def retrieve_node(state: AgentState) -> dict:
    """Lấy các chunk liên quan tới câu hỏi từ Vector DB (ChromaDB)."""
    query = state.get("query", "")

    if not query:
        return {"error": "Thiếu query, không thể tìm kiếm."}

    chunks = await vector_store_service.search_similar_documents(query, top_k=4)

    if not chunks:
        return {"error": "Không tìm thấy tài liệu nào liên quan trong Vector DB."}

    return {"chunks": chunks}
