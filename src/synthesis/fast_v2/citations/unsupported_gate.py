"""Deterministic unsupported-claim gate, run after the structured Citation
Agent and before the finalizer.

Purpose: make the system KNOW, with certainty, which factual/technical
claim spans ended up with zero evidence handles after citation attribution
(the "Chu scenario": a paragraph writes a specific, checkable claim about a
paper's limitation, but the evidence for it lived in a different section's
context and was never available to the Citation Agent for THIS paragraph).
This module does not delete, rewrite, or re-attribute anything, and makes
no LLM call -- it only classifies and reports.

How claim-level handles are recovered without changing the Citation Agent
--------------------------------------------------------------------------
``attribute_paragraph_batch`` (anthropic_citations.py) computes a per-span
handle list internally but only persists the flat rendered text
(``insert_citations_at_spans`` output) plus a flat tag list -- the
per-span mapping itself isn't threaded through to callers. Rather than
touch that function's return contract (out of scope -- "Citation Agent
semantics" must not change), this module recovers the exact same per-span
mapping by inverting ``insert_citations_at_spans`` deterministically:
walk the pre-citation paragraph's spans (the SAME ``split_paragraph_into_spans``
call the Citation Agent used) in lock-step with the post-citation
paragraph, using the identical cursor discipline the insertion function
used to build it. Because insertion is a pure, deterministic function of
(spans, handles), this inversion is exact -- not a heuristic re-parse --
and self-checks the byte-invariant on every span (raises if prose was
touched, which should be structurally impossible but is worth catching).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.synthesis.fast_v2.citations.anthropic_citations import (
    is_substantive_prose,
    split_paragraph_into_spans,
)

FACTUAL_TECHNICAL = "FACTUAL_TECHNICAL"
DISCOURSE_TRANSITION = "DISCOURSE_TRANSITION"

GROUNDED = "GROUNDED"
UNSUPPORTED = "UNSUPPORTED"
NON_FACTUAL_UNCITED_OK = "NON_FACTUAL_UNCITED_OK"

CLEAN = "CLEAN"
PASS_WITH_ISSUES = "PASS_WITH_ISSUES"

#: Deterministic discourse/transition opener heuristic. A span matching this
#: (or under 6 words) is framing/synthesis prose, not a checkable factual or
#: technical claim, so an empty handle list there is an expected outcome,
#: never a gap.
_DISCOURSE_START = re.compile(
    r"^(this section|in summary|in conclusion|building upon|as discussed|"
    r"having established|we now turn|the remainder of|taken together|"
    r"at the same time|the corpus is candid|overall|in sum|in short|"
    r"notably|finally,)",
    re.IGNORECASE,
)

_CITATION_TAG_AT_CURSOR = re.compile(r"^ \[([^\]]+)\]")


class ProseInvariantViolation(RuntimeError):
    """The post-citation paragraph's prose does not match the pre-citation
    paragraph outside of inserted citation tags -- should be structurally
    impossible given insert_citations_at_spans, so this indicates the two
    paragraphs passed in do not actually correspond to each other."""


def classify_span_type(text: str) -> str:
    """Deterministic, non-LLM claim-type classification. A span is
    DISCOURSE_TRANSITION if it opens with a known framing/synthesis phrase
    or is too short to carry a checkable claim; otherwise FACTUAL_TECHNICAL."""
    stripped = text.strip()
    if _DISCOURSE_START.match(stripped) or len(stripped.split()) < 6:
        return DISCOURSE_TRANSITION
    return FACTUAL_TECHNICAL


def extract_span_citations(pre_citation_paragraph: str, post_citation_paragraph: str) -> list[list[str]]:
    """Exact inverse of ``insert_citations_at_spans``: recover the per-span
    handle list by walking both paragraphs in the same left-to-right,
    cursor-based order the insertion function used to build the post-citation
    text. Raises ProseInvariantViolation if a span's prose prefix doesn't
    match verbatim, which would mean the two paragraphs don't correspond."""
    spans = split_paragraph_into_spans(pre_citation_paragraph)
    cursor_pre = 0
    cursor_post = 0
    result: list[list[str]] = []
    for start, end, _text in spans:
        expected_prefix = pre_citation_paragraph[cursor_pre:end]
        actual_prefix = post_citation_paragraph[cursor_post:cursor_post + len(expected_prefix)]
        if actual_prefix != expected_prefix:
            raise ProseInvariantViolation(
                f"span prefix mismatch at pre-citation offset {cursor_pre}:{end} "
                f"-- expected {expected_prefix!r}, got {actual_prefix!r}"
            )
        cursor_post += len(expected_prefix)
        cursor_pre = end

        m = _CITATION_TAG_AT_CURSOR.match(post_citation_paragraph[cursor_post:])
        if m:
            handles = [h.strip() for h in m.group(1).split(",") if h.strip()]
            cursor_post += m.end()
        else:
            handles = []
        result.append(handles)
    return result


