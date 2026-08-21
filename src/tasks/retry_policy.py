"""Pure retry policy for long-running synthesis jobs.

Keeping this logic dependency-free makes retry/terminal-failure semantics easy
to test without importing Celery or database drivers.
"""
from __future__ import annotations


def is_transient_synthesis_error(exc: BaseException) -> bool:
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    msg = str(exc).lower()
    return any(term in msg for term in (
        "409", "429", "timeout", "connection", "rate limit", "ratelimit",
        "duplicate request", "already being processed", "resource_exhausted", "quota"
    ))


def should_retry_synthesis(
    exc: BaseException,
    *,
    retries: int,
    max_retries: int,
) -> bool:
    return is_transient_synthesis_error(exc) and retries < max_retries


def should_mark_failed(
    exc: BaseException,
    *,
    retries: int,
    max_retries: int,
) -> bool:
    return not should_retry_synthesis(exc, retries=retries, max_retries=max_retries)
