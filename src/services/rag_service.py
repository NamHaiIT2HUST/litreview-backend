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

# REDUCE: Answer generation  (PaperQA2: qa_prompt + default_system_prompt)
# Key PaperQA2 principles:
#  1. system_prompt is SHORT and direct: "Answer in a direct and concise tone."
#  2. "Write in the style of a scientific article" → naturally concise
#  3. "do not add any extraneous information" → no padding
#  4. "If insufficient information reply 'I cannot answer'" → honest fallback
#  5. answer_length target (PaperQA2 default: "about 200 words, but can be longer")
_CITATION_KEY_RULES = (
    "Citation rules (follow exactly):\n"
    "- Place citation keys in brackets at the end of each sentence: [1] or [1][2]\n"
    "- Use ONLY the citation keys listed in 'Valid Keys'\n"
    "- Do NOT use author names, years, or page numbers as citations\n"
    "- Valid: [1] | [1][2]. Invalid: [1 and 2] | (1) | Author et al. (2023)"
)

# PaperQA2's default_system_prompt: short, expert-focused
_REDUCE_SYSTEM = (
    "You are a highly advanced academic AI research assistant (similar to NotebookLM)."
    " Your goal is to synthesize the provided excerpts into an extremely detailed, highly structured, comprehensive, and textbook-quality academic answer.\n\n"
    "STRICT GROUNDING RULE — MANDATORY:\n"
    "- You MUST NOT use any external knowledge. All claims MUST be grounded in the provided context.\n"
    "- You MUST ONLY use the information explicitly stated in the provided excerpts.\n"
    "- Answer using whatever relevant information the excerpts DO contain, even if it only covers part of the question — do not decline just because coverage is partial.\n"
    "- Only decline entirely, and state that the information is not found in the documents, if NONE of the excerpts are relevant to the question at all.\n\n"
    "FORMATTING RULE — MANDATORY:\n"
    "- Use Markdown extensively to structure your answer hierarchically.\n"
    "- ALWAYS break your answer down into clear numbered sections (e.g., 1. Định nghĩa Toán học / Mathematical Definition, 2. Ý nghĩa & Tính chất / Properties & Intuition, 3. Các dạng phổ biến / Common Forms, 4. Ứng dụng / Applications).\n"
    "- Provide a high-level summary/overview at the very beginning before diving into the sections.\n"
    "- Use Bullet points (-), Bold text (**), and Italic text (*) generously to organize concepts and make them scannable.\n\n"
    "CONTENT RULE — MANDATORY:\n"
    "- When asked 'what is' (là gì) or to explain a concept, provide a deep, academic explanation. Include the mathematical formulation, geometric or intuitive meaning, and core properties.\n"
    "- CRITICAL: Do NOT skip, flatten, or over-summarize mathematical definitions, lemmas, properties, or proofs. These must be preserved in full detail with exact LaTeX equations.\n\n"
    "SYNTHESIS RULE — MANDATORY:\n"
    "- You MUST synthesize information across ALL provided sources.\n"
    "- If multiple papers discuss the same or related topics, combine their perspectives or compare them.\n"
    "- Do NOT just summarize one source and ignore the others. Aim to use as many provided citation keys as relevant to provide a complete picture.\n\n"
    "LANGUAGE RULE — MANDATORY:\n"
    "- Detect the primary language of the Question.\n"
    "- If the question contains ANY Vietnamese terms or concepts (e.g. 'Discuss Tập loại bỏ tự do', 'là gì'), answer ENTIRELY in Vietnamese.\n"
    "- Only answer in English if the question is 100% English.\n"
    "- NEVER mix languages.\n\n"
    "MATH RULE — MANDATORY:\n"
    "- Use LaTeX for ALL math without exception.\n"
    "- Inline: $\\theta \\in [0,1)$, $\\beta_k$, $\\|u_k - u_{{k-1}}\\|$.\n"
    "- Display (own paragraph): $$\\beta_k = \\min\\left\\{{\\theta, \\frac{{\\varepsilon_k}}{{\\|u_k-u_{{k-1}}\\|}}\\right\\}}$$\n"
    "- Never Unicode math (\u03b8 \u03b2 \u2207 \u03a3 \u03b5 \u2264 \u2208 || ||)."
    " Subscripts: $u_k$. Norms: $\\|\\cdot\\|$. Fractions: $\\frac{{a}}{{b}}$."
)

