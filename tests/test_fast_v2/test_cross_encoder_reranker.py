"""Real cross-encoder reranker adapter -- contract, ordering, and laziness.

The reranker actually used by the validated Dimension-Aware v1 / Evidence-First
experiments is ``cross-encoder/ms-marco-MiniLM-L-6-v2``, wrapped by
``src/services/reranker.py`` on the ``feat/phase123-eval-hybrid-agentic``
worktree (``src/services/reranker.py:13``), which every Evidence-First spike
imports (e.g. ``spike_evidence_first_v0.py:61``).

That implementation's contract, which this adapter must preserve exactly:

* pairs are built ``(query, document_text)`` -- query FIRST;
* scores come from ``CrossEncoder.predict(pairs)`` -- raw logits, unbounded,
  legitimately NEGATIVE;
* results are sorted score-DESCENDING, not returned in input order.

These tests never load the real model. Laziness is asserted structurally.
"""
from __future__ import annotations

import ast
import inspect
import uuid

import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.selection.rerank import (
    EvidenceReranker,
    IdentityReranker,
    apply_reranker,
)


# ---------------------------------------------------------------------------
# Fakes -- stand in for sentence_transformers.CrossEncoder without importing it
# ---------------------------------------------------------------------------
class RecordingCrossEncoder:
    """Mimics ``CrossEncoder.predict``: takes pairs, returns scores in order."""

    def __init__(self, scores):
        self._scores = list(scores)
        self.seen_pairs = None
        self.predict_calls = 0

    def predict(self, pairs):
        self.predict_calls += 1
        self.seen_pairs = list(pairs)
        return self._scores[: len(self.seen_pairs)]


def _unit(text: str, page: int) -> EvidenceUnit:
    return EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Xu 2018",
        page=page,
        text=text,
        source_chunk_id=uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# Test 1 -- input/output contract of the existing protocol
# ---------------------------------------------------------------------------
def test_adapter_satisfies_the_existing_reranker_protocol():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    reranker = CrossEncoderReranker(model_factory=lambda name: RecordingCrossEncoder([0.0]))
    assert isinstance(reranker, EvidenceReranker)


