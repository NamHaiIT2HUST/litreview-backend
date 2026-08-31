"""CPU-only tests for the real product composition root (src/synthesis/fast_v2/runtime.py).

No network, no Chroma, no DB. Construction of every component in this chain
is lazy (documented on each class), so these tests prove *wiring* -- which
concrete class gets selected -- without touching the network.
"""
from __future__ import annotations

import uuid

import pytest


def _hosted_api_settings(**overrides):
    from src.config import Settings

    base = dict(
        synthesis_mode="fast_v2_experimental",
        fast_v2_generator="hosted_api",
        fast_v2_hosted_api_base_url="https://api.example.com/v1",
        fast_v2_hosted_api_key="sk-test-key",
        fast_v2_hosted_api_model="openai/gpt-oss-120b",
    )
    base.update(overrides)
    return Settings(**base)


def test_default_dimensions_are_the_fast_v2_fallback_not_legacy_taxonomy():
    """The real E2E run showed reusing Legacy's EvidenceDimension taxonomy as
    the fast_v2 dimension list produces an unrelated, thin evidence bank.
    The runtime must use the Fast-v2-specific fallback facets instead."""
    from src.models.synthesis_schemas import EvidenceDimension
    from src.synthesis.fast_v2.dimensions.facets import FALLBACK_FACETS
    from src.synthesis.fast_v2.runtime import DEFAULT_DIMENSIONS

    assert DEFAULT_DIMENSIONS == FALLBACK_FACETS
    legacy_values = {d.value for d in EvidenceDimension}
    assert set(DEFAULT_DIMENSIONS).isdisjoint(legacy_values)
    for benchmark_word in ("Xu2010", "Xu2018", "split feasibility", "RQ1", "RQ2"):
        assert benchmark_word not in DEFAULT_DIMENSIONS


def test_run_fast_v2_synthesis_uses_facet_planner_not_legacy_taxonomy(monkeypatch):
    """run_fast_v2_synthesis must derive dimensions from the question via
    detect_facets(), not the old Legacy-taxonomy default."""
    import asyncio

    from src import config as config_module
    from src.synthesis.fast_v2 import runtime as runtime_module
    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline

    monkeypatch.setattr(config_module, "get_settings", lambda: _hosted_api_settings())
    # Bypass the network-touching composition (Chroma/reranker) and just
    # prove run_fast_v2_synthesis's *dimension selection* wiring.
    captured: dict[str, list[str]] = {}

    class _CapturingPipeline(FastSynthesisV2Pipeline):
        async def run(self, *, question, dimensions):  # type: ignore[override]
            captured["dimensions"] = list(dimensions)
            return await super().run(question=question, dimensions=dimensions)

    monkeypatch.setattr(
        runtime_module,
        "build_fast_v2_pipeline",
        lambda **kwargs: _CapturingPipeline(
            retriever=StaticEvidenceRetriever([]), generator=FakeSynthesisGenerator()
        ),
    )

    question = (
        "How do Chen2015 and Park2020 differ in their formulations of the "
        "gradient descent problem, algorithmic strategies, assumptions, and "
        "convergence guarantees?"
    )
    asyncio.run(runtime_module.run_fast_v2_synthesis(paper_ids=[uuid.uuid4()], research_question=question))

    assert captured["dimensions"] == ["formulation", "algorithms", "assumptions", "convergence"]


def test_general_review_question_keeps_topic_optional():
    """Removing the topic must not block synthesis or trigger an LLM call just
    to invent a question; a deterministic general-review prompt is enough."""
    from src.synthesis.fast_v2.runtime import build_general_review_question

    assert build_general_review_question("") == (
        "Provide a general literature review of the selected studies, comparing "
        "methods, findings, datasets, and limitations."
    )
    assert build_general_review_question("  Compare retrieval methods.  ") == "Compare retrieval methods."


