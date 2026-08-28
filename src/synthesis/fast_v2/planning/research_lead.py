"""Outline-first Research Lead planning.

One bounded LLM call turns the selected papers' metadata (title/abstract --
never raw PDF chunks) plus the user's research question into a thematic,
comparative outline: sections with a purpose, a target word count, which
papers a section is expected to compare, and the retrieval queries that
should feed that section specifically.

This plans queries only. It never sees PDF chunks and cannot create evidence
or bypass the later hygiene/rerank/provenance/semantic-verification gates --
those still decide what evidence actually reaches the writer.

Why sections replace the old "dimension" concept
--------------------------------------------------
Retrieval used to run against generic, question-independent facets (see
``dimensions/facets.py``), producing a single flat evidence pack. A section's
``title`` here becomes the pipeline's per-request "dimension": each section
gets its own retrieval queries, its own capped candidate shortlist, and its
own reranked evidence -- see ``dimensions/outline_planner.py`` and
``pipeline.py``.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

MIN_SECTIONS = 4
MAX_SECTIONS = 7
MIN_TOTAL_TARGET_WORDS = 4000
MAX_TOTAL_TARGET_WORDS = 6000

RESEARCH_LEAD_SYSTEM_PROMPT = """You are the Research Lead planning a rigorous, long-form comparative literature review over a set of selected papers.

Given the research question and the selected papers' corpus skims, produce a thematic macro outline and a section-specific retrieval plan.

REQUIREMENTS:
1. {min_sections}-{max_sections} thematic sections. Sections are organized by theme, method, or theoretical development -- NEVER one section per paper.
2. STRICT CORPUS GROUNDING: All proposed outline content (section titles, purposes, comparison targets, and retrieval queries) MUST be strictly grounded in the supplied corpus skims.
   - Do not introduce a specific algorithm family, method name, mathematical property, convergence guarantee, stepsize strategy, extension, application, or technical concept unless it is supported by the supplied skim for at least one selected paper.
   - You may synthesize and generalize wording across papers, but you must NOT introduce speculative technical concepts merely because they are plausible from general domain knowledge.
   - If a desired theme is not clearly supported by the supplied skims, DO NOT invent it; broaden or rephrase the section around genuinely supported concepts.
3. PAPERS_TO_COMPARE AS SUPPORT MAPPING: For every section, every paper listed in `papers_to_compare` must actually contribute evidence to that section's stated theme according to its supplied skim. The section's central technical concepts must be supported by at least one of those papers. Do not force a paper into a section it does not belong in.
4. RETRIEVAL QUERIES GROUNDED IN CORPUS: Each section needs 2-3 `retrieval_queries` derived directly from the research question, section theme, and terminology present or supported in the supplied corpus skims. Do NOT generate speculative queries searching for concepts that the corpus skims give no evidence of.
5. Each section needs: a clear purpose (what intellectual question it answers), a target_words count, and total target_words across all sections must sum to between {min_words} and {max_words}.
6. Do not hardcode or assume paper identities beyond what is given below.

Return ONLY a valid JSON object exactly matching this schema:
{{
  "research_question": "...",
  "sections": [
    {{
      "title": "...",
      "purpose": "...",
      "target_words": 900,
      "papers_to_compare": ["..."],
      "retrieval_queries": ["...", "..."]
    }}
  ]
}}"""


@dataclass(frozen=True)
class SectionPlan:
    """One outline section: what it's for, how long, and how to retrieve for it."""

    id: str
    title: str
    purpose: str
    target_words: int
    papers_to_compare: tuple[str, ...]
    retrieval_queries: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "purpose": self.purpose,
            "target_words": self.target_words,
            "papers_to_compare": list(self.papers_to_compare),
            "retrieval_queries": list(self.retrieval_queries),
        }


@dataclass(frozen=True)
class LongformOutlinePlan:
    """Research Lead's full plan: the framed question plus its section outline."""

    research_question: str
    sections: tuple[SectionPlan, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_question": self.research_question,
            "sections": [section.to_dict() for section in self.sections],
        }


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    first_b = text.find("{")
    last_b = text.rfind("}")
    if first_b == -1 or last_b == -1:
        raise ValueError("Research Lead response contained no JSON object")
    return json.loads(text[first_b : last_b + 1])


def _fallback_outline(research_question: str) -> LongformOutlinePlan:
    """Deterministic, no-LLM fallback: one broad section, never a crash.

    Used only when the LLM response cannot be parsed into the required
    schema -- retrieval still happens (against this section's single
    generic query), it just won't be thematically decomposed.
    """
    return LongformOutlinePlan(
        research_question=research_question,
        sections=(
            SectionPlan(
                id="sec_1",
                title="Literature Synthesis",
                purpose="Synthesize the selected papers in response to the research question.",
                target_words=4000,
                papers_to_compare=(),
                retrieval_queries=(research_question,),
            ),
        ),
    )


class ResearchLeadPlanningError(RuntimeError):
    """Raised when Research Lead outline planning fails all retry attempts or exceeds hard timeout."""
    pass


