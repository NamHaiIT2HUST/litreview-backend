from src.agents.state import AgentState
from src.services.rag_service import rag_service


async def draft_node(state: AgentState) -> dict:
    """Sinh câu trả lời từ chunk đã retrieve, mỗi câu bắt buộc kèm chunk_id."""
    if state.get("error"):
        return {}

    query = state.get("query", "")
    chunks = state.get("chunks", [])

    citations = await rag_service.generate_structured_answer(query, chunks)

    if not citations:
        return {
            "citations": [],
            "response": "Không tìm thấy câu trả lời có thể truy vết được nguồn cho câu hỏi này.",
        }

    full_text = " ".join(c["sentence"] for c in citations)
    return {"citations": citations, "response": full_text}
