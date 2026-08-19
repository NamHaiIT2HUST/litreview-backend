"""One-off migration: re-embed every paper's active ingestion with the
configured OpenAI embedding model.

Vectors currently in Chroma may have been produced by LightweightHashEmbeddings
(the offline fallback in src/services/vector_store.py) if OPENAI_API_KEY or
embedding_provider="openai" wasn't set at ingestion time. Those vectors are not
comparable to query vectors embedded with a real model, so retrieval silently
misses relevant chunks. This script re-embeds each paper's active-ingestion
chunks and swaps out the old vectors for the new ones.

Usage:
    python scripts/reembed_openai_migration.py [--dry-run] [--paper-id UUID]
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from sqlalchemy import select

from src.config import get_settings
from src.database import AsyncSessionLocal
from src.models.db_models import PDFChunk, PageText, Paper
from src.services.vector_store import should_use_openai_embeddings, vector_store_service


def _build_documents(rows) -> list[Document]:
    documents = []
    for chunk, page_num, file_path, title in rows:
        documents.append(
            Document(
                page_content=chunk.chunk_text,
                metadata={
                    "paper_id": str(chunk.paper_id),
                    "page_text_id": str(chunk.page_text_id),
                    "chunk_id": str(chunk.id),
                    "ingestion_id": str(chunk.ingestion_id),
                    "page": page_num,
                    "chunk_index": chunk.chunk_index,
                    "page_char_start": chunk.page_char_start,
                    "page_char_end": chunk.page_char_end,
                    "source": str(file_path) if file_path else f"paper_{chunk.paper_id}.pdf",
                    "paper_title": str(title) if title else "Unknown Title",
                },
            )
        )
    return documents


async def migrate(dry_run: bool = False, only_paper_id: str | None = None) -> None:
    settings = get_settings()
    if not should_use_openai_embeddings(settings):
        raise SystemExit(
            "embedding_provider must be 'openai' and OPENAI_API_KEY must be set "
            "before running this migration (check .env)."
        )

    async with AsyncSessionLocal() as session:
        paper_query = select(Paper.id, Paper.active_ingestion_id).where(
            Paper.active_ingestion_id.isnot(None)
        )
        if only_paper_id:
            paper_query = paper_query.where(Paper.id == only_paper_id)

        papers = (await session.execute(paper_query)).all()
        print(f"Found {len(papers)} papers with an active ingestion to re-embed.")

        migrated, skipped, failed = 0, 0, 0
        for paper_id, ingestion_id in papers:
            chunk_rows = (
                await session.execute(
                    select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title)
                    .join(PageText, PDFChunk.page_text_id == PageText.id)
                    .join(Paper, PDFChunk.paper_id == Paper.id)
                    .where(
                        PDFChunk.paper_id == paper_id,
                        PDFChunk.ingestion_id == ingestion_id,
                    )
                )
            ).fetchall()

            if not chunk_rows:
                print(f"  [skip] paper {paper_id}: no chunks for active ingestion {ingestion_id}")
                skipped += 1
                continue

            documents = _build_documents(chunk_rows)

            if dry_run:
                print(f"  [dry-run] paper {paper_id}: would re-embed {len(documents)} chunks")
                continue

            try:
                count = await vector_store_service.replace_documents_for_paper(
                    str(paper_id), documents
                )
                print(f"  [done] paper {paper_id}: re-embedded {count} chunks")
                migrated += 1
            except Exception as exc:
                print(f"  [error] paper {paper_id}: {exc}")
                failed += 1

        print(
            f"Migration complete. migrated={migrated} skipped={skipped} "
            f"failed={failed} dry_run={dry_run}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="List what would be re-embedded without writing"
    )
    parser.add_argument(
        "--paper-id", default=None, help="Only re-embed this one paper (UUID string)"
    )
    args = parser.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run, only_paper_id=args.paper_id))
