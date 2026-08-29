"""Structured, span-level post-hoc citation attribution over all
substantive prose paragraphs.

Adapted from:
anthropics/claude-cookbooks/patterns/agents/prompts/citations_agent.md
-- but the LLM never sees or reproduces prose (see "Why structured, not
prose-regeneration" below).

Central Invariant:
The synthesized prose must remain identical; the citation stage may ONLY
insert citations. This is now a STRUCTURAL guarantee, not a diff check the
model can fail: the LLM is given pre-segmented sentence/claim spans (never
the reconstructible paragraph text) and returns ONLY a JSON handle
assignment per span. Citation markers are then inserted deterministically
by this module at the spans' stored character offsets -- the model has no
opportunity to alter a single character of prose, so byte-exact
preservation holds by construction.

Why structured, not prose-regeneration
---------------------------------------
The earlier design asked the LLM to copy the whole paragraph back out with
citation tags inserted, verified byte-exactness with a diff check, and
retried/fell back to uncited-original on mismatch. Real-run diagnosis
(2026-08-28, air-pollution validation corpus) captured a concrete failure:
the model added a stray space after an em-dash ("disease--whereas" ->
"disease-- whereas") while otherwise correctly attributing the paragraph,
tripping the diff check and discarding a fully-correct citation via
fail-closed. Asking a model to verbatim-reproduce hundreds of words of
scientific prose (LaTeX, unicode punctuation, numbers) is an unnecessary
task with a real failure rate; deciding which evidence supports a given
short span is the only task that actually needs the model.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Mapping, Sequence
from langchain_openai import ChatOpenAI
from src.config import get_settings
from src.models.synthesis_schemas import EntailmentStatus
from src.services.claim_verification_policy import fuzzy_verbatim_match
from src.services.nli_checker import NLIChecker, NLIModelUnavailableError, resolve_claims_via_nli
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.prompt import format_evidence_context

#: Bridges fast_v2's string handles ("E001") and claim-span ids ("p0_s1")
#: into the uuid.UUID identifiers the Legacy Tier 1/2 modules are typed
#: against (ClaimVerificationDecision.evidence_ids is Pydantic-validated as
#: list[uuid.UUID]). Deterministic so re-derivation within one batch call
#: always agrees with itself; never persisted or compared across processes.
_TIER12_BRIDGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "litreview.fastv2.tier12-bridge")

#: Above this many evidence units in a batch's scope, Tier 2 (NLI) is skipped
#: for that batch -- every claim x evidence pair is one CPU forward pass
#: (~130-170ms per pair, see models/nli_evidence_benchmark_report.md), so an
#: unscoped/global-fallback batch (potentially 100+ evidence units) could
#: otherwise turn one citation batch into a multi-minute stall. Tier 1
#: (string matching, effectively free) always still runs. Skipping Tier 2
#: never loses coverage -- the claim just falls through to Tier 3 (LLM)
#: exactly as it would with NLI_EVIDENCE_ENABLED=false.
TIER2_MAX_EVIDENCE_PER_BATCH = 20


async def _resolve_tier12_assignments(
    span_texts: Mapping[str, str],
    handle_to_unit: Mapping[str, EvidenceUnit],
    *,
    checker: NLIChecker | None = None,
) -> dict[str, list[str]]:
    """Pre-resolve as many claim spans as possible via Tier 1 (deterministic
    near-verbatim match) then Tier 2 (local NLI cross-encoder) before a batch
    ever reaches the LLM (Tier 3). Only settles a span when Tier 1/2 finds
    clear SUPPORT; anything unresolved or contradicted is left for the LLM,
    which remains the only stage that decides "no citation" here -- Tier 1/2
    exist to skip unnecessary LLM calls, not to veto a span the LLM never saw."""
    if not handle_to_unit:
        return {}

    evidence_uuid_map = {
        uuid.uuid5(_TIER12_BRIDGE_NAMESPACE, f"h:{handle}"): handle
        for handle in handle_to_unit
    }
    evidence_pairs_for_match = [
        (eid, handle_to_unit[handle].text) for eid, handle in evidence_uuid_map.items()
    ]

    resolved: dict[str, list[str]] = {}
    remaining: list[tuple[str, str]] = []
    for claim_id, claim_text in span_texts.items():
        match = fuzzy_verbatim_match(claim_text, evidence_pairs_for_match)
        if match is not None:
            resolved[claim_id] = [evidence_uuid_map[match]]
        else:
            remaining.append((claim_id, claim_text))

    if not remaining or len(evidence_uuid_map) > TIER2_MAX_EVIDENCE_PER_BATCH:
        return resolved

    evidence_for_nli = [
        (eid, handle_to_unit[handle].text, "") for eid, handle in evidence_uuid_map.items()
    ]
    try:
        tier2_decisions = await resolve_claims_via_nli(
            claims_with_evidence=[
                (uuid.uuid5(_TIER12_BRIDGE_NAMESPACE, f"c:{claim_id}"), claim_text, evidence_for_nli)
                for claim_id, claim_text in remaining
            ],
            checker=checker,
        )
    except NLIModelUnavailableError:
        return resolved

    remaining_claim_uuid_map = {
        uuid.uuid5(_TIER12_BRIDGE_NAMESPACE, f"c:{claim_id}"): claim_id for claim_id, _ in remaining
    }
    for claim_uuid, decision in tier2_decisions.items():
        if decision.status == EntailmentStatus.supported:
            claim_id = remaining_claim_uuid_map[claim_uuid]
            resolved[claim_id] = [evidence_uuid_map[eid] for eid in decision.evidence_ids]

    return resolved

STRUCTURED_CITATION_SYSTEM_PROMPT = """You are a meticulous scientific citation agent.
You are given a batch of finalized literature review paragraphs, plus an evidence pack. For each paragraph you are shown its FULL, immutable text as CONTEXT ONLY, and a list of claim/sentence spans within it as your actual attribution targets. You must NEVER reproduce, rewrite, paraphrase, normalize, or output any part of the paragraph prose -- your only job is to decide which evidence handle(s), if any, support each claim span.

