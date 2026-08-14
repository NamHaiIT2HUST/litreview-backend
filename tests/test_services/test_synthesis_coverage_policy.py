from src.models.synthesis_schemas import SynthesisClaimType
from src.services.synthesis_coverage_policy import (
    dimensions_needing_expansion,
    ensure_review_dimensions,
    evaluate_section_coverage,
)


def test_section_is_sufficient_with_two_evidence_records():
    result = evaluate_section_coverage(
        evidence_paper_ids=["paper-1", "paper-1"],
        claim_types=[SynthesisClaimType.descriptive],
    )

    assert result.status == "sufficient"
    assert result.evidence_count == 2
    assert result.paper_count == 1


def test_section_is_limited_when_it_has_too_little_evidence():
    result = evaluate_section_coverage(
        evidence_paper_ids=["paper-1"],
        claim_types=[SynthesisClaimType.descriptive],
    )

    assert result.status == "limited"
    assert result.reasons == ["requires_at_least_2_evidence_records"]


def test_comparative_section_requires_two_papers():
    result = evaluate_section_coverage(
        evidence_paper_ids=["paper-1", "paper-1"],
        claim_types=[SynthesisClaimType.comparison],
    )

    assert result.status == "limited"
    assert "comparative_claim_requires_2_papers" in result.reasons


def test_dimension_expands_once_when_initial_evidence_is_thin():
    result = dimensions_needing_expansion(
        dimensions=["methods", "outcomes"],
        paper_ids_by_dimension={"methods": ["p1"], "outcomes": ["p1", "p2"]},
    )

    assert result == ["methods"]


def test_general_review_plan_is_supplemented_when_model_returns_one_dimension():
    from src.models.synthesis_schemas import EvidenceDimension
    assert ensure_review_dimensions([EvidenceDimension.dataset]) == list(EvidenceDimension)


def test_model_plan_cannot_remove_dimensions_from_complete_profile():
    from src.models.synthesis_schemas import EvidenceDimension
    dimensions = [EvidenceDimension.limitations, EvidenceDimension.future_work]
    assert ensure_review_dimensions(dimensions) == list(EvidenceDimension)


def test_missing_papers_are_reported_from_grounded_evidence_coverage():
    from src.services.synthesis_coverage_policy import missing_evidence_paper_ids

    assert missing_evidence_paper_ids(
        selected_paper_ids=["p1", "p2", "p3"],
        evidence_paper_ids=["p1", "p3", "p3"],
    ) == ["p2"]
