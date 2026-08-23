"""Evidence-First domain model.

An :class:`EvidenceUnit` is *reusable input evidence*: a canonical PDF chunk
promoted into the retrieval substrate. It is NOT an LLM-generated answer, and
nothing in this module ever calls an LLM.

Why this is a new type rather than a reuse of ``EvidenceRecord``
---------------------------------------------------------------
``EvidenceRecord.created_from_attempt_id`` is ``nullable=False`` and unique --
an ``EvidenceRecord`` cannot exist without an ``EvidenceExtractionAttempt``,
i.e. without a query-time LLM extraction. Evidence-First produces evidence with
no extraction attempt by construction, so reusing ``EvidenceRecord`` would
either violate the schema or require fabricating an extraction-attempt row.
The field-level mapping between the two is documented in
``docs/architecture/FAST_SYNTHESIS_V2.md`` section J.

Identifier discipline
---------------------
``evidence_id`` and ``source_chunk_id`` are DIFFERENT things and both are
carried. Conflating ``EvidenceRecord.id`` with ``PDFChunk.id`` caused a real
defect during the hygiene spike.

* ``source_chunk_id`` -- the ``PDFChunk`` row this text came from.
* ``evidence_id``     -- the canonical dedupe/citation key for fast_v2,
  derived deterministically from the source chunk identity so the same chunk
  retrieved by two different dimension queries dedupes to one unit.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from typing import Any

# Stable namespace so evidence_id is reproducible across processes and runs.
_EVIDENCE_NAMESPACE = uuid.UUID("6f2a1d64-6f9d-5b53-9f2f-1a5c9d0e7b41")


@dataclass(frozen=True)
class EvidenceUnit:
    """One reusable, provenance-carrying piece of canonical source text."""

    evidence_id: str
    paper_id: uuid.UUID
    title: str
    page: int | None
    text: str
    source_chunk_id: uuid.UUID | None
    page_text_id: uuid.UUID | None
    page_char_start: int | None = None
    page_char_end: int | None = None

    retrieval_score: float | None = None
    rerank_score: float | None = None

    # Populated by the hygiene stage; diagnostics only, never mutates the chunk.
    hygiene_class: str | None = None
    hygiene_score: float | None = None
    hygiene_signals: dict[str, Any] = field(default_factory=dict)

    # Populated by dimension selection / merge.
    selected_for_dimensions: tuple[str, ...] = ()
    dimension_scores: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_chunk(
        cls,
        *,
        paper_id: uuid.UUID,
        title: str,
        page: int | None,
        text: str,
        source_chunk_id: uuid.UUID | None,
        page_text_id: uuid.UUID | None = None,
        page_char_start: int | None = None,
        page_char_end: int | None = None,
        retrieval_score: float | None = None,
    ) -> EvidenceUnit:
        """Promote a canonical chunk into an EvidenceUnit.

        ``text`` is kept verbatim -- no summarisation, no rewriting.
        """
        if not (text or "").strip():
            raise ValueError("EvidenceUnit.text must be non-empty canonical source text")

        return cls(
            evidence_id=cls.build_evidence_id(
                paper_id=paper_id,
                source_chunk_id=source_chunk_id,
                page=page,
                text=text,
            ),
            paper_id=paper_id,
            title=title,
            page=page,
            text=text,
            source_chunk_id=source_chunk_id,
            page_text_id=page_text_id,
            page_char_start=page_char_start,
            page_char_end=page_char_end,
            retrieval_score=retrieval_score,
        )

    @staticmethod
    def build_evidence_id(
        *,
        paper_id: uuid.UUID,
        source_chunk_id: uuid.UUID | None,
        page: int | None,
        text: str,
    ) -> str:
        """Deterministic canonical key.

        Derived from chunk identity when available, otherwise from
        (paper, page, text) so chunk-less sources still dedupe stably.
        Deliberately NOT equal to ``str(source_chunk_id)``.
        """
        if source_chunk_id is not None:
            seed = f"chunk:{source_chunk_id}"
        else:
            seed = f"text:{paper_id}:{page}:{text.strip()}"
        return f"ev-{uuid.uuid5(_EVIDENCE_NAMESPACE, seed)}"

    def with_scores(
        self,
        *,
        retrieval_score: float | None = None,
        rerank_score: float | None = None,
    ) -> EvidenceUnit:
        return replace(
            self,
            retrieval_score=self.retrieval_score if retrieval_score is None else retrieval_score,
            rerank_score=self.rerank_score if rerank_score is None else rerank_score,
        )

    def with_hygiene(
        self,
        *,
        hygiene_class: str,
        hygiene_score: float,
        hygiene_signals: dict[str, Any],
    ) -> EvidenceUnit:
        return replace(
            self,
            hygiene_class=hygiene_class,
            hygiene_score=hygiene_score,
            hygiene_signals=dict(hygiene_signals),
        )

    def with_dimension(self, dimension: str, score: float) -> EvidenceUnit:
        """Record that this unit was selected for ``dimension``."""
        dimensions = tuple(dict.fromkeys((*self.selected_for_dimensions, dimension)))
        scores = {**self.dimension_scores, dimension: score}
        return replace(self, selected_for_dimensions=dimensions, dimension_scores=scores)

    @property
    def best_dimension_score(self) -> float | None:
        if not self.dimension_scores:
            return None
        return max(self.dimension_scores.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "paper_id": str(self.paper_id),
            "title": self.title,
            "page": self.page,
            "text": self.text,
            "source_chunk_id": None if self.source_chunk_id is None else str(self.source_chunk_id),
            "page_text_id": None if self.page_text_id is None else str(self.page_text_id),
            "page_char_start": self.page_char_start,
            "page_char_end": self.page_char_end,
            "retrieval_score": self.retrieval_score,
            "rerank_score": self.rerank_score,
            "hygiene_class": self.hygiene_class,
            "hygiene_score": self.hygiene_score,
            "hygiene_signals": dict(self.hygiene_signals),
            "selected_for_dimensions": list(self.selected_for_dimensions),
            "dimension_scores": dict(self.dimension_scores),
            "best_dimension_score": self.best_dimension_score,
        }
