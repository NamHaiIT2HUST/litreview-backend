"""The one place a model name appears.

Sixteen distinct model names and five base URLs were spread across eight files,
each with its own provider cascade and its own idea of which model to fall back
to. Changing provider meant hunting all of them, which is why fixes kept being
partial: the file in front of you got updated and the seven copies did not.

Adding a provider should be one entry here plus one credential variable, and
nothing else. If a change requires editing another file, this table is missing
something.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    """What a model can actually do, so callers stop discovering it by trial.

    ``supports_json_schema`` and friends are what let the router refuse a
    fallback that would technically respond but not respect the requested
    schema. Without them the only way to find out was to send the request and
    look at what came back -- which is why the synthesis adapter built six
    candidate runners and tried them in turn, paying for each attempt.
    """

    provider: str
    model: str
    context_window: int
    supports_json_schema: bool
    supports_json_mode: bool
    supports_function_calling: bool
    supports_tool_calling: bool
    # Relative, not a price. Used only to prefer the cheaper of two models that
    # both satisfy a request.
    cost_tier: int
    # None means the SDK's own endpoint. Only set for gateways.
    base_url: str | None = None

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}"


def _profile(provider, model, *, context_window, json_schema=True, json_mode=True,
             function_calling=True, tool_calling=True, cost_tier=2, base_url=None):
    return ModelProfile(
        provider=provider,
        model=model,
        context_window=context_window,
        supports_json_schema=json_schema,
        supports_json_mode=json_mode,
        supports_function_calling=function_calling,
        supports_tool_calling=tool_calling,
        cost_tier=cost_tier,
        base_url=base_url,
    )


# Capabilities come from each provider's own documentation. Where a value was
# not verifiable it is set to the conservative option: claiming support the
# model lacks produces output that parses as valid and is not, which is the
# failure mode this whole design exists to prevent.
MODEL_REGISTRY: dict[str, ModelProfile] = {
    p.key: p
    for p in [
        # ---- OpenAI ----
        _profile("openai", "gpt-4o-mini", context_window=128_000, cost_tier=1),
        _profile("openai", "gpt-4o", context_window=128_000, cost_tier=3),

        # ---- Google Gemini ----
        # Structured output is supported; parallel tool calling is not assumed.
        # Google retires dated model names on its own schedule -- gemini-2.0-flash
        # and gemini-1.5-flash both returned 404 NOT_FOUND in production, each
        # pointing at whatever replaced it. Keep this list to names Google's own
        # error responses currently confirm as live, not to what looked current
        # when last edited.
        _profile("gemini", "gemini-3.6-flash", context_window=1_000_000,
                 tool_calling=False, cost_tier=1),
        _profile("gemini", "gemini-flash-lite-latest", context_window=1_000_000,
                 tool_calling=False, cost_tier=1),
        _profile("gemini", "gemini-flash-latest", context_window=1_000_000,
                 tool_calling=False, cost_tier=1),

        # ---- Groq ----
        _profile("groq", "llama-3.3-70b-versatile", context_window=128_000,
                 json_schema=False, cost_tier=1),

        # ---- DeepSeek ----
        _profile("deepseek", "deepseek-chat", context_window=64_000,
                 json_schema=False, cost_tier=1,
                 base_url="https://api.deepseek.com/v1"),

        # ---- OpenAI-compatible gateways ----
        # Third-party gateways re-expose other vendors' models and frequently do
        # not implement the full structured-output surface. json_schema is off
        # for them by default: the UniversalJsonRunner prompt-based path exists
        # precisely because these endpoints kept refusing it.
        _profile("openrouter", "openai/gpt-4o-mini", context_window=128_000,
                 json_schema=False, cost_tier=1,
                 base_url="https://openrouter.ai/api/v1"),
        _profile("xkiro", "deepseek/deepseek-v3.2", context_window=64_000,
                 json_schema=False, cost_tier=1,
                 base_url="https://api.xkiro.com/v1"),
    ]
}


class UnknownModelError(RuntimeError):
    """A configured model is not described here, so its capabilities are unknown."""


def get_profile(provider: str, model: str) -> ModelProfile:
    """Look up a model, or refuse.

    Guessing is not an option: an unregistered model has unknown capabilities,
    and assuming it supports what a task needs is how a request ends up
    answered by something that cannot honour the schema.
    """
    profile = MODEL_REGISTRY.get(f"{provider}:{model}")
    if profile is None:
        known = sorted(p.model for p in MODEL_REGISTRY.values() if p.provider == provider)
        raise UnknownModelError(
            f"Model {model!r} is not registered for provider {provider!r}. "
            f"Known models for this provider: {known or '(none)'}. "
            "Add it to MODEL_REGISTRY in src/services/llm/registry.py together "
            "with its context window and structured-output support."
        )
    return profile


def models_for(provider: str) -> list[ModelProfile]:
    return [p for p in MODEL_REGISTRY.values() if p.provider == provider]


def known_providers() -> list[str]:
    return sorted({p.provider for p in MODEL_REGISTRY.values()})
