"""Rebuild the vector index onto a different embedding model.

Changing EMBEDDING_PROVIDER or EMBEDDING_MODEL changes the coordinate space of
every vector. There is no in-place upgrade and no fallback that makes the old
vectors readable: the only correct move is to build a new index and switch to
it. That is a migration, and this script is how it is run.

The order is build-then-switch, never delete-then-build::

    index_v1_openai_...   (active)      still serving every request
            │
            ├─ index_v2_gemini_...      (building) populated from stored chunks
            │
            ├─ verified                 v2 -> active, v1 -> deprecated
            │
            └─ later, on request        v1 dropped

The chunk text in PostgreSQL is the durable copy, so the new index is built from
the database rather than from the old vectors -- which could not be translated
anyway.

Usage
-----
Preview what would happen (no writes)::

    python -m scripts.reindex_vectors --plan

Build a new index at the currently configured embedding identity::

    python -m scripts.reindex_vectors --build

Promote it once the results look right::

    python -m scripts.reindex_vectors --promote index_v2_gemini_...

Drop a deprecated index after the new one has proven itself::

    python -m scripts.reindex_vectors --drop index_v1_openai_...
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models.db_models import (
    Paper,
    PaperIndex,
    PaperIndexStatus,
    VectorIndex,
    VectorIndexStatus,
)
from src.services import index_registry
from src.services.embedding_manager import collection_name_for, resolve_runtime_identity


async def _describe() -> None:
    settings = get_settings()
    identity = resolve_runtime_identity(settings)
    target_name = collection_name_for(identity, version=await _next_version())

    print(f"Configured embedding identity : {identity.provider}/{identity.model} "
          f"({identity.dimension} dimensions)")
    print(f"A new index would be called    : {target_name}")
    print()

    async with AsyncSessionLocal() as db:
        indexes = (await db.execute(select(VectorIndex).order_by(VectorIndex.version))).scalars().all()
        if not indexes:
            print("No vector index is registered yet.")
        for index in indexes:
            ready = (await db.execute(
                select(PaperIndex).where(
                    PaperIndex.vector_index_id == index.id,
                    PaperIndex.status == PaperIndexStatus.ready,
                )
            )).scalars().all()
            failed = (await db.execute(
                select(PaperIndex).where(
                    PaperIndex.vector_index_id == index.id,
                    PaperIndex.status == PaperIndexStatus.failed,
                )
            )).scalars().all()
            print(f"  {index.collection_name}")
            print(f"    status      : {index.status.value}")
            print(f"    identity    : {index.provider}/{index.model} ({index.dimension} dimensions)")
            print(f"    ready papers: {len(ready)}   failed: {len(failed)}")

        total_papers = (await db.execute(select(Paper))).scalars().all()
        print()
        print(f"Papers in the database: {len(total_papers)}")


async def _next_version() -> int:
    async with AsyncSessionLocal() as db:
        versions = (await db.execute(select(VectorIndex.version))).scalars().all()
    return (max(versions) + 1) if versions else 1


async def _build() -> int:
    """Populate a new index from stored chunks, leaving the current one serving."""
    from langchain_core.documents import Document
    from sqlalchemy import String as SAString

    from src.models.db_models import PageText, PDFChunk
    from src.services.vector_store import VectorStoreService

    settings = get_settings()
    identity = resolve_runtime_identity(settings)
    version = await _next_version()

    # A dedicated service instance pinned to the new identity. The ambient
    # configuration is not consulted again after this point.
    service = VectorStoreService(identity=identity, version=version)
    print(f"Building {service.collection_name} "
          f"({identity.provider}/{identity.model}, {identity.dimension} dimensions)")

    async with AsyncSessionLocal() as db:
        index = await index_registry.get_or_create_index(db, identity, version=version)
        index.status = VectorIndexStatus.building
        await db.commit()

        papers = (await db.execute(select(Paper).where(Paper.active_ingestion_id.isnot(None)))).scalars().all()
        print(f"{len(papers)} papers have an ingestion to rebuild from.")

        succeeded = failed = 0
        for paper in papers:
            rows = (await db.execute(
                select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title)
                .join(PageText, PDFChunk.page_text_id == PageText.id)
                .join(Paper, PDFChunk.paper_id == Paper.id)
                .where(PDFChunk.paper_id.cast(SAString) == str(paper.id))
            )).fetchall()

            if not rows:
                await index_registry.mark_failed(
                    db, paper_id=paper.id, index=index,
                    error="No stored chunks; the paper needs re-ingesting from its source.",
                )
                await db.commit()
                failed += 1
                continue

            documents = [
                Document(
                    page_content=chunk_row.chunk_text,
                    metadata={
                        "paper_id": str(paper.id),
                        "page_text_id": str(chunk_row.page_text_id),
                        "chunk_id": str(chunk_row.id),
                        "ingestion_id": str(chunk_row.ingestion_id),
                        "page": page_num,
                        "chunk_index": chunk_row.chunk_index,
                        "page_char_start": chunk_row.page_char_start,
                        "page_char_end": chunk_row.page_char_end,
                        "source": str(file_path) if file_path else f"paper_{paper.id}.pdf",
                        "paper_title": str(title) if title else "Unknown Title",
                    },
                )
                for chunk_row, page_num, file_path, title in rows
            ]

            await index_registry.mark_indexing(
                db, paper_id=paper.id, index=index, ingestion_id=paper.active_ingestion_id
            )
            await db.commit()
            try:
                await service.add_documents(documents)
            except Exception as exc:
                await index_registry.mark_failed(db, paper_id=paper.id, index=index, error=str(exc))
                await db.commit()
                failed += 1
                print(f"  FAILED {paper.title!r}: {exc}")
                continue

            await index_registry.mark_ready(
                db, paper_id=paper.id, index=index, chunk_count=len(documents)
            )
            await db.commit()
            succeeded += 1

    print()
    print(f"Built {succeeded} papers, {failed} failed.")
    print("The new index is still 'building' and is not serving traffic. Review the")
    print("failures above, then promote it:")
    print(f"    python -m scripts.reindex_vectors --promote {service.collection_name}")
    return 1 if failed else 0


async def _promote(collection_name: str) -> int:
    async with AsyncSessionLocal() as db:
        target = (await db.execute(
            select(VectorIndex).where(VectorIndex.collection_name == collection_name)
        )).scalars().first()
        if target is None:
            print(f"No index named {collection_name!r}.")
            return 1

        others = (await db.execute(
            select(VectorIndex).where(VectorIndex.status == VectorIndexStatus.active)
        )).scalars().all()
        for other in others:
            if other.id != target.id:
                other.status = VectorIndexStatus.deprecated
                print(f"  {other.collection_name} -> deprecated")

        target.status = VectorIndexStatus.active
        await db.commit()
        print(f"  {target.collection_name} -> active")

    print()
    print("Point EMBEDDING_PROVIDER / EMBEDDING_MODEL at this identity in .env so")
    print("running processes open the promoted index, then restart them.")
    return 0


async def _drop(collection_name: str) -> int:
    """Delete a deprecated index. Refuses to touch the one currently serving."""
    from src.services.embedding_manager import EmbeddingIdentity
    from src.services.vector_store import VectorStoreService

    async with AsyncSessionLocal() as db:
        target = (await db.execute(
            select(VectorIndex).where(VectorIndex.collection_name == collection_name)
        )).scalars().first()
        if target is None:
            print(f"No index named {collection_name!r}.")
            return 1
        if target.status == VectorIndexStatus.active:
            print(f"{collection_name!r} is the active index. Promote its replacement first.")
            return 1

        identity = EmbeddingIdentity(target.provider, target.model, target.dimension)
        version = target.version
        links = (await db.execute(
            select(PaperIndex).where(PaperIndex.vector_index_id == target.id)
        )).scalars().all()
        for link in links:
            await db.delete(link)
        await db.delete(target)
        await db.commit()

    service = VectorStoreService(identity=identity, version=version)
    service.vector_store.delete_collection()
    print(f"Dropped {collection_name}.")
    return 0


async def _run(coro) -> int:
    """Run one command and release the database engine before returning.

    Without the dispose, aiosqlite's connection worker is a non-daemon thread
    that never joins: the command prints its whole result and then hangs at
    interpreter shutdown, which looks exactly like the work itself having stalled.
    """
    from src.database import engine

    try:
        result = await coro
        return result or 0
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", action="store_true", help="show current indexes and what a build would create")
    group.add_argument("--build", action="store_true", help="populate a new index at the configured identity")
    group.add_argument("--promote", metavar="COLLECTION", help="make an index the active one")
    group.add_argument("--drop", metavar="COLLECTION", help="delete a deprecated index")
    args = parser.parse_args()

    if args.plan:
        return asyncio.run(_run(_describe()))
    if args.build:
        return asyncio.run(_run(_build()))
    if args.promote:
        return asyncio.run(_run(_promote(args.promote)))
    return asyncio.run(_run(_drop(args.drop)))


if __name__ == "__main__":
    sys.exit(main())
