"""Evidence-First retrieval.

Evidence is retrieved from **reusable canonical chunk representations** that
were produced once at ingestion. There is **no query-time LLM** anywhere in
this module: no ``extract_paper`` call, no evidence-extraction call, no
recovery-extraction loop. That is the central fast_v2 invariant.

Embeddings come from the corrected production backend already configured in
this worktree (``EMBEDDING_PROVIDER=local`` ->
``sentence-transformers/all-MiniLM-L6-v2``, dim 384). The non-semantic hash
embedding stays explicit debug-only (``EMBEDDING_PROVIDER=hash-debug``) and is
never a fallback -- see ``src/services/vector_store.py``.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


@runtime_checkable
class EvidenceRetriever(Protocol):
    """Returns reusable EvidenceUnits for one dimension query."""

    async def retrieve(
        self, query: str, *, limit: int, paper_id: uuid.UUID | None = None
    ) -> Sequence[EvidenceUnit]:
        ...


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evidence_unit_from_document(document: Any, score: float | None = None) -> EvidenceUnit | None:
    """Map a retrieved chunk Document onto an EvidenceUnit.

    Returns ``None`` when the document lacks the provenance needed to cite it.
    Evidence that cannot be traced back to canonical PDF/PageText provenance
    is dropped rather than surfaced without a citation.
    """
    metadata = getattr(document, "metadata", None) or {}
    text = getattr(document, "page_content", "") or ""
    if not text.strip():
        return None

    paper_id = _coerce_uuid(metadata.get("paper_id"))
    if paper_id is None:
        return None

    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=str(metadata.get("paper_title") or metadata.get("title") or "Unknown Title"),
        page=_coerce_int(metadata.get("page")),
        text=text,
        source_chunk_id=_coerce_uuid(metadata.get("chunk_id")),
        page_text_id=_coerce_uuid(metadata.get("page_text_id")),
        page_char_start=_coerce_int(metadata.get("page_char_start")),
        page_char_end=_coerce_int(metadata.get("page_char_end")),
        retrieval_score=score,
    )


class VectorStoreEvidenceRetriever:
    """Evidence-First retriever over the existing Chroma vector store.

    Performs semantic search only. It never invokes an LLM.
    """

    def __init__(self, vector_store_service: Any, *, paper_ids: Sequence[uuid.UUID] | None = None):
        self._vector_store = vector_store_service
        self._paper_ids = [str(pid) for pid in (paper_ids or [])]

    def _filters(self, paper_id: uuid.UUID | None = None) -> dict[str, Any] | None:
        if paper_id is not None:
            if self._paper_ids and str(paper_id) not in self._paper_ids:
                raise ValueError("paper_id scope must be one of the selected paper IDs")
            return {"paper_id": str(paper_id)}
        if not self._paper_ids:
            return None
        if len(self._paper_ids) == 1:
            return {"paper_id": self._paper_ids[0]}
        return {"paper_id": {"$in": self._paper_ids}}

    async def retrieve(
        self, query: str, *, limit: int, paper_id: uuid.UUID | None = None
    ) -> list[EvidenceUnit]:
        results = await self._vector_store.search_similar_documents_with_scores(
            query, top_k=limit, filters=self._filters(paper_id)
        )

        units: list[EvidenceUnit] = []
        for entry in results or []:
            document, score = entry if isinstance(entry, tuple) else (entry, None)
            unit = evidence_unit_from_document(document, score)
            if unit is not None:
                units.append(unit)
        return units


class StaticEvidenceRetriever:
    """Deterministic retriever over a fixed unit list -- tests and smoke runs.

    Not a semantic retriever. It returns the first ``limit`` units and records
    the queries it was asked, so tests can assert query construction.
    """

    def __init__(self, units: Sequence[EvidenceUnit]):
        self._units = list(units)
        self.queries: list[str] = []

    async def retrieve(
        self, query: str, *, limit: int, paper_id: uuid.UUID | None = None
    ) -> list[EvidenceUnit]:
        self.queries.append(query)
        units = self._units
        if paper_id is not None:
            units = [unit for unit in units if unit.paper_id == paper_id]
        return units[:limit]
