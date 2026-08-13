"""Deterministic evidence coverage policy for synthesis sections."""
from __future__ import annotations

from collections.abc import Iterable

from src.models.synthesis_schemas import SectionCoverage, SynthesisClaimType

COMPARATIVE_CLAIM_TYPES = {
    SynthesisClaimType.agreement,
    SynthesisClaimType.disagreement,
    SynthesisClaimType.comparison,
    SynthesisClaimType.trend,
}

DEFAULT_REVIEW_DIMENSIONS = [
    "Methodology and approach",
    "Main findings and outcomes",
    "Limitations and research gaps",
    "Future research directions",
]


def ensure_review_dimensions(dimensions: Iterable[str]) -> list[str]:
    """Ensure an LLM plan is broad enough for a useful general review."""
    result = list(dict.fromkeys(item.strip() for item in dimensions if item.strip()))
    for default in DEFAULT_REVIEW_DIMENSIONS:
        if default not in result:
            result.append(default)
    return result[:8]


def missing_evidence_paper_ids(
    *, selected_paper_ids: Iterable[str], evidence_paper_ids: Iterable[str]
) -> list[str]:
    covered = set(evidence_paper_ids)
    return [paper_id for paper_id in selected_paper_ids if paper_id not in covered]


def dimensions_needing_expansion(
    *, dimensions: Iterable[str], paper_ids_by_dimension: dict[str, Iterable[str]],
) -> list[str]:
    """Return dimensions with fewer than two grounded evidence records."""
    return [
        dimension for dimension in dimensions
        if len(list(paper_ids_by_dimension.get(dimension, []))) < 2
    ]


def evaluate_section_coverage(
    *,
    evidence_paper_ids: Iterable[str],
    claim_types: Iterable[SynthesisClaimType],
    retrieval_attempts: int = 1,
) -> SectionCoverage:
    paper_ids = list(evidence_paper_ids)
    unique_papers = set(paper_ids)
    types = set(claim_types)
    reasons: list[str] = []

    if len(paper_ids) < 2:
        reasons.append("requires_at_least_2_evidence_records")
    if types & COMPARATIVE_CLAIM_TYPES and len(unique_papers) < 2:
        reasons.append("comparative_claim_requires_2_papers")

    return SectionCoverage(
        status="limited" if reasons else "sufficient",
        evidence_count=len(paper_ids),
        paper_count=len(unique_papers),
        retrieval_attempts=retrieval_attempts,
        reasons=reasons,
    )
