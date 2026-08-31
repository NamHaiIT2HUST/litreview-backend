"""Fast v2 real product composition root -- EXPERIMENTAL.

    settings
      -> build_generator()   -> HostedApiGenerator / RemoteOpenScholarGenerator / Fake
      -> get_fast_v2_reranker() -> CrossEncoderReranker / IdentityReranker  (singleton)
      -> get_fast_v2_index()    -> FastV2SemanticIndex (singleton, persistent Chroma)
      -> plan_outline(question, paper_metadata) -> LongformOutlinePlan
      -> OutlineDimensionQueryPlanner (per-section retrieval queries)
      -> FastSynthesisV2Pipeline

This is the ONLY place outside ``src/synthesis/fast_v2/`` tests that
constructs :class:`FastSynthesisV2Pipeline` for a real request. Route/service
code must call :func:`run_fast_v2_synthesis` rather than instantiating
``HostedApiGenerator``/``FastV2HybridEvidenceRetriever`` itself, so the
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
from collections.abc import Sequence
from typing import Any

from src.synthesis.fast_v2.dimensions.facets import (
    FALLBACK_FACETS,
    QuestionFacetDimensionQueryPlanner,
    detect_facets,
)
from src.synthesis.fast_v2.dimensions.outline_planner import OutlineDimensionQueryPlanner
from src.synthesis.fast_v2.evidence.hybrid_retriever import FastV2HybridEvidenceRetriever
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
from src.synthesis.fast_v2.generator.factory import build_generator
from src.synthesis.fast_v2.grounding.semantic import HostedBatchSemanticVerifier
from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline, FastSynthesisV2Result
from src.synthesis.fast_v2.planning.research_lead import (
    LongformOutlinePlan,
    SectionPlan,
    plan_longform_outline,
)
from src.synthesis.fast_v2.selection.factory import build_reranker
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
from src.synthesis.fast_v2.writer import HostedGroundedLiteratureWriter

#: Retained for backward compatibility with anything that imported the old
#: Legacy-taxonomy default; prefer ``detect_facets(question)`` directly.
DEFAULT_DIMENSIONS: tuple[str, ...] = FALLBACK_FACETS

GENERAL_REVIEW_QUESTION = (
    "Provide a general literature review of the selected studies, comparing "
    "methods, findings, datasets, and limitations."
)

_index_singleton: FastV2SemanticIndex | None = None
_reranker_cache: dict[str, Any] = {}


def build_general_review_question(research_question: str | None) -> str:
    """Keep the user topic optional without spending an LLM call to invent it."""
    return research_question.strip() if research_question and research_question.strip() else GENERAL_REVIEW_QUESTION


async def plan_outline(
    *, paper_metadata: Sequence[dict[str, str]], research_question: str, guidance: str | None = None
) -> LongformOutlinePlan:
    """One bounded Research Lead LLM call turns selected titles/abstracts into
    a thematic outline + section-specific retrieval plan.

    This plans queries only. It never sees PDF chunks and cannot create
    evidence or bypass the later hygiene/rerank/provenance/semantic gates.
    Falls back to a single-section deterministic outline (never raises) when
    there is no paper metadata to plan against or the LLM call fails --
    :func:`~src.synthesis.fast_v2.planning.research_lead.plan_longform_outline`
    already handles the parse-failure fallback internally.
    """
    from src.config import get_settings

    if not any(item.get("title") or item.get("abstract") for item in paper_metadata):
        return LongformOutlinePlan(
            research_question=research_question,
            sections=tuple(
                SectionPlan(
                    id=f"sec_{i+1}",
                    title=facet,
                    purpose=f"Cover the '{facet}' aspect of the research question.",
                    target_words=1000,
                    papers_to_compare=(),
                    retrieval_queries=(facet,),
                )
                for i, facet in enumerate(detect_facets(research_question))
            ),
        )

    settings = get_settings()
    base_url = (settings.fast_v2_hosted_api_base_url or settings.get_api_base).rstrip("/")
    api_key = settings.fast_v2_hosted_api_key or settings.effective_openai_api_key
    model = settings.fast_v2_hosted_api_model or settings.synthesis_model or settings.effective_model_name

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0.0)
    return await plan_longform_outline(
        llm, research_question=research_question, paper_metadata=paper_metadata, guidance=guidance
    )


async def ensure_fast_v2_indexed(paper_ids: Sequence[uuid.UUID]) -> list[Any]:
    """Idempotently index selected canonical PDF chunks before retrieval.

    This backfills papers ingested before Fast V2 was introduced and makes the
    first user review self-sufficient. ``index_paper`` upserts by chunk ID, so
    repeating this on later reviews avoids a separate index-state table.
    """
    from src.database import AsyncSessionLocal
    from src.synthesis.fast_v2.evidence.indexing_service import FastV2IndexingService

    service = FastV2IndexingService(AsyncSessionLocal, get_fast_v2_index())
    return [await service.index_paper(paper_id) for paper_id in paper_ids]


def _chroma_client_factory() -> Any:
    """Honour the same CHROMA_HOST/CHROMA_PORT Legacy uses (docker-compose sets
    these inside the container); fall back to the host-machine default
    (localhost:8001, docker-compose's published port) when unset, or local PersistentClient."""
    from src.config import get_settings

    settings = get_settings()
    host = settings.chroma_host or "localhost"
    port = settings.chroma_port if settings.chroma_host else 8001

    import os

    import chromadb

    try:
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        return client
    except Exception:
        local_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "chroma_data")
        )
        os.makedirs(local_path, exist_ok=True)
        return chromadb.PersistentClient(path=local_path)


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


