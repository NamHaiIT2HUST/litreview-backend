"""API cho SLR Swarm (Phase 2).

Skeleton hiện chạy trên adapter in-memory (`deps_provider`) nên demo được ngay
không cần API key. Khi có vLLM/Ollama + SerpApi thật, chỉ cần thay
`build_default_deps` — route và schema giữ nguyên.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.slr_swarm.contracts import KpiSnapshot
from src.agents.slr_swarm.deps_provider import build_default_deps
from src.agents.slr_swarm.graph import run_data_analysis, run_slr
from src.agents.slr_swarm.kpi import estimated_cost_saved

router = APIRouter(prefix="/slr-swarm", tags=["slr-swarm"])


class SLRRunRequest(BaseModel):
    idea: str = Field(min_length=3)
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    human_action: str = ""  # approve | override | edit — để resume sau cảnh báo đỏ


class SLRRunResponse(BaseModel):
    pico: dict | None = None
    gap_map: dict | None = None
    papers_found: int = 0
    included_ids: list[str] = Field(default_factory=list)
    grounding_precision: float = 0.0
    gate_passed: bool = False
    awaiting_human: bool = False
    warnings: list[str] = Field(default_factory=list)
    prisma_rows: list[dict] = Field(default_factory=list)
    latex: str = ""
    bibtex: str = ""
    kpi: KpiSnapshot | None = None
    cost_saved_usd: float = 0.0
    trace: list[dict] = Field(default_factory=list)
    error: str = ""


class DataAnalysisRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    goal: str = ""


def _dump(value) -> dict | None:
    return value.model_dump() if value is not None else None


@router.post("/review", response_model=SLRRunResponse)
async def run_review(payload: SLRRunRequest) -> SLRRunResponse:
    """Luồng 1 — chạy trọn pipeline SLR và trả về bản thảo + KPI."""
    deps = build_default_deps()
    state = await run_slr(
        payload.idea,
        deps,
        inclusion_criteria=payload.inclusion_criteria,
        exclusion_criteria=payload.exclusion_criteria,
        human_action=payload.human_action,
    )

    draft = state.get("draft")
    kpi = state.get("kpi")
    return SLRRunResponse(
        pico=_dump(state.get("pico")),
        gap_map=_dump(state.get("gap_map")),
        papers_found=len(state.get("corpus", [])),
        included_ids=state.get("included_ids", []),
        grounding_precision=state.get("grounding_precision", 0.0),
        gate_passed=bool(state.get("gate_passed")),
        awaiting_human=bool(state.get("awaiting_human")),
        warnings=state.get("warnings", []),
        prisma_rows=[row.model_dump() for row in state.get("prisma_rows", [])],
        latex=draft.latex if draft else "",
        bibtex=draft.bibtex if draft else "",
        kpi=kpi,
        cost_saved_usd=estimated_cost_saved(kpi) if kpi else 0.0,
        trace=state.get("trace", []),
        error=state.get("error", ""),
    )


@router.post("/analyze")
async def run_analysis(payload: DataAnalysisRequest) -> dict:
    """Luồng 2 — profile dữ liệu, gợi ý phương pháp và sinh code phân tích."""
    deps = build_default_deps()
    state = await run_data_analysis(payload.csv_text, payload.goal, deps)

    if state.get("error"):
        raise HTTPException(status_code=422, detail=state["error"])

    return {
        "profile": _dump(state.get("profile")),
        "plan": _dump(state.get("plan")),
        "warnings": state.get("warnings", []),
        "trace": state.get("trace", []),
    }
