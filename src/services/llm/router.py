"""Choosing which model serves a task, in one place.

Eight files each carried their own provider cascade with a different order and a
different set of hardcoded model names. The cascades disagreed, so the same
``.env`` produced different behaviour depending on which feature was running,
and a fix applied to one was invisible to the other seven.

Two properties matter here beyond the consolidation:

*Capability-gated fallback.* Moving to another provider is allowed only when
that provider's model can actually do what the task requires. An unrestricted
fallback answers the request with something that cannot honour the schema, which
does not raise and is not right -- the same shape of bug as substituting random
embeddings.

*Ordered by the operator, not by the code.* ``LLM_PROVIDER_PRIORITY`` lives in
each person's ``.env``, so everyone can prefer the keys they have without
touching a shared file and without producing a merge conflict.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from src.config import get_settings
from src.services.llm.capability import LLMCapability, get_capability
from src.services.llm.credentials import Credential, get_store
from src.services.llm.errors import NoCapableProviderError
from src.services.llm.registry import ModelProfile, get_profile, known_providers

logger = logging.getLogger(__name__)

DEFAULT_PRIORITY = ("gemini", "openai", "groq", "deepseek", "openrouter", "xkiro")

# The three SLR-swarm agents in the Research Setup tab are meant to each spend
# from their own Gemini key (GEMINI_KEY_SCOPE_OPTIMIZER / _CRITERIA_GENERATOR /
# _PICO in .env.example) so one agent's quota exhaustion cannot take out the
# other two. Before this, ``select()`` only ever pulled from the shared
# GEMINI_API_KEYS pool for these tasks, so the three dedicated keys sat unused.
# Falls back to the shared pool when a task has no dedicated key configured.
_TASK_DEDICATED_GEMINI_ENV: dict[str, str] = {
    "optimize_scope": "GEMINI_KEY_SCOPE_OPTIMIZER",
    "generate_criteria": "GEMINI_KEY_CRITERIA_GENERATOR",
    "find_gaps": "GEMINI_KEY_PICO",
    "extract_pico": "GEMINI_KEY_PICO",
}

# Cached per task so a key disabled or cooled down by the invoker stays that
# way across calls, the same guarantee the shared credential store gives.
_dedicated_credentials: dict[str, Credential] = {}

# The Research Setup tab's 3 agents and AI Screening (Tìm kiếm tab) were moved
# from Gemini to OpenAI as their primary provider: Gemini's free tier caps at
# 20 requests/day/model, which this app's real usage exhausts within minutes,
# while the paid OpenAI key has no such wall. Pinned here at the code level
# (not left to LLM_PROVIDER_PRIORITY alone) so it holds regardless of what an
# operator's .env sets that variable to. Gemini's per-task dedicated keys
# remain the fallback if OPENAI_API_KEY is ever unset or rejected -- this only
# reorders provider_priority()'s list for these tasks, it does not remove
# providers from it.
_TASK_PREFERRED_PROVIDER: dict[str, str] = {
    "optimize_scope": "openai",
    "generate_criteria": "openai",
    "find_gaps": "openai",
    "extract_pico": "openai",
    "screen_paper": "openai",
    # Tab Tìm kiếm's remaining two Gemini-first tasks -- confirmed broken in
    # production testing (2026-08-27) by the exact quota wall documented
    # above: RESOURCE_EXHAUSTED, "GenerateRequestsPerDayPerProjectPerModel-
    # FreeTier", limit 20. paper_summary needs a 128k-context model; gpt-4o-mini
    # already satisfies that (see registry.py), so this is not a capability
    # downgrade, only a provider-order change.
    "generate_keywords": "openai",
    "paper_summary": "openai",
    # One-off bulk dataset generation (scripts/finetune_nli/01_generate_dataset.py)
    # runs hundreds of calls in a single script invocation -- the exact shape
    # that blows through Gemini's 20-requests/day/model free-tier wall in
    # minutes, same as the tasks above. Pinned here rather than left to hit
    # that wall on request ~20 of a 200-premise run.
    "generate_nli_training_triplet": "openai",
}


def _provider_order_for(task: str) -> list[str]:
    order = list(provider_priority())
    preferred = _TASK_PREFERRED_PROVIDER.get(task)
    if preferred and preferred in order:
        order.remove(preferred)
        order.insert(0, preferred)
    return order


def _dedicated_credential_for(task: str) -> Credential | None:
    env_var = _TASK_DEDICATED_GEMINI_ENV.get(task)
    if not env_var:
        return None
    cached = _dedicated_credentials.get(task)
    if cached is not None:
        return cached
    key = os.getenv(env_var, "").strip()
    if not key:
        return None
    credential = Credential(provider="gemini", alias=env_var.lower(), key=key)
    _dedicated_credentials[task] = credential
    return credential

# Which env var names the model for each provider. Separate from the credential
# on purpose: changing a key must never change which model runs.
_PROVIDER_MODEL_ENV = {
    "openai": "OPENAI_MODEL",
    "gemini": "GEMINI_MODEL",
    "groq": "GROQ_MODEL",
    "deepseek": "DEEPSEEK_MODEL",
    "openrouter": "OPENROUTER_MODEL",
    "xkiro": "XKIRO_MODEL",
}

_PROVIDER_DEFAULT_MODEL = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-flash-latest",
    "groq": "llama-3.3-70b-versatile",
    "deepseek": "deepseek-chat",
    "openrouter": "openai/gpt-4o-mini",
    "xkiro": "deepseek/deepseek-v3.2",
}


@dataclass(frozen=True)
class Selection:
    """The chosen model plus the reasoning, so a log line explains itself."""

    profile: ModelProfile
    credential: Credential
    task: str
    capability: LLMCapability
    skipped: dict[str, str]

    def describe(self) -> str:
        parts = [f"task={self.task}"]
        if self.capability.json_schema:
            parts.append("needs=json_schema")
        parts.append(f"ctx>={self.capability.min_context}")
        for provider, reason in self.skipped.items():
            parts.append(f"skipped={provider}({reason})")
        parts.append(f"selected={self.profile.key} key={self.credential.alias}")
        return "llm.select " + " ".join(parts)


def provider_priority() -> list[str]:
    raw = os.getenv("LLM_PROVIDER_PRIORITY", "").strip()
    if not raw:
        return list(DEFAULT_PRIORITY)
    ordered = [p.strip().lower() for p in raw.split(",") if p.strip()]
    unknown = [p for p in ordered if p not in known_providers()]
    if unknown:
        raise ValueError(
            f"LLM_PROVIDER_PRIORITY names unknown provider(s): {unknown}. "
            f"Known providers: {known_providers()}."
        )
    return ordered


def model_for(provider: str) -> str:
    env_var = _PROVIDER_MODEL_ENV.get(provider)
    configured = os.getenv(env_var, "").strip() if env_var else ""
    return configured or _PROVIDER_DEFAULT_MODEL.get(provider, "")


def select(task: str) -> Selection:
    """Pick the first provider that has a usable key and a capable model.

    Records why each rejected provider was rejected. That list is the difference
    between "the LLM call failed" and "gemini's key is cooling down, groq's model
    has an 8k context and this step needs 32k, so nothing could serve it".
    """
    capability = get_capability(task)
    store = get_store()
    skipped: dict[str, str] = {}

    for provider in _provider_order_for(task):
        if not store.has_any(provider):
            skipped[provider] = store.unavailable_reason(provider)
            continue

        model = model_for(provider)
        if not model:
            skipped[provider] = "no model configured"
            continue

        try:
            profile = get_profile(provider, model)
        except Exception as exc:
            skipped[provider] = str(exc).split(".")[0]
            continue

        ok, reason = capability.satisfied_by(profile)
        if not ok:
            skipped[provider] = reason
            continue

        credential = None
        if provider == "gemini":
            dedicated = _dedicated_credential_for(task)
            if dedicated is not None and dedicated.is_available:
                credential = dedicated
        if credential is None:
            credential = store.next_for(provider)
        if credential is None:
            skipped[provider] = store.unavailable_reason(provider)
            continue

        selection = Selection(
            profile=profile,
            credential=credential,
            task=task,
            capability=capability,
            skipped=skipped,
        )
        logger.info(selection.describe())
        return selection

    raise NoCapableProviderError(task, skipped)


def build_client(selection: Selection, *, temperature: float = 0.0, max_tokens: int = 8192):
    """Construct the chat model for a selection.

    The only place a provider SDK is instantiated. Callers receive a client and
    never learn which vendor produced it.
    """
    profile = selection.profile
    key = selection.credential.key

    if profile.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=profile.model,
            google_api_key=key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            timeout=60,
        )

    if profile.provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=profile.model,
            api_key=key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # Everything else speaks the OpenAI chat-completions protocol. The base URL
    # comes from the registry, not from inspecting the key's prefix.
    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": profile.model,
        "api_key": key,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_retries": 0,  # retrying is the router's decision, not the SDK's
        "timeout": 60,
    }
    if profile.base_url:
        kwargs["base_url"] = profile.base_url
    return ChatOpenAI(**kwargs)


def get_llm(task: str, *, temperature: float | None = None, max_tokens: int = 8192):
    """Return a chat model able to serve ``task``.

    The single entry point. No caller should contain provider branching.
    """
    settings = get_settings()
    if temperature is None:
        temperature = settings.synthesis_temperature
    selection = select(task)
    return build_client(selection, temperature=temperature, max_tokens=max_tokens)
