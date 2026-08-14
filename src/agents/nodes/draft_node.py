from src.agents.state import AgentState
from src.services.rag_service import rag_service


async def draft_node(state: AgentState) -> dict:
    """Sinh câu trả lời từ chunk đã retrieve, áp dụng Map-Reduce (PaperQA2 style)."""
    if state.get("error"):
        return {}

    query = state.get("query", "")
    chunks = state.get("chunks", [])

    # Dùng pipeline Map-Reduce (có scoring, context footer, citation keys)
    result = await rag_service.generate_answer_with_citations(query, chunks)

    # Nếu không có chunks hoặc LLM không tìm thấy thông tin
    if not result.get("citations") and not chunks:
        return {
            "citations": [],
            "response": result.get("answer", "Không tìm thấy câu trả lời có thể truy vết được nguồn cho câu hỏi này."),
        }

    return {
        "citations": result.get("citations", []),
        "response": result.get("answer", "")
    }
