"""Reranker boundary.

**This module deliberately introduces no reranker model, service, or scoring
convention.** The target worktree contains none, and the validated experiments
used an externally supplied cross-encoder. Introducing a second reranker or
changing the scoring convention is explicitly out of scope for this freeze.

What this module does provide is a pinned contract, because getting the call
signature and return order wrong is exactly what bit the v1 experiment:

* ``rerank(query, texts)`` takes the query first and the candidate texts second.
* It returns ``(index, score)`` pairs, where ``index`` refers back into the
  **input** ``texts`` sequence.
* The returned sequence is in the **reranker's** order (best first). It is NOT
  guaranteed to be in input order, and it MAY be shorter than the input if the
  implementation drops candidates. Callers must re-associate by ``index`` and
  must never zip scores onto inputs positionally.
* Scores are raw cross-encoder logits: unbounded, and **legitimately
  negative**. Do not assume a 0..1 range.

Wiring a concrete reranker is a follow-up task (promotion criterion 6).
"""
from __future__ import annotations

import time
from typing import Any, Protocol, Sequence, runtime_checkable

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


@runtime_checkable
class EvidenceReranker(Protocol):
    """Scores candidate texts against one query. See module docstring."""

    def rerank(self, query: str, texts: Sequence[str]) -> Sequence[tuple[int, float]]:
        ...


def apply_reranker(
    reranker: EvidenceReranker,
    *,
    query: str,
    units: Sequence[EvidenceUnit],
) -> list[EvidenceUnit]:
    """Attach rerank scores to ``units``, re-associating strictly by index.

    Returns units in the reranker's own order. Units the reranker did not
    return are dropped, which is the reranker's decision to make -- this
    function never invents a score.
    """
    if not units:
        return []

    scored: list[EvidenceUnit] = []
    for index, score in reranker.rerank(query, [unit.text for unit in units]):
        if not 0 <= index < len(units):
            raise IndexError(
                f"Reranker returned out-of-range index {index} for "
                f"{len(units)} candidates; check the return-order contract "
                "documented in src/synthesis/fast_v2/selection/rerank.py."
            )
        scored.append(units[index].with_scores(rerank_score=float(score)))
    return scored


def apply_reranker_many(
    reranker: EvidenceReranker,
    *,
    requests: Sequence[tuple[str, Sequence[EvidenceUnit]]],
) -> list[list[EvidenceUnit]]:
    """Apply an optional batch capability without changing reranker protocol.

    Rerankers without ``rerank_many`` retain the exact sequential behavior.
    Batch-capable rerankers must return one scored group per request, in the
    same request order.
    """
    groups = [(query, list(units)) for query, units in requests]
    rerank_many = getattr(reranker, "rerank_many", None)
    if not callable(rerank_many):
        return [
            apply_reranker(reranker, query=query, units=units)
            for query, units in groups
        ]

    ranked_groups = list(
        rerank_many(
            [(query, [unit.text for unit in units]) for query, units in groups]
        )
    )
    if len(ranked_groups) != len(groups):
        raise ValueError(
            f"Batch reranker returned {len(ranked_groups)} groups for "
            f"{len(groups)} requests; group association must be complete."
        )

    results: list[list[EvidenceUnit]] = []
    for (_query, units), ranked in zip(groups, ranked_groups):
        scored: list[EvidenceUnit] = []
        for index, score in ranked:
            if not 0 <= index < len(units):
                raise IndexError(
                    f"Reranker returned out-of-range index {index} for "
                    f"{len(units)} candidates; check the batch return-order contract."
                )
            scored.append(units[index].with_scores(rerank_score=float(score)))
        results.append(scored)
    return results


#: Benchmarked against real cross-encoder pairs (~1600 chars avg,
#: max_length=512): batch_size 8/16/32 wall-clock differs by <6% on CPU --
#: this is compute-bound, not batching-bound, so 32 (fewer Python-level
#: chunks) is kept as default. Configurable because the right value can
#: differ by CPU/deployment target.
GTE_DEFAULT_BATCH_SIZE = 32