Use the full paragraph to understand what an isolated span alone might not make clear: pronoun antecedents, comparison structure, what a "this" or "it" refers to, and how a claim continues or synthesizes a preceding statement. Evidence ownership is still assigned per claim_id, never to the paragraph as a whole.

RULES:
1. FACTUAL/TECHNICAL CLAIM: assign evidence that supports that specific claim's
   factual content. A close paraphrase, restatement, or accurate summary of
   what the evidence says COUNTS as support -- exact wording is never
   required. Evidence that is merely on the same topic, from the same paper,
   or a nearby-but-different result does NOT count.
2. MULTI-PAPER COMPARISON: a claim comparing multiple papers (e.g. "Study A uses X whereas Study B uses Y") needs support for BOTH/ALL sides -- include relevant evidence handles from each paper being compared.
3. SYNTHESIS/INFERENCE: a synthesis claim may cite multiple handles when its conclusion is reasonably grounded in them together. Do not invent an empirical fact during synthesis.
4. DISCOURSE/TRANSITION: a claim with no independently factual content (e.g. "This connection enabled...", "Taken together, these results show...") gets an empty list.
5. UNSUPPORTED CLAIM: if no supplied evidence sufficiently supports a factual claim -- including evidence that is only topically related without supporting the specific claim -- return an empty list for it. An empty list is preferable to a topical citation. This is NOT the same as rule 1's paraphrase case: a claim restating an evidence handle's actual content in different words IS supported by that handle and must NOT be treated as unsupported just because the wording differs.
6. NEIGHBORING CLAIMS: a citation assigned to one claim is never support for a different claim unless that other claim independently receives the same handle. Do not let an unsupported claim borrow a neighbor's citation.
7. Deduplicate: never list the same handle twice for one claim.
8. NEVER invent a handle that is not present in the supplied evidence pack.
9. DO NOT UNDER-CITE: reserve the empty list for claims the evidence pack genuinely does not address at all, not for claims that are merely phrased differently from the source text. If in doubt between "this is a paraphrase of E003" and "this is unsupported," and E003's content genuinely matches the claim's meaning, cite E003.

