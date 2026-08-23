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

from typing import Protocol, Sequence, runtime_checkable

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


class IdentityReranker:
    """Debug/test-only passthrough that preserves the retrieval score.

    NOT a reranker. It exists so the pipeline can be exercised end-to-end on
    CPU without a cross-encoder. Using it in a real run means "no reranking
    happened", and the recorded rerank timings will be meaningless.
    """

    def rerank(self, query: str, texts: Sequence[str]) -> list[tuple[int, float]]:
        return [(index, 0.0) for index, _ in enumerate(texts)]
