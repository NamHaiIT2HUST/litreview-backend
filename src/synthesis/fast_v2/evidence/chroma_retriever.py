"""Fast v2 production retriever -- persistent semantic Chroma collection.

Satisfies the ``EvidenceRetriever`` protocol
(``src/synthesis/fast_v2/evidence/retrieval.py``). Queries the dedicated
``FastV2SemanticIndex`` (MiniLM-384, versioned collection, no OpenAI
dependency) rather than the Legacy ``VectorStoreService``/Chroma path.

``InMemoryCosineEvidenceRetriever`` remains the parity/reproducibility
oracle. This class is production: same embedding model, same cosine metric,
persistent instead of re-encoded per query.

Chroma calls are synchronous; this wrapper runs them in a thread via
``asyncio.to_thread`` so the async ``EvidenceRetriever`` protocol is honoured
without blocking the event loop.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex


class FastV2ChromaEvidenceRetriever:
    """Production Evidence-First retriever over the persistent Fast v2 index."""

    def __init__(self, index: FastV2SemanticIndex, *, paper_ids: Sequence[uuid.UUID]) -> None:
        self._index = index
        self._paper_ids = list(paper_ids)

    async def retrieve(
        self, query: str, *, limit: int, paper_id: uuid.UUID | None = None
    ) -> list[EvidenceUnit]:
        if paper_id is not None and paper_id not in self._paper_ids:
            raise ValueError("paper_id scope must be one of the selected paper IDs")
        paper_ids = self._paper_ids if paper_id is None else [paper_id]
        return await asyncio.to_thread(
            self._index.query, query, limit=limit, paper_ids=paper_ids
        )
