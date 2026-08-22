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

# PaperQA2 & ScholarQA grounded system prompt: expert, zero-hallucination, strict attribution
_REDUCE_SYSTEM = (
    "You are a highly precise, grounded academic AI research assistant (inspired by PaperQA2 and ScholarQA).\n"
    "Your mission is to synthesize the provided excerpts into a clear, accurate, and completely faithful scientific answer.\n\n"
    "STRICT GROUNDING RULE — MANDATORY (ZERO-HALLUCINATION POLICY):\n"
    "- You MUST NOT use any external knowledge. All claims, equations, numbers, and facts MUST be strictly derived from and supported by the provided excerpts.\n"
    "- Do NOT extrapolate, speculate, or introduce general background topics (e.g. historical context, unrelated applications, broad taxonomies) unless they are explicitly present in the provided excerpts.\n"
    "- Answer using whatever relevant information the excerpts DO contain, even if it only covers part of the question — do not decline just because coverage is partial.\n"
    "- Only decline entirely, and state that the information is not found in the documents, if NONE of the excerpts are relevant to the question at all.\n\n"
    "CITATION RULE — MANDATORY:\n"
    "- Every single factual sentence MUST include the appropriate citation key(s) from 'Valid Keys' at the end, e.g., 'Thuật toán A đạt độ chính xác 95% trên tập dữ liệu B [1].'\n"
    "- Only cite citation keys that actually contain the supporting evidence.\n\n"
    "FORMATTING & STRUCTURE RULE:\n"
    "- Use clean Markdown (bullet points, bold text, headings) to organize the answer logically based ONLY on the evidence available.\n"
    "- Do NOT force arbitrary boilerplate sections if the text does not contain that information.\n"
    "- Present mathematical equations in LaTeX (Inline: $...$, Display: $$...$$). Never skip or distort equations or theorems provided in the text.\n\n"
    "LANGUAGE RULE — MANDATORY:\n"
    "- Detect the primary language of the Question.\n"
    "- If the question contains ANY Vietnamese terms or concepts (e.g. 'Discuss Tập loại bỏ tự do', 'là gì', 'phương pháp'), answer ENTIRELY in Vietnamese.\n"
    "- Only answer in English if the question is 100% English.\n"
    "- NEVER mix languages."
)

