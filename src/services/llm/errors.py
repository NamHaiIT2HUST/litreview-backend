"""Telling apart failures worth retrying from failures that will never clear.

Everything used to count as transient. ``_is_transient_provider_error`` returned
True for 400, 401, 403, 404, 409 and 422 alongside 429 and 5xx, so a wrong key
drove the entire candidate-by-retry matrix -- up to twenty-four billed calls for
one logical step, each one certain to fail the same way. A deployment was found
running on a placeholder key doing exactly that.

The distinction is simple: does sending this request again, or sending it
somewhere else, stand any chance of working?

* Wrong key, missing permission, unknown model, malformed request -> no. Stop.
* Rate limit, quota, timeout, 5xx -> yes. Another key or another provider.
"""
from __future__ import annotations

import enum

# Nothing about the request changes on a retry, so neither does the answer.
_PERMANENT_STATUS = frozenset({400, 401, 403, 404, 405, 409, 422})
_TRANSIENT_STATUS = frozenset({408, 425, 429})

_QUOTA_MARKERS = (
    "429", "rate limit", "ratelimit", "resource_exhausted", "quota",
    "too many requests", "overloaded", "high demand", "capacity",
)
_AUTH_MARKERS = (
    "invalid api key", "incorrect api key", "invalid_api_key",
    "api key not valid", "unauthorized", "authentication", "401",
)
_PERMISSION_MARKERS = ("forbidden", "permission denied", "not allowed", "403")
_NOT_FOUND_MARKERS = ("model not found", "does not exist", "no such model", "404")
_TRANSIENT_MARKERS = (
    "timeout", "timed out", "connection", "unavailable", "bad gateway",
    "gateway timeout", "500", "502", "503", "504", "temporarily",
)


class FailureKind(enum.Enum):
    """What to do next, which is the only thing the router needs to know."""

    QUOTA = "quota"           # this key is spent; try another key or provider
    AUTH = "auth"             # this key is wrong; disable it, try another
    PERMISSION = "permission"  # the account cannot use this model; skip provider
    NOT_FOUND = "not_found"   # the model does not exist; configuration is wrong
    BAD_REQUEST = "bad_request"  # our request is malformed; our bug
    TRANSIENT = "transient"   # retry may work
    UNKNOWN = "unknown"       # treated as permanent; see classify()

    @property
    def is_permanent(self) -> bool:
        return self in {
            FailureKind.PERMISSION,
            FailureKind.NOT_FOUND,
            FailureKind.BAD_REQUEST,
            FailureKind.UNKNOWN,
        }

    @property
    def should_try_another_provider(self) -> bool:
        return self in {FailureKind.QUOTA, FailureKind.AUTH, FailureKind.PERMISSION,
                        FailureKind.TRANSIENT}


def classify(exc: BaseException) -> FailureKind:
    """Decide what a provider failure means.

    Unknown failures are treated as permanent. That is the deliberate choice:
    the previous default was the opposite, and an unrecognised error being
    retried across every key and provider is precisely how a single
    misconfiguration turned into a bill.
    """
    status = getattr(exc, "status_code", None)
    message = str(exc).lower()

    # Text wins over status for quota, because providers report exhaustion with
    # assorted 4xx codes whose bodies say "rate limit".
    if any(marker in message for marker in _QUOTA_MARKERS):
        return FailureKind.QUOTA

    if isinstance(status, int):
        if status == 401:
            return FailureKind.AUTH
        if status == 403:
            return FailureKind.PERMISSION
        if status == 404:
            return FailureKind.NOT_FOUND
        if status == 429:
            # Rate limited or out of quota. Distinct from a generic transient
            # failure: the fix is a different key, not another attempt on this one.
            return FailureKind.QUOTA
        if status in _PERMANENT_STATUS:
            return FailureKind.BAD_REQUEST
        if status in _TRANSIENT_STATUS or status >= 500:
            return FailureKind.TRANSIENT

    if any(marker in message for marker in _AUTH_MARKERS):
        return FailureKind.AUTH
    if any(marker in message for marker in _PERMISSION_MARKERS):
        return FailureKind.PERMISSION
    if any(marker in message for marker in _NOT_FOUND_MARKERS):
        return FailureKind.NOT_FOUND
    if any(marker in message for marker in _TRANSIENT_MARKERS):
        return FailureKind.TRANSIENT

    return FailureKind.UNKNOWN


class NoCapableProviderError(RuntimeError):
    """No configured provider can serve this task.

    Lists every provider considered and why each was rejected, so the answer to
    "why did this fail" does not require reading code.
    """

    def __init__(self, task: str, reasons: dict[str, str]):
        self.task = task
        self.reasons = reasons
        detail = "\n".join(f"  - {provider}: {reason}" for provider, reason in reasons.items())
        super().__init__(
            f"No configured LLM provider can serve task {task!r}.\n{detail}\n"
            "Set a key for a provider whose model meets the task's requirements, "
            "or adjust LLM_PROVIDER_PRIORITY."
        )


class LLMBudgetExceededError(RuntimeError):
    """A single unit of work asked for more provider calls than allowed."""
