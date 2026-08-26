"""LLM access for the whole application.

    from src.services.llm import get_llm
    llm = get_llm(task="extract_evidence")

There should be no provider branching anywhere else. If a caller needs to know
which vendor answered, that is a sign the task's requirements belong in
``capability.TASK_REGISTRY`` rather than in the caller.
"""
from src.services.llm.capability import (
    TASK_REGISTRY,
    LLMCapability,
    UnknownTaskError,
    get_capability,
)
from src.services.llm.credentials import get_store, reset_store
from src.services.llm.errors import (
    FailureKind,
    LLMBudgetExceededError,
    NoCapableProviderError,
    classify,
)
from src.services.llm.invoker import CallBudget, CallOutcome, ainvoke_with_failover
from src.services.llm.registry import (
    MODEL_REGISTRY,
    ModelProfile,
    UnknownModelError,
    get_profile,
    known_providers,
)
from src.services.llm.router import (
    Selection,
    build_client,
    get_llm,
    model_for,
    provider_priority,
    select,
)

__all__ = [
    "MODEL_REGISTRY",
    "TASK_REGISTRY",
    "CallBudget",
    "CallOutcome",
    "FailureKind",
    "LLMBudgetExceededError",
    "LLMCapability",
    "ModelProfile",
    "NoCapableProviderError",
    "Selection",
    "UnknownModelError",
    "UnknownTaskError",
    "ainvoke_with_failover",
    "build_client",
    "classify",
    "get_capability",
    "get_llm",
    "get_profile",
    "get_store",
    "known_providers",
    "model_for",
    "provider_priority",
    "reset_store",
    "select",
]
