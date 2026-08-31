"""API cho SLR Swarm (Phase 2).

Skeleton hiện chạy trên adapter in-memory (`deps_provider`) nên demo được ngay
không cần API key. Khi có vLLM/Ollama + SerpApi thật, chỉ cần thay
`build_default_deps` — route và schema giữ nguyên.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.agents.slr_swarm.agents.criteria_generator import CriteriaGenerationResult, run_criteria_generator
from src.agents.slr_swarm.agents.gap_finder import run_gap_finder
from src.agents.slr_swarm.agents.scope_optimizer import ScopeAnalysisResult, run_scope_optimizer
from src.agents.slr_swarm.contracts import KpiSnapshot
from src.agents.slr_swarm.deps_provider import build_default_deps
from src.agents.slr_swarm.graph import run_data_analysis, run_slr
from src.agents.slr_swarm.kpi import estimated_cost_saved
from src.config import get_settings

router = APIRouter(prefix="/slr-swarm", tags=["slr-swarm"])
logger = logging.getLogger(__name__)

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


class DataAnalysisRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    goal: str = ""


@router.post("/analyze")
async def analyze_data(payload: DataAnalysisRequest):
    """Endpoint phân tích dữ liệu và lập kế hoạch thống kê."""
    if not payload.csv_text or not payload.csv_text.strip():
        raise HTTPException(status_code=422, detail="csv_text is empty")
    deps = build_default_deps(use_real_llm=_is_real())
    try:
        res = await run_data_analysis(payload.csv_text, payload.goal, deps)
        return res
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ----------------- STUDIO PANEL ENDPOINTS -----------------

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
    """Agent 1: Gap Map & PICO Finder."""
    try:
        deps = build_default_deps(real=_is_real())
        state = {
            "idea": payload.idea,
            "research_field": payload.research_field,
            "criteria_include": payload.criteria_include,
            "criteria_exclude": payload.criteria_exclude,
            "corpus": payload.corpus,
        }
        res = await run_gap_finder(state, deps)
        pico = res.get("pico")
        gap_map = res.get("gap_map")
        return SetupResponse(
            pico=_dump(pico),
            gap_map=_dump(gap_map),
            warnings=res.get("warnings", []),
            trace=res.get("trace", []),
            error=res.get("error", ""),
        )
    except Exception as e:
        return SetupResponse(error=str(e))

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
@router.post("/suggest-criteria", response_model=CriteriaGenerationResult)
async def generate_criteria(payload: CriteriaRequest) -> CriteriaGenerationResult:
    """Agent Tự Động Sinh Tiêu Chí (Criteria Auto-Generator) — Đề xuất Inclusion & Exclusion."""
    return await run_criteria_generator(payload.idea, payload.research_field)


class SearchRequest(BaseModel):
    idea: str
    pico: dict
    corpus: list[dict] = Field(default_factory=list)

class SearchResponse(BaseModel):
    corpus: list[dict] = []
    seed_ids: list[str] = []
    warnings: list[str] = []
    trace: list[dict] = []
    error: str = ""

@router.post("/step2-search", include_in_schema=False)
async def step2_search(payload: SearchRequest):
    """[DISABLED] Snowballing — AI Studio panel removed from UI."""
    raise HTTPException(status_code=410, detail="AI Studio panel đã bị xóa khỏi giao diện.")

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

@router.post("/step3-draft", include_in_schema=False)
async def step3_draft(payload: DraftRequest):
    """[DISABLED] PRISMA + LaTeX drafter — AI Studio panel removed from UI."""
    raise HTTPException(status_code=410, detail="AI Studio panel đã bị xóa khỏi giao diện.")

# ----------------- DATA ANALYSIS (Agent 5 — DISABLED) -----------------
# NOTE: this route shares its path with the active `/analyze` endpoint above,
# which was registered first -- FastAPI matches in registration order, so
# this handler is unreachable. Left in place (dead code) rather than removed
# since disabling this behavior was evidently a deliberate but incomplete
# change; the class is renamed only to stop it from shadowing the real
# DataAnalysisRequest above.
class _DisabledDataAnalysisRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    goal: str = ""

@router.post("/analyze", include_in_schema=False)
async def run_analysis(payload: _DisabledDataAnalysisRequest):
    """[DISABLED] CSV Data Copilot (Agent 5) — AI Studio panel removed from UI."""
    raise HTTPException(status_code=410, detail="AI Studio panel đã bị xóa khỏi giao diện.")


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
            backward_refs = [{**_dump(r), "source": "citation_graph"} for r in b_records[:5]]
        if f_records:
            forward_cits = [{**_dump(r), "source": "citation_graph"} for r in f_records[:5]]
    except Exception:
        pass

    # `deps.citations` (InMemoryCitations, see deps_provider.py) is a fixed
    # in-memory stub with a single demo edge -- there is no real citation-
    # graph integration wired in yet, so this branch fires for every real
    # paper. The LLM below is asked to *invent* plausible-sounding ancestor/
    # descendant papers (titles, DOIs, citation counts included) when no real
    # data is found; those are speculative suggestions, not verified
    # citations, so every entry it produces is tagged "ai_generated" and the
    # frontend must show that distinction rather than presenting them as
    # real search results.
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
                backward_refs = [{**item, "source": "ai_generated"} for item in data["backward_ancestors"]]
            if not forward_cits and data.get("forward_descendants"):
                forward_cits = [{**item, "source": "ai_generated"} for item in data["forward_descendants"]]
        except Exception:
            pass

    return {
        "seed_paper": payload.model_dump(),
        "backward_ancestors": backward_refs or [],
        "forward_descendants": forward_cits or [],
        "has_unverified_ai_entries": any(
            item.get("source") == "ai_generated" for item in (backward_refs or []) + (forward_cits or [])
        ),
    }


# ----------------- PAPER SUMMARY (TL;DR ONE-PAGER) -----------------
class PaperSummaryRequest(BaseModel):
    paper_id: str
    title: str
    abstract: str | None = ""
    authors: Any = ""
    year: Any = 2024
    venue: str | None = ""
    citations: Any = 0
    doi: str | None = ""

@router.post("/paper-summary")
async def get_paper_summary(payload: PaperSummaryRequest) -> dict:
    """Sinh bản tóm tắt TL;DR và cấu trúc bài báo cực kỳ chi tiết."""
    import json

    abstract_text = payload.abstract if payload.abstract and len(payload.abstract) > 20 else "NO ABSTRACT AVAILABLE."

    # --- AUTO-FETCH FULL TEXT IF DOI IS AVAILABLE ---
    full_text = ""
    is_paywalled = False

    if payload.doi:
        try:
            import io

            import aiohttp
            import pypdf
            async with aiohttp.ClientSession() as session:
                unpaywall_url = f"https://api.unpaywall.org/v2/{payload.doi}?email=admin@litreview.ai"
                async with session.get(unpaywall_url, timeout=4) as resp:
                    if resp.status == 200:
                        oa_data = await resp.json()
                        if oa_data.get("best_oa_location") and oa_data["best_oa_location"].get("url_for_pdf"):
                            pdf_url = oa_data["best_oa_location"]["url_for_pdf"]
                            async with session.get(pdf_url, timeout=10) as pdf_resp:
                                if pdf_resp.status == 200:
                                    pdf_bytes = await pdf_resp.read()
                                    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                                    # Đọc TOÀN BỘ bài báo (không giới hạn số trang)
                                    full_text = "\n".join(page.extract_text() for page in reader.pages)
                                    full_text = full_text[:200000] # Giới hạn an toàn (khoảng 50-60 trang)
                        else:
                            is_paywalled = True
        except Exception as e:
            print(f"Full-text fetch failed for {payload.doi}: {e}")
            is_paywalled = True

    # --- XÂY DỰNG PROMPT ĐỘNG ---
    if full_text:
        context_block = f"""
