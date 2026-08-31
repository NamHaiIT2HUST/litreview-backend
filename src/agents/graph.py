from langgraph.graph import END, StateGraph

from src.agents.nodes.agentic_rag_node import agentic_rag_node
from src.agents.nodes.draft_node import draft_node
from src.agents.nodes.guard_node import guard_node
from src.agents.nodes.retrieve_node import retrieve_node
from src.agents.state import AgentState


def route_query(state: AgentState) -> str:
    """Điều hướng truy vấn dựa trên task_type."""
    task_type = state.get("task_type", "standard")
    if task_type == "deep_research":
        return "agentic_rag"
    return "retrieve"


def after_retrieve(state: AgentState) -> str:
    """Nếu retrieve lỗi (thiếu query / không tìm thấy chunk) thì dừng, không gọi Guard."""
    if state.get("error"):
        return END
    return "guard"


def after_guard(state: AgentState) -> str:
    """Nếu Guard chặn hết nguồn (toàn bộ retracted) thì dừng, không gọi LLM."""
    if state.get("error"):
        return END
    return "draft"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("guard", guard_node)
    graph.add_node("draft", draft_node)
    graph.add_node("agentic_rag", agentic_rag_node)

    # Add edges
    graph.set_conditional_entry_point(
        route_query,
        {
            "agentic_rag": "agentic_rag",
            "retrieve": "retrieve"
        }
    )
    graph.add_conditional_edges("retrieve", after_retrieve)
    graph.add_conditional_edges("guard", after_guard)
    graph.add_edge("draft", END)
    graph.add_edge("agentic_rag", END)

    return graph.compile()


agent = build_graph()
