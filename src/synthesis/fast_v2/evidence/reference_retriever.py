"""Reference retriever -- reproduces the validated Dimension-Aware v1 experiment.

**Not the production default.** ``VectorStoreEvidenceRetriever`` (Chroma) is
fast_v2's normal retrieval path and is untouched by this module. This class
exists solely so a parity harness can replay the exact retrieval mechanism
that produced the validated v1 bank sizes/scores, so the rest of the fast_v2
pipeline (hygiene, reranker, selection policy, merge) can be tested against a
known-faithful evidence source instead of an unverified production index.

Reproduces, verbatim, the original spike's approach
(``dimension_aware_v0/run_dimension_aware_v1.py`` /
``spike_evidence_first_v2_section_routing.py``):

* fetch canonical ``PDFChunk`` rows for the given paper IDs from Postgres;
* embed the corpus fresh, in-memory, with
  ``sentence-transformers/all-MiniLM-L6-v2`` (no Chroma, no cached index);
* embed the query fresh with the same model;
* cosine similarity, exact (not approximate-nearest-neighbour);
* return the top ``limit`` candidates, best first.

Model load is lazy (first :meth:`retrieve` call), matching
``CrossEncoderReranker`` and ``OpenScholarGenerator``'s laziness discipline --
importing this module on a CPU-only machine must not pull in torch.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Sequence

import numpy as np

from src.synthesis.fast_v2.evidence.models import EvidenceUnit

REFERENCE_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class InMemoryCosineEvidenceRetriever:
    """Fresh in-memory cosine retrieval over a fixed paper set. Parity/reproducibility only."""

    def __init__(
        self,
        session_factory: Callable[[], Any],
        *,
        paper_ids: Sequence[uuid.UUID],
        model_name: str = REFERENCE_EMBED_MODEL,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._paper_ids = list(paper_ids)
        self._model_name = model_name
        self._model_factory = model_factory
        self._model: Any = None

        # Populated once by _ensure_corpus(); the corpus and its embedding
        # matrix are fixed for the lifetime of this retriever instance.
        self._units: list[EvidenceUnit] | None = None
        self._matrix_normed: np.ndarray | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _default_model_factory(self, model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    def _load_model(self) -> Any:
        if self._model is None:
            factory = self._model_factory or self._default_model_factory
            self._model = factory(self._model_name)
        return self._model

    async def _ensure_corpus(self) -> None:
        if self._units is not None:
            return

        from sqlalchemy import select

        from src.models.db_models import Paper, PDFChunk

        units: list[EvidenceUnit] = []
        async with self._session_factory() as db:
            chunk_rows = await db.execute(
                select(PDFChunk).where(PDFChunk.paper_id.in_(self._paper_ids))
            )
            chunks = list(chunk_rows.scalars().all())

            paper_rows = await db.execute(select(Paper).where(Paper.id.in_(self._paper_ids)))
            title_by_paper = {p.id: p.title for p in paper_rows.scalars().all()}

        for chunk in chunks:
            units.append(
                EvidenceUnit.from_chunk(
                    paper_id=chunk.paper_id,
                    title=title_by_paper.get(chunk.paper_id, "Unknown Title"),
                    page=chunk.page,
                    text=chunk.chunk_text,
                    source_chunk_id=chunk.id,
                    page_text_id=chunk.page_text_id,
                    page_char_start=chunk.page_char_start,
                    page_char_end=chunk.page_char_end,
                )
            )

        self._units = units
        if not units:
            self._matrix_normed = np.zeros((0, 0))
            return

        model = self._load_model()
        embeddings = model.encode(
            [unit.text for unit in units], convert_to_numpy=True, show_progress_bar=False
        )
        matrix = np.asarray(embeddings)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self._matrix_normed = matrix / np.where(norms == 0, 1, norms)

    async def retrieve(self, query: str, *, limit: int) -> list[EvidenceUnit]:
        await self._ensure_corpus()
        units = self._units or []
        if not units:
            return []

        model = self._load_model()
        query_embedding = model.encode([query], convert_to_numpy=True)
        query_vec = query_embedding[0]
        norm = np.linalg.norm(query_vec)
        query_vec = query_vec / (norm if norm else 1)

        scores = self._matrix_normed @ query_vec
        ranked_idx = np.argsort(-scores)[:limit]

        return [
            units[i].with_scores(retrieval_score=float(scores[i])) for i in ranked_idx
        ]