Return ONLY a JSON object of the exact form:
{"assignments": {"<claim_id>": ["E001", ...], "<claim_id>": [], ...}}
Include exactly one entry per claim_id you were given, across all paragraphs in the batch, in any order. No prose, no commentary, no markdown fences, no other keys."""

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


#: Deterministic sentence/claim boundary: a run of whitespace preceded by
#: sentence-ending punctuation and followed by a capital letter, a LaTeX
#: escape, or a `$` (so we don't split mid-formula on the period inside
#: "e.g." followed by a lowercase continuation, though "et al." followed by
#: a capitalized next sentence is not distinguishable by this heuristic --
#: acceptable: a missed split only means two claims share one span, which
#: is the ALLOWED "same evidence supports adjacent claims" case, never a
#: prose-mutation risk).
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\$])")


def split_paragraph_into_spans(paragraph: str) -> list[tuple[int, int, str]]:
    """Deterministically split into (start, end, text) sentence/claim spans
    covering the paragraph in left-to-right, non-overlapping order. This is
    a lightweight heuristic splitter, not an NLP sentence tokenizer -- it
    exists to give the citation model claim-sized units, never to be shown
    to or reconstructed by the model itself. Whitespace between spans is
    deliberately left unassigned to either span; ``insert_citations_at_spans``
    copies straight from the original string, so any splitter imprecision
    can only affect claim GRANULARITY, never prose byte-exactness."""
    if not paragraph:
        return []
    boundaries = [0]
    for m in _SENTENCE_BOUNDARY.finditer(paragraph):
        boundaries.append(m.start())
        boundaries.append(m.end())
    boundaries.append(len(paragraph))

    spans: list[tuple[int, int, str]] = []
    for i in range(0, len(boundaries) - 1, 2):
        start, end = boundaries[i], boundaries[i + 1]
        text = paragraph[start:end]
        if text.strip():
            spans.append((start, end, text))
    return spans


def insert_citations_at_spans(
    paragraph: str,
    spans: Sequence[tuple[int, int, str]],
    span_handles: Sequence[Sequence[str]],
) -> str:
    """Deterministically construct the cited paragraph by copying
    ``paragraph`` verbatim and inserting `` [E001, ...]`` only right after
    each span's end offset when it has handles. Structurally guarantees the
    prose-invariant: with all-empty handle lists this returns ``paragraph``
    unchanged, character for character."""
    out: list[str] = []
    cursor = 0
    for (start, end, _text), handles in zip(spans, span_handles):
        out.append(paragraph[cursor:end])
        if handles:
            out.append(f" [{', '.join(handles)}]")
        cursor = end
    out.append(paragraph[cursor:])
    return "".join(out)


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
    section_papers_to_compare: Mapping[str, Sequence[str]] | None = None,
) -> set[str] | None:
    """Decide which evidence_ids a batch may cite from, given the sections
    its paragraphs belong to. Returns None (full pack) when scoping isn't
    available or safe to apply -- never returns an empty/under-scoped set
    that would starve a paragraph of evidence it needs.

    Local retrieval, global provenance (see claim_034/Chu audit): a passage
    about a paper that IS listed in this section's own papers_to_compare,
    but that retrieval happened to select for a DIFFERENT section instead,
    is still legitimate evidence for a claim about that paper here -- the
    paper is relevant to this section by the Planner's own outline, the
    passage genuinely exists in the corpus, and Citation Agent's own
    semantic-support check (attribute_paragraph_batch) still has to decide
    per-claim whether it actually supports the specific sentence. This does
    NOT open the full evidence pool: only evidence already selected for
    SOME section (never re-retrieved), and only for papers this section's
    own outline already names as relevant -- an unrelated paper's evidence
    from another section is still excluded exactly as before.
    """
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

    if section_papers_to_compare:
        allowed_papers: set[str] = set()
        for sid in distinct:
            allowed_papers.update(section_papers_to_compare.get(sid) or ())
        if allowed_papers:
            for other_sid, units in section_evidence.items():
                if other_sid in distinct:
                    continue  # already fully included above
                for u in units:
                    if u.title in allowed_papers:
                        scope.add(u.evidence_id)

    return scope


#: How many times a whole batch's structured-assignment call may be retried
#: on a JSON-format failure (NOT a prose-mutation retry -- there is no
#: prose for the model to mutate anymore).
STRUCTURED_CALL_MAX_ATTEMPTS = 2


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
    out_of_scope_handles_rejected: int = 0
    final_bound_citations: int = 0
    uncited_substantive_paragraphs: int = 0
    stage_latency_seconds: float = 0.0
    provider_attempts: int = 0
    total_tokens_used: int = 0
    total_input_tokens_used: int = 0
    number_of_batches: int = 0
    paragraph_details: list[dict] = field(default_factory=list)

    # Failure-TYPE telemetry (section IX): a transport failure must never be
    # indistinguishable from an honest "the model looked and found no
    # support" outcome -- they are counted separately here.
    successful_batches: int = 0
    transport_timeout_batches: int = 0
    transport_http_error_batches: int = 0
    parse_failed_batches: int = 0
    invalid_assignment_entries_rejected: int = 0
    unknown_claim_ids_rejected: int = 0
    semantic_empty_assignments: int = 0
    batch_records: list[dict] = field(default_factory=list)

    # Tier 1/2 pre-filter telemetry (Module 1 integration into fast_v2).
    tier1_2_resolved_claims: int = 0
    llm_calls_skipped_by_tier1_2: int = 0

    def to_dict(self) -> dict:
        latencies = sorted(r["provider_latency_seconds"] for r in self.batch_records if r.get("provider_latency_seconds") is not None)

        def _pct(p: float) -> float | None:
            if not latencies:
                return None
            idx = min(len(latencies) - 1, int(round(p * (len(latencies) - 1))))
            return round(latencies[idx], 2)

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
            "out_of_scope_handles_rejected": self.out_of_scope_handles_rejected,
            "final_bound_citations": self.final_bound_citations,
            "uncited_substantive_paragraphs": self.uncited_substantive_paragraphs,
            "stage_latency_seconds": round(self.stage_latency_seconds, 2),
            "provider_attempts": self.provider_attempts,
            "total_tokens_used": self.total_tokens_used,
            "total_input_tokens_used": self.total_input_tokens_used,
            "number_of_batches": self.number_of_batches,
            "paragraph_details": self.paragraph_details,
            "successful_batches": self.successful_batches,
            "transport_timeout_batches": self.transport_timeout_batches,
            "transport_http_error_batches": self.transport_http_error_batches,
            "parse_failed_batches": self.parse_failed_batches,
            "invalid_assignment_entries_rejected": self.invalid_assignment_entries_rejected,
            "unknown_claim_ids_rejected": self.unknown_claim_ids_rejected,
            "semantic_empty_assignments": self.semantic_empty_assignments,
            "tier1_2_resolved_claims": self.tier1_2_resolved_claims,
            "llm_calls_skipped_by_tier1_2": self.llm_calls_skipped_by_tier1_2,
            "batch_latency_p50_seconds": _pct(0.50),
            "batch_latency_p95_seconds": _pct(0.95),
            "batch_latency_max_seconds": round(latencies[-1], 2) if latencies else None,
            "batch_records": self.batch_records,
        }


@dataclass(frozen=True)
class FullCitationAttributionResult:
    attributed_markdown: str
    overall_diff_passed: bool
    telemetry: CitationCoverageTelemetry


def _parse_structured_assignments(text: str) -> tuple[dict[str, list[str]], int] | tuple[None, int]:
    """Parse {"assignments": {claim_id: [handles...], ...}} from a model
    response. Returns (None, 0) on a top-level malformed shape (PARSE_FAILED
    -- caller retries/fails the whole batch closed). A per-entry malformed
    shape (e.g. handles not a list) is dropped individually and counted as
    the second return value (invalid_assignment_entries), NOT a batch-level
    failure. Never touches/returns prose."""
    clean_text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    clean_text = re.sub(r"\n?```$", "", clean_text)
    try:
        parsed = json.loads(clean_text)
        assignments = parsed["assignments"]
        if not isinstance(assignments, dict):
            return None, 0
    except (json.JSONDecodeError, KeyError, TypeError):
        return None, 0

    cleaned: dict[str, list[str]] = {}
    invalid_entries = 0
    for claim_id, handles in assignments.items():
        if not isinstance(handles, list):
            invalid_entries += 1
            continue
        # Dedupe while preserving order (rule 7: never list a handle twice).
        cleaned[str(claim_id)] = list(dict.fromkeys(str(h).strip() for h in handles if str(h).strip()))
    return cleaned, invalid_entries


#: Fixed response/read timeout for one Citation batch call. NOT adaptive.
#: Real-run evidence (2026-08-28, air-pollution corpus, 35s timeout): every
#: one of 11 failures was TimeoutError, and GoRouter's own usage log showed
#: those exact requests completing (and being billed) at 34-48s -- the
#: provider finished the work after the client had already given up and
#: discarded/paid for it. 120s gives ~2.5x margin over the worst observed
#: completion (48s) while staying bounded; adaptive per-span timeout is
#: deliberately deferred (no evidence yet that latency scales predictably
#: with span count).
CITATION_BATCH_TIMEOUT_SECONDS = 120.0

TRANSPORT_TIMEOUT = "transport_timeout"
TRANSPORT_HTTP_ERROR = "transport_http_error"
PARSE_FAILED = "parse_failed"


async def attribute_paragraph_batch(
    llm: ChatOpenAI,
    batch_items: list[tuple[int, str]],  # (block_idx, paragraph_text)
    context_text: str,
    available_handles: set[str],
    sem: asyncio.Semaphore,
    handle_to_unit: Mapping[str, EvidenceUnit] | None = None,
    section_id: str | None = None,
    batch_id: int = 0,
    nli_checker_override: NLIChecker | None = None,
) -> tuple[dict[int, tuple[str, str, list[str]]], int, int, int, dict]:
    """Structured claim-level citation assignment for a batch of paragraphs.

    The LLM never sees or reproduces paragraph prose. Each paragraph is sent
    as FULL_PARAGRAPH (reasoning context only -- pronouns, comparison
    structure, cross-sentence synthesis) plus its deterministically split
    claim spans (the actual attribution targets, see
    ``split_paragraph_into_spans``). The model returns ONLY
    ``{"assignments": {claim_id: [handles...]}}``; citation markers are then
    inserted at the spans' stored character offsets
    (``insert_citations_at_spans``) -- prose byte-exactness is therefore a
    structural property of this function, not a check the model can fail.

    Returns:
        results_map: {block_idx: (attributed_text, status, emitted_handles)}
        provider_attempts: int
        output_tokens_used: int
        input_tokens_used: int
        batch_record: dict (section IX/XVIII telemetry -- failure type,
            latency, counts; see keys below)
    """
    attempts = 1
    output_tokens = 0
    input_tokens = 0
    invalid_entries_total = 0

    paragraph_spans: dict[int, list[tuple[int, int, str]]] = {}
    span_texts: dict[str, str] = {}
    total_claim_count = 0
    for local_id, (b_idx, p_text) in enumerate(batch_items):
        spans = split_paragraph_into_spans(p_text)
        paragraph_spans[b_idx] = spans
        total_claim_count += len(spans)
        for i, (_start, _end, text) in enumerate(spans):
            span_texts[f"p{local_id}_s{i}"] = text.strip()

    settings = get_settings()
    tier12_assignments: dict[str, list[str]] = {}
    if settings.nli_evidence_enabled:
        tier12_assignments = await _resolve_tier12_assignments(
            span_texts, handle_to_unit or {}, checker=nli_checker_override
        )
    tier1_or_2_resolved_count = len(tier12_assignments)

    paragraph_payload: list[dict] = []
    for local_id, (b_idx, p_text) in enumerate(batch_items):
        spans = paragraph_spans[b_idx]
        paragraph_payload.append({
            "paragraph_id": f"p{local_id}",
            "full_paragraph": p_text,
            "claim_spans": [
                {"claim_id": f"p{local_id}_s{i}", "text": text.strip(), "char_start": start, "char_end": end}
                for i, (start, end, text) in enumerate(spans)
                if f"p{local_id}_s{i}" not in tier12_assignments
            ],
        })

    def _build_human_prompt(payload: list[dict]) -> str:
        return f"""Supplied Evidence Pack:
{context_text}

