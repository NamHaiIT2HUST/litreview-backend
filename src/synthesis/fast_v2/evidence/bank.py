"""Grounded Evidence Bank -- deterministic merge/dedupe and the generator input.

The bank is the **only** evidence input to the fast_v2 generator. The
generator never performs retrieval itself; if it needs something that is not
in the bank, the answer is that it does not get it.

Dedupe is deterministic and keyed on the canonical ``evidence_id``. There is
**no LLM semantic dedup** -- two textually similar but distinct chunks stay
distinct. Evidence selected by several dimensions is merged into one unit that
retains ``selected_for_dimensions``, ``dimension_scores`` and
``best_dimension_score``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


def merge_evidence(
    evidence_by_dimension: Mapping[str, Sequence[EvidenceUnit]],
) -> list[EvidenceUnit]:
    """Deterministically dedupe per-dimension selections into one list.

    Ordering is by ``best_dimension_score`` descending, then ``evidence_id``
    for a stable tiebreak.
    """
    merged: dict[str, EvidenceUnit] = {}

    for dimension in evidence_by_dimension:
        for unit in evidence_by_dimension[dimension] or ():
            score = unit.dimension_scores.get(dimension)
            existing = merged.get(unit.evidence_id)
            if existing is None:
                merged[unit.evidence_id] = unit
                continue
            # Same canonical evidence reached from another dimension: keep one
            # unit and accumulate the dimension metadata onto it.
            if score is not None:
                merged[unit.evidence_id] = existing.with_dimension(dimension, score)
            else:
                for other, other_score in unit.dimension_scores.items():
                    merged[unit.evidence_id] = merged[unit.evidence_id].with_dimension(
                        other, other_score
                    )

    return sorted(
        merged.values(),
        key=lambda unit: (-(unit.best_dimension_score or 0.0), unit.evidence_id),
    )


@dataclass(frozen=True)
class GroundedEvidenceBank:
    """Serializable evidence bundle handed to the generator."""

    question: str
    dimensions: tuple[str, ...]
    evidence: tuple[EvidenceUnit, ...]
    coverage: dict[str, Any] = field(default_factory=dict)
    paper_distribution: dict[str, int] = field(default_factory=dict)
    pages_represented: dict[str, list[int]] = field(default_factory=dict)

    query_ms: float | None = None
    retrieval_ms: float | None = None
    rerank_ms: float | None = None

    @classmethod
    def build(
        cls,
        *,
        question: str,
        dimensions: Sequence[str],
        evidence_by_dimension: Mapping[str, Sequence[EvidenceUnit]],
        query_ms: float | None = None,
        retrieval_ms: float | None = None,
        rerank_ms: float | None = None,
    ) -> GroundedEvidenceBank:
        requested = tuple(dimensions)
        merged = merge_evidence(evidence_by_dimension)

        paper_distribution: dict[str, int] = {}
        pages: dict[str, list[int]] = {}
        for unit in merged:
            paper_distribution[unit.title] = paper_distribution.get(unit.title, 0) + 1
            if unit.page is not None:
                bucket = pages.setdefault(unit.title, [])
                if unit.page not in bucket:
                    bucket.append(unit.page)
        for bucket in pages.values():
            bucket.sort()

        covered = [
            dimension
            for dimension in requested
            if any(dimension in unit.selected_for_dimensions for unit in merged)
        ]
        uncovered = [dimension for dimension in requested if dimension not in covered]

        coverage = {
            "dimensions_requested": len(requested),
            "dimensions_with_evidence": len(covered),
            "dimensions_without_evidence": uncovered,
            "evidence_count": len(merged),
            "paper_count": len({unit.paper_id for unit in merged}),
            # Honest: an empty or thin bank is reported, never padded.
            "is_thin": len(merged) == 0 or bool(uncovered),
        }

        return cls(
            question=question,
            dimensions=requested,
            evidence=tuple(merged),
            coverage=coverage,
            paper_distribution=paper_distribution,
            pages_represented=pages,
            query_ms=query_ms,
            retrieval_ms=retrieval_ms,
            rerank_ms=rerank_ms,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "dimensions": list(self.dimensions),
            "evidence": [unit.to_dict() for unit in self.evidence],
            "coverage": dict(self.coverage),
            "paper_distribution": dict(self.paper_distribution),
            "pages_represented": {k: list(v) for k, v in self.pages_represented.items()},
            "query_ms": self.query_ms,
            "retrieval_ms": self.retrieval_ms,
            "rerank_ms": self.rerank_ms,
        }