_REDUCE_HUMAN = (
    "Context:\n\n{context}\n\nValid Keys: {valid_keys}\n\n---\n\n"
    "Question: {question}\n\n"
    "Write a comprehensive, deep, and textbook-style structured answer that synthesizes information from across ALL the provided contexts."
    " Your answer should be highly detailed (acting like a comprehensive study guide). Break it down into clear logical sections (e.g. Definition, Intuition, Properties, Forms/Applications).\n"
    " If the context contains information that answers the question — even partially, or only some"
    " aspects of it — you MUST write an answer using that information. Do not refuse just because"
    " one detail is missing; answer what the context supports and note what it doesn't cover.\n"
    " Only if NONE of the provided excerpts are relevant to the question at all, immediately reply"
    " \"Tôi không thể trả lời câu hỏi này dựa trên tài liệu. / I cannot answer this based on the provided documents.\" and STOP.\n"
    " For each part of your answer, indicate which sources most support it"
    " via citation keys at the end of sentences.\n"
    " Only cite from the context above and only use the citation keys from 'Valid Keys'.\n"
    " Remember to use Markdown formatting (headings, lists, bolding) to make the answer highly readable and analytical.\n\n"
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
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            api_key=openai_key,
            base_url=base_url,
            temperature=settings.llm_temperature,
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
        chain = MAP_PROMPT | self.grounded_llm | StrOutputParser()
        raw = await chain.ainvoke({
            "citation_key": citation_key,
            "source_name": source_name,
            "paper_title": paper_title,
            "page": page,
            "excerpt": excerpt,
            "question": question,
        })
        data = _parse_chunk_json(raw)
        result = ChunkSummary(
            summary=data.get("summary", ""),
            relevance_score=data.get("relevance_score", 0),
        )
        logger.info("MAP [%s] score=%d  %s", citation_key, result.relevance_score, ascii(result.summary[:80]))
        return citation_key, result

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

        reduce_chain = REDUCE_PROMPT | self.grounded_llm | StrOutputParser()
        answer = await reduce_chain.ainvoke({
            "context": context_str,
            "valid_keys": valid_keys,
            "question": query,
        })
        return answer

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

        # ── MAP ──────────────────────────────────────────────────────────────
        tasks = []
        key_to_meta: dict[str, dict] = {}

        for i, doc in enumerate(chunks):
            ckey = self.make_citation_key(doc, i)
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
                "filename": os.path.basename(str(source)),
                "page_char_start": doc.metadata.get("page_char_start"),
                "page_char_end": doc.metadata.get("page_char_end"),
                "raw_text": doc.page_content,
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

        # Resilience Fallback: Nếu câu hỏi mang tính tổng quan (e.g. "tổng quan tài liệu", "tóm tắt")
        # hoặc MAP bị lọc quá gắt, tự động dùng các chunk hàng đầu làm ngữ cảnh thay vì từ chối trả lời.
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
            }

        logger.info("FILTER (with_citations): %d/%d chunks kept.", len(scored), len(chunks))

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
        valid_keys = ", ".join(f"[{ckey}]" for ckey, _ in scored)

        reduce_chain = REDUCE_PROMPT | self.grounded_llm | StrOutputParser()
        answer = await reduce_chain.ainvoke({
            "context": context_str,
            "valid_keys": valid_keys,
            "question": query,
        })

        # ── Build traceable citation metadata (PaperQA2 bib-style) ──────────
        # Extract which keys actually appear in the answer (e.g. [1])
        cited_keys_in_answer: set[str] = set(re.findall(r'\[([^\]]+)\]', answer))
        cited_flat: set[str] = set()
        for group in cited_keys_in_answer:
            for k in group.split(","):
                cited_flat.add(k.strip())

        citations = []
        context_used = []
        for ckey, cs in scored:
            meta = key_to_meta[ckey]
            page_raw = meta["page"]
            page_display = int(page_raw) + 1 if str(page_raw).isdigit() else page_raw

            # citation entry (for deduplicated source list)
            citations.append({
                "key": ckey,
                "paper_title": meta["paper_title"],
                "page": page_display,
                "paper_id": meta["paper_id"],
                "filename": meta["filename"],
                "cited_in_answer": ckey in cited_flat,
                "page_char_start": meta.get("page_char_start"),
                "page_char_end": meta.get("page_char_end"),
                "snippet": cs.summary[:300].strip(),
                "raw_text": meta["raw_text"],
            })
            # context_used entry (for "sources used" panel in ChatPanel)
            context_used.append({
                "key": ckey,
                "paper_title": meta["paper_title"],
                "page_display": str(page_display),
                "paper_id": meta["paper_id"],
                "filename": meta["filename"],
                "snippet": cs.summary[:300].strip(),
                "raw_text": meta["raw_text"],
                "score": cs.relevance_score,
                "page_char_start": meta.get("page_char_start"),
                "page_char_end": meta.get("page_char_end"),
            })

        return {
            "answer": answer,
            "citations": citations,
            "context_used": context_used,
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