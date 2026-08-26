"""Registry for which papers are usable in which vector index.

PostgreSQL is the control plane: it answers "is this paper actually searchable"
without having to interrogate Chroma. Chroma holds the vectors and its own copy
of the embedding identity, so the two can be checked against each other.

The state machine is deliberately small::

    PENDING -> INDEXING -> READY
                       \\-> FAILED

Only ``READY`` may be retrieved from. Before this existed there was no way to
express a partially-written ingestion: ``persist_pdf_provenance`` set
``active_ingestion_id`` and committed, then the vector write ran and swallowed
its own errors, so a paper whose embedding calls ran out of quota halfway was
recorded as fully ingested with nothing behind it. Retrieval could not tell
that paper apart from a complete one, and neither could anyone reading the
database.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.db_models import PaperIndex, PaperIndexStatus, VectorIndex, VectorIndexStatus
from src.services.embedding_manager import EmbeddingIdentity, collection_name_for


async def get_or_create_index(
    db: AsyncSession, identity: EmbeddingIdentity, version: int = 1
) -> VectorIndex:
    """Return the registry row for an embedding identity, creating it if new."""
    collection_name = collection_name_for(identity, version)
    existing = (
        await db.execute(select(VectorIndex).where(VectorIndex.collection_name == collection_name))
    ).scalars().first()
    if existing is not None:
        return existing

    index = VectorIndex(
        id=uuid.uuid4(),
        collection_name=collection_name,
        provider=identity.provider,
        model=identity.model,
        dimension=identity.dimension,
        version=version,
        # A brand new index is usable as soon as it exists; "building" is for a
        # replacement index being populated alongside a live one, which is what
        # a model migration creates.
        status=VectorIndexStatus.active,
    )
    db.add(index)
    await db.flush()
    return index


async def get_active_index(db: AsyncSession) -> VectorIndex | None:
    return (
        await db.execute(
            select(VectorIndex)
            .where(VectorIndex.status == VectorIndexStatus.active)
            .order_by(VectorIndex.version.desc())
        )
    ).scalars().first()


async def _get_or_create_link(
    db: AsyncSession, *, paper_id: uuid.UUID, index: VectorIndex
) -> PaperIndex:
    link = (
        await db.execute(
            select(PaperIndex).where(
                PaperIndex.paper_id == paper_id,
                PaperIndex.vector_index_id == index.id,
            )
        )
    ).scalars().first()
    if link is None:
        link = PaperIndex(
            id=uuid.uuid4(),
            paper_id=paper_id,
            vector_index_id=index.id,
            status=PaperIndexStatus.pending,
        )
        db.add(link)
        await db.flush()
    return link


async def mark_indexing(
    db: AsyncSession, *, paper_id: uuid.UUID, index: VectorIndex, ingestion_id: uuid.UUID | None
) -> PaperIndex:
    """Record that indexing has started, before any vector is written.

    Committed by the caller ahead of the write, so a process that dies midway
    leaves a paper visibly stuck in INDEXING instead of looking complete.
    """
    link = await _get_or_create_link(db, paper_id=paper_id, index=index)
    link.status = PaperIndexStatus.indexing
    link.ingestion_id = ingestion_id
    link.error_message = None
    return link


async def mark_ready(
    db: AsyncSession, *, paper_id: uuid.UUID, index: VectorIndex, chunk_count: int
) -> PaperIndex:
    link = await _get_or_create_link(db, paper_id=paper_id, index=index)
    link.status = PaperIndexStatus.ready
    link.chunk_count = chunk_count
    link.error_message = None
    link.indexed_at = datetime.now(UTC)
    return link


async def mark_failed(
    db: AsyncSession, *, paper_id: uuid.UUID, index: VectorIndex, error: str
) -> PaperIndex:
    """Record why a paper is not searchable.

    Keeping the reason matters as much as the status: "this paper has no
    evidence" and "this paper could not be embedded because the key ran out of
    quota" look identical downstream otherwise.
    """
    link = await _get_or_create_link(db, paper_id=paper_id, index=index)
    link.status = PaperIndexStatus.failed
    link.error_message = error[:2000]
    return link


async def is_ready(db: AsyncSession, *, paper_id: uuid.UUID, index: VectorIndex) -> bool:
    link = (
        await db.execute(
            select(PaperIndex).where(
                PaperIndex.paper_id == paper_id,
                PaperIndex.vector_index_id == index.id,
            )
        )
    ).scalars().first()
    return link is not None and link.status == PaperIndexStatus.ready


async def ready_paper_ids(db: AsyncSession, *, index: VectorIndex) -> set[uuid.UUID]:
    """Papers a retrieval pipeline is allowed to draw evidence from."""
    rows = await db.execute(
        select(PaperIndex.paper_id).where(
            PaperIndex.vector_index_id == index.id,
            PaperIndex.status == PaperIndexStatus.ready,
        )
    )
    return {row[0] for row in rows.all()}
