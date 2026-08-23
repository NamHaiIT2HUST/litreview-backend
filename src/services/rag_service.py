"""RAG Service - Map-Reduce architecture inspired by PaperQA2.

Pipeline:
  1. MAP    - Score & summarise each chunk concurrently (JSON output).
  2. FILTER - Drop low-relevance chunks; sort descending.
  3. REDUCE - Synthesise a cited, language-matched answer like NotebookLM.

PaperQA2-inspired improvements (2026-08):
  - MIN_RELEVANCE_SCORE lowered 3→2 (matches PaperQA2's evidence_relevance_score_cutoff=1 spirit).
  - MAX_CONTEXT_CHUNKS reduced 8→5 (quality over quantity, per PaperQA2 answer_max_sources=5).
  - MAP prompt enriched with paper_title so LLM knows which paper each chunk comes from.
  - REDUCE context now includes "Valid Keys:" footer (mirrors PaperQA2 CONTEXT_OUTER_PROMPT).
  - generate_answer_with_citations() returns traceable citation metadata per key.
  - Robust JSON parser (handles fractions, bad escapes, missing commas).
  - Short human-readable citation keys (e.g. "paper_p3") instead of UUIDs.
  - Strict language-mirroring: answer language matches question language.
  - Citation format matches PaperQA2 style: (key1, key2) parenthetical.
"""

import asyncio
import json
import logging
import os
import re
from typing import List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.config import get_settings
from src.services.map_reduce_optimizer import map_reduce_optimizer
from src.services.rag_guardrail_service import rag_guardrail_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds — aligned with PaperQA2 philosophy
# ---------------------------------------------------------------------------
# PaperQA2 uses evidence_relevance_score_cutoff=1 (very permissive — let MAP decide).
# We use 2 as a slight safety margin. The new MAP prompt naturally gives 0 to
# irrelevant chunks, so heavy filtering at this level is unnecessary.
MIN_RELEVANCE_SCORE = 2
# PaperQA2 uses answer_max_sources=5. We increase to 10 so multiple papers can fit in the context.
MAX_CONTEXT_CHUNKS = 10
# Grounding-sensitive steps (MAP scoring, REDUCE synthesis, structured citation
# extraction) need run-to-run consistency, not creative variation — keep this
# near 0 rather than inheriting the chat-oriented llm_temperature default.
GROUNDED_TEMPERATURE = 0.1



# ---------------------------------------------------------------------------
# Pydantic schema for MAP step output
# ---------------------------------------------------------------------------
class ChunkSummary(BaseModel):
    summary: str = Field(default="", description="Relevant information from the chunk.")
    relevance_score: int = Field(default=0, ge=0, le=10)


# ---------------------------------------------------------------------------
# Robust JSON parser (ported from paperqa2 core.py llm_parse_json)
# ---------------------------------------------------------------------------
def _parse_chunk_json(raw: str) -> dict:
    """Parse LLM JSON output robustly - handles common LLM formatting mistakes."""
    # Strip <think> tags (reasoning models)
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip markdown fences
    text = text.split("```json")[-1].split("```")[0]

    # Fix fraction scores: "relevance_score": 8/10 -> 8
    text = re.sub(
        r'"relevance_score"\s*:\s*(\d+)/(\d+)',
        lambda m: f'"relevance_score": {round(int(m.group(1)) / int(m.group(2)) * 10)}',
        text,
    )

    # Ensure wrapped in braces
    if "{" not in text and "}" not in text:
        text = json.dumps({"summary": text})

    text = ("{" + text.split("{", 1)[-1]).rsplit("}", 1)[0] + "}"

    # Escape raw newlines inside quoted strings
    def escape_newlines(m: re.Match) -> str:
        return m.group(0).replace("\n", "\\n")

    text = re.sub(r'"(?:[^"\\]|\\.)*"', escape_newlines, text)

    # Fix bad backslashes
    text = re.sub(r'\\([^"\\/bfnrtu])', r"\\\\\\1", text)

    # Add missing commas between fields
    text = re.sub(r'(?<=[}\]0-9"])\s*(?="[^"\\]*"\s*:)', ", ", text)

    # Remove duplicate/trailing commas
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r"\{\s*,", "{", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: regex extract
        sm = re.search(r'"summary"\s*:\s*"(.*?)",\s*"relevance_score"', text, re.DOTALL)
        sc = re.search(r'"relevance_score"\s*:\s*"?(\d+)"?', text)
        if sm and sc:
            return {"summary": sm.group(1), "relevance_score": int(sc.group(1))}
        return {"summary": "", "relevance_score": 0}

    # Normalise key name variants (e.g. "score", "Relevance")
    for key in list(data):
        if re.search(r"relevance|score", key, re.IGNORECASE) and key != "relevance_score":
            data["relevance_score"] = data.pop(key)

    # Normalise relevance_score to int
    if "relevance_score" in data and not isinstance(data["relevance_score"], int):
        try:
            data["relevance_score"] = round(float(data["relevance_score"]))
        except (ValueError, TypeError):
            data["relevance_score"] = 0

    return data