def test_ensure_fast_v2_indexed_rebuilds_selected_papers(monkeypatch):
    """A previously-ingested PDF must become retrievable on its first review,
    even when it predates the dedicated Fast V2 collection."""
    import asyncio

    from src.synthesis.fast_v2 import runtime as runtime_module

    paper_ids = [uuid.uuid4(), uuid.uuid4()]
    indexed: list[uuid.UUID] = []

    class _IndexingService:
        def __init__(self, session_factory, index):
            assert session_factory is not None
            assert index == "fast-index"

        async def index_paper(self, paper_id):
            indexed.append(paper_id)
            return object()

    monkeypatch.setattr(runtime_module, "get_fast_v2_index", lambda: "fast-index")
    monkeypatch.setattr(
        "src.synthesis.fast_v2.evidence.indexing_service.FastV2IndexingService",
        _IndexingService,
    )

    asyncio.run(runtime_module.ensure_fast_v2_indexed(paper_ids))

    assert indexed == paper_ids


def test_composition_root_selects_hosted_api_generator_from_settings(monkeypatch):
    from src import config as config_module
    from src.synthesis.fast_v2.evidence.hybrid_retriever import FastV2HybridEvidenceRetriever
    from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator
    from src.synthesis.fast_v2.grounding.semantic import HostedBatchSemanticVerifier
    from src.synthesis.fast_v2.runtime import build_fast_v2_pipeline
    from src.synthesis.fast_v2.selection.rerank import IdentityReranker
    from src.synthesis.fast_v2.writer import HostedGroundedLiteratureWriter

    monkeypatch.setattr(config_module, "get_settings", lambda: _hosted_api_settings())

    pipeline = build_fast_v2_pipeline(paper_ids=[uuid.uuid4()])

    assert isinstance(pipeline.generator, HostedApiGenerator)
    assert pipeline.generator.model == "openai/gpt-oss-120b"
    assert isinstance(pipeline.semantic_verifier, HostedBatchSemanticVerifier)
    assert pipeline.semantic_verifier.model == "openai/gpt-oss-120b"
    assert isinstance(pipeline.literature_writer, HostedGroundedLiteratureWriter)
    assert isinstance(pipeline.retriever, FastV2HybridEvidenceRetriever)
    # fast_v2_reranker defaults to "identity" unless FAST_V2_RERANKER=cross_encoder.
    assert isinstance(pipeline.reranker, IdentityReranker)


def test_composition_root_gives_selected_paper_ids_to_comparative_planner(monkeypatch):
    from src import config as config_module
    from src.synthesis.fast_v2.runtime import build_fast_v2_pipeline

    monkeypatch.setattr(config_module, "get_settings", lambda: _hosted_api_settings())
    paper_a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    paper_b = uuid.UUID("22222222-2222-2222-2222-222222222222")

    pipeline = build_fast_v2_pipeline(paper_ids=[paper_a, paper_b])
    queries = pipeline.planner.plan(
        research_question=(
            "How do the selected papers differ in their formulations of the "
            "gradient descent problem and convergence guarantees?"
        ),
        dimensions=["formulation", "convergence"],
    )

    assert [(query.dimension, query.paper_id) for query in queries] == [
        ("formulation", paper_a),
        ("formulation", paper_b),
        ("convergence", paper_a),
        ("convergence", paper_b),
    ]


def test_composition_root_selects_cross_encoder_reranker_when_configured(monkeypatch):
    from src import config as config_module
    from src.synthesis.fast_v2.runtime import build_fast_v2_pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    monkeypatch.setattr(
        config_module, "get_settings", lambda: _hosted_api_settings(fast_v2_reranker="cross_encoder")
    )

    pipeline = build_fast_v2_pipeline(paper_ids=[uuid.uuid4()])

    assert isinstance(pipeline.reranker, CrossEncoderReranker)
    assert pipeline.reranker.is_loaded is False  # construction must not load the model


