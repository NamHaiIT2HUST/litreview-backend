"""Targeted, structurally-guarded repair for VERBATIM_RISK claim spans
flagged by ``verbatim_gate.py``.

Scope, by design (not negotiable via prompting):
  - Touches ONLY the flagged span's own character range inside its own
    paragraph. Every other character of the paragraph -- and every other
    paragraph in the document -- is copied through byte-identical.
  - The LLM is given the flagged span's text, the phrase it copies from the
    source, and the source text for MEANING reference only; it returns
    ONLY a replacement string for that span. It never sees or touches
    surrounding prose it could accidentally rewrite.
  - Citation handles are NOT re-derived. The paragraph's existing
    ``extract_span_citations`` handle assignment is carried over unchanged
    onto the repaired spans by position -- this is what "no Citation Agent
    rerun" means concretely here.
  - Numeric/statistical content in the original span must reappear verbatim
    in the replacement (checked deterministically, not trusted from the
    model) or the repair for that span is rejected.
  - After substitution, the paragraph's claim-span COUNT must stay
    identical (checked via the same deterministic splitter used
    everywhere else) or the whole paragraph's repair is rejected --
    otherwise the carried-over handle assignment could attach to the wrong
    span.
  - After a successful substitution, the verbatim gate is re-run on the new
    span text; if it is STILL flagged, the substitution is reverted and the
    claim is reported unresolved rather than accepted on faith.

One LLM call per paragraph that has 1+ flagged spans (never one call per
span, and never a whole-document rewrite). No retry loop -- a rejected
repair is reported, not retried, per the "no repeated tuning" scope of this
task.
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from src.synthesis.fast_v2.citations.anthropic_citations import (
    insert_citations_at_spans,
    is_substantive_prose,
    split_paragraph_into_spans,
)
from src.synthesis.fast_v2.citations.unsupported_gate import extract_span_citations
from src.synthesis.fast_v2.citations.verbatim_gate import (
    MIN_RUN_WORDS,
    VERBATIM_RISK,
    VerbatimGateRecord,
    _is_numeric_run,
    _longest_common_run,
    _tokenize,
)

REPAIR_TIMEOUT_SECONDS = 60.0

REPAIR_SYSTEM_PROMPT = """You paraphrase individual sentences that were flagged as copying their source text too closely, one small batch at a time.

You will receive a JSON array of flagged claims, each with:
- claim_id: identifier, echo it back exactly
- flagged_text: the sentence as currently written (this is what you must rewrite)
- matched_phrase: the exact wording it shares with the source -- your rewrite must NOT reuse this phrase or close variants of it
- source_text: the evidence passage it cites, for verifying you preserve the same meaning -- do not copy wording from this either

Rules, all mandatory:
1. Preserve the exact factual meaning of flagged_text. Do not add, remove, or change any fact.
2. Any number, percentage, confidence interval, statistical value, or unit (e.g. "1.05", "95% CI", "PM2.5") in flagged_text MUST appear character-for-character identical in your rewrite. Never paraphrase numbers.
3. Do not reuse matched_phrase or near-synonyms of it in the same word order.
4. Keep roughly the same length and register (formal academic prose).
5. Do not merge with or reference other sentences -- rewrite ONLY the given flagged_text as a self-contained replacement for it.
6. Do not insert citation markers, brackets, or handles of any kind.

