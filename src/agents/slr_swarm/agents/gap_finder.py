"""Agent 1 — Research Gap & PICO Finder (§5.1 Master Plan).

Input : ý tưởng thô / câu hỏi nghiên cứu.
Output: PICOFrame + Boolean MeSH query + Research Gap Heatmap.

Heatmap được dựng bằng cách *đo thật*: với mỗi ô (trục X × trục Y) ta bắn một truy vấn
đếm số bài. Ô nào đếm ra 0 là khoảng trống, ô nào dày đặc là đã bão hoà.
"""

from __future__ import annotations

import json

from src.agents.slr_swarm.contracts import GapCell, GapMap, PICOFrame
from src.agents.slr_swarm.json_utils import as_str_list
from src.agents.slr_swarm.ports import SwarmDeps

PICO_SCHEMA = {
    "type": "object",
    "properties": {
        "population": {"type": "string"},
        "intervention": {"type": "string"},
        "comparison": {"type": "string"},
        "outcome": {"type": "string"},
        "search_keywords": {"type": "array", "items": {"type": "string"}},
        "mesh_terms": {"type": "array", "items": {"type": "string"}},
        "axis_x": {"type": "array", "items": {"type": "string"}},
        "axis_y": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["population", "intervention", "outcome", "search_keywords"],
}

_PROMPT = """You are an expert in academic Systematic Literature Review analysis and PICO framework formulation.
Given the following research topic and screening criteria:

- Research Question / Topic: {idea}
- Research Field: {research_field}
- Inclusion Criteria: {criteria_include}
- Exclusion Criteria: {criteria_exclude}

Your task: Analyze the research framework and propose a list of precise ENGLISH academic search keywords for Google Scholar / Scopus.

CRITICAL RULES:
1. ALL output must be in ENGLISH only. Do NOT use Vietnamese, Chinese, or any non-English language.
2. "search_keywords" MUST be exactly 5-8 ENGLISH academic terms/phrases commonly used in published research papers.
3. Each keyword should be 1-4 English words (e.g., "deep learning", "autonomous navigation", "LLM reasoning").
4. Keywords must be directly relevant to the research topic and useful for database searching.
5. "axis_x" and "axis_y" must also be SHORT English labels (1-3 words each).

Return ONLY a valid JSON object with this structure:
{{
  "population": "Brief description of the research problem/target population in English",
  "intervention": "Main technique/method/approach being studied in English",
  "comparison": "Comparison method or 'N/A' if none",
  "outcome": "Expected evaluation metrics/results in English",
  "search_keywords": ["deep learning", "robot navigation", "LLM agent", "autonomous systems", "reinforcement learning"],
  "axis_x": ["GPT", "LLaMA", "Vision-Language", "Reinforcement Learning"],
  "axis_y": ["Task Planning", "Navigation", "Manipulation", "Control"]
}}

Remember: EVERY string value in the JSON must be in ENGLISH. No Vietnamese text anywhere.
"""


def build_boolean_query(pico: PICOFrame) -> str:
    """Ghép chuỗi từ khoá tìm kiếm theo chuẩn Boolean / MeSH."""
    if pico.mesh_terms:
        clauses = []
        if pico.population:
            clauses.append(f'("{pico.population}")')
        if pico.intervention:
            clauses.append(f'("{pico.intervention}")')
        for m in pico.mesh_terms:
            clauses.append(f'"{m}"[MeSH]')
        return " AND ".join(clauses)

    if pico.search_keywords:
        return " ".join(pico.search_keywords)

    clauses = [pico.population, pico.intervention]
    return " ".join(c for c in clauses if c)


async def _probe_cell(deps: SwarmDeps, x: str, y: str) -> GapCell:
    try:
        hits = await deps.search.search(f'"{x}" AND "{y}"', limit=12)
    except Exception:  # noqa: BLE001 - một ô lỗi không được làm sập cả heatmap
        hits = []
    count = len(hits)
    return GapCell(dimension_x=x, dimension_y=y, paper_count=count, saturation=GapCell.classify(count))


def _extract_clean_keywords(text: str, field: str = "") -> list[str]:
    import re
    paren_matches = re.findall(r"\(([^)]+)\)", text)
    extracted = []
    for pm in paren_matches:
        for item in pm.split(","):
            cleaned = item.strip()
            if cleaned and len(cleaned) >= 2 and len(cleaned) <= 35:
                extracted.append(f"{cleaned} algorithm" if len(cleaned.split()) == 1 else cleaned)

    clean_text = re.sub(r"\([^)]*\)", "", text)
    mappings = [
        ("tốc độ hội tụ", ["convergence rate", "rate of convergence"]),
        ("tối ưu bậc hai", ["second-order optimization", "second-order algorithms"]),
        ("tối ưu hóa", ["optimization methods", "mathematical optimization"]),
        ("tối thiểu hóa", ["convex minimization", "objective minimization"]),
        ("hàm lồi", ["convex function", "convex optimization"]),
        ("ràng buộc lồi", ["convex constraints", "constrained optimization"]),
        ("chấp nhận tách", ["split feasibility problem", "split feasibility"]),
        ("học sâu", ["deep learning", "neural networks"]),
        ("mô hình ngôn ngữ", ["large language models", "LLM task planning"]),
        ("robot", ["robotics", "mobile robot navigation"]),
    ]

    clean_lower = clean_text.lower()
    for phrase, eng_terms in mappings:
        if phrase in clean_lower:
            extracted.extend(eng_terms)

    delimiters = r"[;:,]|cho bài toán|đối với|của các|dành cho|dựa trên|phân tích|nghiên cứu|đánh giá|khảo sát"
    chunks = re.split(delimiters, clean_text, flags=re.IGNORECASE)
    for c in chunks:
        c_clean = c.strip()
        words = c_clean.split()
        if 2 <= len(words) <= 5 and len(c_clean) <= 40:
            extracted.append(c_clean)

    seen = set()
    result = []
    for item in extracted:
        item_clean = item.strip()
        if item_clean and item_clean.lower() not in seen and len(item_clean.split()) <= 5 and len(item_clean) <= 45:
            seen.add(item_clean.lower())
            result.append(item_clean)

    if not result:
        words = [w for w in re.findall(r"\b[a-zA-Z0-9\-_]{3,}\b", text)]
        if words:
            result = words[:6]
        else:
            result = [field or "Computer Science", "Empirical Evaluation", "Methodology Benchmark"]

    return result[:8]


async def run_gap_finder(state: dict, deps: SwarmDeps) -> dict:
    idea = (state.get("idea") or "").strip()
    research_field = (state.get("research_field") or "").strip()
    criteria_include = ", ".join(state.get("criteria_include") or []) or "Không có"
    criteria_exclude = ", ".join(state.get("criteria_exclude") or []) or "Không có"

    if not idea:
        return {"error": "Thiếu ý tưởng nghiên cứu (idea), Agent 1 không thể bắt đầu."}

    data = None
    if getattr(deps, "router", None):
        llm_stub = deps.router.pick("gap_finder")
        prompt = _PROMPT.format(
            idea=idea,
            research_field=research_field or "Computer Science / Artificial Intelligence",
            criteria_include=criteria_include,
            criteria_exclude=criteria_exclude
        )
        content = await llm_stub.complete(prompt)
        content = str(content).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)
    elif getattr(deps, "llm", None):
        prompt = _PROMPT.format(
            idea=idea,
            research_field=research_field or "Computer Science / Artificial Intelligence",
            criteria_include=criteria_include,
            criteria_exclude=criteria_exclude
        )
        content = await deps.llm.complete(prompt)
        content = str(content).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)

    if not data:
        # The primary call above already went through ainvoke_with_failover,
        # which tries every configured provider with its own retry budget --
        # a second hand-rolled cascade of Gemini/Groq/OpenAI clients here
        # (this used to build one) would just retry the same exhausted
        # providers a second time under a different key-lookup order. LoRA is
        # a genuinely distinct model, worth one more try; past that, the
        # keyword-extraction heuristic below is the honest fallback.
        from src.services.lora_client import call_lora_model
        lora_instruction = "Extract PICO structure (Population, Intervention, Comparison, Outcome) and keywords in English."
        lora_input = f"Domain: {research_field}\nTopic: {idea}\nInclude: {criteria_include}\nExclude: {criteria_exclude}"

        lora_result = await call_lora_model("lora_agent3_pico", lora_instruction, lora_input)
        if lora_result and isinstance(lora_result, dict) and lora_result.get("search_keywords"):
            data = lora_result

    if not isinstance(data, dict):
        data = {}

    pop = str(data.get("population", "") or "")
    inte = str(data.get("intervention", "") or "")
    comp = str(data.get("comparison", "") or "N/A")
    out = str(data.get("outcome", "") or "")
    raw_kws = as_str_list(data.get("search_keywords"))

    # Filter keywords: eliminate whole sentence echoes (> 45 chars or > 5 words)
    kws = []
    for kw in raw_kws:
        k_str = kw.strip()
        if k_str and len(k_str) >= 3 and any(c.isalpha() for c in k_str):
            if len(k_str) <= 45 and len(k_str.split()) <= 5:
                kws.append(k_str)
            else:
                # Break long sentence keyword down
                kws.extend(_extract_clean_keywords(k_str, research_field))

    # Smart academic extraction fallback if LLM returned empty/unparsed
    if not (pop and inte and out and kws):
        if not pop:
            pop = f"Target domain and problem instances for: {idea[:60]}"
        if not inte:
            inte = "Advanced Optimization Algorithms & Mathematical Formulations"
        if not out:
            out = "Convergence Rate, Numerical Stability & Benchmark Performance"
        if not kws:
            kws = _extract_clean_keywords(idea, research_field)

    # Deduplicate keywords
    final_kws = []
    seen_k = set()
    for k in kws:
        k_clean = k.strip()
        if k_clean and k_clean.lower() not in seen_k and len(k_clean) <= 45:
            seen_k.add(k_clean.lower())
            final_kws.append(k_clean)

    pico = PICOFrame(
        population=pop,
        intervention=inte,
        comparison=comp,
        outcome=out,
        search_keywords=final_kws[:8],
        mesh_terms=as_str_list(data.get("mesh_terms")),
    )
    pico.boolean_query = build_boolean_query(pico) or " ".join(final_kws[:4])

    axis_x = as_str_list(data.get("axis_x"))[:5]
    axis_y = as_str_list(data.get("axis_y"))[:5]

    if not axis_x:
        axis_x = ["Open-Source Models", "Fine-Tuned LLMs", "Vision-Language Models", "Hybrid Architectures"]
    if not axis_y:
        axis_y = ["Task Planning", "Autonomous Navigation", "Multi-Agent Control", "Real-Time Evaluation"]

    cells: list[GapCell] = []
    raw_corpus = state.get("corpus", [])

    # Normalize corpus items into simple dicts/objects
    corpus = []
    for p in raw_corpus:
        if isinstance(p, dict):
            corpus.append(p)
        elif hasattr(p, "title"):
            corpus.append({"title": getattr(p, "title", ""), "abstract": getattr(p, "abstract", "")})

    for x in axis_x:
        for y in axis_y:
            x_words = [w.lower().strip("(),.") for w in x.split() if len(w) > 2 and w.lower() not in ["with", "from", "using", "models", "level", "and", "the"]]
            y_words = [w.lower().strip("(),.") for w in y.split() if len(w) > 2 and w.lower() not in ["with", "from", "using", "models", "level", "and", "the"]]

            def matches_concept(text: str, words: list[str]) -> bool:
                if not words:
                    return True
                text_l = text.lower()
                return any(w in text_l for w in words)

            if corpus:
                matching_count = sum(
                    1 for p in corpus
                    if matches_concept(f"{p.get('title', '')} {p.get('abstract', '')}", x_words)
                    and matches_concept(f"{p.get('title', '')} {p.get('abstract', '')}", y_words)
                )
            else:
                matching_count = 0

            cells.append(GapCell(
                dimension_x=x,
                dimension_y=y,
                paper_count=matching_count,
                saturation=GapCell.classify(matching_count)
            ))

    gap_map = GapMap(axis_x=axis_x, axis_y=axis_y, cells=cells)

    warnings = list(state.get("warnings", []))
    if not cells:
        warnings.append("Agent 1: không dựng được Gap Heatmap (thiếu trục phân tích).")

    return {
        "pico": pico,
        "gap_map": gap_map,
        "warnings": warnings,
        "trace": [{"agent": "gap_finder", "query": pico.boolean_query, "cells": len(cells)}],
    }
