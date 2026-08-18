"""API cho SLR Swarm (Phase 2).

Skeleton hiện chạy trên adapter in-memory (`deps_provider`) nên demo được ngay
không cần API key. Khi có vLLM/Ollama + SerpApi thật, chỉ cần thay
`build_default_deps` — route và schema giữ nguyên.
"""

from __future__ import annotations
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.slr_swarm.contracts import KpiSnapshot, PICOFrame, PaperRecord
from src.agents.slr_swarm.deps_provider import build_default_deps
from src.agents.slr_swarm.graph import run_data_analysis, run_slr
from src.agents.slr_swarm.agents.gap_finder import run_gap_finder
from src.agents.slr_swarm.agents.snowball import run_snowball
from src.agents.slr_swarm.agents.peer_screener import run_peer_screener
from src.agents.slr_swarm.agents.prisma_drafter import run_prisma_drafter
from src.agents.slr_swarm.agents.scope_optimizer import run_scope_optimizer, ScopeAnalysisResult
from src.agents.slr_swarm.agents.criteria_generator import run_criteria_generator, CriteriaGenerationResult
from src.agents.slr_swarm.kpi import compute_kpi, estimated_cost_saved
from src.config import get_settings

router = APIRouter(prefix="/slr-swarm", tags=["slr-swarm"])

def _is_real() -> bool:
    is_test = bool(os.environ.get("PYTEST_CURRENT_TEST")) or get_settings().app_env == "test"
    s = get_settings()
    return not is_test and bool(s.openai_api_key or s.effective_gemini_api_key)

def _dump(value) -> dict | None:
    return value.model_dump() if value is not None else None

# ----------------- OLD ALL-IN-ONE ENDPOINT -----------------
class SLRRunRequest(BaseModel):
    idea: str = Field(min_length=3)
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    human_action: str = ""

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

@router.post("/review", response_model=SLRRunResponse)
async def run_review(payload: SLRRunRequest) -> SLRRunResponse:
    deps = build_default_deps(use_real_llm=_is_real())
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

# ----------------- DECOUPLED ENDPOINTS (NEW) -----------------
class SetupRequest(BaseModel):
    idea: str
    research_field: str = ""
    criteria_include: list[str] = Field(default_factory=list)
    criteria_exclude: list[str] = Field(default_factory=list)
    corpus: list[dict] = Field(default_factory=list)

class SetupResponse(BaseModel):
    pico: dict | None = None
    gap_map: dict | None = None
    warnings: list[str] = []
    trace: list[dict] = []
    error: str = ""

@router.post("/step1-setup", response_model=SetupResponse)
async def step1_setup(payload: SetupRequest) -> SetupResponse:
    deps = build_default_deps(use_real_llm=_is_real())
    corpus_records = [PaperRecord(**c) for c in payload.corpus] if payload.corpus else []
    state = await run_gap_finder({
        "idea": payload.idea,
        "research_field": payload.research_field,
        "criteria_include": payload.criteria_include,
        "criteria_exclude": payload.criteria_exclude,
        "corpus": corpus_records,
        "warnings": []
    }, deps)
    return SetupResponse(
        pico=_dump(state.get("pico")),
        gap_map=_dump(state.get("gap_map")),
        warnings=state.get("warnings", []),
        trace=state.get("trace", []),
        error=state.get("error", "")
    )

class ScopeRequest(BaseModel):
    idea: str
    research_field: str = ""

@router.post("/optimize-scope", response_model=ScopeAnalysisResult)
async def optimize_scope(payload: ScopeRequest) -> ScopeAnalysisResult:
    """Agent Cố Vấn Phạm Vi (Scope Optimizer Agent) — Phân tích độ rộng/hẹp đề tài."""
    return await run_scope_optimizer(payload.idea, payload.research_field)

class CriteriaRequest(BaseModel):
    idea: str
    research_field: str = ""

@router.post("/generate-criteria", response_model=CriteriaGenerationResult)
async def generate_criteria(payload: CriteriaRequest) -> CriteriaGenerationResult:
    """Agent Tự Động Sinh Tiêu Chí (Criteria Auto-Generator) — Đề xuất Inclusion & Exclusion."""
    return await run_criteria_generator(payload.idea, payload.research_field)


class SearchRequest(BaseModel):
    idea: str
    pico: dict
    corpus: list[dict] = Field(default_factory=list) # Add existing corpus so Snowball can expand it!

class SearchResponse(BaseModel):
    corpus: list[dict] = []
    seed_ids: list[str] = []
    warnings: list[str] = []
    trace: list[dict] = []
    error: str = ""

@router.post("/step2-search", response_model=SearchResponse)
async def step2_search(payload: SearchRequest) -> SearchResponse:
    deps = build_default_deps(use_real_llm=_is_real())
    pico = PICOFrame(**payload.pico) if payload.pico else None
    
    # If the user already provided a corpus (from manual search), we feed it into state so Agent 2 can expand it.
    initial_corpus = [PaperRecord(**c) for c in payload.corpus] if payload.corpus else []
    
    state = await run_snowball({"idea": payload.idea, "pico": pico, "corpus": initial_corpus, "warnings": []}, deps)
    corpus_dicts = [_dump(p) for p in state.get("corpus", [])]
    return SearchResponse(
        corpus=corpus_dicts,
        seed_ids=state.get("seed_ids", []),
        warnings=state.get("warnings", []),
        trace=state.get("trace", []),
        error=state.get("error", "")
    )

