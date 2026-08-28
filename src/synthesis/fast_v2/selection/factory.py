"""Reranker selection.

Follows the same pattern as the other fast_v2 knobs added in ``src/config.py``
(``synthesis_mode``, ``fast_v2_relevance_threshold``, ...): a validated
``Literal`` setting whose default is the safe, deterministic option, resolved
through one explicit factory rather than an implicit import-time singleton.

Default is ``"identity"`` -- :class:`IdentityReranker`, which performs **no**
reranking. That keeps imports, CI, and CPU-only machines free of a model
download, and keeps unit tests deterministic. ``"cross_encoder"`` must be
opted into explicitly via ``FAST_V2_RERANKER=cross_encoder``.
"""
from __future__ import annotations

from src.synthesis.fast_v2.selection.rerank import EvidenceReranker, IdentityReranker

RERANKER_MODES = ("identity", "cross_encoder", "gte")


def build_reranker(mode: str | None = None) -> EvidenceReranker:
    """Return the configured reranker. Constructing it loads no model."""
    if mode is None:
        from src.config import get_settings

        mode = get_settings().fast_v2_reranker

    if mode == "identity":
        return IdentityReranker()

    if mode == "cross_encoder":
        from src.config import get_settings
        from src.synthesis.fast_v2.selection.cross_encoder import (
            CROSS_ENCODER_MODEL,
            CrossEncoderReranker,
        )

        model_name = getattr(get_settings(), "fast_v2_reranker_model", CROSS_ENCODER_MODEL)
        return CrossEncoderReranker(model_name=model_name)

    if mode == "gte":
        # Chosen production reranker (Alibaba-NLP/gte-reranker-modernbert-base)
        # for the outline-first long-form pipeline. Wraps
        # src/services/reranker_service.py's singleton, NOT the MiniLM
        # adapter in selection/cross_encoder.py -- the "cross_encoder" mode
        # above stays pinned to MiniLM for the frozen RQ1/RQ2 benchmark.
        from src.synthesis.fast_v2.selection.rerank import (
            CrossEncoderReranker as GTECrossEncoderReranker,
        )

        return GTECrossEncoderReranker()

    raise ValueError(
        f"unknown fast_v2 reranker {mode!r}; expected one of {RERANKER_MODES}. "
        "fast_v2 does not guess a reranker -- a wrong reranker silently "
        "changes the evidence bank."
    )