@dataclass
class ClaimGateRecord:
    claim_id: str
    section_id: str | None
    paragraph_id: int
    text: str
    type: str
    evidence: list[str]
    status: str

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "section_id": self.section_id,
            "paragraph_id": self.paragraph_id,
            "text": self.text,
            "type": self.type,
            "evidence": self.evidence,
            "status": self.status,
        }


@dataclass
class UnsupportedClaimGateResult:
    total_claim_spans: int = 0
    grounded_factual_claims: int = 0
    unsupported_factual_claims: int = 0
    nonfactual_uncited_claims: int = 0
    records: list[ClaimGateRecord] = field(default_factory=list)

    @property
    def unsupported_claim_ids(self) -> list[str]:
        return [r.claim_id for r in self.records if r.status == UNSUPPORTED]

    @property
    def quality_status(self) -> str:
        return CLEAN if self.unsupported_factual_claims == 0 else PASS_WITH_ISSUES

    def to_dict(self) -> dict:
        return {
            "total_claim_spans": self.total_claim_spans,
            "grounded_factual_claims": self.grounded_factual_claims,
            "unsupported_factual_claims": self.unsupported_factual_claims,
            "nonfactual_uncited_claims": self.nonfactual_uncited_claims,
            "unsupported_claim_ids": self.unsupported_claim_ids,
            "quality_status": self.quality_status,
            "records": [r.to_dict() for r in self.records],
        }


def evaluate_unsupported_claims(
    pre_citation_markdown: str,
    post_citation_markdown: str,
    paragraph_section_ids: dict[int, str | None] | None = None,
) -> UnsupportedClaimGateResult:
    """Deterministic gate: for every claim span in every substantive
    paragraph, classify factual/technical vs discourse and grounded vs
    unsupported. Does not modify prose. No LLM call.

    ``pre_citation_markdown`` / ``post_citation_markdown`` must be the same
    document split on ``"\\n\\n"`` block boundaries before and after the
    Citation Agent ran (i.e. the Writer draft and the final attributed
    markdown) -- the same pairing already produced and persisted by every
    run (``writer_output_clean.md`` and ``final_review_after_citations.md``).
    """
    pre_blocks = pre_citation_markdown.split("\n\n")
    post_blocks = post_citation_markdown.split("\n\n")

    result = UnsupportedClaimGateResult()
    for para_idx, (pre_block, post_block) in enumerate(zip(pre_blocks, post_blocks)):
        if not is_substantive_prose(pre_block):
            continue
        spans = split_paragraph_into_spans(pre_block)
        span_handles = extract_span_citations(pre_block, post_block)
        section_id = paragraph_section_ids.get(para_idx) if paragraph_section_ids else None

        for span_index, ((_start, _end, text), handles) in enumerate(zip(spans, span_handles)):
            claim_type = classify_span_type(text)
            if claim_type == FACTUAL_TECHNICAL:
                status = GROUNDED if handles else UNSUPPORTED
            else:
                status = NON_FACTUAL_UNCITED_OK

            result.total_claim_spans += 1
            if status == GROUNDED:
                result.grounded_factual_claims += 1
            elif status == UNSUPPORTED:
                result.unsupported_factual_claims += 1
            else:
                result.nonfactual_uncited_claims += 1

            result.records.append(ClaimGateRecord(
                claim_id=f"p{para_idx}_s{span_index}",
                section_id=section_id,
                paragraph_id=para_idx,
                text=text.strip(),
                type=claim_type,
                evidence=handles,
                status=status,
            ))

    return result
