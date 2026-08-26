"""Running a call, and deciding what to do when it fails.

This is where the cost behaviour actually lives. Selecting a model is cheap;
what used to be expensive was the reaction to failure. A wrong key was
classified as transient, so the synthesis adapter walked its six candidate
runners four times over -- twenty-four billed calls for one logical step, every
one of them failing identically.

The rules here follow from :mod:`src.services.llm.errors`:

* wrong model or malformed request -> stop, nothing else will help
* wrong key -> disable that key, try the next one
* quota -> set that key aside, try the next key or provider
* transient -> retry, with a bounded budget

and a call budget caps the total regardless, so no single unit of work can run
away.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field

from src.services.llm.errors import (
    FailureKind,
    LLMBudgetExceededError,
    NoCapableProviderError,
    classify,
)
from src.services.llm.router import Selection, build_client, select

logger = logging.getLogger(__name__)

# Backoff between transient retries of the same provider.
_RETRY_DELAYS = (1.0, 2.0, 4.0)


@dataclass
class CallBudget:
    """A ceiling on provider calls for one unit of work.

    Exists because the per-call rules alone do not bound the total: a long
    synthesis makes hundreds of independent calls, and a provider degrading
    intermittently can multiply each one. The budget is what turns "each call is
    sensible" into "this session cannot cost more than N calls".
    """

    max_calls: int = 200
    used: int = 0
    label: str = "session"

    def spend(self) -> None:
        self.used += 1
        if self.used > self.max_calls:
            raise LLMBudgetExceededError(
                f"{self.label} exceeded its budget of {self.max_calls} LLM calls. "
                "Either the work is larger than expected or a provider is failing "
                "repeatedly; stopping rather than continuing to spend."
            )

    @property
    def remaining(self) -> int:
        return max(0, self.max_calls - self.used)


@dataclass
class CallOutcome:
    """What a call cost and who served it, for the audit trail."""

    selection: Selection
    attempts: int = 0
    duration_ms: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


async def ainvoke_with_failover(
    task: str,
    build_runner,
    messages,
    *,
    budget: CallBudget | None = None,
    temperature: float | None = None,
    max_tokens: int = 8192,
):
    """Run ``build_runner(client)`` against the first provider that can serve it.

    ``build_runner`` receives the chat client and returns whatever will actually
    be invoked -- typically ``client.with_structured_output(schema)``. Keeping
    that a callback lets the invoker own provider selection and failure handling
    while the caller keeps control of the response shape.

    Returns ``(result, outcome)``.
    """
    budget = budget or CallBudget()
    tried_providers: dict[str, str] = {}
    started = time.perf_counter()
    attempts = 0
    last_exc: BaseException | None = None
    selection: Selection | None = None
    errors: list[tuple[str, str]] = []

    while True:
        try:
            selection = select(task)
        except NoCapableProviderError as exc:
            if last_exc is not None:
                # Providers existed but all of them failed; report that, not the
                # bare "nothing configured" message.
                raise last_exc from exc
            raise

        if selection.profile.provider in tried_providers:
            # select() would keep handing back the same exhausted provider.
            raise last_exc or NoCapableProviderError(task, tried_providers)

        client = build_client(selection, temperature=temperature, max_tokens=max_tokens)
        runner = build_runner(client)

        for attempt in range(len(_RETRY_DELAYS) + 1):
            budget.spend()
            attempts += 1
            try:
                result = await runner.ainvoke(messages)
                outcome = CallOutcome(
                    selection=selection,
                    attempts=attempts,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    errors=errors,
                )
                return result, outcome
            except Exception as exc:
                last_exc = exc
                kind = classify(exc)
                errors.append((selection.profile.key, f"{kind.value}: {str(exc)[:200]}"))

                if kind is FailureKind.AUTH:
                    selection.credential.disable(f"rejected by {selection.profile.provider}")
                    logger.warning(
                        "Key %s for %s was rejected; disabling it for this process.",
                        selection.credential.alias, selection.profile.provider,
                    )
                    break
                if kind is FailureKind.QUOTA:
                    selection.credential.cool_down()
                    logger.warning(
                        "Key %s for %s is out of quota; setting it aside.",
                        selection.credential.alias, selection.profile.provider,
                    )
                    break
                if kind.is_permanent:
                    # Nothing about the request changes on a retry or on another
                    # provider, so stop here rather than paying to confirm it.
                    logger.error(
                        "Permanent failure on %s (%s): %s",
                        selection.profile.key, kind.value, exc,
                    )
                    raise
                if attempt < len(_RETRY_DELAYS):
                    await asyncio.sleep(_RETRY_DELAYS[attempt] + random.uniform(0.1, 0.5))
                else:
                    break

        tried_providers[selection.profile.provider] = (
            errors[-1][1] if errors else "failed"
        )
