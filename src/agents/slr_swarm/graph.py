"""Master Orchestrator — dựng LangGraph cho 2 luồng của Phase 2.

Khác biệt so với nhánh `feature/multi-agent-synthesis` (fan-out QA workers):
ở đây các agent nối thành một *state graph có checkpoint*, có cổng kiểm định
Grounding >= 80% chặn giữa đường, và có điểm dừng HITL để nghiên cứu viên
Approve / Override / Edit trước khi bản thảo được sinh ra.

    START → Agent1 (PICO & Gap) → Agent2 (Snowball) → Agent3 (Peer Screener)
          → [gate: grounding >= threshold?]
                ├─ không đạt → human_review (interrupt) → Approve/Override → Agent4
                └─ đạt      → Agent4 (PRISMA & Drafter) → finalize (KPI) → END
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.slr_swarm.agents.code_copilot import run_code_copilot
from src.agents.slr_swarm.agents.gap_finder import run_gap_finder
from src.agents.slr_swarm.agents.peer_screener import run_peer_screener
from src.agents.slr_swarm.agents.prisma_drafter import run_prisma_drafter
from src.agents.slr_swarm.agents.snowball import run_snowball
from src.agents.slr_swarm.kpi import compute_kpi
from src.agents.slr_swarm.ports import SwarmDeps
from src.agents.slr_swarm.state import DataAnalysisState, SLRState

AgentFn = Callable[[dict, SwarmDeps], Awaitable[dict]]

HUMAN_REVIEW_NODE = "human_review"


def _bind(fn: AgentFn, deps: SwarmDeps, name: str) -> Callable[[dict], Awaitable[dict]]:
    """Gắn deps vào agent và bọc lỗi: một agent hỏng thì dừng graph, không chạy tiếp mù."""

    async def node(state: dict) -> dict:
        if state.get("error"):
            return {}
        try:
            return await fn(state, deps)
        except Exception as exc:  # noqa: BLE001 - báo lỗi ra state để HITL thấy
            return {
                "error": f"{name} lỗi: {exc}",
                "trace": [{"agent": name, "error": repr(exc)}],
            }

    node.__name__ = name
    return node


# --------------------------------------------------------------------------- #
# Luồng 1: Systematic Literature Review
# --------------------------------------------------------------------------- #
def _make_gate(deps: SwarmDeps) -> Callable[[dict], dict]:
    async def gate(state: dict) -> dict:
        if state.get("error"):
            return {}

        precision = float(state.get("grounding_precision", 0.0) or 0.0)
        kept = len(state.get("included_ids", []))
        warnings = list(state.get("warnings", []))
        passed = precision >= deps.grounding_threshold and kept >= deps.min_papers

        if not passed:
            warnings.append(
                f"Cảnh báo đỏ (Insufficient Data): grounding {precision:.0%} "
                f"/ {kept} bài — chưa đạt ngưỡng {deps.grounding_threshold:.0%} "
                f"và tối thiểu {deps.min_papers} bài. Cần nghiên cứu viên xác nhận."
            )

        return {
            "gate_passed": passed,
            "awaiting_human": not passed,
            "warnings": warnings,
            "trace": [{"agent": "gate", "passed": passed, "grounding_precision": precision}],
        }

    return gate


async def _human_review(state: dict) -> dict:
    """Điểm dừng HITL.

    Khi graph được compile kèm checkpointer, LangGraph interrupt TRƯỚC node này;
    UI đọc state, người dùng bấm Approve/Override/Edit rồi resume. Không có
    checkpointer (test, batch) thì mặc định là chặn — im lặng đi tiếp mới là nguy hiểm.
    """
    action = (state.get("human_action") or "").strip().lower()
    return {
        "awaiting_human": action not in ("approve", "override", "edit"),
        "trace": [{"agent": "human_review", "action": action or "pending"}],
    }


def _route_after_gate(state: dict) -> str:
    if state.get("error"):
        return "finalize"
    return "draft" if state.get("gate_passed") else HUMAN_REVIEW_NODE


def _route_after_human(state: dict) -> str:
    if state.get("error") or state.get("awaiting_human"):
        return "finalize"
    return "draft"


def _make_finalize(deps: SwarmDeps) -> Callable[[dict], Awaitable[dict]]:
    async def finalize(state: dict) -> dict:
        return {
            "kpi": compute_kpi(state, deps),
            "trace": [{"agent": "finalize", "error": state.get("error", "")}],
        }

    return finalize


def build_slr_graph(deps: SwarmDeps, *, checkpointer: Any = None):
    """Compile graph luồng 1. Truyền `checkpointer` để bật interrupt HITL thật."""
    graph = StateGraph(SLRState)

    graph.add_node("gap_finder", _bind(run_gap_finder, deps, "gap_finder"))
    graph.add_node("snowball", _bind(run_snowball, deps, "snowball"))
    graph.add_node("screener", _bind(run_peer_screener, deps, "screener"))
    graph.add_node("gate", _make_gate(deps))
    graph.add_node(HUMAN_REVIEW_NODE, _human_review)
    graph.add_node("draft", _bind(run_prisma_drafter, deps, "draft"))
    graph.add_node("finalize", _make_finalize(deps))

    graph.add_edge(START, "gap_finder")
    graph.add_edge("gap_finder", "snowball")
    graph.add_edge("snowball", "screener")
    graph.add_edge("screener", "gate")
    graph.add_conditional_edges(
        "gate", _route_after_gate, {"draft": "draft", HUMAN_REVIEW_NODE: HUMAN_REVIEW_NODE, "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        HUMAN_REVIEW_NODE, _route_after_human, {"draft": "draft", "finalize": "finalize"}
    )
    graph.add_edge("draft", "finalize")
    graph.add_edge("finalize", END)

    if checkpointer is not None:
        return graph.compile(checkpointer=checkpointer, interrupt_before=[HUMAN_REVIEW_NODE])
    return graph.compile()


async def run_slr(
    idea: str,
    deps: SwarmDeps,
    *,
    inclusion_criteria: list[str] | None = None,
    exclusion_criteria: list[str] | None = None,
    human_action: str = "",
) -> dict:
    """Chạy trọn luồng 1 một lượt (không checkpoint) — dùng cho API demo và test."""
    app = build_slr_graph(deps)
    return await app.ainvoke(
        {
            "idea": idea,
            "inclusion_criteria": inclusion_criteria or [],
            "exclusion_criteria": exclusion_criteria or [],
            "human_action": human_action,
            "warnings": [],
            "started_at": time.monotonic(),
        }
    )


# --------------------------------------------------------------------------- #
# Luồng 2: Initial Data Analysis
# --------------------------------------------------------------------------- #
def build_data_graph(deps: SwarmDeps):
    graph = StateGraph(DataAnalysisState)
    graph.add_node("code_copilot", _bind(run_code_copilot, deps, "code_copilot"))
    graph.add_edge(START, "code_copilot")
    graph.add_edge("code_copilot", END)
    return graph.compile()


async def run_data_analysis(csv_text: str, goal: str, deps: SwarmDeps) -> dict:
    app = build_data_graph(deps)
    return await app.ainvoke({"csv_text": csv_text, "goal": goal, "warnings": []})