def test_local_embedding_and_reranker_loaders_do_not_probe_huggingface_network(monkeypatch):
    """Local development must use cached checkpoints immediately."""
    import sys
    import types

    calls = []

    class _SentenceTransformer:
        def __init__(self, name, **kwargs):
            calls.append(("embed", name, kwargs))

    class _CrossEncoder:
        def __init__(self, name, **kwargs):
            calls.append(("rerank", name, kwargs))

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(
            SentenceTransformer=_SentenceTransformer,
            CrossEncoder=_CrossEncoder,
        ),
    )
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    FastV2SemanticIndex(chroma_client_factory=object)._default_model_factory("embed-model")
    CrossEncoderReranker()._default_model_factory("rerank-model")

    assert calls == [
        (
            "embed",
            "embed-model",
            {
                "local_files_only": True,
                "trust_remote_code": True,
                "backend": "onnx",
                "model_kwargs": {"file_name": "onnx/model_int8.onnx"},
            },
        ),
        ("rerank", "rerank-model", {"local_files_only": True}),
    ]


def test_default_settings_keep_legacy_as_the_supported_production_flow():
    """"legacy" is the only supported production path (see src/config.py's
    own comment above `synthesis_mode`) and must stay the default until the
    promotion criteria documented there are actually met -- fast_v2 still
    has open correctness gaps (e.g. the "gte" reranker mode crashes on a
    fresh checkout with no local model cache, see test_cross_encoder_reranker.py)
    that make flipping this default premature."""
    from src.config import Settings

    settings = Settings()
    assert settings.synthesis_mode == "legacy"
    assert settings.fast_v2_enabled is False


def test_missing_hosted_config_fails_loud(monkeypatch):
    from src import config as config_module
    from src.synthesis.fast_v2.runtime import build_fast_v2_pipeline

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _hosted_api_settings(
            fast_v2_hosted_api_base_url="", fast_v2_hosted_api_key="", fast_v2_hosted_api_model=""
        ),
    )

    with pytest.raises(ValueError, match="FAST_V2_HOSTED_API"):
        build_fast_v2_pipeline(paper_ids=[uuid.uuid4()])


def test_fake_generator_cannot_be_selected_in_activated_fast_v2_runtime(monkeypatch):
    """fast_v2_experimental active + FAST_V2_GENERATOR left at its default
    'fake' must fail loudly, never silently run a fake generator against a
    real request."""
    from src import config as config_module
    from src.config import Settings
    from src.synthesis.fast_v2.runtime import build_fast_v2_pipeline

    monkeypatch.setattr(
        config_module, "get_settings", lambda: Settings(synthesis_mode="fast_v2_experimental")
    )

    with pytest.raises(ValueError, match="FAST_V2_GENERATOR"):
        build_fast_v2_pipeline(paper_ids=[uuid.uuid4()])


def test_hosted_api_generator_never_logs_or_prints_the_api_key(monkeypatch, caplog):
    """Construction + a failing generate() call must not leak the key into
    logs. hosted_api.py imports no logging module at all -- this proves the
    invariant behaviourally, not just by source inspection."""
    from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
    from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator
    from src.synthesis.fast_v2.generator.remote_openscholar import FastV2GenerationError

    secret_key = "sk-do-not-leak-this-value-12345"

    class _FailingClient:
        def post(self, *args, **kwargs):
            raise ConnectionError("simulated network failure")

    generator = HostedApiGenerator(
        base_url="https://api.example.com/v1",
        api_key=secret_key,
        model="openai/gpt-oss-120b",
        http_client_factory=lambda: _FailingClient(),
    )

    empty_bank = GroundedEvidenceBank.build(question="q", dimensions=["d"], evidence_by_dimension={})

    caplog.set_level("DEBUG")
    with pytest.raises(FastV2GenerationError) as excinfo:
        generator.generate(question="q", evidence_bank=empty_bank)

    assert secret_key not in str(excinfo.value)
    assert secret_key not in caplog.text


