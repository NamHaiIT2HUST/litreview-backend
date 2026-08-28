"""Deterministic P-165 provenance/citation finalizer for fast_v2.

**P-165 is the citation authority.** Production Fast v2 renders citations only
from provenance-validated structured claims. The older native-index finalizer
remains for compatibility tests and historical artifacts; native bracket
numbers are always untrusted diagnostics.

Final provenance chain::

    validated support ID -> EvidenceUnit -> canonical text/page/source offsets

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
from src.synthesis.fast_v2.grounding.interface import GroundedDraft

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


def finalize_structured_draft(
    *,
    grounded: GroundedDraft,
    evidence_bank: GroundedEvidenceBank,
    finalize_ms: float | None = None,
) -> FinalizedSynthesis:
    """Render only provenance-validated manifest statements.

    Raw generator prose and native citation markers are never copied into the
    output. This function validates no semantics; it consumes the guard's
    already validated IDs, paper ownership, and canonical evidence spans.
    """
    evidence_by_id = {
        unit.evidence_id: unit for unit in evidence_bank.evidence
    }
    paper_order: dict[UUID, int] = {}
    for unit in evidence_bank.evidence:
        if unit.paper_id not in paper_order:
            paper_order[unit.paper_id] = len(paper_order) + 1

    if not grounded.validated_claims:
        return FinalizedSynthesis(
            text="Insufficient validated evidence to answer the question.",
            citation_authority=CITATION_AUTHORITY,
            native_citation_indices=grounded.draft.native_citation_indices,
            rejected_native_indices=grounded.draft.native_citation_indices,
            generation_calls=0,
            finalize_ms=finalize_ms,
            diagnostics={
                "papers_cited": 0,
                "evidence_available": len(evidence_bank.evidence),
                "validated_claims": 0,
                "dropped_claims": len(grounded.dropped_claims),
            },
        )

    out: list[str] = []
    citations: list[FinalCitation] = []
    cursor = 0

    def append(value: str) -> None:
        nonlocal cursor
        out.append(value)
        cursor += len(value)

    claims_by_facet: dict[str, list[Any]] = {}
    seen_claim_signatures: set[tuple[Any, ...]] = set()
    for claim in grounded.validated_claims:
        signature = (
            claim.facet,
            claim.is_comparative,
            tuple(
                (
                    statement.claim_text,
                    statement.paper_id,
                    tuple(
                        (
                            support.evidence_id,
                            support.paper_id,
                            support.quote_char_start,
                            support.quote_char_end,
                        )
                        for support in statement.supports
                    ),
                )
                for statement in claim.statements
            ),
        )
        if signature in seen_claim_signatures:
            continue
        seen_claim_signatures.add(signature)
        claims_by_facet.setdefault(claim.facet, []).append(claim)

    # Retrieval dimensions set a useful stable order, but writer-approved
    # thematic titles are not necessarily identical to those query labels.
    # Render those additional titles too; otherwise finalization silently
    # collapses a multi-section review into one retrieval facet.
    ordered_facets = [
        facet for facet in evidence_bank.dimensions if facet in claims_by_facet
    ]
    ordered_facets.extend(
        facet for facet in claims_by_facet if facet not in ordered_facets
    )
    rendered_facets = 0
    for facet in ordered_facets:
        facet_claims = claims_by_facet.get(facet, ())
        if not facet_claims:
            continue
        if rendered_facets:
            append("\n\n")
        append(f"**{facet.replace('_', ' ').title()}**\n\n")
        rendered_facets += 1

        for claim_index, claim in enumerate(facet_claims):
            if claim_index:
                append("\n\n")
            for statement_index, statement in enumerate(claim.statements):
                if statement_index:
                    append(" ")
                append(statement.claim_text.strip())
                append(" ")
                seen_statement_evidence: set[str] = set()
                seen_statement_papers: set[UUID] = set()
                for support in statement.supports:
                    if support.evidence_id in seen_statement_evidence:
                        continue
                    seen_statement_evidence.add(support.evidence_id)
                    unit = evidence_by_id[support.evidence_id]
                    # Citation markers identify papers, not chunks. Several
                    # chunks from one paper support one statement, but should
                    # render as one readable marker such as [2], never [2]x4.
                    if unit.paper_id in seen_statement_papers:
                        continue
                    seen_statement_papers.add(unit.paper_id)
                    marker = f"[{paper_order[unit.paper_id]}]"
                    marker_start = cursor
                    append(marker)
                    citations.append(
                        FinalCitation(
                            evidence_id=unit.evidence_id,
                            paper_id=unit.paper_id,
                            paper_title=unit.title,
                            citation_marker=marker,
                            review_char_start=marker_start,
                            review_char_end=cursor,
                            source_page=unit.page,
                            source_char_start=support.source_char_start,
                            source_char_end=support.source_char_end,
                            quoted_snippet=support.support_quote,
                        )
                    )

    native = grounded.draft.native_citation_indices
    return FinalizedSynthesis(
        text="".join(out).strip(),
        citations=tuple(citations),
        citation_authority=CITATION_AUTHORITY,
        native_citation_indices=native,
        rejected_native_indices=native,
        generation_calls=0,
        finalize_ms=finalize_ms,
        diagnostics={
            "papers_cited": len({citation.paper_id for citation in citations}),
            "evidence_available": len(evidence_bank.evidence),
            "validated_claims": len(grounded.validated_claims),
            "dropped_claims": len(grounded.dropped_claims),
        },
    )


_HANDLE_CITATION_REGEX = re.compile(r"\[(E\d{3}(?:,\s*E\d{3})*)\]")


def finalize_natural_markdown(
    *,
    markdown_text: str,
    evidence_bank: GroundedEvidenceBank,
    handle_mapping: dict[str, str],
) -> FinalizedSynthesis:
    """Deterministically parse handles [E001] from Markdown and bind to FinalCitation objects."""
    evidence_by_id = {unit.evidence_id: unit for unit in evidence_bank.evidence}
    
    citations: list[FinalCitation] = []
    
    # Paper display order
    paper_order: dict[UUID, int] = {}
    for unit in evidence_bank.evidence:
        if unit.paper_id not in paper_order:
            paper_order[unit.paper_id] = len(paper_order) + 1

    # Find all citation matches
    for match in _HANDLE_CITATION_REGEX.finditer(markdown_text):
        raw_handles = match.group(1)
        start_idx = match.start()
        end_idx = match.end()
        
        handles = [h.strip() for h in raw_handles.split(",") if h.strip()]
        for h in handles:
            ev_id = handle_mapping.get(h)
            if ev_id and ev_id in evidence_by_id:
                unit = evidence_by_id[ev_id]
                citations.append(
                    FinalCitation(
                        evidence_id=unit.evidence_id,
                        paper_id=unit.paper_id,
                        paper_title=unit.title,
                        citation_marker=f"[{h}]",
                        review_char_start=start_idx,
                        review_char_end=end_idx,
                        source_page=unit.page,
                        source_char_start=unit.page_char_start,
                        source_char_end=unit.page_char_end,
                        quoted_snippet=unit.text[:150] + "...",
                    )
                )

    return FinalizedSynthesis(
        text=markdown_text.strip(),
        citations=tuple(citations),
        citation_authority=CITATION_AUTHORITY,
        diagnostics={
            "papers_cited": len({citation.paper_id for citation in citations}),
            "total_citations": len(citations),
            "evidence_available": len(evidence_bank.evidence),
        },
    )