async def ainvoke_with_retry(
    llm: ChatOpenAI,
    messages: list,
    max_retries: int = 1,
    timeout_seconds: float = 75.0,
):
    """Execute LLM call with a hard timeout (60-90s) and at most 1 retry."""
    import datetime

    last_error: Exception | None = None
    total_attempts = 1 + max_retries

    for attempt in range(1, total_attempts + 1):
        req_start_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
        t0 = time.perf_counter()
        print(
            f"[Research Lead] Planning attempt {attempt}/{total_attempts} started at {req_start_dt} "
            f"(timeout={timeout_seconds}s)...",
            flush=True,
        )
        try:
            resp = await asyncio.wait_for(llm.ainvoke(messages), timeout=timeout_seconds)
            elapsed = round(time.perf_counter() - t0, 2)
            req_end_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
            print(
                f"[Research Lead] Planning attempt {attempt}/{total_attempts} succeeded in {elapsed}s "
                f"(end={req_end_dt}).",
                flush=True,
            )
            return resp
        except (asyncio.TimeoutError, TimeoutError):
            elapsed = round(time.perf_counter() - t0, 2)
            req_end_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
            last_error = TimeoutError(f"Planning LLM request timed out after {elapsed}s (limit={timeout_seconds}s)")
            print(
                f"[Research Lead] Attempt {attempt}/{total_attempts} TIMEOUT: "
                f"planning_attempt={attempt}, request_start={req_start_dt}, request_end={req_end_dt}, "
                f"elapsed={elapsed}s, timeout/error={last_error}, retry_count={attempt-1}",
                flush=True,
            )
        except Exception as exc:
            elapsed = round(time.perf_counter() - t0, 2)
            req_end_dt = datetime.datetime.now(datetime.timezone.utc).isoformat()
            last_error = exc
            print(
                f"[Research Lead] Attempt {attempt}/{total_attempts} FAILED: "
                f"planning_attempt={attempt}, request_start={req_start_dt}, request_end={req_end_dt}, "
                f"elapsed={elapsed}s, timeout/error={exc}, retry_count={attempt-1}",
                flush=True,
            )

        if attempt < total_attempts:
            print(f"[Research Lead] Retrying planning request in 2.0s...", flush=True)
            await asyncio.sleep(2.0)

    raise ResearchLeadPlanningError(
        f"Research Lead planning failed after {total_attempts} attempts. Last error: {last_error}"
    ) from last_error


def _parse_outline(data: dict[str, Any], research_question: str) -> LongformOutlinePlan:
    raw_sections = data.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("Research Lead response has no sections")

    sections: list[SectionPlan] = []
    for idx, raw in enumerate(raw_sections, 1):
        if not isinstance(raw, dict):
            continue
        sec_id = str(raw.get("id") or f"sec_{idx}").strip()
        title = str(raw.get("title") or "").strip()
        purpose = str(raw.get("purpose") or "").strip()
        if not title or not purpose:
            continue
        try:
            target_words = int(raw.get("target_words") or 0)
        except (TypeError, ValueError):
            target_words = 0
        papers = tuple(
            str(item).strip() for item in (raw.get("papers_to_compare") or []) if str(item).strip()
        )
        queries = tuple(
            str(item).strip() for item in (raw.get("retrieval_queries") or []) if str(item).strip()
        )
        if not queries:
            queries = (f"{title}. {purpose}",)
        sections.append(
            SectionPlan(
                id=sec_id,
                title=title,
                purpose=purpose,
                target_words=target_words or 800,
                papers_to_compare=papers,
                retrieval_queries=queries,
            )
        )

    if not sections:
        raise ValueError("Research Lead response had no usable sections")

    return LongformOutlinePlan(
        research_question=str(data.get("research_question") or research_question).strip()
        or research_question,
        sections=tuple(sections),
    )


async def plan_longform_outline(
    llm: ChatOpenAI,
    *,
    research_question: str,
    paper_metadata: Sequence[dict[str, str]] = (),
    timeout_seconds: float = 75.0,
    max_retries: int = 1,
) -> LongformOutlinePlan:
    """One LLM call: research question -> thematic outline + section retrieval plan.

    If planning fails or times out after retries, raises ResearchLeadPlanningError
    to halt pipeline execution cleanly.
    """
    papers = [
        {"title": item.get("title", "")[:500], "abstract": item.get("abstract", "")[:3000]}
        for item in paper_metadata
        if item.get("title") or item.get("abstract")
    ]
    system_prompt = RESEARCH_LEAD_SYSTEM_PROMPT.format(
        min_sections=MIN_SECTIONS,
        max_sections=MAX_SECTIONS,
        min_words=MIN_TOTAL_TARGET_WORDS,
        max_words=MAX_TOTAL_TARGET_WORDS,
    )
    user_prompt = (
        f"Research Question:\n{research_question}\n\n"
        f"Selected papers (title/abstract only):\n{json.dumps(papers, ensure_ascii=False)}"
    )
    resp = await ainvoke_with_retry(
        llm,
        [("system", system_prompt), ("human", user_prompt)],
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
    data = _extract_json_object(str(resp.content))
    return _parse_outline(data, research_question)