class DraftRequest(BaseModel):
    idea: str
    pico: dict
    corpus: list[dict]
    inclusion_criteria: list[str] = []
    exclusion_criteria: list[str] = []

class DraftResponse(BaseModel):
    included_ids: list[str] = []
    grounding_precision: float = 0.0
    prisma_rows: list[dict] = []
    latex: str = ""
    bibtex: str = ""
    kpi: KpiSnapshot | None = None
    cost_saved_usd: float = 0.0
    warnings: list[str] = []
    trace: list[dict] = []
    error: str = ""

@router.post("/step3-draft", response_model=DraftResponse)
async def step3_draft(payload: DraftRequest) -> DraftResponse:
    deps = build_default_deps(use_real_llm=_is_real())
    pico = PICOFrame(**payload.pico) if payload.pico else None
    corpus = [PaperRecord(**c) for c in payload.corpus]
    
    state = {
        "idea": payload.idea,
        "pico": pico,
        "corpus": corpus,
        "inclusion_criteria": payload.inclusion_criteria,
        "exclusion_criteria": payload.exclusion_criteria,
        "warnings": [],
        "started_at": time.monotonic()
    }
    
    state = await run_peer_screener(state, deps)
    if state.get("error"):
        return DraftResponse(error=state["error"])
        
    state = await run_prisma_drafter(state, deps)
    if state.get("error"):
        return DraftResponse(error=state["error"])
        
    kpi = compute_kpi(state, deps)
    draft = state.get("draft")
    
    return DraftResponse(
        included_ids=state.get("included_ids", []),
        grounding_precision=state.get("grounding_precision", 0.0),
        prisma_rows=[row.model_dump() for row in state.get("prisma_rows", [])],
        latex=draft.latex if draft else "",
        bibtex=draft.bibtex if draft else "",
        kpi=kpi,
        cost_saved_usd=estimated_cost_saved(kpi) if kpi else 0.0,
        warnings=state.get("warnings", []),
        trace=state.get("trace", [])
    )

# ----------------- DATA ANALYSIS (Agent 5) -----------------
class DataAnalysisRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    goal: str = ""

@router.post("/analyze")
async def run_analysis(payload: DataAnalysisRequest) -> dict:
    """Luồng 2 — profile dữ liệu, gợi ý phương pháp và sinh code phân tích."""
    deps = build_default_deps(use_real_llm=_is_real())
    state = await run_data_analysis(payload.csv_text, payload.goal, deps)

    if state.get("error"):
        raise HTTPException(status_code=422, detail=state["error"])

    return {
        "profile": _dump(state.get("profile")),
        "plan": _dump(state.get("plan")),
        "warnings": state.get("warnings", []),
        "trace": state.get("trace", []),
    }


# ----------------- CITATION GENEALOGY (Agent 1: Smart Snowballing) -----------------
class GenealogyRequest(BaseModel):
    paper_id: str
    title: str
    doi: str = ""
    authors: str = ""
    year: int = 2024
    abstract: str = ""

@router.post("/paper-genealogy")
async def get_paper_genealogy(payload: GenealogyRequest) -> dict:
    """Khám phá cây phả hệ trích dẫn: 2 chiều Backward (tiền đề) và Forward (kế thừa)."""
    deps = build_default_deps(use_real_llm=_is_real())
    backward_refs = []
    forward_cits = []
    
    try:
        b_records = await deps.citations.references(payload.paper_id or payload.doi)
        f_records = await deps.citations.citations(payload.paper_id or payload.doi)
        if b_records:
            backward_refs = [_dump(r) for r in b_records[:5]]
        if f_records:
            forward_cits = [_dump(r) for r in f_records[:5]]
    except Exception:
        pass
        
    if not backward_refs or not forward_cits:
        llm = deps.router.pick("planning")
        prompt = f"""You are an expert in academic citation network analysis and systematic literature review.
Given this research paper:
- Title: {payload.title}
- Authors: {payload.authors}
- Year: {payload.year}
- Abstract: {payload.abstract}

Identify:
1. "backward_ancestors": 3-4 seminal, foundational papers (published before {payload.year}) that this paper built upon.
2. "forward_descendants": 3-4 recent subsequent papers (published between {payload.year} and 2026) that cited and extended this paper's work.

Return ONLY a valid JSON object:
{{
  "backward_ancestors": [
    {{"id": "gen_b_1", "title": "Foundational Paper Title", "authors": "Author et al.", "year": 2019, "venue": "Nature / CVPR / ICML", "citations": 850, "doi": "10.1016/...", "relevance_note": "Cung cấp khung lý thuyết nền tảng và bộ dữ liệu gốc."}}
  ],
  "forward_descendants": [
    {{"id": "gen_f_1", "title": "Recent Extension Title", "authors": "Author et al.", "year": 2025, "venue": "IEEE TPAMI / NeurIPS", "citations": 45, "doi": "10.1109/...", "relevance_note": "Mở rộng phương pháp và kiểm nghiệm trên môi trường thời gian thực."}}
  ]
}}
"""
        try:
            raw = await llm.complete(prompt)
            from src.agents.slr_swarm.json_utils import parse_object
            data = parse_object(raw)
            if not backward_refs and data.get("backward_ancestors"):
                backward_refs = data["backward_ancestors"]
            if not forward_cits and data.get("forward_descendants"):
                forward_cits = data["forward_descendants"]
        except Exception:
            pass

    return {
        "seed_paper": payload.model_dump(),
        "backward_ancestors": backward_refs or [],
        "forward_descendants": forward_cits or []
    }
