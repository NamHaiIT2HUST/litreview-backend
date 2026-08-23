"""Generator selection.

Follows the same pattern as ``src/synthesis/fast_v2/selection/factory.py``: a
validated ``Literal`` setting whose default is the safe, deterministic option,
resolved through one explicit factory rather than an implicit import-time
singleton.

Default is ``"fake"`` -- :class:`FakeSynthesisGenerator`, which loads nothing
and calls nothing. That keeps imports, CI, and CPU-only machines free of a
GPU/network dependency. ``"remote_openscholar"`` (HTTP, warm GPU service),
``"hosted_api"`` (generic OpenAI-compatible pay-per-request API), and
``"local_vllm"`` (in-process vLLM, requires a local GPU) must be opted into
explicitly.

Activated-runtime guardrail
----------------------------
``"fake"`` is only reachable two ways: (a) the caller passes ``mode="fake"``
explicitly -- the test/dev-only path -- or (b) resolving from settings when
``synthesis_mode`` is still ``"legacy"`` (fast_v2 inactive, so which generator
would run is moot). If ``synthesis_mode == "fast_v2_experimental"`` and
``FAST_V2_GENERATOR`` was left at its default ``"fake"``, resolving from
settings raises loudly instead of silently running a fake generator in an
activated Fast v2 runtime -- that combination almost always means someone
flipped ``SYNTHESIS_MODE`` and forgot to also point ``FAST_V2_GENERATOR`` at
a real backend. Legacy (``synthesis_mode == "legacy"``) is completely
unaffected by this guard and always starts up normally regardless of any
``FAST_V2_*`` generator config.
"""
from __future__ import annotations

from src.synthesis.fast_v2.generator.base import SynthesisGenerator
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator

GENERATOR_MODES = ("fake", "local_vllm", "remote_openscholar", "hosted_api")


def build_generator(
    mode: str | None = None,
    *,
    base_url: str | None = None,
    hosted_api_base_url: str | None = None,
    hosted_api_key: str | None = None,
    hosted_api_model: str | None = None,
) -> SynthesisGenerator:
    """Return the configured generator. Constructing it loads no model."""
    if mode is None:
        from src.config import get_settings

        settings = get_settings()
        mode = settings.fast_v2_generator
        if base_url is None:
            base_url = getattr(settings, "fast_v2_openscholar_base_url", "") or None
        if hosted_api_base_url is None:
            hosted_api_base_url = getattr(settings, "fast_v2_hosted_api_base_url", "") or None
        if hosted_api_key is None:
            hosted_api_key = getattr(settings, "fast_v2_hosted_api_key", "") or None
        if hosted_api_model is None:
            hosted_api_model = getattr(settings, "fast_v2_hosted_api_model", "") or None

        if settings.fast_v2_enabled and mode == "fake":
            raise ValueError(
                "SYNTHESIS_MODE=fast_v2_experimental is active but FAST_V2_GENERATOR "
                "is still its default 'fake' -- refusing to silently run a fake "
                "generator in an activated Fast v2 runtime. Set FAST_V2_GENERATOR to "
                "'remote_openscholar', 'hosted_api', or 'local_vllm' (with their "
                "required config), or call build_generator(mode='fake') explicitly "
                "from a test/dev-only caller if a fake generator is genuinely intended."
            )

    if mode == "fake":
        return FakeSynthesisGenerator()

    if mode == "local_vllm":
        from src.synthesis.fast_v2.generator.openscholar import OpenScholarGenerator

        return OpenScholarGenerator()

    if mode == "remote_openscholar":
        if not base_url:
            raise ValueError(
                "FAST_V2_GENERATOR=remote_openscholar requires "
                "FAST_V2_OPENSCHOLAR_BASE_URL to be set. fast_v2 does not guess "
                "a GPU service endpoint."
            )
        from src.synthesis.fast_v2.generator.remote_openscholar import (
            RemoteOpenScholarGenerator,
        )

        return RemoteOpenScholarGenerator(base_url=base_url)

    if mode == "hosted_api":
        missing = [
            name for name, value in (
                ("FAST_V2_HOSTED_API_BASE_URL", hosted_api_base_url),
                ("FAST_V2_HOSTED_API_KEY", hosted_api_key),
                ("FAST_V2_HOSTED_API_MODEL", hosted_api_model),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"FAST_V2_GENERATOR=hosted_api requires {', '.join(missing)} to be "
                "set. fast_v2 does not guess a hosted-API provider/model/key."
            )
        from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator

        return HostedApiGenerator(
            base_url=hosted_api_base_url, api_key=hosted_api_key, model=hosted_api_model
        )

    raise ValueError(
        f"unknown fast_v2 generator {mode!r}; expected one of {GENERATOR_MODES}. "
        "fast_v2 does not guess a generator -- a wrong generator silently "
        "changes latency/cost."
    )
