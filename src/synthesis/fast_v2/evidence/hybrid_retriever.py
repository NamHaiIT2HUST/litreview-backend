"""Hybrid (dense + BM25) Evidence-First retriever, fused with Reciprocal Rank Fusion.

Satisfies the ``EvidenceRetriever`` protocol (``evidence/retrieval.py``).
Dense-only retrieval (semantic embedding cosine similarity) misses exact
terminology/formula/algorithm-name matches that a domain scientist expects a
literature search to catch; BM25 alone misses paraphrase/semantic relation.
Fusing both with RRF gets the benefit of each without picking one.

Both legs query the SAME persistent ``FastV2SemanticIndex`` -- dense via its
existing ``query()`` (embedding), lexical via its ``keyword_query()`` (BM25
over the same paper-scoped document set, see ``evidence/bm25.py``). No
separate index to build or keep in sync.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex

#: Standard RRF constant (Cormack, Clarke & Buettcher 2009) -- dampens the
#: influence of rank 1 vs rank 2 so one leg's top hit doesn't dominate purely
#: by being first; not tuned per-corpus.
RRF_K = 60


class FastV2HybridEvidenceRetriever:
    """Production Evidence-First retriever: dense + BM25, RRF-fused."""

    def __init__(
        self,
        index: FastV2SemanticIndex,
        *,
        paper_ids: Sequence[uuid.UUID],
        pool_multiplier: int = 3,
        min_pool: int = 40,
    ) -> None:
        self._index = index
        self._paper_ids = list(paper_ids)
        self._pool_multiplier = pool_multiplier
        self._min_pool = min_pool

    async def retrieve(
        self, query: str, *, limit: int, paper_id: uuid.UUID | None = None
    ) -> list[EvidenceUnit]:
        scoped_ids = [paper_id] if paper_id is not None else self._paper_ids
        pool_limit = max(limit * self._pool_multiplier, self._min_pool)

        dense_units, bm25_units = await asyncio.gather(
            asyncio.to_thread(self._index.query, query, limit=pool_limit, paper_ids=scoped_ids),
            asyncio.to_thread(self._index.keyword_query, query, limit=pool_limit, paper_ids=scoped_ids),
        )

        rrf_scores: dict[str, float] = {}
        by_id: dict[str, EvidenceUnit] = {}
        for rank, unit in enumerate(dense_units):
            rrf_scores[unit.evidence_id] = rrf_scores.get(unit.evidence_id, 0.0) + 1.0 / (RRF_K + rank + 1)
            by_id.setdefault(unit.evidence_id, unit)
        for rank, unit in enumerate(bm25_units):
            rrf_scores[unit.evidence_id] = rrf_scores.get(unit.evidence_id, 0.0) + 1.0 / (RRF_K + rank + 1)
            by_id.setdefault(unit.evidence_id, unit)

        ranked_ids = sorted(rrf_scores, key=lambda eid: rrf_scores[eid], reverse=True)[:limit]
        # retrieval_score is overwritten with the fused RRF score -- this is
        # what downstream fusion/cap/selection (pipeline.py) sorts by, so it
        # must reflect the combined ranking, not either leg's raw score alone.
        return [
            by_id[evidence_id].with_scores(retrieval_score=rrf_scores[evidence_id])
            for evidence_id in ranked_ids
        ]