def build_fast_v2_pipeline(
    *, paper_ids: Sequence[uuid.UUID], outline: LongformOutlinePlan | None = None
) -> FastSynthesisV2Pipeline:
    """Compose the real product Fast v2 pipeline from settings.

    Fails loudly (via ``build_generator``/``build_reranker``) rather than
    silently substituting a fake/identity component when the runtime is
    activated but misconfigured.
    """
    from src.config import get_settings

    settings = get_settings()
    retriever = FastV2HybridEvidenceRetriever(get_fast_v2_index(), paper_ids=paper_ids)
    reranker = get_fast_v2_reranker()
    # Pass the raw FAST_V2_HOSTED_API_* settings through UNRESOLVED (no
    # generic-credential fallback) so build_generator()'s own "fast_v2 does
    # not guess a hosted-API provider/model/key" validation can actually
    # fire when they're unset -- falling back to settings.get_api_base /
    # effective_openai_api_key here made that check unreachable in practice,
    # since any deployment with OPENAI_API_KEY set (the norm, per the
    # Cấu hình/Tìm kiếm tabs routing) would silently reuse it instead of
    # raising. build_generator() only needs these when
    # fast_v2_generator == "hosted_api"; other modes ignore them.
    hosted_base_url = settings.fast_v2_hosted_api_base_url or None
    hosted_api_key = settings.fast_v2_hosted_api_key or None
    hosted_model = settings.fast_v2_hosted_api_model or None
    generator = build_generator(
        hosted_api_base_url=hosted_base_url,
        hosted_api_key=hosted_api_key,
        hosted_api_model=hosted_model,
    )
    semantic_verifier = None
    literature_writer = None
    if settings.fast_v2_generator == "hosted_api":
        semantic_verifier = HostedBatchSemanticVerifier(
            base_url=hosted_base_url,
            api_key=hosted_api_key,
            model=settings.fast_v2_verifier_model or hosted_model,
        )
        literature_writer = HostedGroundedLiteratureWriter(
            base_url=hosted_base_url,
            api_key=hosted_api_key,
            model=settings.fast_v2_writer_model or hosted_model,
            max_tokens=settings.fast_v2_writer_max_tokens,
        )
    selection_policy = EvidenceSelectionPolicy(
        max_per_dimension=settings.fast_v2_max_evidence_per_dimension,
        relevance_threshold=settings.fast_v2_relevance_threshold,
    )
    # Outline-first: when Research Lead already produced a section outline,
    # its per-section retrieval_queries drive retrieval directly. Without an
    # outline (explicit `dimensions=` override, e.g. tests/benchmarks), fall
    # back to the generic question-facet planner.
    planner = (
        OutlineDimensionQueryPlanner(outline)
        if outline is not None
        else QuestionFacetDimensionQueryPlanner(paper_ids=paper_ids)
    )
    return FastSynthesisV2Pipeline(
        retriever=retriever,
        generator=generator,
        reranker=reranker,
        planner=planner,
        semantic_verifier=semantic_verifier,
        literature_writer=literature_writer,
        selection_policy=selection_policy,
        candidates_per_dimension=settings.fast_v2_candidates_per_dimension,
        evidence_budget=settings.fast_v2_evidence_budget,
        section_candidate_cap=settings.fast_v2_section_candidate_cap,
        max_total_rerank_pairs=settings.fast_v2_max_total_rerank_pairs,
        outline=outline,
    )


