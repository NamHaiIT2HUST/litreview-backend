"""Fast v2 real product composition root -- EXPERIMENTAL.

    settings
      -> build_generator()   -> HostedApiGenerator / RemoteOpenScholarGenerator / Fake
      -> get_fast_v2_reranker() -> CrossEncoderReranker / IdentityReranker  (singleton)
      -> get_fast_v2_index()    -> FastV2SemanticIndex (singleton, persistent Chroma)
      -> detect_facets(question) -> QuestionFacetDimensionQueryPlanner
      -> FastSynthesisV2Pipeline

This is the ONLY place outside ``src/synthesis/fast_v2/`` tests that
constructs :class:`FastSynthesisV2Pipeline` for a real request. Route/service
code must call :func:`run_fast_v2_synthesis` rather than instantiating
``HostedApiGenerator``/``FastV2ChromaEvidenceRetriever`` itself, so the
existing generator/reranker factories stay the single source of truth for
which backend actually runs.

Facets, not Legacy dimensions
------------------------------
fast_v2's planner deliberately requires **explicit** dimensions -- see
``src/synthesis/fast_v2/dimensions/planner.py``. The first real product E2E
reused Legacy's ``EvidenceDimension`` taxonomy here, which produced an
unrelated, thin evidence bank (see
``scratch/fast_v2_parity_results/e2e_real_backend_diagnostic.md``, not
committed). This module now derives facets from the question itself via
``dimensions/facets.py::detect_facets`` instead.

Process-wide singletons
------------------------
``FastV2SemanticIndex``/reranker construction is cheap, but the *model*
inside each is lazy-loaded on first use -- loading it inside a user request
is the "cold model load" latency this module exists to avoid (see section 5
of the runtime-integration task). ``get_fast_v2_index()``/
``get_fast_v2_reranker()`` are process-wide singletons so :func:`warm_fast_v2`
(called once at backend startup, see ``src/main.py``) actually benefits every
subsequent request.

Legacy (``src/synthesis/graph.py``) never imports this module.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Sequence

from src.synthesis.fast_v2.dimensions.facets import (
    FALLBACK_FACETS,
    QuestionFacetDimensionQueryPlanner,
    detect_facets,
)
from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
from src.synthesis.fast_v2.generator.factory import build_generator
from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline, FastSynthesisV2Result
from src.synthesis.fast_v2.selection.factory import build_reranker
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
from src.synthesis.fast_v2.writer import HostedGroundedLiteratureWriter

#: Retained for backward compatibility with anything that imported the old
#: Legacy-taxonomy default; prefer ``detect_facets(question)`` directly.
DEFAULT_DIMENSIONS: tuple[str, ...] = FALLBACK_FACETS

_index_singleton: FastV2SemanticIndex | None = None
_reranker_cache: dict[str, Any] = {}


def _chroma_client_factory() -> Any:
    """Honour the same CHROMA_HOST/CHROMA_PORT Legacy uses (docker-compose sets
    these inside the container); fall back to the host-machine default
    (localhost:8001, docker-compose's published port) when unset."""
    from src.config import get_settings

    settings = get_settings()
    host = settings.chroma_host or "localhost"
    port = settings.chroma_port if settings.chroma_host else 8001

    import chromadb

    return chromadb.HttpClient(host=host, port=port)


def get_fast_v2_index() -> FastV2SemanticIndex:
    """Process-wide singleton. Constructing this loads no model and opens no
    connection (lazy) -- call :meth:`FastV2SemanticIndex.warm` to force it."""
    global _index_singleton
    if _index_singleton is None:
        _index_singleton = FastV2SemanticIndex(chroma_client_factory=_chroma_client_factory)
    return _index_singleton


def get_fast_v2_reranker() -> Any:
    """Process-wide singleton, cached per configured reranker mode."""
    from src.config import get_settings

    mode = get_settings().fast_v2_reranker
    if mode not in _reranker_cache:
        _reranker_cache[mode] = build_reranker(mode)
    return _reranker_cache[mode]


async def warm_fast_v2() -> dict[str, float]:
    """Load local evidence models into process memory. Zero LLM/API calls.

    Only warms local, CPU-only evidence-pipeline resources (embedding model,
    reranker, Chroma collection handle) -- never OpenScholar, never a hosted
    generator, never any network call to an LLM provider. Call once at
    backend startup when Fast v2 is enabled (see ``src/main.py``); failures
    are never swallowed here so an activated-but-broken Fast v2 runtime fails
    the startup loudly instead of silently eating cold-load latency on the
    first real request.
    """
    started = time.perf_counter()
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    index = get_fast_v2_index()
    await asyncio.to_thread(index.warm)
    timings["embedding_index_warmup_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)

    t0 = time.perf_counter()
    reranker = get_fast_v2_reranker()
    load = getattr(reranker, "load", None)
    if callable(load):
        await asyncio.to_thread(load)
    timings["reranker_warmup_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)

    timings["warmup_ms"] = round((time.perf_counter() - started) * 1000.0, 3)
    return timings


def build_fast_v2_pipeline(*, paper_ids: Sequence[uuid.UUID]) -> FastSynthesisV2Pipeline:
    """Compose the real product Fast v2 pipeline from settings.

    Fails loudly (via ``build_generator``/``build_reranker``) rather than
    silently substituting a fake/identity component when the runtime is
    activated but misconfigured.
    """
    from src.config import get_settings

    settings = get_settings()
    retriever = FastV2ChromaEvidenceRetriever(get_fast_v2_index(), paper_ids=paper_ids)
    reranker = get_fast_v2_reranker()
    generator = build_generator()
    literature_writer = None
    if settings.fast_v2_generator == "hosted_api":
        literature_writer = HostedGroundedLiteratureWriter(
            base_url=settings.fast_v2_hosted_api_base_url,
            api_key=settings.fast_v2_hosted_api_key,
            model=settings.fast_v2_hosted_api_model,
        )
    selection_policy = EvidenceSelectionPolicy(
        max_per_dimension=settings.fast_v2_max_evidence_per_dimension,
        relevance_threshold=settings.fast_v2_relevance_threshold,
    )
    return FastSynthesisV2Pipeline(
        retriever=retriever,
        generator=generator,
        reranker=reranker,
        planner=QuestionFacetDimensionQueryPlanner(paper_ids=paper_ids),
        literature_writer=literature_writer,
        selection_policy=selection_policy,
        candidates_per_dimension=settings.fast_v2_candidates_per_dimension,
    )


async def run_fast_v2_synthesis(
    *,
    paper_ids: Sequence[uuid.UUID],
    research_question: str,
    dimensions: Sequence[str] | None = None,
) -> FastSynthesisV2Result:
    pipeline = build_fast_v2_pipeline(paper_ids=paper_ids)
    facets = list(dimensions) if dimensions else detect_facets(research_question)
    return await pipeline.run(question=research_question, dimensions=facets)