# ---------------------------------------------------------------------------
# Prompt templates — modelled after PaperQA2 prompts.py
# ---------------------------------------------------------------------------

# MAP: Evidence extraction per chunk  (PaperQA2: summary_json_system_prompt + summary_json_prompt)
# Key PaperQA2 principles:
#  1. "Your summary will be given to a model to generate an answer" → MAP knows its role
#  2. "Do not directly answer the question" → prevent premature answering
#  3. summary_length is controlled (~100 words, like PaperQA2's evidence_summary_length)
#  4. Simple 0-10 scoring without complex rubrics (PaperQA2 doesn't use rubrics)
_MAP_SYSTEM = (
    "Provide a summary of the relevant information that could help answer the question,"
    " based on the excerpt below."
    " Your summary, combined with many others, will be given to a model to generate an answer.\n\n"
    "Respond ONLY with valid JSON (no markdown fences) in exactly this format:\n"
    '{{"summary": "...", "relevance_score": 0}}\n\n'
    "Rules:\n"
    "- `summary`: Relevant information from the excerpt that could help answer the question."
    " Write a DETAILED summary (about 150-250 words). Do NOT directly answer the question — only extract evidence."
    " If the question is broad or theoretical (e.g., 'discuss', 'overview', 'là gì'), extract high-level concepts, but DO NOT skip core mathematical definitions, theorems, or proofs. These are CRITICAL evidence, not minor details."
    " Always extract specific numbers, exact equations, and mathematical logic if present and relevant. Preserve the intuitive or geometric meaning if mentioned in the text."
    ' If the excerpt is not relevant, leave `summary` empty.\n'
    "- `relevance_score`: Integer 0-10 for relevance of `summary` to the question."
    " 0 = not relevant at all. 10 = directly and specifically answers the question.\n"
    "- The excerpt may or may not contain relevant information."
    " If not relevant, leave `summary` empty and set `relevance_score` to 0.\n"
    "- LANGUAGE RULE: Detect the primary language of the Question."
    " If the question contains ANY Vietnamese terms (e.g., 'Discuss Tập loại bỏ tự do'), ALWAYS write the `summary` in Vietnamese.\n"
    "- MATH RULE: Use LaTeX for all math notation. Never skip or over-summarize mathematical formulas, definitions, and lemmas."
    " Inline: $\\theta$, $\\beta_k$, $\\|u_k\\|$. Display: $$...$$."
    " Never use Unicode math (\u03b8 \u03b2 \u2207 etc.)."
)
_MAP_HUMAN = (
    "Excerpt from {paper_title} — {source_name} (page {page}):\n\n---\n\n{excerpt}\n\n---\n\n"
    "Question: {question}\n\n"
    "CRITICAL: If the Question contains ANY Vietnamese words (e.g. 'Tập loại bỏ tự do'), you MUST write the `summary` entirely in Vietnamese.\n\n"
    "JSON:"
)

MAP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _MAP_SYSTEM),
    ("human", _MAP_HUMAN),
])

# REDUCE: Answer generation  (PaperQA2: qa_prompt + default_system_prompt & ScholarQA)
_CITATION_KEY_RULES = (
    "Citation rules (follow exactly):\n"
    "- Place citation keys in brackets at the end of each sentence: [1] or [1][2]\n"
    "- Use ONLY the citation keys listed in 'Valid Keys'\n"
    "- Do NOT use author names, years, or page numbers as citations\n"
    "- Valid: [1] | [1][2]. Invalid: [1 and 2] | (1) | Author et al. (2023)"
)

