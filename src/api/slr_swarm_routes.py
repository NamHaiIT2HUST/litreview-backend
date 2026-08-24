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

# ----------------- STUDIO PANEL ENDPOINTS (DISABLED) -----------------
# Các endpoint sau đây phục vụ panel "AI Studio (Agent 2-5)" đã bị xóa khỏi UI.
# Giữ lại schemas và code để dễ rollback. Route trả 410 Gone.

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

@router.post("/step1-setup", include_in_schema=False)
async def step1_setup(payload: SetupRequest):
    """[DISABLED] Gap Map — AI Studio panel removed from UI."""
    raise HTTPException(status_code=410, detail="AI Studio panel đã bị xóa khỏi giao diện.")

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
class DataAnalysisRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    goal: str = ""

@router.post("/analyze", include_in_schema=False)
async def run_analysis(payload: DataAnalysisRequest):
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

from typing import Optional, Any

# ----------------- PAPER SUMMARY (TL;DR ONE-PAGER) -----------------
class PaperSummaryRequest(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = ""
    authors: Any = ""
    year: Any = 2024
    venue: Optional[str] = ""
    citations: Any = 0
    doi: Optional[str] = ""

@router.post("/paper-summary")
async def get_paper_summary(payload: PaperSummaryRequest) -> dict:
    """Sinh bản tóm tắt TL;DR và cấu trúc bài báo cực kỳ chi tiết."""
    # Dùng key từ biến môi trường để bảo mật khi push code lên GitHub
    API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    
    abstract_text = payload.abstract if payload.abstract and len(payload.abstract) > 20 else "NO ABSTRACT AVAILABLE."
    
    # --- AUTO-FETCH FULL TEXT IF DOI IS AVAILABLE ---
    full_text = ""
    is_paywalled = False
    
    if payload.doi:
        try:
            import aiohttp
            import pypdf
            import io
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
        predict_prefix = ""
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
    try:
        import json
        from src.services.synthesis_llm_service import synthesis_llm_service
        llm = synthesis_llm_service._get_llm()
        msg = await llm.ainvoke([("human", prompt)])
        raw_text = msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(raw_text, list):
            raw_text = "".join(part.get("text", "") for part in raw_text if isinstance(part, dict))
        # Làm sạch JSON (loại bỏ markdown block nếu có)
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        return data
    except Exception as e:
        return {
            "error": str(e),
            "tldr": f"Không thể kết nối đến máy chủ AI (Lỗi: {str(e)[:50]}). Vui lòng thử lại.",
            "objective": "Lỗi kết nối",
            "methodology": "Lỗi kết nối",
            "dataset": "Lỗi kết nối",
            "key_findings": "Lỗi kết nối",
            "limitations": "Lỗi kết nối",
            "reliability_metrics": {}
        }

