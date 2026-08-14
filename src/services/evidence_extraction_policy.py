"""Retry policy for evidence extraction/grounding batches."""
from __future__ import annotations


MAX_TARGETED_RECOVERY_PER_DIMENSION = 1
MAX_TARGETED_RECOVERY_PER_PAPER = 4


def recovery_budget_allows(
    *,
    existing_dimension_retries: int,
    existing_paper_retries: int,
    max_per_dimension: int = MAX_TARGETED_RECOVERY_PER_DIMENSION,
    max_per_paper: int = MAX_TARGETED_RECOVERY_PER_PAPER,
) -> bool:
    """Bound targeted recovery without accepting ungrounded evidence.

    Before this budget, repeated coverage/recovery passes could re-run the same
    expanded dimension. The default policy permits one targeted retry per
    dimension and four total retries for one paper in a synthesis session.
    """
    return (
        existing_dimension_retries < max_per_dimension
        and existing_paper_retries < max_per_paper
    )


def should_retry_evidence_batch(
    *,
    attempt_number: int,
    had_candidates: bool,
    had_grounding_failure: bool,
) -> bool:
    """Retry once when any first-pass candidate failed deterministic grounding.

    A legitimate empty extraction means the paper/context contains no evidence
    for that dimension and must not trigger another LLM call.
    """
    return (
        attempt_number == 1
        and had_candidates
        and had_grounding_failure
    )