# Adaptive Grounded System Prompt: ScholarQA, PaperQA2 & ASTA-Bench Intent-Driven Formulation
_REDUCE_SYSTEM = (
    "You are an elite academic AI research assistant inspired by ScholarQA, PaperQA2, and NotebookLM.\n"
    "Your mission is to synthesize the provided document excerpts into a scientifically accurate, completely grounded, and intelligently formatted answer tailored specifically to the user's question.\n\n"
    "STRICT GROUNDING RULE — MANDATORY (ZERO-HALLUCINATION POLICY):\n"
    "- You MUST NOT use any external knowledge. All facts, equations, definitions, author names, theorems, and data MUST be strictly derived from and supported by the provided context excerpts.\n"
    "- Do NOT speculate or extrapolate facts not present in the excerpts.\n"
    "- Answer using whatever relevant information the excerpts DO contain, even if it only covers part of the question.\n"
    "- Only decline entirely if NONE of the excerpts contain relevant information to answer any part of the question.\n\n"
    "CITATION RULE — MANDATORY:\n"
    "- Every factual statement or claim MUST include the appropriate citation key(s) at the end, e.g., 'Thuật toán CQ hội tụ với bước lặp thích nghi [1].'\n"
    "- Use ONLY the citation keys listed in 'Valid Keys' (e.g. [1], [2], or [1][2]).\n"
    "- Do NOT use author names, years, or page numbers as citations (use only brackets like [1]).\n\n"
    "ADAPTIVE FORMATTING GUIDELINES (CHOOSE THE BEST STRUCTURE FOR THE QUESTION INTENT):\n"
    "Analyze the Question intent and dynamically choose the most effective, clear, and elegant Markdown structure:\n"
    "1. **Direct Fact / Specific Question** (e.g., 'Tác giả bài báo là ai?', 'Hàm mục tiêu là gì?'):\n"
    "   - Answer directly and concisely in 1-2 focused paragraphs with citations [1].\n"
    "   - Do NOT force arbitrary section headings if the answer is straightforward.\n\n"
    "2. **Algorithm / Step-by-Step / Mathematical Derivation Question** (e.g., 'Các bước của thuật toán CQ', 'Cách cập nhật bước lặp'):\n"
    "   - Present an introductory sentence [1].\n"
    "   - List sequential algorithmic steps clearly (e.g., **Bước 1 (Khởi tạo)**, **Bước 2 (Lặp chiếu)**) with exact LaTeX formulas [1][2].\n"
    "   - State convergence conditions or termination criteria if mentioned in the text [1].\n\n"
    "3. **Comparison / Trade-off Question** (e.g., 'So sánh phương pháp A và B', 'Ưu nhược điểm'):\n"
    "   - Summarize the main distinction briefly [1].\n"
    "   - Use a clean Markdown comparison table (`| Tiêu chí | Phương pháp A | Phương pháp B |`) or bullet points contrasting the methods [1][2].\n\n"
    "4. **Comprehensive Overview / In-Depth Research Question** (e.g., 'Tổng quan bài toán SFP', 'Phân tích mô hình'):\n"
    "   - Organize logically with clear Markdown headings (e.g., `### 💡 Tổng quan`, `### 📌 Mô hình toán học & Định nghĩa`, `### ⚙️ Phương pháp & Thuật toán giải`, `### ⚖️ Đặc tính & Nhận xét`) with full LaTeX notation and citations [1][2].\n\n"
    "MATH & EQUATIONS RULE — MANDATORY:\n"
    "- Always use standard LaTeX for all mathematical expressions and variables.\n"
    "- Inline math MUST be enclosed in single dollar signs: `$x$`, `$C$`, `$\\min_{{x}}$`, `$\\delta_C(x)$`.\n"
    "- Display / Block equations MUST be enclosed in double dollar signs: $$...$$\n"
    "- NEVER output raw unescaped LaTeX, backslash-parentheses `\\( ... \\)`, or raw unformatted math text.\n\n"
    "LANGUAGE RULE — MANDATORY:\n"
    "- Detect the language of the Question.\n"
    "- If the question contains ANY Vietnamese words or terms, answer ENTIRELY in natural, professional academic Vietnamese.\n"
    "- Only answer in English if the question is 100% English."
)