def test_query_goes_first_and_texts_are_passed_in_input_order():
    """The v1 reranker built ``(query, doc_text)`` pairs. Never the reverse."""
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([1.0, 2.0, 3.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    reranker.rerank("convergence rate", ["alpha", "beta", "gamma"])

    assert model.seen_pairs == [
        ("convergence rate", "alpha"),
        ("convergence rate", "beta"),
        ("convergence rate", "gamma"),
    ]


def test_returned_indices_point_back_into_the_input_sequence():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([0.5, 9.0, -3.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    result = reranker.rerank("q", ["alpha", "beta", "gamma"])

    assert sorted(index for index, _ in result) == [0, 1, 2]
    assert dict(result) == {0: pytest.approx(0.5), 1: pytest.approx(9.0), 2: pytest.approx(-3.0)}


def test_empty_input_short_circuits_without_touching_the_model():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([1.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    assert reranker.rerank("q", []) == []
    assert model.predict_calls == 0
    assert reranker.is_loaded is False


# ---------------------------------------------------------------------------
# Test 2 -- ordering is score-descending, as the selection policy expects
# ---------------------------------------------------------------------------
def test_output_is_sorted_score_descending():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([0.11, 8.4, -1.47, 2.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    result = reranker.rerank("q", ["a", "b", "c", "d"])

    assert [index for index, _ in result] == [1, 3, 0, 2]
    assert [score for _, score in result] == sorted(
        (score for _, score in result), reverse=True
    )


def test_negative_logits_are_preserved_not_clamped():
    """ms-marco cross-encoder logits are unbounded; the spike recorded -1.47."""
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([-0.49, -1.47])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    scores = [score for _, score in reranker.rerank("q", ["a", "b"])]
    assert scores == [pytest.approx(-0.49), pytest.approx(-1.47)]


def test_apply_reranker_reorders_units_by_the_adapter_ordering():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    units = [_unit("alpha", 1), _unit("beta", 2), _unit("gamma", 3)]
    model = RecordingCrossEncoder([0.1, 5.0, 1.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    reranked = apply_reranker(reranker, query="q", units=units)

    assert [unit.text for unit in reranked] == ["beta", "gamma", "alpha"]
    assert [unit.rerank_score for unit in reranked] == [
        pytest.approx(5.0),
        pytest.approx(1.0),
        pytest.approx(0.1),
    ]


def test_batch_rerank_uses_one_predict_call_and_preserves_pair_and_group_order():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([0.1, 3.0, 2.0, -1.0, 4.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model)

    result = reranker.rerank_many(
        [
            ("formulation", ["alpha", "beta"]),
            ("convergence", ["gamma", "delta", "epsilon"]),
        ]
    )

    assert model.predict_calls == 1
    assert model.seen_pairs == [
        ("formulation", "alpha"),
        ("formulation", "beta"),
        ("convergence", "gamma"),
        ("convergence", "delta"),
        ("convergence", "epsilon"),
    ]
    assert result == [
        [(1, pytest.approx(3.0)), (0, pytest.approx(0.1))],
        [
            (2, pytest.approx(4.0)),
            (0, pytest.approx(2.0)),
            (1, pytest.approx(-1.0)),
        ],
    ]


def test_top_k_truncates_only_when_explicitly_configured():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    model = RecordingCrossEncoder([0.1, 5.0, 1.0])
    reranker = CrossEncoderReranker(model_factory=lambda name: model, top_k=2)

    result = reranker.rerank("q", ["a", "b", "c"])
    assert [index for index, _ in result] == [1, 2]


# ---------------------------------------------------------------------------
# Test 3 -- model loading is lazy
# ---------------------------------------------------------------------------
def test_constructing_the_adapter_does_not_load_the_model():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    calls: list[str] = []

    def factory(name: str):
        calls.append(name)
        return RecordingCrossEncoder([1.0])

    reranker = CrossEncoderReranker(model_factory=factory)

    assert calls == []
    assert reranker.is_loaded is False

    reranker.rerank("q", ["a"])
    assert calls == ["cross-encoder/ms-marco-MiniLM-L-6-v2"]
    assert reranker.is_loaded is True


def test_the_model_is_loaded_once_and_cached():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    calls: list[str] = []

    def factory(name: str):
        calls.append(name)
        return RecordingCrossEncoder([1.0, 1.0])

    reranker = CrossEncoderReranker(model_factory=factory)
    reranker.rerank("q", ["a"])
    reranker.rerank("q", ["b"])

    assert calls == ["cross-encoder/ms-marco-MiniLM-L-6-v2"]


def test_heavy_libraries_are_not_top_level_imports():
    """Same AST discipline as the OpenScholar adapter (test_generator.py)."""
    from src.synthesis.fast_v2.selection import cross_encoder

    tree = ast.parse(inspect.getsource(cross_encoder))
    top_level_imports = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module.split(".")[0])

    assert "sentence_transformers" not in top_level_imports
    assert "torch" not in top_level_imports
    assert "transformers" not in top_level_imports


def test_the_real_loader_still_exists_inside_a_function():
    """A lazy import that was deleted would make this adapter a stub."""
    from src.synthesis.fast_v2.selection import cross_encoder

    source = inspect.getsource(cross_encoder)
    assert "from sentence_transformers import CrossEncoder" in source


# ---------------------------------------------------------------------------
# Test 4 -- importing fast_v2 on a CPU-only machine is safe
# ---------------------------------------------------------------------------
def test_importing_fast_v2_pulls_in_no_heavy_model_library():
    """Walk every fast_v2 module's AST; none may import a heavy lib at module
    scope. A module-scope import would load the model on any CPU-only box that
    merely imports the package."""
    import pathlib
    import pkgutil

    import src.synthesis.fast_v2 as fast_v2

    heavy = {"sentence_transformers", "torch", "transformers", "vllm"}
    offenders: list[str] = []
    seen = 0

    for module_info in pkgutil.walk_packages(fast_v2.__path__, f"{fast_v2.__name__}."):
        module = __import__(module_info.name, fromlist=["_"])
        source_file = getattr(module, "__file__", None)
        if source_file is None:
            continue
        seen += 1
        tree = ast.parse(pathlib.Path(source_file).read_text(encoding="utf-8"))
        for node in tree.body:
            names: set[str] = set()
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            if names & heavy:
                offenders.append(f"{module_info.name}: {sorted(names & heavy)}")

    assert seen >= 10, "the walk must actually have inspected the fast_v2 modules"
    assert offenders == []


def test_fast_v2_import_does_not_register_heavy_modules_in_sys_modules():
    import subprocess
    import sys

    code = (
        "import sys; import src.synthesis.fast_v2.pipeline; "
        "import src.synthesis.fast_v2.selection.cross_encoder; "
        "print(sorted(m for m in ('sentence_transformers','torch','vllm') if m in sys.modules))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert completed.stdout.strip() == "[]", completed.stdout


# ---------------------------------------------------------------------------
# Test 5 -- IdentityReranker regression: unchanged and still usable
# ---------------------------------------------------------------------------
def test_identity_reranker_still_returns_input_order_with_zero_scores():
    reranker = IdentityReranker()
    assert reranker.rerank("q", ["a", "b", "c"]) == [(0, 0.0), (1, 0.0), (2, 0.0)]
    assert reranker.rerank("q", []) == []
    assert isinstance(reranker, EvidenceReranker)


def test_identity_reranker_preserves_retrieval_ordering_through_apply():
    units = [_unit("alpha", 1), _unit("beta", 2)]
    reranked = apply_reranker(IdentityReranker(), query="q", units=units)
    assert [unit.text for unit in reranked] == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# Test 6 -- selection via config / dependency injection
# ---------------------------------------------------------------------------
def test_default_config_selects_the_deterministic_identity_reranker():
    from src.config import Settings

    assert Settings(_env_file=None).fast_v2_reranker == "identity"


def test_factory_returns_identity_by_default():
    from src.synthesis.fast_v2.selection.factory import build_reranker

    assert isinstance(build_reranker(), IdentityReranker)


def test_factory_returns_the_cross_encoder_when_explicitly_configured():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker
    from src.synthesis.fast_v2.selection.factory import build_reranker

    reranker = build_reranker(mode="cross_encoder")

    assert isinstance(reranker, CrossEncoderReranker)
    assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Selecting it must still not load anything.
    assert reranker.is_loaded is False


def test_factory_rejects_an_unknown_reranker_name_loudly():
    from src.synthesis.fast_v2.selection.factory import build_reranker

    with pytest.raises(ValueError, match="unknown"):
        build_reranker(mode="totally-not-a-reranker")


def test_config_rejects_an_unknown_reranker_value():
    from pydantic import ValidationError

    from src.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, fast_v2_reranker="qwen3")


def test_pipeline_accepts_the_cross_encoder_via_dependency_injection():
    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    reranker = CrossEncoderReranker(model_factory=lambda name: RecordingCrossEncoder([1.0]))
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever([]),
        generator=FakeSynthesisGenerator(),
        reranker=reranker,
    )

    assert pipeline.reranker is reranker


def test_pipeline_still_defaults_to_identity_when_no_reranker_is_injected():
    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline

    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever([]),
        generator=FakeSynthesisGenerator(),
    )

    assert isinstance(pipeline.reranker, IdentityReranker)


# ---------------------------------------------------------------------------
# Test 7 -- no query-time extraction LLM call is introduced
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cross_encoder_path_makes_zero_extraction_llm_calls():
    """Extends the frozen zero-extraction invariant to the real reranker."""
    from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    class CountingLLM:
        def __init__(self) -> None:
            self.calls = 0

        def __getattr__(self, name: str):
            def _boom(*args, **kwargs):
                self.calls += 1
                raise AssertionError(
                    f"fast_v2 invoked an evidence-extraction LLM ({name}); "
                    "query-time extraction LLM calls must be zero."
                )

            return _boom

    extraction_llm = CountingLLM()
    units = [_unit("alpha", 1), _unit("beta", 2)]
    model = RecordingCrossEncoder([2.0, 1.0])

    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        generator=FakeSynthesisGenerator(),
        reranker=CrossEncoderReranker(model_factory=lambda name: model),
        extraction_llm=extraction_llm,
    )

    result = await pipeline.run(question="Q", dimensions=["convergence"])

    assert extraction_llm.calls == 0
    assert result.timings["extraction_calls"] == 0


def test_the_adapter_module_contains_no_llm_client_import():
    from src.synthesis.fast_v2.selection import cross_encoder

    source = inspect.getsource(cross_encoder)
    for forbidden in ("openai", "litellm", "langchain_openai", "ChatGoogleGenerative"):
        assert forbidden not in source
