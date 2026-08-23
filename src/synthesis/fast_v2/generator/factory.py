"""Generator selection.

Follows the same pattern as ``src/synthesis/fast_v2/selection/factory.py``: a
validated ``Literal`` setting whose default is the safe, deterministic option,
resolved through one explicit factory rather than an implicit import-time
singleton.

Default is ``"fake"`` -- :class:`FakeSynthesisGenerator`, which loads nothing
and calls nothing. That keeps imports, CI, and CPU-only machines free of a
GPU/network dependency. ``"remote_openscholar"`` (HTTP, warm GPU service) and
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
unaffected by this guard and always starts up normally regardless of
``FAST_V2_GENERATOR``/``FAST_V2_OPENSCHOLAR_BASE_URL``.
"""
from __future__ import annotations

from src.synthesis.fast_v2.generator.base import SynthesisGenerator
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator

GENERATOR_MODES = ("fake", "local_vllm", "remote_openscholar")


def build_generator(mode: str | None = None, *, base_url: str | None = None) -> SynthesisGenerator:
    """Return the configured generator. Constructing it loads no model."""
    if mode is None:
        from src.config import get_settings

        settings = get_settings()
        mode = settings.fast_v2_generator
        if base_url is None:
            base_url = getattr(settings, "fast_v2_openscholar_base_url", "") or None

        if settings.fast_v2_enabled and mode == "fake":
            raise ValueError(
                "SYNTHESIS_MODE=fast_v2_experimental is active but FAST_V2_GENERATOR "
                "is still its default 'fake' -- refusing to silently run a fake "
                "generator in an activated Fast v2 runtime. Set FAST_V2_GENERATOR to "
                "'remote_openscholar' (with FAST_V2_OPENSCHOLAR_BASE_URL) or "
                "'local_vllm', or call build_generator(mode='fake') explicitly from "
                "a test/dev-only caller if a fake generator is genuinely intended."
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

    raise ValueError(
        f"unknown fast_v2 generator {mode!r}; expected one of {GENERATOR_MODES}. "
        "fast_v2 does not guess a generator -- a wrong generator silently "
        "changes latency/cost."
    )