_REDUCE_HUMAN = (
    "Context:\n\n{context}\n\nValid Keys: {valid_keys}\n\n---\n\n"
    "Question: {question}\n\n"
    "Write an accurate, well-structured academic answer adhering strictly to the guidelines above.\n"
    "Follow these strict constraints:\n"
    "1. Base your answer ONLY on the context provided above. Do not hallucinate facts not in the context.\n"
    "2. Dynamically format your response according to the question intent (direct answer, step-by-step algorithm, comparison table, or structured overview).\n"
    "3. For each factual statement, place the supporting citation key(s) at the end, like [1] or [1][2]. Use ONLY keys from 'Valid Keys'.\n"
    "4. Present ALL mathematical variables and formulas in LaTeX ($...$ for inline, $$...$$ for display equations).\n"
    "5. If NONE of the excerpts are relevant at all, reply: \"Tôi không thể trả lời câu hỏi này dựa trên tài liệu được cung cấp. / I cannot answer this based on the provided documents.\" and STOP.\n\n"
    + _CITATION_KEY_RULES + "\n\n"
    "CRITICAL LANGUAGE RULE: If the Question contains ANY Vietnamese words, your ENTIRE Answer below MUST be in Vietnamese. Do NOT use English unless the question is 100% English.\n\n"
    "Answer:"
)


REDUCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _REDUCE_SYSTEM),
    ("human", _REDUCE_HUMAN),
])