_REDUCE_HUMAN = (
    "Context:\n\n{context}\n\nValid Keys: {valid_keys}\n\n---\n\n"
    "Question: {question}\n\n"
    "Write an accurate, well-structured, and strictly grounded answer that synthesizes information from the provided excerpts.\n"
    "Follow these strict constraints:\n"
    "1. Base your answer ONLY on the context provided above. Do not hallucinate or extrapolate facts not in the context.\n"
    "2. For each factual sentence, place the supporting citation key(s) at the end, like [1] or [1][2]. Use ONLY keys from 'Valid Keys'.\n"
    "3. If the context contains partial information, answer what the context supports and briefly state what is not covered in the excerpts.\n"
    "4. If NONE of the excerpts are relevant at all, reply: \"Tôi không thể trả lời câu hỏi này dựa trên tài liệu được cung cấp. / I cannot answer this based on the provided documents.\" and STOP.\n\n"
    + _CITATION_KEY_RULES + "\n\n"
    "CRITICAL LANGUAGE RULE: Look at the Question carefully. If it contains ANY Vietnamese words, your ENTIRE Answer below MUST be in Vietnamese. Do NOT use English unless the question is 100% English.\n\n"
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
            timeout=30.0,
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
                "answer": "Tôi không tìm thấy ngữ cảnh nào phù hợp. / No relevant context found.",
                "citations": [],
                "context_used": [],
            }

        # ── MAP with Pre-Filtering & Semantic Caching ────────────────────────
        prefiltered_tuples, tokens_saved_prefilter = map_reduce_optimizer.prefilter_chunks(query, chunks, min_word_overlap=1)
        
        tasks = []
        task_info = []
        cached_results: list[tuple[str, ChunkSummary]] = []
        key_to_meta: dict[str, dict] = {}
        tokens_saved_cache = 0
        cache_hits = 0
        chunks_sent_llm = 0

        for i, (orig_idx, doc) in enumerate(prefiltered_tuples):
            ckey = self.make_citation_key(doc, orig_idx)
            if ckey in key_to_meta:
                ckey = f"{ckey}_{orig_idx}"
            source = doc.metadata.get("source", "unknown")
            page = str(doc.metadata.get("page", "?"))
            paper_title = self._get_paper_title(doc)
            key_to_meta[ckey] = {
                "source": source,
                "page": page,
                "paper_title": paper_title,
                "paper_id": str(doc.metadata.get("paper_id", "")),
                "filename": os.path.basename(str(source)),
                "page_char_start": doc.metadata.get("page_char_start"),
                "page_char_end": doc.metadata.get("page_char_end"),
                "raw_text": doc.page_content,
            }

            # Check cache
            cached_sum = map_reduce_optimizer.cache.get(doc.page_content, query)
            if cached_sum is not None:
                cached_results.append((ckey, cached_sum))
                tokens_saved_cache += map_reduce_optimizer.estimate_tokens(doc.page_content)
                cache_hits += 1
            else:
                chunks_sent_llm += 1
                task_info.append((ckey, doc.page_content))
                tasks.append(self._map_chunk(
                    ckey,
                    os.path.basename(str(source)),
                    paper_title,
                    page,
                    doc.page_content,
                    query,
                ))

        map_results = []
        if tasks:
            async_res = await asyncio.gather(*tasks, return_exceptions=True)
            for (ckey, content), item in zip(task_info, async_res):
                if isinstance(item, Exception):
                    logger.warning("Map task exception: %s", item)
                    continue
                map_results.append(item)
                # Store in cache
                map_reduce_optimizer.cache.set(content, query, item[1])

        map_results.extend(cached_results)

        # ── FILTER & SORT ────────────────────────────────────────────────────
        scored: list[tuple[str, ChunkSummary]] = []
        for item in map_results:
            ckey, summary = item
            if summary.relevance_score >= MIN_RELEVANCE_SCORE and summary.summary.strip():
                scored.append((ckey, summary))

        scored.sort(key=lambda x: x[1].relevance_score, reverse=True)
        scored = scored[:MAX_CONTEXT_CHUNKS]

        # Resilience Fallback: Nếu câu hỏi mang tính tổng quan hoặc MAP bị lọc quá gắt
        if not scored and chunks:
            for i, doc in enumerate(chunks[:MAX_CONTEXT_CHUNKS]):
                ckey = self.make_citation_key(doc, i)
                if ckey not in key_to_meta:
                    source = doc.metadata.get("source", "unknown")
                    page = str(doc.metadata.get("page", "1"))
                    paper_title = self._get_paper_title(doc)
                    key_to_meta[ckey] = {
                        "source": source,
                        "page": page,
                        "paper_title": paper_title,
                        "paper_id": str(doc.metadata.get("paper_id", "")),
                        "filename": os.path.basename(str(source)),
                        "page_char_start": doc.metadata.get("page_char_start"),
                        "page_char_end": doc.metadata.get("page_char_end"),
                        "raw_text": doc.page_content,
                    }
                scored.append((ckey, ChunkSummary(summary=doc.page_content[:800], relevance_score=5)))

        if not scored:
            return {
                "answer": (
                    "Không tìm thấy thông tin liên quan trong tài liệu để trả lời câu hỏi này.\n"
                    "No relevant information found in the uploaded documents."
                ),
                "citations": [],
                "context_used": [],
                "cost_report": map_reduce_optimizer.compute_cost_report(
                    prompt_tokens=0, completion_tokens=0, tokens_saved_cache=0,
                    tokens_saved_prefilter=tokens_saved_prefilter, cache_hits=0,
                    total_chunks=len(chunks), chunks_sent=0
                ).__dict__,
            }

        logger.info("FILTER (with_citations): %d/%d chunks kept (Cache hits: %d).", len(scored), len(chunks), cache_hits)

        # Remap to numeric citations [1], [2], ...
        numeric_scored = []
        numeric_key_to_meta = {}
        for idx, (old_ckey, cs) in enumerate(scored, start=1):
            new_ckey = str(idx)
            numeric_scored.append((new_ckey, cs))
            numeric_key_to_meta[new_ckey] = key_to_meta.get(old_ckey, {})
            
        scored = numeric_scored
        key_to_meta = numeric_key_to_meta

        # ── REDUCE ───────────────────────────────────────────────────────────
        context_lines = []
        for ckey, cs in scored:
            meta = key_to_meta[ckey]
            page_display = int(meta["page"]) + 1 if str(meta["page"]).isdigit() else meta["page"]
            context_lines.append(
                f"[{ckey}] (Paper: {meta['paper_title']}, page {page_display}):\n{cs.summary}"
            )
        context_str = "\n\n".join(context_lines)
        valid_keys = {f"[{ckey}]" for ckey, _ in scored}
        valid_keys_str = ", ".join(sorted(valid_keys))

        try:
            reduce_chain = REDUCE_PROMPT | self.grounded_llm | StrOutputParser()
            raw_answer = await asyncio.wait_for(
                reduce_chain.ainvoke({
                    "context": context_str,
                    "valid_keys": valid_keys_str,
                    "question": query,
                }),
                timeout=30.0
            )
        except Exception as e:
            logger.warning("REDUCE error: %s, using extractive fallback synthesis", e)
            extracted_points = []
            for ckey, cs in scored[:4]:
                if cs.summary.strip():
                    extracted_points.append(f"- {cs.summary.strip()} [{ckey}]")
            raw_answer = "Dựa trên các tài liệu đã cung cấp:\n" + "\n".join(extracted_points)

        # ── Guardrails: Sanitize Citations & Strip Hallucinated Keys ──────────
        valid_numeric_keys = {ckey for ckey, _ in scored}
        sanitized_answer, hallucinated_keys = rag_guardrail_service.sanitize_citations(
            raw_answer, valid_keys=valid_numeric_keys
        )

        # ── Build traceable citation metadata (PaperQA2 bib-style) ──────────
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
            page_raw = meta["page"]
            page_display = int(page_raw) + 1 if str(page_raw).isdigit() else page_raw

            citations.append({
                "key": ckey,
                "paper_title": meta["paper_title"],
                "page": page_display,
                "paper_id": meta["paper_id"],
                "filename": meta["filename"],
                "cited_in_answer": ckey in cited_flat,
                "page_char_start": meta.get("page_char_start"),
                "page_char_end": meta.get("page_char_end"),
                "snippet": cs.summary.strip() or (meta.get("raw_text") or "")[:400].strip(),
                "raw_text": meta["raw_text"],
                "summary": cs.summary.strip(),
            })
            context_used.append({
                "key": ckey,
                "paper_title": meta["paper_title"],
                "page_display": str(page_display),
                "paper_id": meta["paper_id"],
                "filename": meta["filename"],
                "snippet": cs.summary.strip() or (meta.get("raw_text") or "")[:400].strip(),
                "summary": cs.summary.strip(),
                "raw_text": meta["raw_text"],
                "score": cs.relevance_score,
                "page_char_start": meta.get("page_char_start"),
                "page_char_end": meta.get("page_char_end"),
            })

        # Token & Cost summary computation
        prompt_tokens_est = map_reduce_optimizer.estimate_tokens(context_str + query)
        comp_tokens_est = map_reduce_optimizer.estimate_tokens(sanitized_answer)
        cost_report = map_reduce_optimizer.compute_cost_report(
            prompt_tokens=prompt_tokens_est,
            completion_tokens=comp_tokens_est,
            tokens_saved_cache=tokens_saved_cache,
            tokens_saved_prefilter=tokens_saved_prefilter,
            cache_hits=cache_hits,
            total_chunks=len(chunks),
            chunks_sent=chunks_sent_llm,
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