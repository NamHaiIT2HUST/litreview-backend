"""TDD coverage for the GTE reranker latency-optimization pass: model
lifecycle (singleton reuse), batched multi-section inference via
rerank_many, section-local ranking correctness, and configurable batch
size. All model inference is mocked -- no real model download/load in
these tests.

NOTE: src/services/reranker_service.py's own rewrite (hard-swap to
Alibaba-NLP/gte-reranker-modernbert-base with local_files_only=True) was
deliberately NOT ported from feat/synthesis-fast-v2-ui -- that model isn't
cached locally or on the EC2 deployment target, and reranker_service.py is
shared with the live default paper-search reranking endpoints (not gated
behind fast_v2_reranker="gte", which stays "identity" by default). Only
the self-contained CrossEncoderReranker batching/telemetry rewrite in
src/synthesis/fast_v2/selection/rerank.py was ported, so the load-lifecycle
telemetry test that depended on the reranker_service.py rewrite is omitted.
"""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.selection.rerank import CrossEncoderReranker, apply_reranker_many


class _FakeModel:
    """Deterministic stand-in for sentence_transformers.CrossEncoder.
    Score = negative index within the query's own text list, so ordering
    is predictable and reversible for assertions."""

    def __init__(self):
        self.predict_call_count = 0
        self.last_batch_size = None
        self.last_pairs_len = None

    def predict(self, pairs, batch_size=32):
        self.predict_call_count += 1
        self.last_batch_size = batch_size
        self.last_pairs_len = len(pairs)
        # Score by a hash of (query, text) so groups don't collide in score
        # space, but is fully deterministic across runs.
        return [float(-(hash((q, t)) % 1000)) for q, t in pairs]


class _FakeRerankerService:
    def __init__(self, model=None, load_ms=None):
        self._model = model or _FakeModel()
        self.last_load_ms = load_ms
        self.loaded_this_process = model is not None
        self.last_call_triggered_load = False
        self.get_model_calls = 0

    def _get_model(self):
        self.get_model_calls += 1
        if self._model is None:
            self.last_call_triggered_load = True
            self.loaded_this_process = True
            self._model = _FakeModel()
        else:
            self.last_call_triggered_load = False
        return self._model


def _unit(evidence_id: str, text: str) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=evidence_id, paper_id=uuid.uuid4(), title="Paper", page=1,
        text=text, source_chunk_id=None, page_text_id=None,
    )


# 1 & 2: model loaded at most once per process; 5 sections don't create 5 instances
def test_model_loaded_at_most_once_across_many_rerank_calls():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    for i in range(5):
        reranker.rerank(f"query {i}", [f"text {i} a", f"text {i} b"])
    assert service.get_model_calls == 5  # _get_model called each time...
    assert service._model.predict_call_count == 5  # ...but always the SAME model instance


def test_five_sections_share_one_model_instance_not_five():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    seen_model_ids = set()
    for i in range(5):
        reranker.rerank(f"query {i}", ["text a", "text b"])
        seen_model_ids.add(id(service._get_model()))
    assert len(seen_model_ids) == 1


# 3 & 4: multi-section batched inference, results map back to correct section
def test_rerank_many_batches_all_sections_into_one_predict_call():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    requests = [
        ("query for section A", ["a-text-0", "a-text-1", "a-text-2"]),
        ("query for section B", ["b-text-0", "b-text-1"]),
    ]
    results = reranker.rerank_many(requests)
    assert service._model.predict_call_count == 1
    assert service._model.last_pairs_len == 5  # 3 + 2, one shared call
    assert len(results) == 2
    assert len(results[0]) == 3
    assert len(results[1]) == 2


def test_rerank_many_results_map_back_to_correct_section_texts():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    requests = [
        ("qA", ["a0", "a1"]),
        ("qB", ["b0", "b1", "b2"]),
    ]
    results = reranker.rerank_many(requests)
    # every index in section A's results must be a valid index into section A's own list (0,1)
    for idx, _score in results[0]:
        assert 0 <= idx < 2
    for idx, _score in results[1]:
        assert 0 <= idx < 3


