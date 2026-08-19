"""LangGraph workflow for evidence-first literature synthesis."""
from __future__ import annotations

import uuid

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from src.database import DATABASE_URL, session_scope
from src.services.synthesis_service import synthesis_service
from src.models.synthesis_schemas import EvidenceDimension
from src.services.synthesis_write_gate import SynthesisWriteGate
from src.synthesis.state import SynthesisState

synthesis_write_gate = SynthesisWriteGate(DATABASE_URL)


async def prepare_node(state: SynthesisState) -> dict:
    session_id = uuid.UUID(state["session_id"])
    async with session_scope() as db:
        prepared = await synthesis_service.prepare_session(db, session_id)
    return {
        **prepared,
        "dimensions": [dimension.value for dimension in EvidenceDimension],
    }


def dispatch_papers(state: SynthesisState):
    return [
        Send(
            "extract_paper",
            {
                "session_id": state["session_id"],
                "research_question": state["research_question"],
                "paper_id": paper_id,
                "dimensions": state["dimensions"],
            },
        )
        for paper_id in state["paper_ids"]
    ]


async def extract_paper_node(state: dict) -> dict:
    paper_id = uuid.UUID(state["paper_id"])
    session_id = uuid.UUID(state["session_id"])
    async with synthesis_write_gate.hold():
        async with session_scope() as db:
            await synthesis_service.extract_paper_evidence(
                db,
                session_id=session_id,
                paper_id=paper_id,
                research_question=state["research_question"],
                dimensions=list(state["dimensions"]),
            )
    return {"completed_papers": [str(paper_id)]}


async def cross_paper_node(state: SynthesisState) -> dict:
    expected = set(state["paper_ids"])
    completed = set(state.get("completed_papers", []))
    if completed != expected:
        missing = expected - completed
        raise RuntimeError(
            "Paper extraction fan-in incomplete; missing: "
            + ", ".join(sorted(missing))
        )

    async with session_scope() as db:
        claim_ids = await synthesis_service.cross_paper_analysis(
            db,
            session_id=uuid.UUID(state["session_id"]),
            research_question=state["research_question"],
        )
    return {"claim_ids": claim_ids}


async def deduplicate_evidence_node(state: SynthesisState) -> dict:
    """Fail open: semantic QA must never prevent synthesis completion."""
    try:
        async with session_scope() as db:
            count = await synthesis_service.deduplicate_evidence(
                db,
                session_id=uuid.UUID(state["session_id"]),
            )
        return {"deduplicated_evidence_count": count}
    except Exception:
        return {"deduplicated_evidence_count": 0}


MAX_COVERAGE_EXPANSION_ROUNDS = 3


async def ensure_coverage_node(state: SynthesisState) -> dict:
    expected = set(state["paper_ids"])
    completed = set(state.get("completed_papers", []))
    if completed != expected:
        raise RuntimeError("Cannot expand retrieval before every paper is extracted")
    async with synthesis_write_gate.hold():
        async with session_scope() as db:
            all_expanded: list[str] = []
            for _ in range(MAX_COVERAGE_EXPANSION_ROUNDS):
                # expand_thin_dimensions_once marks a dimension "sparse" (and
                # excludes it from future rounds) once an expansion attempt
                # yields no new evidence, so this loop naturally terminates
                # even when coverage never reaches the 2-paper threshold.
                expanded = await synthesis_service.expand_thin_dimensions_once(
                    db,
                    session_id=uuid.UUID(state["session_id"]),
                    paper_ids=[uuid.UUID(value) for value in state["paper_ids"]],
                    research_question=state["research_question"],
                    dimensions=list(state["dimensions"]),
                )
                if not expanded:
                    break
                all_expanded.extend(expanded)
            await synthesis_service.recover_and_validate_paper_coverage(
                db,
                session_id=uuid.UUID(state["session_id"]),
                paper_ids=[uuid.UUID(value) for value in state["paper_ids"]],
                research_question=state["research_question"],
            )
    return {"expanded_dimensions": all_expanded}


async def build_outline_node(state: SynthesisState) -> dict:
    async with session_scope() as db:
        section_ids = await synthesis_service.build_outline(
            db,
            session_id=uuid.UUID(state["session_id"]),
            research_question=state["research_question"],
        )
    return {"section_ids": section_ids}


def dispatch_sections(state: SynthesisState):
    return [
        Send(
            "draft_section",
            {
                "session_id": state["session_id"],
                "research_question": state["research_question"],
                "section_id": section_id,
            },
        )
        for section_id in state["section_ids"]
    ]


async def draft_section_node(state: dict) -> dict:
    async with session_scope() as db:
        payload = await synthesis_service.draft_section(
            db,
            section_id=uuid.UUID(state["section_id"]),
            research_question=state["research_question"],
        )
    return {"drafted_sections": [payload]}


async def finalize_node(state: SynthesisState) -> dict:
    expected_sections = set(state.get("section_ids", []))
    drafted = state.get("qa_sections", state.get("drafted_sections", []))
    drafted_ids = {str(item.get("section_id")) for item in drafted}
    if drafted_ids != expected_sections:
        missing = expected_sections - drafted_ids
        raise RuntimeError(
            "Section drafting fan-in incomplete; missing: "
            + ", ".join(sorted(missing))
        )

    async with session_scope() as db:
        review = await synthesis_service.finalize_review(
            db,
            session_id=uuid.UUID(state["session_id"]),
            drafted_sections=drafted,
            qa_warning=state.get("qa_warning"),
        )
    return {"review_markdown": review}


async def qa_review_node(state: SynthesisState) -> dict:
    expected_sections = set(state.get("section_ids", []))
    drafted = state.get("drafted_sections", [])
    drafted_ids = {str(item.get("section_id")) for item in drafted}
    if drafted_ids != expected_sections:
        missing = expected_sections - drafted_ids
        raise RuntimeError("Cannot run QA before all sections are drafted: " + ", ".join(sorted(missing)))

    try:
        async with session_scope() as db:
            qa_sections, qa_warning = await synthesis_service.qa_drafted_review(
                db,
                session_id=uuid.UUID(state["session_id"]),
                drafted_sections=drafted,
            )
        return {"qa_sections": qa_sections, "qa_warning": qa_warning or ""}
    except Exception as exc:
        return {
            "qa_sections": drafted,
            "qa_warning": f"Automatic QA could not be completed: {str(exc)[:500]}",
        }


def build_synthesis_graph(checkpointer=None):
    graph = StateGraph(SynthesisState)
    graph.add_node("prepare", prepare_node)
    graph.add_node("extract_paper", extract_paper_node)
    graph.add_node("ensure_coverage", ensure_coverage_node)
    graph.add_node("deduplicate_evidence", deduplicate_evidence_node)
    graph.add_node("cross_paper", cross_paper_node)
    graph.add_node("build_outline", build_outline_node)
    graph.add_node("draft_section", draft_section_node)
    graph.add_node("qa_review", qa_review_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "prepare")
    graph.add_conditional_edges("prepare", dispatch_papers, ["extract_paper"])
    graph.add_edge("extract_paper", "ensure_coverage")
    graph.add_edge("ensure_coverage", "deduplicate_evidence")
    graph.add_edge("deduplicate_evidence", "cross_paper")
    graph.add_edge("cross_paper", "build_outline")
    graph.add_conditional_edges("build_outline", dispatch_sections, ["draft_section"])
    graph.add_edge("draft_section", "qa_review")
    graph.add_edge("qa_review", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)
