from src.services.evidence_extraction_policy import should_retry_evidence_batch


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
