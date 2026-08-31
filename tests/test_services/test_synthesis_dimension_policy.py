from src.models.synthesis_schemas import EvidenceDimension
from src.services.synthesis_coverage_policy import (
    dimension_extraction_rules,
    normalize_dimension,
    normalize_planned_dimensions,
    should_accept_dimension_scope,
)


def test_planner_output_cannot_remove_dimensions_from_complete_profile():
    assert normalize_planned_dimensions([EvidenceDimension.limitations]) == list(EvidenceDimension)


def test_empty_planner_result_uses_safe_fallback():
    assert normalize_planned_dimensions([]) == list(EvidenceDimension)


def test_serialized_dimension_string_is_normalized_at_runtime_boundary():
    assert normalize_dimension("findings") is EvidenceDimension.findings


def test_limitation_rules_exclude_baseline_drawbacks_and_future_work():
    rules = dimension_extraction_rules(EvidenceDimension.limitations)
    assert "own proposed method" in rules
    assert "baseline" in rules
    assert "future_work" in rules


def test_baseline_limitation_is_rejected_before_grounding():
    assert should_accept_dimension_scope(
        EvidenceDimension.limitations,
        "baseline",
    ) is False
    assert should_accept_dimension_scope(
        EvidenceDimension.limitations,
        "proposed_method",
    ) is True