# ---------------------------------------------------------------------------
# RAGService
# ---------------------------------------------------------------------------
class RAGService:
    def __init__(self):
        self._settings = get_settings()
        self._llm = None

    @property
    def llm(self):
        settings = get_settings()
        openai_key = settings.effective_openai_api_key
        gemini_key = settings.effective_gemini_api_key
        groq_key = settings.groq_api_key or os.getenv("GROQ_API_KEY") or ""
        provider = (
            getattr(settings, "llm_provider", "")
            or os.getenv("LLM_PROVIDER")
            or getattr(settings, "synthesis_llm_provider", "")
            or os.getenv("SYNTHESIS_LLM_PROVIDER")
            or ""
        ).lower().strip()

        model_name = settings.effective_model_name

        # Auto-detect provider if unspecified
        if not provider or provider == "auto":
            if model_name.startswith("gemini-") or model_name.startswith("models/gemini"):
                provider = "gemini"
            elif model_name.startswith("groq/") or ("llama-" in model_name and groq_key and not openai_key):
                provider = "groq"
            elif openai_key:
                provider = "openai"
            elif gemini_key:
                provider = "gemini"
            elif groq_key:
                provider = "groq"
            else:
                provider = "openai"

        # 1. Gemini
        if provider == "gemini":
            if not gemini_key:
                if openai_key:
                    # Graceful fallback to OpenAI-compatible
                    provider = "openai"
                else:
                    raise RuntimeError("Gemini API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env.")
            else:
                from langchain_google_genai import ChatGoogleGenerativeAI
                g_model = model_name if model_name.startswith("gemini-") else "gemini-2.0-flash"
                return ChatGoogleGenerativeAI(
                    model=g_model,
                    google_api_key=gemini_key,
                    temperature=settings.llm_temperature,
                )

        # 2. Groq
        if provider == "groq":
            if not groq_key:
                if openai_key:
                    provider = "openai"
                else:
                    raise RuntimeError("Groq synthesis requires GROQ_API_KEY in .env.")
            else:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model=model_name if model_name else "llama-3.3-70b-versatile",
                    api_key=groq_key,
                    temperature=settings.llm_temperature,
                )

        # 3. OpenAI-compatible (DeepSeek, OpenRouter, xkiro, SiliconFlow, OpenAI, vLLM, custom proxy)
        if not openai_key:
            if gemini_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=gemini_key,
                    temperature=settings.llm_temperature,
                )
            raise RuntimeError(
                "API key required. Set OPENAI_API_KEY, LLM_API_KEY, DEEPSEEK_API_KEY, "
                "or GEMINI_API_KEY in .env."
            )

        from langchain_openai import ChatOpenAI
        base_url = settings.get_api_base or None
        extra_headers = {}
        if base_url and "openrouter" in base_url:
            extra_headers = {"HTTP-Referer": "https://localhost", "X-Title": "LitReview Agent"}
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            api_key=openai_key,
            base_url=base_url,
            temperature=settings.llm_temperature,
            timeout=60.0,
            max_retries=2,
            default_headers=extra_headers if extra_headers else None,
        )


    @property
    def grounded_llm(self):
        """Low-temperature view of `llm` for grounding-sensitive steps (MAP
        evidence scoring, REDUCE answer synthesis, structured citation
        extraction) where run-to-run consistency matters more than creative
        variation. Mirrors the synthesis pipeline's synthesis_temperature=0.0
        convention (see config.py), which `llm_temperature`'s 0.7 default
        never adopted for this file's grounding-heavy chains.
        """
        return self.llm.bind(temperature=GROUNDED_TEMPERATURE)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def make_chunk_id(doc: Document, index: int) -> str:
        """Full chunk ID for internal tracking (not shown to user)."""
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        return f"{os.path.basename(str(source))}::p{page}::{index}"

    @staticmethod
    def make_citation_key(doc: Document, index: int) -> str:
        """Short human-readable key shown in citations, e.g. 'paper_p3'.
        Matches PaperQA2's short-key approach for readability.
        """
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        # Extract short filename stem, strip UUIDs prefix if present
        stem = os.path.splitext(os.path.basename(str(source)))[0]
        # If filename starts with UUID pattern, take the part after the first underscore group
        uuid_prefix = re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)$",
            stem,
            re.IGNORECASE,
        )
        if uuid_prefix:
            stem = uuid_prefix.group(1)
        # Truncate to max 30 chars and make URL-safe
        stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)[:30].strip("_")
        return f"{stem}_p{page}"

    @staticmethod
    def _get_paper_title(doc: Document) -> str:
        """Extract human-readable paper title from chunk metadata.
        Falls back to filename stem if title not in metadata.
        """
        # Prefer explicit 'paper_title' metadata injected by the route
        title = doc.metadata.get("paper_title", "")
        if title:
            return str(title)
        # Fallback: derive from source filename (strip UUID prefix)
        source = doc.metadata.get("source", "unknown")
        stem = os.path.splitext(os.path.basename(str(source)))[0]
        uuid_prefix = re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_(.+)$",
            stem,
            re.IGNORECASE,
        )
        if uuid_prefix:
            stem = uuid_prefix.group(1)
        return stem[:60]

    def _format_docs(self, docs: List[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    # -----------------------------------------------------------------------
    # MAP step
    # -----------------------------------------------------------------------
    async def _map_chunk(
        self, citation_key: str, source_name: str, paper_title: str, page: str, excerpt: str, question: str
    ) -> tuple[str, ChunkSummary]:
        """Score and summarise one chunk. Returns (citation_key, ChunkSummary).
        PaperQA2-inspired: passes paper_title to MAP prompt so LLM understands source context.
        """
        try:
            chain = MAP_PROMPT | self.grounded_llm | StrOutputParser()
            raw = await asyncio.wait_for(
                chain.ainvoke({
                    "citation_key": citation_key,
                    "source_name": source_name,
                    "paper_title": paper_title,
                    "page": page,
                    "excerpt": excerpt,
                    "question": question,
                }),
                timeout=18.0
            )
            data = _parse_chunk_json(raw)
            result = ChunkSummary(
                summary=data.get("summary", ""),
                relevance_score=data.get("relevance_score", 0),
            )
            logger.info("MAP [%s] score=%d  %s", citation_key, result.relevance_score, ascii(result.summary[:80]))
            return citation_key, result
        except Exception as e:
            logger.warning("MAP error on chunk [%s]: %s", citation_key, e)
            q_words = set(re.findall(r"\w{4,}", question.lower()))
            chunk_words = set(re.findall(r"\w{4,}", excerpt.lower()))
            overlap = len(q_words & chunk_words)
            if overlap >= 2:
                return citation_key, ChunkSummary(summary=excerpt[:400].strip(), relevance_score=max(3, min(8, overlap * 2)))
            return citation_key, ChunkSummary(summary="", relevance_score=0)

    # -----------------------------------------------------------------------
    # Main Map-Reduce pipeline
    # -----------------------------------------------------------------------
    async def generate_answer_map_reduce(self, query: str, chunks: List[Document]) -> str:
        """Full Map-Reduce RAG pipeline.

        PaperQA2-inspired improvements:
        - Lower MIN_RELEVANCE_SCORE (2 vs old 3) → fewer false negatives
        - Lower MAX_CONTEXT_CHUNKS (5 vs old 8) → focused, higher-quality context
        - paper_title in MAP so LLM knows which paper each excerpt comes from
        - Valid Keys footer in REDUCE prompt (mirrors PaperQA2 CONTEXT_OUTER_PROMPT)
        """
        if not chunks:
            return "Tôi không tìm thấy ngữ cảnh nào phù hợp. / No relevant context found."

        # ── MAP (all chunks concurrently) ────────────────────────────────────
        tasks = []
        key_to_meta: dict[str, dict] = {}

        for i, doc in enumerate(chunks):
            ckey = self.make_citation_key(doc, i)
            # Ensure unique keys if filename+page collide
            if ckey in key_to_meta:
                ckey = f"{ckey}_{i}"
            source = doc.metadata.get("source", "unknown")
            page = str(doc.metadata.get("page", "?"))
            paper_title = self._get_paper_title(doc)
            key_to_meta[ckey] = {
                "source": source,
                "page": page,
                "paper_title": paper_title,
                "paper_id": str(doc.metadata.get("paper_id", "")),
            }
            tasks.append(self._map_chunk(
                ckey,
                os.path.basename(str(source)),
                paper_title,
                page,
                doc.page_content,
                query,
            ))

        map_results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── FILTER & SORT ────────────────────────────────────────────────────
        scored: list[tuple[str, ChunkSummary]] = []
        for item in map_results:
            if isinstance(item, Exception):
                logger.warning("Map task exception: %s", item)
                continue
            ckey, summary = item
            if summary.relevance_score >= MIN_RELEVANCE_SCORE and summary.summary.strip():
                scored.append((ckey, summary))

        scored.sort(key=lambda x: x[1].relevance_score, reverse=True)
        scored = scored[:MAX_CONTEXT_CHUNKS]

        if not scored:
            return (
                "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này.\n"
                "No relevant information found in the uploaded documents."
            )

        logger.info("FILTER: %d/%d chunks kept.", len(scored), len(chunks))

        # Remap to numeric citations [1], [2], ...
        numeric_scored = []
        numeric_key_to_meta = {}
        for idx, (old_ckey, cs) in enumerate(scored, start=1):
            new_ckey = str(idx)
            numeric_scored.append((new_ckey, cs))
            numeric_key_to_meta[new_ckey] = key_to_meta[old_ckey]
            
        scored = numeric_scored
        key_to_meta = numeric_key_to_meta

        # PaperQA2 context_inner format: "{name}: {text}\nFrom {citation}"
        # We use: "[key] (Paper: Title, page N):\n{summary}"
        context_lines = []
        for ckey, cs in scored:
            meta = key_to_meta[ckey]
            page_display = int(meta["page"]) + 1 if str(meta["page"]).isdigit() else meta["page"]
            title_display = meta["paper_title"]
            context_lines.append(
                f"[{ckey}] (Paper: {title_display}, page {page_display}):\n{cs.summary}"
            )
        context_str = "\n\n".join(context_lines)

        # PaperQA2 CONTEXT_OUTER_PROMPT pattern: context_str + "Valid Keys: key1, key2..."
        valid_keys = ", ".join(f"[{ckey}]" for ckey, _ in scored)

        try:
            reduce_chain = REDUCE_PROMPT | self.grounded_llm | StrOutputParser()
            answer = await asyncio.wait_for(
                reduce_chain.ainvoke({
                    "context": context_str,
                    "valid_keys": valid_keys,
                    "question": query,
                }),
                timeout=30.0
            )
            return answer
        except Exception as e:
            logger.warning("REDUCE error in map_reduce: %s", e)
            extracted_points = [f"- {cs.summary.strip()} [{ckey}]" for ckey, cs in scored[:4] if cs.summary.strip()]
            return "Dựa trên các tài liệu đã cung cấp:\n" + "\n".join(extracted_points)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    async def generate_answer(self, query: str, chunks: List[Document]) -> str:
        return await self.generate_answer_map_reduce(query, chunks)

    async def generate_answer_with_citations(
        self, query: str, chunks: List[Document]
    ) -> dict:
        """Extended API: returns answer + traceable citation metadata.

        PaperQA2-inspired: each citation key maps to its source DocDetails
        (paper_title, page, paper_id, filename) — allowing the frontend to
        render clickable source cards instead of raw "Nguồn #N" labels.

        Returns:
            {
              "answer": str,
              "citations": [
                  {"key": "paper_p3", "paper_title": "...", "page": 3,
                   "paper_id": "uuid", "filename": "..."}
              ],
              "context_used": [
                  {"key": "paper_p3", "paper_title": "...", "page_display": "4",
                   "snippet": "...first 200 chars of summary..."}
              ]
            }
        """
        if not chunks:
            return {
                "answer": "Tôi không tìm thấy ngữ cảnh nào phù hợp trong các tài liệu đã tải lên. / No relevant context found in uploaded documents.",
                "citations": [],
                "context_used": [],
            }

        # ── Ultra-Fast Direct Evidence-Context Synthesis ─────────────────────
        # Take top relevant chunks (up to MAX_CONTEXT_CHUNKS = 8)
        top_chunks = chunks[:MAX_CONTEXT_CHUNKS]

        scored: list[tuple[str, ChunkSummary]] = []
        key_to_meta: dict[str, dict] = {}
        context_lines = []

        for idx, doc in enumerate(top_chunks, start=1):
            ckey = str(idx)
            source = doc.metadata.get("source", "unknown")
            page_raw = doc.metadata.get("page", 1)
            page_display = int(page_raw) + 1 if str(page_raw).isdigit() else page_raw
            paper_title = self._get_paper_title(doc)
            content_clean = doc.page_content.strip()

            meta = {
                "source": source,
                "page": page_raw,
                "page_display": str(page_display),
                "paper_title": paper_title,
                "paper_id": str(doc.metadata.get("paper_id", "")),
                "filename": os.path.basename(str(source)),
                "page_char_start": doc.metadata.get("page_char_start"),
                "page_char_end": doc.metadata.get("page_char_end"),
                "raw_text": content_clean,
                "snippet": content_clean[:350] + ("..." if len(content_clean) > 350 else ""),
            }
            key_to_meta[ckey] = meta
            scored.append((ckey, ChunkSummary(summary=content_clean[:1800], relevance_score=9)))
            context_lines.append(
                f"[{ckey}] (Paper: {paper_title}, page {page_display}):\n{content_clean}"
            )

        context_str = "\n\n".join(context_lines)
        valid_keys = {f"[{ckey}]" for ckey, _ in scored}
        valid_keys_str = ", ".join(sorted(valid_keys))

        # ── Single Fast High-Precision REDUCE Call ───────────────────────────
        try:
            reduce_chain = REDUCE_PROMPT | self.grounded_llm | StrOutputParser()
            raw_answer = await asyncio.wait_for(
                reduce_chain.ainvoke({
                    "context": context_str,
                    "valid_keys": valid_keys_str,
                    "question": query,
                }),
                timeout=60.0
            )
        except Exception as e:
            logger.warning("REDUCE error: %s, using extractive fallback synthesis", e)
            extracted_points = []
            for ckey, _ in scored[:4]:
                meta = key_to_meta[ckey]
                clean_snippet = re.sub(r'\s+', ' ', meta['snippet']).strip()
                extracted_points.append(f"- **{meta['paper_title']}** (Trang {meta['page_display']}): {clean_snippet} [{ckey}]")
            raw_answer = (
                "### 💡 Tóm tắt cốt lõi (TLDR)\n"
                "Dưới đây là các thông tin chính được trích xuất trực tiếp từ tài liệu nguồn [1].\n\n"
                "### 📌 Phân tích chi tiết & Nội dung trích xuất\n"
                + "\n".join(extracted_points) + "\n\n"
                "### ⚖️ Lưu ý\n"
                "- Vui lòng xem chi tiết tại các tài liệu trích dẫn tương ứng [1]."
            )


        # ── Guardrails: Sanitize Citations & Strip Hallucinated Keys ──────────
        valid_numeric_keys = {ckey for ckey, _ in scored}
        sanitized_answer, hallucinated_keys = rag_guardrail_service.sanitize_citations(
            raw_answer, valid_keys=valid_numeric_keys
        )

        # ── Build Traceable Citation Metadata (PaperQA2 bib-style) ───────────
        cited_keys_in_answer: set[str] = set(re.findall(r'\[([^\]]+)\]', sanitized_answer))
        cited_flat: set[str] = set()
        for group in cited_keys_in_answer:
            for k in group.split(","):
                k_str = k.strip()
                if k_str:
                    cited_flat.add(k_str)

        citations = []
        context_used = []
        for ckey, cs in scored:
            meta = key_to_meta[ckey]
            page_display = meta["page_display"]

            item_dict = {
                "key": ckey,
                "paper_title": meta["paper_title"],
                "filename": meta["filename"],
                "paper_id": meta["paper_id"],
                "page": meta["page"],
                "page_display": str(page_display),
                "page_char_start": meta.get("page_char_start"),
                "page_char_end": meta.get("page_char_end"),
                "snippet": meta["snippet"],
                "raw_text": meta["raw_text"],
                "summary": meta["snippet"],
                "score": cs.relevance_score,
                "cited_in_answer": ckey in cited_flat,
            }
            context_used.append(item_dict)
            if ckey in cited_flat or not cited_flat:
                citations.append(item_dict)

        # Token & Cost summary computation
        prompt_tokens_est = map_reduce_optimizer.estimate_tokens(context_str + query)
        comp_tokens_est = map_reduce_optimizer.estimate_tokens(sanitized_answer)
        cost_report = map_reduce_optimizer.compute_cost_report(
            prompt_tokens=prompt_tokens_est,
            completion_tokens=comp_tokens_est,
            tokens_saved_cache=0,
            tokens_saved_prefilter=0,
            cache_hits=0,
            total_chunks=len(chunks),
            chunks_sent=len(top_chunks),
        )

        return {
            "answer": sanitized_answer,
            "citations": citations,
            "context_used": context_used,
            "hallucinated_citations_stripped": hallucinated_keys,
            "cost_report": cost_report.__dict__,
        }


    async def generate_structured_answer(self, query: str, chunks: List[Document]) -> list[dict]:
        """Structured output for synthesis pipelines: [{sentence, chunk_id, source}]."""
        if not chunks:
            return []

        indexed_context = []
        id_map: dict[str, str] = {}
        for i, doc in enumerate(chunks):
            ckey = self.make_citation_key(doc, i)
            if ckey in id_map:
                ckey = f"{ckey}_{i}"
            id_map[ckey] = doc.metadata.get("source", "unknown")
            indexed_context.append(f"[{ckey}]\n{doc.page_content}")

        context_str = "\n\n".join(indexed_context)

        structured_prompt = PromptTemplate(
            template=(
                "You are a research assistant. Based ONLY on the excerpts marked [key] below, "
                "answer the question.\n\n"
                "RULES:\n"
                "- Split the answer into individual sentences.\n"
                "- EACH sentence must cite exactly 1 key as evidence.\n"
                "- If no excerpt is sufficient, return empty array [].\n"
                "- Return ONLY valid JSON array, no markdown fences.\n"
                "- Write each sentence in the SAME language as the Question.\n\n"
                'JSON format: [{"sentence": "...", "chunk_id": "..."}]\n\n'
                "Excerpts:\n{context}\n\n"
                "Question: {question}\n\nJSON:"
            ),
            input_variables=["context", "question"],
        )
        chain = structured_prompt | self.grounded_llm | StrOutputParser()
        raw = await chain.ainvoke({"context": context_str, "question": query})
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return []

        return [
            {"sentence": item.get("sentence", ""), "chunk_id": cid, "source": id_map[cid]}
            for item in parsed
            if (cid := item.get("chunk_id", "")) in id_map
        ]


rag_service = RAGService()