Return ONLY a JSON object: {"repairs": {claim_id: "rewritten sentence", ...}} with exactly one entry per claim_id given. No other text."""

_DIGIT_GROUP_RE = re.compile(r"\d[\d.,]*\d|\d+")


def _extract_digit_groups(text: str) -> list[str]:
    return _DIGIT_GROUP_RE.findall(text)


def _numeric_content_preserved(original: str, replacement: str) -> bool:
    for group in _extract_digit_groups(original):
        if group not in replacement:
            return False
    return True


def _length_is_sane(original: str, replacement: str) -> bool:
    orig_len = len(original.split())
    new_len = len(replacement.split())
    if orig_len == 0:
        return False
    ratio = new_len / orig_len
    return 0.4 <= ratio <= 2.5


@dataclass
class RepairOutcome:
    claim_id: str
    paragraph_id: int
    original_text: str
    repaired_text: str | None
    status: str  # "REPAIRED" | "UNSAFE_NUMERIC_CHANGED" | "UNSAFE_LENGTH" | \
                 # "UNSAFE_STILL_VERBATIM" | "UNSAFE_SPAN_COUNT_MISMATCH" | \
                 # "UNSAFE_NO_MODEL_RESPONSE" | "TRANSPORT_FAILED"
    remaining_run_words: int | None = None

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "paragraph_id": self.paragraph_id,
            "original_text": self.original_text,
            "repaired_text": self.repaired_text,
            "status": self.status,
            "remaining_run_words": self.remaining_run_words,
        }


@dataclass
class RepairResult:
    repaired_markdown: str
    outcomes: list[RepairOutcome] = field(default_factory=list)

    @property
    def repaired_count(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "REPAIRED")

    @property
    def unresolved_claim_ids(self) -> list[str]:
        return [o.claim_id for o in self.outcomes if o.status != "REPAIRED"]

    def to_dict(self) -> dict:
        return {
            "repaired_count": self.repaired_count,
            "unresolved_claim_ids": self.unresolved_claim_ids,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }


def _parse_repairs(content: str) -> dict[str, str] | None:
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            data = json.loads(content[start:end + 1])
        except (json.JSONDecodeError, TypeError):
            return None
    repairs = data.get("repairs") if isinstance(data, dict) else None
    if not isinstance(repairs, dict):
        return None
    return {str(k): str(v) for k, v in repairs.items() if isinstance(v, str) and v.strip()}


async def _call_repair_llm(llm, batch: list[dict]) -> dict[str, str] | None:
    human_prompt = "Flagged claims:\n" + json.dumps(batch, ensure_ascii=False) + \
        "\n\nReturn ONLY the JSON object described in your instructions."
    try:
        resp = await asyncio.wait_for(
            llm.ainvoke([
                ("system", REPAIR_SYSTEM_PROMPT),
                ("human", human_prompt),
            ]),
            timeout=REPAIR_TIMEOUT_SECONDS,
        )
    except Exception:
        return None
    return _parse_repairs(str(resp.content))


async def repair_verbatim_claims(
    llm,
    pre_citation_markdown: str,
    post_citation_markdown: str,
    flagged_records: Sequence[VerbatimGateRecord],
    handle_to_evidence_text: Mapping[str, str],
) -> RepairResult:
    """Repair only the flagged VERBATIM_RISK spans, leaving every other
    character of the document untouched. Returns the repaired markdown
    (citations re-inserted at the same positions with the same handles)
    plus a per-claim outcome report -- including claims that could NOT be
    safely repaired, which are left as their original text and reported,
    never silently dropped or force-applied.
    """
    pre_blocks = pre_citation_markdown.split("\n\n")
    post_blocks = post_citation_markdown.split("\n\n")

    flagged_by_paragraph: dict[int, list[VerbatimGateRecord]] = {}
    for rec in flagged_records:
        if rec.status != VERBATIM_RISK:
            continue
        flagged_by_paragraph.setdefault(rec.paragraph_id, []).append(rec)

    outcomes: list[RepairOutcome] = []
    new_pre_blocks = list(pre_blocks)
    new_post_blocks = list(post_blocks)

    for para_idx, records in flagged_by_paragraph.items():
        pre_block = pre_blocks[para_idx]
        post_block = post_blocks[para_idx]
        if not is_substantive_prose(pre_block):
            continue

        spans = split_paragraph_into_spans(pre_block)
        span_handles = extract_span_citations(pre_block, post_block)
        span_index_by_claim_id = {f"p{para_idx}_s{i}": i for i in range(len(spans))}

        batch_payload = []
        for rec in records:
            idx = span_index_by_claim_id.get(rec.claim_id)
            if idx is None:
                continue
            batch_payload.append({
                "claim_id": rec.claim_id,
                "flagged_text": spans[idx][2].strip(),
                "matched_phrase": rec.matched_phrase,
                "source_text": handle_to_evidence_text.get(rec.handle or "", "")[:1200],
            })
        if not batch_payload:
            continue

        repairs = await _call_repair_llm(llm, batch_payload)
        if repairs is None:
            for rec in records:
                outcomes.append(RepairOutcome(rec.claim_id, para_idx, rec.text, None, "TRANSPORT_FAILED"))
            continue

        # Build the candidate new paragraph by substituting only the
        # accepted spans' text; every other span's slice is copied verbatim.
        candidate_pieces: list[str] = []
        span_accept: dict[int, tuple[str, RepairOutcome]] = {}
        for rec in records:
            idx = span_index_by_claim_id.get(rec.claim_id)
            if idx is None:
                continue
            original_text = spans[idx][2]
            replacement = repairs.get(rec.claim_id)
            if replacement is None or not replacement.strip():
                outcomes.append(RepairOutcome(rec.claim_id, para_idx, original_text.strip(), None, "UNSAFE_NO_MODEL_RESPONSE"))
                continue
            if not _numeric_content_preserved(original_text, replacement):
                outcomes.append(RepairOutcome(rec.claim_id, para_idx, original_text.strip(), None, "UNSAFE_NUMERIC_CHANGED"))
                continue
            if not _length_is_sane(original_text, replacement):
                outcomes.append(RepairOutcome(rec.claim_id, para_idx, original_text.strip(), None, "UNSAFE_LENGTH"))
                continue
            # Re-run the verbatim check against EVERY handle actually cited
            # on this span, not just the single worst-offender handle
            # verbatim_gate originally reported -- a span can cite more than
            # one paper, and a paraphrase aimed at one citation's wording
            # can coincidentally still overlap a DIFFERENT citation's
            # source text (real case found in the frozen-artifact repair
            # run: a span citing both E007 and E008 was checked only
            # against E008, while the accepted rewrite still ran 8 words
            # verbatim against E007).
            replacement_words = _tokenize(replacement)
            worst_run, worst_phrase = 0, []
            for h in span_handles[idx]:
                src_text = handle_to_evidence_text.get(h, "")
                if not src_text:
                    continue
                run, phrase = _longest_common_run(replacement_words, _tokenize(src_text))
                if run > worst_run:
                    worst_run, worst_phrase = run, phrase
            if worst_run >= MIN_RUN_WORDS and not _is_numeric_run(worst_phrase):
                outcomes.append(RepairOutcome(rec.claim_id, para_idx, original_text.strip(), None, "UNSAFE_STILL_VERBATIM", remaining_run_words=worst_run))
                continue
            span_accept[idx] = (replacement.strip(), RepairOutcome(rec.claim_id, para_idx, original_text.strip(), replacement.strip(), "REPAIRED"))

        if not span_accept:
            continue  # nothing safely repairable in this paragraph -- leave it untouched

        cursor = 0
        for i, (start, end, text) in enumerate(spans):
            if i in span_accept:
                candidate_pieces.append(pre_block[cursor:start])
                candidate_pieces.append(span_accept[i][0])
            else:
                candidate_pieces.append(pre_block[cursor:end])
            cursor = end
        candidate_pieces.append(pre_block[cursor:])
        new_pre_block = "".join(candidate_pieces)

        # Span-count invariant: if the repair changed how many claim spans
        # the paragraph splits into, the carried-over handle assignment
        # (by position) can no longer be trusted to line up -- reject the
        # WHOLE paragraph's repair rather than risk mis-attributing a
        # citation to the wrong sentence.
        new_spans = split_paragraph_into_spans(new_pre_block)
        if len(new_spans) != len(spans):
            for _idx, (_txt, outcome) in span_accept.items():
                outcomes.append(RepairOutcome(outcome.claim_id, para_idx, outcome.original_text, None, "UNSAFE_SPAN_COUNT_MISMATCH"))
            continue

        new_post_block = insert_citations_at_spans(new_pre_block, new_spans, span_handles)
        new_pre_blocks[para_idx] = new_pre_block
        new_post_blocks[para_idx] = new_post_block
        outcomes.extend(outcome for _txt, outcome in span_accept.values())

    return RepairResult(
        repaired_markdown="\n\n".join(new_post_blocks),
        outcomes=outcomes,
    )
