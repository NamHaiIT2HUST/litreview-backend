"""Lắp ráp `SwarmDeps` mặc định cho runtime.

Skeleton: dùng adapter in-memory để pipeline chạy được ngay từ lần clone đầu.
Bước tích hợp thật thay từng port một (search → citations → corpus → LLM local),
không phải viết lại graph.
"""

from __future__ import annotations

import json
import os
import re
from src.agents.slr_swarm.contracts import PaperRecord
from src.agents.slr_swarm.ports import ModelRouter, SwarmDeps
from src.agents.slr_swarm.stubs import (
    DefaultScriptedLLM,
    InMemoryCitations,
    InMemoryCorpus,
    InMemorySearch,
)

_DEMO_PAPERS = [
    PaperRecord(
        paper_id="P1",
        title="Deep learning for ECG arrhythmia detection",
        abstract="We evaluated 500 patients with ECG recordings using a convolutional neural network.",
        year=2023,
        venue="IEEE TBME",
        doi="10.1000/demo1",
        pdf_available=True,
    ),
    PaperRecord(
        paper_id="P2",
        title="Transformer models on cardiac signals",
        abstract="A transformer architecture applied to cardiac signals of adult patients.",
        year=2024,
        venue="Nature Digital Medicine",
        doi="10.1000/demo2",
        pdf_available=True,
    ),
]

_DEMO_FULLTEXT = {
    "P1": [
        "Deep learning for ECG arrhythmia detection\n"
        "In this retrospective cohort study we evaluated 500 patients with ECG recordings.\n"
        "The convolutional neural network reached an accuracy of 0.94 on the held out set.\n"
        "A limitation is that this is single center data.",
    ],
    "P2": [
        "Transformer models on cardiac signals\n"
        "We evaluated 500 patients with ECG recordings in a retrospective cohort study.\n"
        "Our convolutional neural network baseline reached an accuracy of 0.94.\n"
        "The main limitation is single center data collection.",
    ],
}


from src.agents.slr_swarm.ports import LLMPort
from src.config import get_settings

class RealLLMAdapter(LLMPort):
    async def complete(self, prompt: str, *, schema: dict | None = None) -> str:
        if schema:
            prompt += f"\n\nOutput MUST be valid JSON matching this schema:\n{json.dumps(schema)}"

        from src.config import get_settings
        s = get_settings()
        keys = s.all_gemini_api_keys
        gemini_key = (os.getenv("GEMINI_KEY_PICO") or (keys[2] if len(keys) > 2 else (keys[0] if len(keys) > 0 else "")) or s.gemini_api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
        groq_key = (os.getenv("GROQ_API_KEY") or s.groq_api_key or "").strip()
        openai_key = (os.getenv("OPENAI_API_KEY") or s.effective_openai_api_key or s.openai_api_key or "").strip()

        llm_candidates = []
        if gemini_key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            for m in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]:
                try:
                    llm_candidates.append(ChatGoogleGenerativeAI(model=m, google_api_key=gemini_key, temperature=0.3, max_retries=1))
                except Exception:
                    pass

        if groq_key:
            try:
                from langchain_groq import ChatGroq
                llm_candidates.append(ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_key, temperature=0.3, max_retries=1))
            except Exception:
                pass

        if openai_key:
            try:
                from langchain_openai import ChatOpenAI
                llm_candidates.append(ChatOpenAI(
                    model=s.effective_model_name or "deepseek/deepseek-v3.2",
                    openai_api_key=openai_key,
                    base_url=s.get_api_base or None,
                    temperature=0.3,
                    max_retries=1,
                    timeout=10,
                ))
            except Exception:
                pass

        try:
            from src.services.synthesis_llm_service import synthesis_llm_service
            fallback_llm = synthesis_llm_service._get_llm()
            if fallback_llm:
                llm_candidates.append(fallback_llm)
        except Exception:
            pass

        import asyncio
        for llm in llm_candidates:
            try:
                msg = await asyncio.wait_for(llm.ainvoke([("human", prompt)]), timeout=10.0)
                content = msg.content if hasattr(msg, "content") else str(msg)
                if isinstance(content, list):
                    return "".join(part.get("text", "") for part in content if isinstance(part, dict))
                return str(content)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"RealLLMAdapter candidate error: {e}")

        return "{}"

from src.services.search_service import get_serpapi_count
from src.agents.slr_swarm.ports import SearchPort
from src.config import get_settings

class RealSearchAdapter(SearchPort):
    async def search(self, query: str, *, limit: int = 20) -> list[PaperRecord]:
        s = get_settings()
        api_key = s.serpapi_api_key or os.getenv("SERPAPI_API_KEY") or ""
        if not api_key:
            # Fallback sang InMemorySearch nếu không có key SerpAPI
            terms = [t.lower() for t in re.findall(r'"([^"]+)"', query)] or [query.lower()]
            return [p for p in _DEMO_PAPERS if any(term in f"{p.title} {p.abstract}".lower() for term in terms)]
        
        # Gọi đếm thật từ Google Scholar qua SerpAPI
        total = await get_serpapi_count(query, api_key)
        # Trả về danh sách PaperRecord tượng trưng với độ dài = total (để _probe_cell lấy len())
        return [PaperRecord(paper_id=f"count_{i}", title="") for i in range(min(total, limit))]

def build_default_deps(**overrides) -> SwarmDeps:
    papers = {p.paper_id: p for p in _DEMO_PAPERS}
    
    use_real = overrides.pop("use_real_llm", None)
    if use_real is None:
        use_real = overrides.pop("real", None)
    if use_real is None:
        s = get_settings()
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST")) or s.app_env == "test"
        use_real = not is_test and bool(s.openai_api_key or s.effective_gemini_api_key or s.gemini_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))
    
    local_llm = RealLLMAdapter() if use_real else DefaultScriptedLLM()
    search_port = RealSearchAdapter() if use_real else InMemorySearch(_DEMO_PAPERS, match_all=True)
    
    deps = SwarmDeps(
        router=ModelRouter(local=local_llm),
        search=search_port,
        citations=InMemoryCitations(papers, edges={"P1": ([], ["P2"])}),
        corpus=InMemoryCorpus(_DEMO_FULLTEXT),
        min_papers=2,
        baseline_minutes=14 * 8 * 60,
    )
    for key, value in overrides.items():
        setattr(deps, key, value)
    return deps
