"""Anthropic-style post-hoc citation attribution over all substantive prose paragraphs.

Adapted directly from:
anthropics/claude-cookbooks/patterns/agents/prompts/citations_agent.md

Central Invariant:
The synthesized prose must remain identical; the citation stage may ONLY insert citations.
A diff check verifies that prose text without citation markers is byte-identical to the original prose.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Mapping, Sequence
from langchain_openai import ChatOpenAI
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.prompt import format_evidence_context

CITATIONS_AGENT_SYSTEM_PROMPT = """You are a meticulous scientific citation agent.
Your task is to take a finalized literature review paragraph and insert inline citation handles [E001], [E002] to attribute factual statements to the provided evidence passages.

CRITICAL INVARIANTS:
1. BYTE-EXACT PROSE COPY: You must preserve the input text byte-for-byte. DO NOT change, rewrite, rephrase, add, or delete ANY words, letters, punctuation, numbers, line breaks, whitespace, or LaTeX formulas.
2. ABSOLUTELY NO LATEX REWRITING: Do NOT normalize, reformat, or alter ANY LaTeX math formulas, commands (e.g. \\nabla, \\frac, \\|, \\top, \\gamma), delimiters ($...$, $$...$$, \\[...\\]), backslashes, superscripts, subscripts, or equations. Copy every single mathematical symbol and formula EXACTLY as written.
3. CITATION-ONLY INSERTIONS: ONLY insert bracketed citation handles (e.g. [E001] or [E001, E002]) immediately after the factual claims or equations they support.
4. VALID HANDLES ONLY: Every inserted citation must strictly correspond to an evidence handle present in the supplied evidence pack. If a statement has no supporting evidence, DO NOT insert a citation handle.
5. Output ONLY the exact paragraph text with inserted citation handles. No commentary, explanations, or extra markdown fences."""

_CITATION_TAG_REGEX = re.compile(r"\s*\[E\d{3}(?:,\s*E\d{3})*\]")


def strip_citations(text: str) -> str:
    """Normalize text by removing citation tags and whitespace for diff invariant check."""
    cleaned = _CITATION_TAG_REGEX.sub("", text)
    return re.sub(r"\s+", " ", cleaned).strip()


_CITATION_TAG_CAPTURE = re.compile(r"\[(E\d{3}(?:,\s*E\d{3})*)\]")


def strip_out_of_scope_handles(text: str, allowed_handles: set[str]) -> str:
    """Drop any handle from an inserted [E###, ...] tag that isn't in
    ``allowed_handles`` (the evidence the model was actually shown for this
    paragraph). A tag with no remaining valid handles is removed entirely.
    Never touches prose outside citation tags -- prose invariant is
    unaffected by this."""

    def _rewrite(match: re.Match[str]) -> str:
        kept = [h.strip() for h in match.group(1).split(",") if h.strip() in allowed_handles]
        return f"[{', '.join(kept)}]" if kept else ""

    return _CITATION_TAG_CAPTURE.sub(_rewrite, text)


def is_substantive_prose(paragraph: str) -> bool:
    """Check if a paragraph is a substantive prose text (not heading, math block, or divider)."""
    p = paragraph.strip()
    if not p:
        return False
    if p.startswith("#"):
        return False
    if p.startswith("---") or p.startswith("***") or p.startswith("___"):
        return False
    # Pure standalone equation blocks
    if (p.startswith("\\[") and p.endswith("\\]")) or (p.startswith("$$") and p.endswith("$$")):
        return False
    # Extremely short fragments
    if len(p.split()) < 5:
        return False
    return True


def build_paragraph_section_map(
    raw_blocks: Sequence[str],
    sections: Sequence[tuple[str, str]],
) -> dict[int, str | None]:
    """Map each paragraph block index to a section id by walking back to the
    nearest preceding '## ...' heading that names a known section title.

    Blocks before the first matched section heading, or under a heading that
    does not match any known section (e.g. '## Introduction', '## Conclusion',
    '## References'), map to ``None`` -- meaning "global scope, not confined
    to one section's evidence" -- never silently mis-scoped to the wrong
    section. This is deliberately conservative: a false-negative (None, i.e.
    "give it the full evidence pack") is safe, a false-positive section match
    is not.
    """
    result: dict[int, str | None] = {}
    current: str | None = None
    for idx, block in enumerate(raw_blocks):
        stripped = block.strip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip().lower()
            matched = None
            for sec_id, sec_title in sections:
                if sec_title.lower() in heading_text:
                    matched = sec_id
                    break
            current = matched  # None for Introduction/Conclusion/References/unmatched headings
        result[idx] = current
    return result


def _global_handle_index(evidence: Sequence[EvidenceUnit]) -> tuple[dict[str, str], dict[str, EvidenceUnit]]:
    """Handle numbers are POSITIONAL in the full evidence list and MUST stay
    stable across scoped subsets, because provenance binding downstream
    (section_pipeline.py) re-derives the same E### -> EvidenceUnit mapping
    from the same full list independently. Renumbering a subset would bind
    citations to the wrong evidence unit."""
    handle_by_id = {unit.evidence_id: f"E{idx:03d}" for idx, unit in enumerate(evidence, start=1)}
    unit_by_id = {unit.evidence_id: unit for unit in evidence}
    return handle_by_id, unit_by_id


def format_scoped_evidence_context(
    evidence: Sequence[EvidenceUnit],
    scope_evidence_ids: set[str] | None,
) -> tuple[str, set[str]]:
    """Build the evidence-pack text for one batch, restricted to
    ``scope_evidence_ids`` (None = full pack, unchanged legacy behavior).
    Handles keep their GLOBAL position-derived number, not a local 1..k
    renumbering, so downstream provenance binding against the full list
    still resolves correctly."""
    handle_by_id, _ = _global_handle_index(evidence)
    parts: list[str] = []
    handles: set[str] = set()
    for unit in evidence:
        if scope_evidence_ids is not None and unit.evidence_id not in scope_evidence_ids:
            continue
        handle = handle_by_id[unit.evidence_id]
        parts.append(f"--- [{handle}] (Source: {unit.title}, Page {unit.page}) ---\n{unit.text.strip()}")
        handles.add(handle)
    return "\n\n".join(parts), handles


#: A batch whose paragraphs span more than this many distinct sections is
#: treated as "global" (full evidence pack) rather than unioning that many
#: section pools -- past this point the union no longer saves meaningful
#: tokens over just sending everything, so the extra bookkeeping isn't worth it.
MAX_SECTIONS_PER_SCOPED_BATCH = 3


def resolve_batch_evidence_scope(
    batch_section_ids: Sequence[str | None],
    section_evidence: Mapping[str, Sequence[EvidenceUnit]] | None,
) -> set[str] | None:
    """Decide which evidence_ids a batch may cite from, given the sections
    its paragraphs belong to. Returns None (full pack) when scoping isn't
    available or safe to apply -- never returns an empty/under-scoped set
    that would starve a paragraph of evidence it needs."""
    if not section_evidence:
        return None
    distinct = {sid for sid in batch_section_ids if sid is not None}
    if not distinct or len(distinct) > MAX_SECTIONS_PER_SCOPED_BATCH:
        return None  # global/introduction/conclusion paragraph, or too spread out to bother scoping
    if not distinct.issubset(section_evidence.keys()):
        return None
    scope: set[str] = set()
    for sid in distinct:
        scope.update(u.evidence_id for u in section_evidence[sid])
    return scope


BATCHED_CITATIONS_AGENT_SYSTEM_PROMPT = """You are a meticulous scientific citation agent.
Your task is to take a batch of finalized literature review paragraphs and insert inline citation handles [E001], [E002] to attribute factual statements to the provided evidence passages.

CRITICAL INVARIANTS:
1. BYTE-EXACT PROSE COPY: You must preserve the input text byte-for-byte. DO NOT change, rewrite, rephrase, add, or delete ANY words, letters, punctuation, numbers, line breaks, whitespace, or LaTeX formulas.
2. ABSOLUTELY NO LATEX REWRITING: Do NOT normalize, reformat, or alter ANY LaTeX math formulas, commands (e.g. \\nabla, \\frac, \\|, \\top, \\gamma), delimiters ($...$, $$...$$, \\[...\\]), backslashes, superscripts, subscripts, or equations. Copy every single mathematical symbol and formula EXACTLY as written.
3. CITATION-ONLY INSERTIONS: ONLY insert bracketed citation handles (e.g. [E001] or [E001, E002]) immediately after the factual claims or equations they support.
4. VALID HANDLES ONLY: Every inserted citation must strictly correspond to an evidence handle present in the supplied evidence pack. If a statement has no supporting evidence, DO NOT insert a citation handle.
5. Output each paragraph wrapped in exact xml tags: <paragraph id="X">attributed paragraph text</paragraph> matching the input id.
6. Do NOT output any preamble, commentary, or markdown fences outside the <paragraph> tags."""


@dataclass
class CitationCoverageTelemetry:
    total_paragraphs: int = 0
    substantive_paragraphs: int = 0
    attributed_attempted: int = 0
    passed_first_attempt: int = 0
    passed_after_retry: int = 0
    failed_closed: int = 0
    skipped_non_substantive: int = 0
    silently_skipped_substantive: int = 0
    citation_markers_emitted: int = 0
    valid_handles: int = 0
    invalid_handles_rejected: int = 0
    final_bound_citations: int = 0
    uncited_substantive_paragraphs: int = 0
    stage_latency_seconds: float = 0.0
    provider_attempts: int = 0
    total_tokens_used: int = 0
    total_input_tokens_used: int = 0
    number_of_batches: int = 0
    paragraph_details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_paragraphs": self.total_paragraphs,
            "substantive_paragraphs": self.substantive_paragraphs,
            "attributed_attempted": self.attributed_attempted,
            "passed_first_attempt": self.passed_first_attempt,
            "passed_after_retry": self.passed_after_retry,
            "failed_closed": self.failed_closed,
            "skipped_non_substantive": self.skipped_non_substantive,
            "silently_skipped_substantive": self.silently_skipped_substantive,
            "citation_markers_emitted": self.citation_markers_emitted,
            "valid_handles": self.valid_handles,
            "invalid_handles_rejected": self.invalid_handles_rejected,
            "final_bound_citations": self.final_bound_citations,
            "uncited_substantive_paragraphs": self.uncited_substantive_paragraphs,
            "stage_latency_seconds": round(self.stage_latency_seconds, 2),
            "provider_attempts": self.provider_attempts,
            "total_tokens_used": self.total_tokens_used,
            "total_input_tokens_used": self.total_input_tokens_used,
            "number_of_batches": self.number_of_batches,
            "paragraph_details": self.paragraph_details,
        }


@dataclass(frozen=True)
class FullCitationAttributionResult:
    attributed_markdown: str
    overall_diff_passed: bool
    telemetry: CitationCoverageTelemetry


async def attribute_single_paragraph(
    llm: ChatOpenAI,
    paragraph: str,
    context_text: str,
    available_handles: set[str],
    sem: asyncio.Semaphore,
) -> tuple[str, bool, bool, int, int, int, list[str]]:
    """Attribute one paragraph with semaphore concurrency, 60s timeout, 1 diff retry and fail-closed protection."""
    prompt = f"""Supplied Evidence Pack:
{context_text}

Paragraph:
{paragraph}

Insert inline citation handles [E###] into the exact paragraph above without altering any words:"""

    attempts = 1
    output_tokens = 0
    input_tokens = 0

    async with sem:
        # First attempt with 60s timeout
        resp = None
        try:
            resp = await asyncio.wait_for(
                llm.ainvoke([
                    ("system", CITATIONS_AGENT_SYSTEM_PROMPT),
                    ("human", prompt)
                ]),
                timeout=60.0
            )
        except Exception:
            await asyncio.sleep(1.0)
            attempts += 1
            try:
                resp = await asyncio.wait_for(
                    llm.ainvoke([
                        ("system", CITATIONS_AGENT_SYSTEM_PROMPT),
                        ("human", prompt)
                    ]),
                    timeout=60.0
                )
            except Exception:
                return paragraph, False, False, attempts, 0, 0, []

        usage = getattr(resp, "usage_metadata", {}) or {}
        attr_text = str(resp.content).strip()
        output_tokens += usage.get("output_tokens", 0)
        input_tokens += usage.get("input_tokens", 0)

        # Check diff invariant
        if strip_citations(paragraph) == strip_citations(attr_text):
            emitted = _CITATION_TAG_REGEX.findall(attr_text)
            return attr_text, True, False, attempts, output_tokens, input_tokens, emitted

        # Second attempt (targeted retry) with 60s timeout
        attempts += 1
        try:
            resp2 = await asyncio.wait_for(
                llm.ainvoke([
                    ("system", CITATIONS_AGENT_SYSTEM_PROMPT + "\n\nCRITICAL DIFF WARNING (RETRY): Your previous attempt modified protected text, punctuation, or LaTeX formulas! You must perform an EXACT verbatim copy of the input text, preserving every character, symbol, delimiter, and formula byte-for-byte, inserting ONLY [E###] citation tags."),
                    ("human", prompt)
                ]),
                timeout=60.0
            )
            attr_text2 = str(resp2.content).strip()
            usage2 = getattr(resp2, "usage_metadata", {}) or {}
            output_tokens += usage2.get("output_tokens", 0)
            input_tokens += usage2.get("input_tokens", 0)
            if strip_citations(paragraph) == strip_citations(attr_text2):
                emitted = _CITATION_TAG_REGEX.findall(attr_text2)
                return attr_text2, False, True, attempts, output_tokens, input_tokens, emitted
        except Exception:
            pass

    # Fail closed: return exact original prose
    return paragraph, False, False, attempts, output_tokens, input_tokens, []


def _parse_xml_paragraphs(text: str) -> dict[int, str]:
    """Extract <paragraph id="X">text</paragraph> from model response robustly."""
    clean_text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    clean_text = re.sub(r"\n?```$", "", clean_text)
    pattern = re.compile(r'<paragraph\s+id=["\']?(\d+)["\']?>([\s\S]*?)</paragraph>', re.IGNORECASE)
    results = {}
    for match in pattern.finditer(clean_text):
        idx = int(match.group(1))
        content = match.group(2).strip()
        results[idx] = content
    return results


async def attribute_paragraph_batch(
    llm: ChatOpenAI,
    batch_items: list[tuple[int, str]],  # (block_idx, paragraph_text)
    context_text: str,
    available_handles: set[str],
    sem: asyncio.Semaphore,
) -> tuple[dict[int, tuple[str, str, list[str]]], int, int, int]:
    """Attribute a batch of paragraphs concurrently.

    Returns:
        results_map: {block_idx: (attributed_text, status, emitted_handles)}
        provider_attempts: int
        output_tokens_used: int
        input_tokens_used: int
    """
    attempts = 1
    output_tokens = 0
    input_tokens = 0
    results_map: dict[int, tuple[str, str, list[str]]] = {}

    def _wrap(local_id: int, text: str) -> str:
        return f'<paragraph id="{local_id}">\n{text}\n</paragraph>'

    def _build_human_prompt(items: list[tuple[int, tuple[int, str]]]) -> str:
        wrapped = [_wrap(local_id, p_text) for local_id, (_, p_text) in items]
        return f"""Supplied Evidence Pack:
{context_text}

Paragraphs to attribute:
{chr(10).join(wrapped)}

Insert inline citation handles [E###] into each paragraph above and wrap each in its respective <paragraph id="X">...</paragraph> tag. Keep all words, formulas, and characters byte-identical:"""

    indexed_items = list(enumerate(batch_items))  # (local_id, (b_idx, p_text))
    human_prompt = _build_human_prompt(indexed_items)

    async with sem:
        resp = None
        try:
            resp = await asyncio.wait_for(
                llm.ainvoke([
                    ("system", BATCHED_CITATIONS_AGENT_SYSTEM_PROMPT),
                    ("human", human_prompt)
                ]),
                timeout=35.0
            )
        except Exception:
            resp = None

        if resp is not None:
            usage = getattr(resp, "usage_metadata", {}) or {}
            output_tokens += usage.get("output_tokens", 0)
            input_tokens += usage.get("input_tokens", 0)
            parsed = _parse_xml_paragraphs(str(resp.content).strip())

            all_passed = True
            for local_id, (b_idx, p_text) in indexed_items:
                if local_id in parsed and strip_citations(p_text) == strip_citations(parsed[local_id]):
                    emitted = _CITATION_TAG_REGEX.findall(parsed[local_id])
                    results_map[b_idx] = (parsed[local_id], "passed_first_attempt", emitted)
                else:
                    all_passed = False

            if all_passed:
                return results_map, attempts, output_tokens, input_tokens

            # TARGETED RETRY: only paragraphs that failed the diff-invariant
            # check on the first attempt are resent. Paragraphs that already
            # passed are frozen in results_map and never resent -- this is
            # the dominant lever on provider_attempts/tokens for batches with
            # one bad paragraph out of N.
            failed_items = [(local_id, item) for local_id, item in indexed_items if item[0] not in results_map]
            attempts += 1
            retry_prompt = _build_human_prompt(failed_items)
            try:
                resp2 = await asyncio.wait_for(
                    llm.ainvoke([
                        ("system", BATCHED_CITATIONS_AGENT_SYSTEM_PROMPT + "\n\nCRITICAL DIFF WARNING (RETRY): Your previous attempt modified protected text, punctuation, or LaTeX formulas! Ensure ALL paragraphs are wrapped in <paragraph id=\"X\"> tags, preserving every character, symbol, delimiter, and formula byte-for-byte, inserting ONLY [E###] tags."),
                        ("human", retry_prompt)
                    ]),
                    timeout=35.0
                )
                usage2 = getattr(resp2, "usage_metadata", {}) or {}
                output_tokens += usage2.get("output_tokens", 0)
                input_tokens += usage2.get("input_tokens", 0)
                parsed2 = _parse_xml_paragraphs(str(resp2.content).strip())
                for local_id, (b_idx, p_text) in failed_items:
                    if b_idx not in results_map:
                        if local_id in parsed2 and strip_citations(p_text) == strip_citations(parsed2[local_id]):
                            emitted = _CITATION_TAG_REGEX.findall(parsed2[local_id])
                            results_map[b_idx] = (parsed2[local_id], "passed_after_retry", emitted)
            except Exception:
                pass

    # Concurrent fallback for any unresolved paragraphs in this batch
    unresolved_items = [(b_idx, p_text) for local_id, (b_idx, p_text) in enumerate(batch_items) if b_idx not in results_map]
    if unresolved_items:
        fallback_tasks = [
            attribute_single_paragraph(
                llm=llm,
                paragraph=p_text,
                context_text=context_text,
                available_handles=available_handles,
                sem=sem,
            )
            for _, p_text in unresolved_items
        ]
        fallback_results = await asyncio.gather(*fallback_tasks)
        for (b_idx, p_text), (p_attr, p_first, p_retry, p_att, p_out_tok, p_in_tok, emitted) in zip(unresolved_items, fallback_results):
            attempts += p_att
            output_tokens += p_out_tok
            input_tokens += p_in_tok
            if p_first:
                status = "passed_first_attempt"
            elif p_retry:
                status = "passed_after_retry"
            else:
                status = "failed_closed_kept_uncited"
            results_map[b_idx] = (p_attr, status, emitted)

    return results_map, attempts, output_tokens, input_tokens


async def attribute_all_prose_paragraphs(
    llm: ChatOpenAI,
    draft_markdown: str,
    evidence: Sequence[EvidenceUnit],
    batch_size: int = 3,
    concurrency: int = 5,
    section_evidence: Mapping[str, Sequence[EvidenceUnit]] | None = None,
    sections: Sequence[tuple[str, str]] | None = None,
) -> FullCitationAttributionResult:
    """Attribute all substantive prose paragraphs using concurrent batched mode with concurrent single-paragraph fallback.

    When ``section_evidence`` (section_id -> its EvidenceUnits, e.g. from
    section_pipeline.py's already-computed section_contexts) and ``sections``
    (ordered (section_id, title) pairs matching the outline) are both
    supplied, each batch's evidence pack is scoped to the union of the
    sections its paragraphs belong to, instead of always sending the full
    globally-selected evidence pool to every batch. Introduction/Conclusion/
    unmatched paragraphs and batches spanning too many sections fall back to
    the full pack (see resolve_batch_evidence_scope). Omitting either
    argument reproduces the original unscoped behavior exactly.
    """
    t0_stage = time.perf_counter()
    full_context_text, handle_mapping = format_evidence_context(evidence)
    global_available_handles = set(handle_mapping.keys())

    raw_blocks = draft_markdown.split("\n\n")
    telemetry = CitationCoverageTelemetry(total_paragraphs=len(raw_blocks))
    sem = asyncio.Semaphore(concurrency)

    paragraph_section_ids = build_paragraph_section_map(raw_blocks, sections) if sections else {}

    substantive_items: list[tuple[int, str]] = []
    for idx, block in enumerate(raw_blocks):
        if is_substantive_prose(block):
            telemetry.substantive_paragraphs += 1
            telemetry.attributed_attempted += 1
            substantive_items.append((idx, block))
        else:
            telemetry.skipped_non_substantive += 1

    # Chunk substantive paragraphs into batches
    batches: list[list[tuple[int, str]]] = []
    for i in range(0, len(substantive_items), batch_size):
        batches.append(substantive_items[i : i + batch_size])

    telemetry.number_of_batches = len(batches)
    print(f"  Dispatching {len(substantive_items)} substantive paragraphs in {len(batches)} batches (BatchSize={batch_size}, Concurrency={concurrency})...", flush=True)

    # Per-paragraph evidence scope, tracked so validation below rejects a
    # handle the model was never shown even if it happens to be globally
    # valid -- scoping must not silently widen what counts as "valid".
    paragraph_scope_handles: dict[int, set[str]] = {}
    batch_contexts: list[str] = []
    for batch in batches:
        batch_section_ids = [paragraph_section_ids.get(b_idx) for b_idx, _ in batch]
        scope_ids = resolve_batch_evidence_scope(batch_section_ids, section_evidence)
        if scope_ids is None:
            batch_context_text, batch_handles = full_context_text, global_available_handles
        else:
            batch_context_text, batch_handles = format_scoped_evidence_context(evidence, scope_ids)
        batch_contexts.append(batch_context_text)
        for b_idx, _ in batch:
            paragraph_scope_handles[b_idx] = batch_handles

    batch_tasks = [
        attribute_paragraph_batch(
            llm=llm,
            batch_items=b,
            context_text=ctx,
            available_handles=paragraph_scope_handles[b[0][0]],
            sem=sem,
        )
        for b, ctx in zip(batches, batch_contexts)
    ]

    batch_results = await asyncio.gather(*batch_tasks)

    attributed_blocks = list(raw_blocks)
    merged_results: dict[int, tuple[str, str, list[str]]] = {}

    for b_res, attempts, out_tok, in_tok in batch_results:
        telemetry.provider_attempts += attempts
        telemetry.total_tokens_used += out_tok
        telemetry.total_input_tokens_used += in_tok
        merged_results.update(b_res)

    for idx, block in enumerate(raw_blocks):
        if idx not in merged_results:
            telemetry.paragraph_details.append({
                "index": idx,
                "type": "heading_or_non_substantive",
                "status": "skipped",
                "preview": block[:80] + "..." if len(block) > 80 else block
            })
            continue

        attr_p, status, emitted = merged_results[idx]

        # Parse emitted handles and check validity against the scope this
        # paragraph's batch was actually shown, not just the global pool --
        # a handle that is globally valid but wasn't in THIS paragraph's
        # evidence scope was never actually shown to the model, so it must
        # be rejected and stripped, not silently bound downstream.
        allowed_handles = paragraph_scope_handles.get(idx, global_available_handles)
        p_emitted_handles: list[str] = []
        for tag in emitted:
            handles = re.findall(r"E\d{3}", tag)
            for h in handles:
                telemetry.citation_markers_emitted += 1
                p_emitted_handles.append(h)
                if h in allowed_handles:
                    telemetry.valid_handles += 1
                else:
                    telemetry.invalid_handles_rejected += 1

        attributed_blocks[idx] = strip_out_of_scope_handles(attr_p, allowed_handles)

        if status == "passed_first_attempt":
            telemetry.passed_first_attempt += 1
        elif status == "passed_after_retry":
            telemetry.passed_after_retry += 1
        else:
            telemetry.failed_closed += 1
            attributed_blocks[idx] = block # Fail-closed

        if not p_emitted_handles or status == "failed_closed_kept_uncited":
            telemetry.uncited_substantive_paragraphs += 1

        telemetry.paragraph_details.append({
            "index": idx,
            "type": "substantive_prose",
            "status": status,
            "emitted_handles": p_emitted_handles,
            "preview": block[:80] + "..." if len(block) > 80 else block
        })

    telemetry.silently_skipped_substantive = telemetry.substantive_paragraphs - telemetry.attributed_attempted
    telemetry.stage_latency_seconds = time.perf_counter() - t0_stage
    
    final_text = "\n\n".join(attributed_blocks)
    overall_diff = (strip_citations(draft_markdown) == strip_citations(final_text))
    
    return FullCitationAttributionResult(
        attributed_markdown=final_text,
        overall_diff_passed=overall_diff,
        telemetry=telemetry,
    )