async def run_fast_v2_synthesis(
    *,
    paper_ids: Sequence[uuid.UUID],
    research_question: str,
    dimensions: Sequence[str] | None = None,
    paper_metadata: Sequence[dict[str, str]] = (),
) -> FastSynthesisV2Result:
    outline: LongformOutlinePlan | None = None
    if dimensions is None:
        outline = await plan_outline(
            paper_metadata=paper_metadata, research_question=research_question
        )
        facets = [section.title for section in outline.sections]
    else:
        facets = list(dimensions)

    pipeline = build_fast_v2_pipeline(paper_ids=paper_ids, outline=outline)
    return await pipeline.run(question=research_question, dimensions=facets)


async def run_section_scoped_synthesis(
    *,
    paper_ids: Sequence[uuid.UUID],
    approved_outline: LongformOutlinePlan,
    artifact_dir: str | None = None,
    citation_batch_size: int = 4,
    citation_concurrency: int = 4,
) -> FastSynthesisV2Result:
    """Execute section-scoped synthesis with an approved LongformOutlinePlan.

    Bypasses: Generator Draft 1, Global Evidence Bank merge, ClaimManifest,
    SemanticVerifier, LiteratureWriter Draft 2.
    """
    from langchain_openai import ChatOpenAI

    from src.config import get_settings
    from src.synthesis.fast_v2.section_pipeline import SectionScopedSynthesisPipeline

    settings = get_settings()
    retriever = FastV2HybridEvidenceRetriever(get_fast_v2_index(), paper_ids=paper_ids)
    reranker = get_fast_v2_reranker()

    base_url = (settings.fast_v2_hosted_api_base_url or settings.get_api_base).rstrip("/")
    api_key = settings.fast_v2_hosted_api_key or settings.effective_openai_api_key
    writer_model = settings.fast_v2_writer_model or settings.synthesis_model or settings.effective_model_name
    citation_model = settings.fast_v2_verifier_model or settings.synthesis_model or settings.effective_model_name

    writer_llm = ChatOpenAI(
        model=writer_model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        max_tokens=settings.fast_v2_writer_max_tokens or 12000,
        timeout=300,
        stream_usage=True,
    )
    citation_llm = ChatOpenAI(
        model=citation_model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0,
        timeout=120,
    )

    pipeline = SectionScopedSynthesisPipeline(
        retriever=retriever,
        reranker=reranker,
        writer_llm=writer_llm,
        citation_llm=citation_llm,
        candidates_per_dimension=settings.fast_v2_candidates_per_dimension or 30,
        section_candidate_cap=settings.fast_v2_section_candidate_cap or 25,
        writer_max_tokens=settings.fast_v2_writer_max_tokens or 8192,
        artifact_dir=artifact_dir,
        citation_batch_size=citation_batch_size,
        citation_concurrency=citation_concurrency,
    )
    return await pipeline.run(approved_outline=approved_outline, paper_ids=paper_ids)

