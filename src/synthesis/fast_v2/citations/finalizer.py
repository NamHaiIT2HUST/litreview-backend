"""Deterministic P-165 provenance/citation finalizer for fast_v2.

**P-165 is the citation authority.** The generator's own bracket numbers are a
prompt-local temporary namespace, and OpenScholar has a known history of
citation-namespace failures and misattribution. They are therefore treated as
*untrusted input*: every native index is resolved back through the evidence
bank, and any index that does not resolve is discarded and reported, never
published.

Final provenance chain::

    native index -> EvidenceUnit -> evidence_id -> paper/page/source offsets

Relationship to the Legacy finalizer
------------------------------------
``SynthesisService.finalize_review`` remains the authority for the Legacy
path and is untouched. It cannot be reused directly here because it resolves
citations by querying ``SynthesisClaim`` / ``ClaimEvidenceLink`` /
``EvidenceRecord`` rows, and fast_v2 produces no ``EvidenceRecord``
(``created_from_attempt_id`` is NOT NULL, so an EvidenceRecord cannot exist
without an LLM extraction attempt -- see the ADR section J).

This module deliberately mirrors Legacy's *conventions* so the two paths
render provenance the same way: per-paper display numbers assigned in bank
order, ``[n]`` markers, and citations carrying ``source_page``,
``source_char_start/end`` and ``quoted_snippet``.

Nothing in this module calls an LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.generator.prompt import RESPONSE_END, RESPONSE_START

CITATION_AUTHORITY = "p165_deterministic_finalizer"

_NATIVE_MARKER = re.compile(r"\[(\d{1,3})\]")


@dataclass(frozen=True)
class FinalCitation:
    """One authoritative citation, resolved from a P-165 evidence id."""

    evidence_id: str
    paper_id: UUID
    paper_title: str
    citation_marker: str
    review_char_start: int
    review_char_end: int
    source_page: int | None
    source_char_start: int | None
    source_char_end: int | None
    quoted_snippet: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "paper_id": str(self.paper_id),
            "paper_title": self.paper_title,
            "citation_marker": self.citation_marker,
            "review_char_start": self.review_char_start,
            "review_char_end": self.review_char_end,
            "source_page": self.source_page,
            "source_char_start": self.source_char_start,
            "source_char_end": self.source_char_end,
            "quoted_snippet": self.quoted_snippet,
        }


@dataclass(frozen=True)
class FinalizedSynthesis:
    """Deterministically finalized text plus authoritative citations."""

    text: str
    citations: tuple[FinalCitation, ...] = ()
    citation_authority: str = CITATION_AUTHORITY
    native_citation_indices: tuple[int, ...] = ()
    rejected_native_indices: tuple[int, ...] = ()
    generation_calls: int = 0
    finalize_ms: float | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "citations": [citation.to_dict() for citation in self.citations],
            "citation_authority": self.citation_authority,
            "native_citation_indices": list(self.native_citation_indices),
            "rejected_native_indices": list(self.rejected_native_indices),
            "generation_calls": self.generation_calls,
            "finalize_ms": self.finalize_ms,
            "diagnostics": dict(self.diagnostics),
        }


def finalize_draft(
    *,
    draft: GeneratedDraft,
    evidence_bank: GroundedEvidenceBank,
    finalize_ms: float | None = None,
) -> FinalizedSynthesis:
    """Rewrite the draft's temporary indices into authoritative P-165 markers."""
    body = (draft.text or "").replace(RESPONSE_START, "").replace(RESPONSE_END, "").strip()

    evidence = list(evidence_bank.evidence)

    # Per-paper display numbers, assigned in bank order -- same convention as
    # the Legacy finalizer's paper_order.
    paper_order: dict[UUID, int] = {}
    for unit in evidence:
        if unit.paper_id not in paper_order:
            paper_order[unit.paper_id] = len(paper_order) + 1

    citations: list[FinalCitation] = []
    native_seen: list[int] = []
    rejected: list[int] = []

    out: list[str] = []
    cursor = 0
    position = 0

    for match in _NATIVE_MARKER.finditer(body):
        index = int(match.group(1))
        if index not in native_seen:
            native_seen.append(index)

        # Copy the text before this marker.
        segment = body[position : match.start()]
        out.append(segment)
        cursor += len(segment)
        position = match.end()

        if not 0 <= index < len(evidence):
            # Untrusted generator index: drop it, record it, publish nothing.
            if index not in rejected:
                rejected.append(index)
            continue

        unit = evidence[index]
        marker = f"[{paper_order[unit.paper_id]}]"
        marker_start = cursor
        out.append(marker)
        cursor += len(marker)

        citations.append(
            FinalCitation(
                evidence_id=unit.evidence_id,
                paper_id=unit.paper_id,
                paper_title=unit.title,
                citation_marker=marker,
                review_char_start=marker_start,
                review_char_end=cursor,
                source_page=unit.page,
                source_char_start=unit.page_char_start,
                source_char_end=unit.page_char_end,
                quoted_snippet=unit.text,
            )
        )

    tail = body[position:]
    out.append(tail)

    return FinalizedSynthesis(
        text="".join(out),
        citations=tuple(citations),
        citation_authority=CITATION_AUTHORITY,
        native_citation_indices=tuple(native_seen),
        rejected_native_indices=tuple(rejected),
        generation_calls=0,
        finalize_ms=finalize_ms,
        diagnostics={
            "papers_cited": len({c.paper_id for c in citations}),
            "evidence_available": len(evidence),
        },
    )
