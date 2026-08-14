"""Deterministic evidence coverage policy for synthesis sections."""
from __future__ import annotations

from collections.abc import Iterable

from src.models.synthesis_schemas import EvidenceDimension, EvidenceSubjectScope, SectionCoverage, SynthesisClaimType

COMPARATIVE_CLAIM_TYPES = {
    SynthesisClaimType.agreement,
    SynthesisClaimType.disagreement,
    SynthesisClaimType.comparison,
    SynthesisClaimType.trend,
}

CORE_REVIEW_DIMENSIONS = [
    EvidenceDimension.objective,
    EvidenceDimension.method,
    EvidenceDimension.findings,
]
FALLBACK_REVIEW_DIMENSIONS = CORE_REVIEW_DIMENSIONS + [EvidenceDimension.limitations]


def normalize_dimension(value: EvidenceDimension | str) -> EvidenceDimension:
    return value if isinstance(value, EvidenceDimension) else EvidenceDimension(value)


def dimension_extraction_rules(dimension: EvidenceDimension | str) -> str:
    dimension = normalize_dimension(dimension)
    rules = {
        EvidenceDimension.objective: (
            "Extract the paper's explicitly stated objective, aim, purpose, or research question. "
            "Prefer sentences from the abstract, introduction, or stated contributions. Return "
            "multiple distinct objectives when the paper explicitly states them; do not infer an "
            "objective from methods or results."
        ),
        EvidenceDimension.limitations: (
            "Extract multiple limitations when explicitly stated. Extract only limitations the paper explicitly attributes to its own proposed method, "
            "study design, data, or conclusions. Do not extract drawbacks of a baseline or competitor "
            "method. Do not classify planned work or statements beginning with future work as a "
            "limitation; those belong to future_work."
        ),
        EvidenceDimension.future_work: (
            "Extract multiple future directions when explicitly stated. Extract only work explicitly proposed for future investigation or stated as outside the "
            "current paper's scope. Do not repeat a limitation unless the paper explicitly frames it "
            "as future_work."
        ),
        EvidenceDimension.dataset: (
            "Extract all named datasets, cohorts, samples, or experimental cases used. When a table or "
            "continuous passage lists multiple datasets/cases, return one comprehensive evidence value "
            "enumerating every visible name rather than separate single-name items."
        ),
        EvidenceDimension.evaluation: "Extract evaluation metrics, baselines, protocols, and comparison criteria.",
    }
    return rules.get(dimension, "Extract evidence only for the requested dimension.")


def should_accept_dimension_scope(
    dimension: EvidenceDimension | str,
    applies_to: EvidenceSubjectScope | str,
) -> bool:
    dimension = normalize_dimension(dimension)
    scope = applies_to if isinstance(applies_to, EvidenceSubjectScope) else EvidenceSubjectScope(applies_to)
    if dimension == EvidenceDimension.limitations:
        return scope in {EvidenceSubjectScope.proposed_method, EvidenceSubjectScope.study}
    return True


def dimension_retrieval_hint(dimension: EvidenceDimension | str) -> str:
    dimension = normalize_dimension(dimension)
    hints = {
        EvidenceDimension.dataset: "datasets benchmark data Table sample cohort experimental cases",
        EvidenceDimension.evaluation: "evaluation metrics accuracy runtime efficiency comparison protocol",
        EvidenceDimension.limitations: "limitations drawbacks proposed method study threats validity",
    }
    return hints.get(dimension, dimension.value)


def normalize_planned_dimensions(
    dimensions: Iterable[EvidenceDimension | str],
) -> list[EvidenceDimension]:
    # Consume/validate planner output for compatibility and observability, but
    # never let planning omit a standard literature-review profile field.
    list(dict.fromkeys(normalize_dimension(item) for item in dimensions))
    return list(EvidenceDimension)


def ensure_review_dimensions(dimensions: Iterable[EvidenceDimension]) -> list[EvidenceDimension]:
    return normalize_planned_dimensions(dimensions)


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