# 5 & 6: ranking stays section-local; top-k unchanged vs old per-section inference
def test_ranking_is_section_local_not_mixed_across_sections():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    requests = [(f"q{i}", [f"t{i}-{j}" for j in range(4)]) for i in range(3)]
    batched = reranker.rerank_many(requests)

    # Compare against calling rerank() independently per section (old path).
    service_seq = _FakeRerankerService(model=service._model)  # same model = same scoring function
    reranker_seq = CrossEncoderReranker(service=service_seq)
    sequential = [reranker_seq.rerank(q, texts) for q, texts in requests]

    for b_group, s_group in zip(batched, sequential):
        assert b_group == s_group  # identical ranking + scores per section, batched or not


def test_top_k_selection_matches_sequential_per_section_baseline():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    requests = [("q1", [f"t{j}" for j in range(6)]), ("q2", [f"u{j}" for j in range(6)])]
    batched = reranker.rerank_many(requests)
    top2_batched = [[idx for idx, _ in group[:2]] for group in batched]

    reranker2 = CrossEncoderReranker(service=_FakeRerankerService(model=service._model))
    sequential = [reranker2.rerank(q, texts) for q, texts in requests]
    top2_sequential = [[idx for idx, _ in group[:2]] for group in sequential]

    assert top2_batched == top2_sequential


# 7: batch size configurable
def test_batch_size_is_configurable_and_passed_to_predict():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service, batch_size=8)
    reranker.rerank_many([("q", ["a", "b", "c"])])
    assert service._model.last_batch_size == 8


def test_default_batch_size_is_32():
    reranker = CrossEncoderReranker(service=_FakeRerankerService())
    assert reranker.batch_size == 32


# 8 & 9: empty section behaves correctly; one-section path still works
def test_empty_section_in_a_multi_section_batch_returns_empty_group():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    results = reranker.rerank_many([("q1", ["a", "b"]), ("q2", [])])
    assert results[1] == []
    assert len(results[0]) == 2


def test_all_sections_empty_never_touches_the_model():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    results = reranker.rerank_many([("q1", []), ("q2", [])])
    assert results == [[], []]
    assert service.get_model_calls == 0


def test_single_section_path_still_works_via_apply_reranker_many():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    units = [_unit("ev-1", "text one"), _unit("ev-2", "text two")]
    result = apply_reranker_many(reranker, requests=[("q", units)])
    assert len(result) == 1
    assert len(result[0]) == 2
    assert all(u.rerank_score is not None for u in result[0])


# 10: inference failure surfaced cleanly
def test_inference_failure_propagates_not_swallowed():
    class _BrokenModel:
        def predict(self, pairs, batch_size=32):
            raise RuntimeError("simulated inference crash")

    service = _FakeRerankerService(model=_BrokenModel())
    reranker = CrossEncoderReranker(service=service)
    with pytest.raises(RuntimeError, match="simulated inference crash"):
        reranker.rerank_many([("q", ["a", "b"])])


def test_missing_predict_method_raises_clear_runtime_error():
    # rerank.py's own failure check is hasattr(model, "predict") -- matching
    # the existing (pre-existing-this-session) reranker_service.py, which
    # signals "no usable model" by returning the literal string "fallback",
    # not None. See the RuntimeError message in
    # src/synthesis/fast_v2/selection/rerank.py::CrossEncoderReranker.rerank_many.
    service = _FakeRerankerService()
    service._get_model = lambda: "fallback"
    reranker = CrossEncoderReranker(service=service)
    with pytest.raises(RuntimeError, match="not loaded"):
        reranker.rerank_many([("q", ["a"])])


def test_score_count_mismatch_raises_value_error():
    class _MismatchedModel:
        def predict(self, pairs, batch_size=32):
            return [1.0]  # wrong count for >1 pair

    service = _FakeRerankerService(model=_MismatchedModel())
    reranker = CrossEncoderReranker(service=service)
    with pytest.raises(ValueError, match="scores"):
        reranker.rerank_many([("q", ["a", "b"])])


# 11: telemetry records inference timing
def test_inference_timing_telemetry_is_recorded():
    service = _FakeRerankerService()
    reranker = CrossEncoderReranker(service=service)
    assert reranker.last_inference_ms is None
    reranker.rerank_many([("q", ["a", "b"])])
    assert reranker.last_inference_ms is not None
    assert reranker.last_inference_ms >= 0.0
    assert reranker.last_forward_call_count == 1
