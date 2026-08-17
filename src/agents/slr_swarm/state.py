"""State schema cho SLR Swarm graph.

Khác với `src/agents/state.py` (RAG một lượt), state này sống qua nhiều chặng và
được checkpoint lại, để HITL có thể dừng giữa chừng rồi resume.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from src.agents.slr_swarm.contracts import (
    AnalysisPlan,
    DatasetProfile,
    GapMap,
    KpiSnapshot,
    PaperRecord,
    PICOFrame,
    PrismaRow,
    ReviewDraft,
    ScreeningVerdict,
)


def merge_papers(left: list[PaperRecord], right: list[PaperRecord]) -> list[PaperRecord]:
    """Reducer: gộp corpus từ nhiều nhánh swarm, khử trùng theo paper_id.

    Giữ bản có seed_distance nhỏ hơn (gần hạt nhân hơn thì đáng tin hơn).
    """
    merged: dict[str, PaperRecord] = {p.paper_id: p for p in left}
    for paper in right:
        current = merged.get(paper.paper_id)
        if current is None or paper.seed_distance < current.seed_distance:
            merged[paper.paper_id] = paper
    return list(merged.values())


class SLRState(TypedDict, total=False):
    """Luồng 1 — Systematic Literature Review (§4.1 Master Plan)."""

    # Input
    idea: str
    inclusion_criteria: list[str]
    exclusion_criteria: list[str]

    # Agent 1
    pico: PICOFrame
    gap_map: GapMap

    # Agent 2
    corpus: Annotated[list[PaperRecord], merge_papers]
    seed_ids: list[str]

    # Agent 3
    verdicts: list[ScreeningVerdict]
    included_ids: list[str]
    grounding_precision: float

    # Cổng kiểm định + HITL
    gate_passed: bool
    warnings: list[str]
    awaiting_human: bool
    human_action: str  # approve | override | edit

    # Agent 4
    prisma_rows: list[PrismaRow]
    draft: ReviewDraft

    # Vận hành
    kpi: KpiSnapshot
    started_at: float
    error: str
    trace: Annotated[list[dict], operator.add]


class DataAnalysisState(TypedDict, total=False):
    """Luồng 2 — Initial Data Analysis (§4.2 Master Plan)."""

    goal: str
    csv_text: str
    profile: DatasetProfile
    plan: AnalysisPlan
    warnings: list[str]
    error: str
    trace: Annotated[list[dict], operator.add]