Paragraphs (JSON array of {{paragraph_id, full_paragraph (CONTEXT ONLY, never to be reproduced), claim_spans}}):
{json.dumps(payload, ensure_ascii=False)}

Return ONLY the JSON assignments object described in your instructions, with exactly one entry per claim_id across all paragraphs above."""

    async def _call(payload: list[dict], extra_system: str = "") -> tuple[dict[str, list[str]] | None, int, int, str | None]:
        started = time.perf_counter()
        try:
            resp = await asyncio.wait_for(
                llm.ainvoke([
                    ("system", STRUCTURED_CITATION_SYSTEM_PROMPT + extra_system),
                    ("human", _build_human_prompt(payload)),
                ]),
                timeout=CITATION_BATCH_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, TimeoutError):
            elapsed = time.perf_counter() - started
            print(f"[Citation Agent] batch {batch_id} call TIMEOUT after {elapsed:.1f}s (limit={CITATION_BATCH_TIMEOUT_SECONDS}s)", flush=True)
            return None, 0, 0, TRANSPORT_TIMEOUT
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            print(
                f"[Citation Agent] batch {batch_id} call failed: {type(exc).__name__}"
                f"{f' (HTTP {status_code})' if status_code else ''}: {exc}",
                flush=True,
            )
            return None, 0, 0, TRANSPORT_HTTP_ERROR
        usage = getattr(resp, "usage_metadata", {}) or {}
        content = str(resp.content)
        assignments, n_invalid = _parse_structured_assignments(content)
        nonlocal invalid_entries_total
        invalid_entries_total += n_invalid
        if assignments is None:
            print(
                f"[Citation Agent] batch {batch_id} call returned HTTP 200 but content did not "
                f"parse as {{'assignments': {{...}}}} JSON (len={len(content)}): {content[:300]!r}",
                flush=True,
            )
            return None, usage.get("output_tokens", 0), usage.get("input_tokens", 0), PARSE_FAILED
        return assignments, usage.get("output_tokens", 0), usage.get("input_tokens", 0), None

    all_claims_resolved_by_tier12 = total_claim_count > 0 and tier1_or_2_resolved_count == total_claim_count
    t0_batch = time.perf_counter()
    if all_claims_resolved_by_tier12:
        # Every claim in this batch was already settled by Tier 1/2 -- no
        # prose left for the LLM to attribute, so skip the call entirely.
        assignments, failure_type = {}, None
    else:
        async with sem:
            assignments, out_tok, in_tok, failure_type = await _call(paragraph_payload)
            output_tokens += out_tok
            input_tokens += in_tok

            if assignments is None and STRUCTURED_CALL_MAX_ATTEMPTS > 1:
                attempts += 1
                assignments, out_tok, in_tok, failure_type = await _call(
                    paragraph_payload,
                    "\n\nYour previous response was not valid JSON in the required "
                    "{\"assignments\": {...}} shape. Return ONLY that JSON object, nothing else.",
                )
                output_tokens += out_tok
                input_tokens += in_tok
    batch_latency = time.perf_counter() - t0_batch

    # A batch-level failure (transport or parse) after retries fails CLOSED
    # for every paragraph in the batch: every claim gets zero handles, which
    # insert_citations_at_spans renders as the original paragraph text
    # completely unchanged -- safe (uncited, never mutated), never hidden
    # behind a stray citation, and never silently counted as "the model
    # judged this unsupported" (that is semantic_empty_assignment, a
    # different, non-failure outcome -- see batch_record below).
    status = "passed_first_attempt" if assignments is not None and attempts == 1 else (
        "passed_after_retry" if assignments is not None else "failed_closed_kept_uncited"
    )
    batch_succeeded = assignments is not None
    if assignments is None:
        assignments = {}

    known_claim_ids = {c["claim_id"] for p in paragraph_payload for c in p["claim_spans"]}
    unknown_claim_ids = [cid for cid in assignments if cid not in known_claim_ids]

    empty_assignment_count = 0
    results_map: dict[int, tuple[str, str, list[str]]] = {}
    for local_id, (b_idx, p_text) in enumerate(batch_items):
        spans = paragraph_spans[b_idx]
        handle_lists: list[list[str]] = []
        emitted_tags: list[str] = []
        for span_index in range(len(spans)):
            claim_id = f"p{local_id}_s{span_index}"
            if claim_id in tier12_assignments:
                handles = tier12_assignments[claim_id]
            else:
                handles = assignments.get(claim_id, [])  # missing claim_id defaults explicitly to []
            handle_lists.append(handles)
            if handles:
                emitted_tags.append(f"[{', '.join(handles)}]")
            elif batch_succeeded:
                empty_assignment_count += 1  # a genuine model judgment of "no support", not a failure
                # Temporary diagnostic (2026-08-30): coverage stayed low after
                # loosening the citation prompt (rule 1/5/9). Log exactly which
                # spans the model judged unsupported so this can be read from
                # production logs and classified as genuine discourse/inference
                # (expected) vs. a real factual claim being under-cited (bug),
                # instead of guessing from a UI screenshot.
                print(f"[Citation Agent] EMPTY assignment for {claim_id}: {span_texts.get(claim_id, '')[:180]!r}", flush=True)
        attr_text = insert_citations_at_spans(p_text, spans, handle_lists)
        results_map[b_idx] = (attr_text, status, emitted_tags)

    batch_record = {
        "batch_id": batch_id,
        "section_id": section_id,
        "paragraph_ids": [b_idx for b_idx, _ in batch_items],
        "paragraph_count": len(batch_items),
        "claim_count": total_claim_count,
        "evidence_count": len(available_handles),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "attempt_number": attempts,
        "provider_latency_seconds": round(batch_latency, 2),
        "result_status": status,
        "failure_type": failure_type if not batch_succeeded else None,
        "timeout_flag": failure_type == TRANSPORT_TIMEOUT,
        "invalid_assignment_entries": invalid_entries_total,
        "unknown_claim_ids_rejected": len(unknown_claim_ids),
        "semantic_empty_assignments": empty_assignment_count,
        "tier1_2_resolved_claims": tier1_or_2_resolved_count,
        "llm_call_skipped": all_claims_resolved_by_tier12,
    }

    return results_map, attempts, output_tokens, input_tokens, batch_record


async def attribute_all_prose_paragraphs(
    llm: ChatOpenAI,
    draft_markdown: str,
    evidence: Sequence[EvidenceUnit],
    batch_size: int = 3,
    concurrency: int = 5,
    section_evidence: Mapping[str, Sequence[EvidenceUnit]] | None = None,
    sections: Sequence[tuple[str, str]] | None = None,
    section_papers_to_compare: Mapping[str, Sequence[str]] | None = None,
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
    handle_by_evidence_id, unit_by_evidence_id = _global_handle_index(evidence)
    handle_to_unit_full = {handle: unit_by_evidence_id[eid] for eid, handle in handle_by_evidence_id.items()}

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

    # Chunk substantive paragraphs into batches. When section scoping is
    # active, group by section FIRST so a batch never straddles a section
    # boundary -- a plain contiguous chunker would routinely mix 2+ sections
    # into one batch once batch_size approaches a section's paragraph count,
    # which forces resolve_batch_evidence_scope to fall back to the full
    # pack and defeats the whole point of scoping. Without section info this
    # degrades to the original single contiguous-chunk behavior exactly.
    batches: list[list[tuple[int, str]]] = []
    if paragraph_section_ids:
        groups: list[list[tuple[int, str]]] = []
        current_group: list[tuple[int, str]] = []
        current_section: str | None | object = object()  # sentinel, never equal to a real section id
        for item in substantive_items:
            b_idx, _ = item
            sid = paragraph_section_ids.get(b_idx)
            if sid != current_section:
                if current_group:
                    groups.append(current_group)
                current_group = []
                current_section = sid
            current_group.append(item)
        if current_group:
            groups.append(current_group)
        for group in groups:
            for i in range(0, len(group), batch_size):
                batches.append(group[i : i + batch_size])
    else:
        for i in range(0, len(substantive_items), batch_size):
            batches.append(substantive_items[i : i + batch_size])

    telemetry.number_of_batches = len(batches)
    print(f"  Dispatching {len(substantive_items)} substantive paragraphs in {len(batches)} batches (BatchSize={batch_size}, Concurrency={concurrency})...", flush=True)

    # Per-paragraph evidence scope, tracked so validation below rejects a
    # handle the model was never shown even if it happens to be globally
    # valid -- scoping must not silently widen what counts as "valid".
    paragraph_scope_handles: dict[int, set[str]] = {}
    batch_contexts: list[str] = []
    batch_handle_to_units: list[dict[str, EvidenceUnit]] = []
    for batch in batches:
        batch_section_ids = [paragraph_section_ids.get(b_idx) for b_idx, _ in batch]
        scope_ids = resolve_batch_evidence_scope(batch_section_ids, section_evidence, section_papers_to_compare)
        if scope_ids is None:
            batch_context_text, batch_handles = full_context_text, global_available_handles
        else:
            batch_context_text, batch_handles = format_scoped_evidence_context(evidence, scope_ids)
        batch_contexts.append(batch_context_text)
        batch_handle_to_units.append({h: handle_to_unit_full[h] for h in batch_handles})
        for b_idx, _ in batch:
            paragraph_scope_handles[b_idx] = batch_handles

    batch_tasks = [
        attribute_paragraph_batch(
            llm=llm,
            batch_items=b,
            context_text=ctx,
            available_handles=paragraph_scope_handles[b[0][0]],
            sem=sem,
            handle_to_unit=batch_handle_to_units[batch_idx],
            section_id=paragraph_section_ids.get(b[0][0]) if paragraph_section_ids else None,
            batch_id=batch_idx,
        )
        for batch_idx, (b, ctx) in enumerate(zip(batches, batch_contexts))
    ]

    batch_results = await asyncio.gather(*batch_tasks)

    attributed_blocks = list(raw_blocks)
    merged_results: dict[int, tuple[str, str, list[str]]] = {}

    for b_res, attempts, out_tok, in_tok, batch_record in batch_results:
        telemetry.provider_attempts += attempts
        telemetry.total_tokens_used += out_tok
        telemetry.total_input_tokens_used += in_tok
        telemetry.batch_records.append(batch_record)
        telemetry.invalid_assignment_entries_rejected += batch_record["invalid_assignment_entries"]
        telemetry.unknown_claim_ids_rejected += batch_record["unknown_claim_ids_rejected"]
        telemetry.semantic_empty_assignments += batch_record["semantic_empty_assignments"]
        telemetry.tier1_2_resolved_claims += batch_record["tier1_2_resolved_claims"]
        if batch_record["llm_call_skipped"]:
            telemetry.llm_calls_skipped_by_tier1_2 += 1
        if batch_record["failure_type"] is None:
            telemetry.successful_batches += 1
        elif batch_record["failure_type"] == TRANSPORT_TIMEOUT:
            telemetry.transport_timeout_batches += 1
        elif batch_record["failure_type"] == TRANSPORT_HTTP_ERROR:
            telemetry.transport_http_error_batches += 1
        elif batch_record["failure_type"] == PARSE_FAILED:
            telemetry.parse_failed_batches += 1
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
                elif h in global_available_handles:
                    # Genuinely exists in the evidence pool, but wasn't in
                    # THIS paragraph's scoped context -- the model was never
                    # shown it. Tracked separately from a truly-invalid
                    # (nonexistent) handle so telemetry doesn't silently
                    # conflate "hallucinated handle" with "scope leak".
                    telemetry.out_of_scope_handles_rejected += 1
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

