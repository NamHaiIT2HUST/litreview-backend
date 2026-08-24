"""Fast v2 Evidence-First ingestion service.

canonical PDFChunk/Paper (Postgres) -> EvidenceUnit -> FastV2SemanticIndex

No LLM extraction here, at ingestion or query time -- this only computes a
semantic embedding for text that already exists in the database.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex, IndexStats


class FastV2IndexingService:
    """Index / reindex / rebuild the Fast v2 semantic collection from canonical chunks."""

    def __init__(self, session_factory: Callable[[], Any], index: FastV2SemanticIndex) -> None:
        self._session_factory = session_factory
        self._index = index

    async def _fetch_units_for_papers(self, paper_ids: Sequence[uuid.UUID]) -> list[EvidenceUnit]:
        from sqlalchemy import select

        from src.models.db_models import Paper, PDFChunk

        async with self._session_factory() as db:
            chunk_rows = await db.execute(select(PDFChunk).where(PDFChunk.paper_id.in_(paper_ids)))
            chunks = list(chunk_rows.scalars().all())

            paper_rows = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
            title_by_paper = {p.id: p.title for p in paper_rows.scalars().all()}

        units = []
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
        return units

    async def index_paper(self, paper_id: uuid.UUID) -> IndexStats:
        """Index one paper. Idempotent: safe to call on an already-indexed paper."""
        units = await self._fetch_units_for_papers([paper_id])
        if not units:
            return IndexStats(paper_id=paper_id, chunks_seen=0, chunks_indexed=0, chunks_skipped_empty=0)
        return self._index.index_units(units)

    async def reindex_paper(self, paper_id: uuid.UUID) -> IndexStats:
        """Delete then re-index one paper's chunks.

        Upsert alone (index_paper) already handles the common case of
        updated chunk text for an unchanged chunk id set. This variant also
        clears stale rows for chunk ids that no longer exist upstream (e.g.
        the paper was re-chunked with different boundaries).
        """
        self._index.delete_paper(paper_id)
        return await self.index_paper(paper_id)

    async def rebuild_collection(self, paper_ids: Sequence[uuid.UUID]) -> list[IndexStats]:
        """Rebuild the Fast v2 collection for exactly the given paper set."""
        stats = []
        for paper_id in paper_ids:
            stats.append(await self.reindex_paper(paper_id))
        return stats
