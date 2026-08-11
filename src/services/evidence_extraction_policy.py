"""Retry policy for evidence extraction/grounding batches."""
from __future__ import annotations


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