def test_exactly_one_generation_call_through_the_composed_pipeline():
    """No automatic retry anywhere in the real composition path."""
    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline

    generator = FakeSynthesisGenerator()
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever([]), generator=generator
    )

    import asyncio

    result = asyncio.run(pipeline.run(question="q", dimensions=["objective"]))

    assert result.timings.get("generation_calls") == 1
    assert result.claim_grounding_status == "unvalidated"


# --------------------------------------------------------------------------
# Warmup: zero LLM/API calls, reuses model instances (singletons)
# --------------------------------------------------------------------------

def test_warmup_makes_zero_generator_or_api_calls(monkeypatch):
    """warm_fast_v2 must only touch local embedding/reranker resources --
    never build_generator, never HostedApiGenerator, never any network call
    to an LLM provider."""
    import asyncio

    from src import config as config_module
    from src.synthesis.fast_v2 import runtime as runtime_module

    monkeypatch.setattr(
        config_module, "get_settings", lambda: _hosted_api_settings(fast_v2_reranker="identity")
    )

    class _FakeIndex:
        def __init__(self):
            self.warmed = False

        def warm(self):
            self.warmed = True

    fake_index = _FakeIndex()
    monkeypatch.setattr(runtime_module, "get_fast_v2_index", lambda: fake_index)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_generator must never be called by warm_fast_v2")

    monkeypatch.setattr(runtime_module, "build_generator", _fail_if_called)

    timings = asyncio.run(runtime_module.warm_fast_v2())

    assert fake_index.warmed is True
    assert "warmup_ms" in timings
    assert "embedding_index_warmup_ms" in timings


def test_warmup_reuses_the_same_index_instance_as_the_pipeline(monkeypatch):
    """get_fast_v2_index() must be a process-wide singleton -- warming it at
    startup only helps subsequent requests if build_fast_v2_pipeline reuses
    the exact same (already-warmed) instance rather than constructing a new
    one per request."""
    from src import config as config_module
    from src.synthesis.fast_v2 import runtime as runtime_module

    monkeypatch.setattr(config_module, "get_settings", lambda: _hosted_api_settings())
    runtime_module._index_singleton = None  # isolate from other tests
    try:
        first = runtime_module.get_fast_v2_index()
        second = runtime_module.get_fast_v2_index()
        assert first is second

        pipeline = runtime_module.build_fast_v2_pipeline(paper_ids=[uuid.uuid4()])
        assert pipeline.retriever._index is first
    finally:
        runtime_module._index_singleton = None


# --------------------------------------------------------------------------
# Generation metadata propagation (input_tokens/output_tokens/network ms)
# --------------------------------------------------------------------------

def test_hosted_generation_metadata_survives_into_pipeline_diagnostics():
    """The first real E2E showed input_tokens/output_tokens/generation_ms
    present on GeneratedDraft but missing from the pipeline's diagnostics
    dict -- a propagation gap, not a provider gap. Prove the fix with a
    generator double that returns real usage numbers."""
    import asyncio

    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.base import GeneratedDraft
    from src.synthesis.fast_v2.grounding.manifest import ClaimManifest
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline

    class _StubGenerator:
        def generate(self, *, question, evidence_bank):
            return GeneratedDraft(
                text='{"claims":[]}',
                model_name="stub/model",
                prompt_version="p165_structured_claim_manifest_v2",
                claim_manifest=ClaimManifest(claims=()),
                generation_calls=1,
                input_tokens=3997,
                output_tokens=1584,
                finish_reason="stop",
                generation_ms=9869.561,
            )

    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever([]), generator=_StubGenerator()
    )
    result = asyncio.run(pipeline.run(question="q", dimensions=["formulation"]))

    assert result.diagnostics["input_tokens"] == 3997
    assert result.diagnostics["output_tokens"] == 1584
    assert result.diagnostics["generation_network_ms"] == 9869.561
    assert result.diagnostics["generation_calls"] == 1
