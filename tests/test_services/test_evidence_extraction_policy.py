from src.services.evidence_extraction_policy import (
    MAX_TARGETED_RECOVERY_PER_DIMENSION,
    MAX_TARGETED_RECOVERY_PER_PAPER,
    recovery_budget_allows,
    should_retry_evidence_batch,
)


def test_retry_when_any_candidate_failed_grounding_even_if_another_grounded():
    assert should_retry_evidence_batch(
        attempt_number=1,
        had_candidates=True,
        had_grounding_failure=True,
    ) is True


def test_do_not_retry_legitimate_empty_evidence_batch():
    assert should_retry_evidence_batch(
        attempt_number=1,
        had_candidates=False,
        had_grounding_failure=False,
    ) is False


def test_never_retry_after_second_attempt():
    assert should_retry_evidence_batch(
        attempt_number=2,
        had_candidates=True,
        had_grounding_failure=True,
    ) is False


def test_targeted_recovery_budget_allows_one_per_dimension_and_four_per_paper():
    assert MAX_TARGETED_RECOVERY_PER_DIMENSION == 1
    assert MAX_TARGETED_RECOVERY_PER_PAPER == 4
    assert recovery_budget_allows(existing_dimension_retries=0, existing_paper_retries=0)
    assert not recovery_budget_allows(existing_dimension_retries=1, existing_paper_retries=1)
    assert not recovery_budget_allows(existing_dimension_retries=0, existing_paper_retries=4)