PAPER DETAILS (FULL TEXT EXTRACTED!):
Title: {payload.title}
Authors: {payload.authors}
Year: {payload.year}
Venue: {payload.venue}

--- FULL TEXT (ENTIRE PAPER) ---
{full_text}
--- END FULL TEXT ---

CRITICAL INSTRUCTIONS:
- You have access to the actual full text of this paper! You DO NOT need to guess.
- Extract the EXACT methodology, dataset sizes, limitations, and key findings directly from the full text.
- Be extremely comprehensive and detailed.
"""
        tldr_hint = "Một đoạn tóm tắt siêu tốc (2-3 câu). Bắt buộc ghi chú rõ ràng ở đầu: '🟢 ĐÃ ĐỌC TOÀN VĂN (FULL-TEXT OPEN ACCESS)'"
    else:
        paywall_warning = "🔴 BÀI BÁO BỊ KHÓA BẢN QUYỀN (PAYWALL / TRẢ PHÍ)." if is_paywalled else "⚠️ KHÔNG TÌM THẤY BẢN TOÀN VĂN."

        context_block = f"""
PAPER DETAILS (ABSTRACT ONLY - PAYWALLED):
Title: {payload.title}
Abstract: {abstract_text}
Authors: {payload.authors}
Year: {payload.year}
Venue: {payload.venue}

CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
1. You MUST explicitly start the 'tldr' field with this exact warning: '{paywall_warning} AI chỉ tóm tắt dựa trên Abstract và tiêu đề.'
2. If a specific detail (like dataset size, specific algorithm, or metrics) is NOT in the abstract, you MUST state "Bị khóa bản quyền, không có số liệu" (Paywalled, no data). DO NOT GUESS OR INVENT NUMBERS.
3. Extract any exact numbers, sample sizes, or metrics you can find in the abstract.
"""
        tldr_hint = f"Bắt buộc mở đầu bằng: '{paywall_warning} AI chỉ tóm tắt dựa trên Abstract...'. Sau đó mới tóm tắt 2-3 câu."

    prompt = f"""You are an elite scientific researcher and AI assistant. Your task is to provide an EXTREMELY DETAILED and COMPREHENSIVE structured summary of the following research paper.

{context_block}

Return ONLY a valid JSON object with EXACTLY these keys:
{{
  "tldr": "{tldr_hint}",
  "objective": "Trình bày chi tiết: Họ muốn giải quyết vấn đề gì? (Ghi 'Không rõ' nếu thiếu dữ kiện).",
  "methodology": "Phân tích kỹ lưỡng: Thuật toán, kiến trúc là gì? (Tuyệt đối không bịa thuật toán nếu không chắc chắn).",
  "dataset": "Mô tả chi tiết: Kích thước mẫu, nguồn dữ liệu. (Ghi 'Không đề cập' hoặc 'Bị khóa bản quyền, không có số liệu' nếu không có).",
  "key_findings": "Liệt kê rõ ràng: Kết quả, chỉ số hiệu suất. (Chỉ ghi số liệu có thật trong văn bản, nếu không có ghi 'Bị khóa bản quyền, không có số liệu').",
  "limitations": "Phân tích sắc bén: Điểm yếu, giới hạn của phương pháp dựa trên suy luận học thuật.",
  "is_paywalled": {"true" if is_paywalled else "false"},
  "reliability_metrics": {{
    "citations": {payload.citations},
    "venue": "{payload.venue}",
    "year": {payload.year}
  }}
}}
"""
    from src.services.llm import ainvoke_with_failover

    try:
        msg, _outcome = await ainvoke_with_failover(
            "paper_summary",
            lambda client: client,
            [("human", prompt)],
            temperature=0.3,
        )
        raw_text = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(raw_text, list):
            raw_text = "".join(part.get("text", "") for part in raw_text if isinstance(part, dict))
        raw_text = str(raw_text).strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        return json.loads(raw_text.strip())
    except Exception as e:
        logger.warning(f"Paper summary LLM call failed: {e}")
        return {
            "error": str(e),
            "tldr": "Hệ thống AI đang gặp tải cao hoặc gián đoạn mạng tạm thời. Vui lòng bấm thử lại sau giây lát.",
            "objective": "Không thể kết nối tới AI",
            "methodology": "Không thể kết nối tới AI",
            "dataset": "Không thể kết nối tới AI",
            "key_findings": "Không thể kết nối tới AI",
            "limitations": "Không thể kết nối tới AI",
            "reliability_metrics": {}
        }

