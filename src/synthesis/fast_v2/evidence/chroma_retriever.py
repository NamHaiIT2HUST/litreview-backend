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
from typing import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex


class FastV2ChromaEvidenceRetriever:
    """Production Evidence-First retriever over the persistent Fast v2 index."""

    def __init__(self, index: FastV2SemanticIndex, *, paper_ids: Sequence[uuid.UUID]) -> None:
        self._index = index
        self._paper_ids = list(paper_ids)

    async def retrieve(self, query: str, *, limit: int) -> list[EvidenceUnit]:
        return await asyncio.to_thread(
            self._index.query, query, limit=limit, paper_ids=self._paper_ids
        )