class CrossEncoderReranker:
    """Production cross-encoder reranker wrapping RerankerService
    (Alibaba-NLP/gte-reranker-modernbert-base -- BGE is retired, see
    src/services/reranker_service.py for the model actually loaded)."""

    def __init__(self, service: Any | None = None, *, batch_size: int = GTE_DEFAULT_BATCH_SIZE) -> None:
        if service is None:
            from src.services.reranker_service import reranker_service
            self._service = reranker_service
        else:
            self._service = service
        self.batch_size = batch_size
        #: Populated after each rerank()/rerank_many() call.
        self.last_inference_ms: float | None = None
        self.last_forward_call_count: int = 0

    def load(self) -> Any:
        """Materialise the model now. Lets application startup warmup
        (``warm_fast_v2`` in runtime.py) pay the model-load cost once, up
        front, instead of on the first real synthesis request."""
        return self._service._get_model()

    def rerank(self, query: str, texts: Sequence[str]) -> list[tuple[int, float]]:
        return self.rerank_many(((query, texts),))[0]

    def rerank_many(
        self,
        requests: Sequence[tuple[str, Sequence[str]]],
    ) -> list[list[tuple[int, float]]]:
        """Score ordered query/text groups with ONE model.predict() call.

        Pairs are flattened group-major (section-major) and text-major, so
        section N's candidates always occupy the same slice regardless of
        how many other sections are batched alongside it. Scores are split
        back out and ranked INDEPENDENTLY per group -- batching pairs for
        one shared forward pass never mixes ranking across sections; the
        query differs per group and sorting happens strictly within each
        group's own score slice.
        """
        groups = [(query, list(texts)) for query, texts in requests]
        pairs = [[query, text] for query, texts in groups for text in texts]
        if not pairs:
            self.last_inference_ms = 0.0
            self.last_forward_call_count = 0
            return [[] for _ in groups]

        model = self._service._get_model()
        # RerankerService returns the literal string "fallback" (not raising)
        # when its local model directory is missing or fails to load --
        # calling .predict() on that would crash with an opaque
        # AttributeError. Fail loudly with a clear message instead, per this
        # pipeline's own "never silently reach for the wrong evidence"
        # principle (see selection/factory.py's reranker-selection comment).
        if not hasattr(model, "predict"):
            raise RuntimeError(
                "fast_v2_reranker='gte' selected but the underlying reranker "
                "model is not loaded (RerankerService fell back to a "
                "placeholder -- its local model directory './models/temp_bge-base' "
                "is missing or failed to load). Refusing to silently use an "
                "unrelated/no-op fallback here; either provide the model "
                "locally or select fast_v2_reranker='identity'/'cross_encoder'."
            )

        t0 = time.perf_counter()
        scores = model.predict(pairs, batch_size=self.batch_size)
        self.last_inference_ms = (time.perf_counter() - t0) * 1000.0
        self.last_forward_call_count = 1

        if len(scores) != len(pairs):
            raise ValueError(
                f"Reranker returned {len(scores)} scores for {len(pairs)} "
                "candidates; scores must be positional and complete."
            )

        results: list[list[tuple[int, float]]] = []
        offset = 0
        for _query, texts in groups:
            group_scores = scores[offset : offset + len(texts)]
            offset += len(texts)
            indexed_scores = [(i, float(score)) for i, score in enumerate(group_scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            results.append(indexed_scores)
        return results


class IdentityReranker:
    """Debug/test-only passthrough that preserves the retrieval score.

    NOT a reranker. It exists so the pipeline can be exercised end-to-end on
    CPU without a cross-encoder. Using it in a real run means "no reranking
    happened", and the recorded rerank timings will be meaningless.
    """

    def rerank(self, query: str, texts: Sequence[str]) -> list[tuple[int, float]]:
        return [(index, 0.0) for index, _ in enumerate(texts)]
