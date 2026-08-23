"""One-off helper: register a local PDF as a Paper and run it through the real
ingestion pipeline (extract -> chunk -> embed -> persist), so it becomes
searchable exactly like any uploaded paper.

Usage:
    python scripts/ingest_local_pdf.py <path-to-pdf> --title "Some Title"
"""

import argparse
import asyncio
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import AsyncSessionLocal
from src.models.db_models import Paper
from src.services.document_processor import DocumentProcessor
from src.services.ingestion_service import persist_pdf_provenance
from src.services.vector_store import vector_store_service

DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
UPLOAD_ROOT = Path("uploads/papers") / str(DEFAULT_PROJECT_ID)


async def ingest(pdf_path: Path, title: str) -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    dest_name = f"{uuid.uuid4()}_{pdf_path.name}"
    dest_path = UPLOAD_ROOT / dest_name
    shutil.copy2(pdf_path, dest_path)

    processor = DocumentProcessor()
    pages, chunks = processor.extract_and_chunk(str(dest_path), paper_title=title)
    if not chunks or not any(c.page_content.strip() for c in chunks):
        raise RuntimeError(f"No extractable text in {pdf_path}")

    paper_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        paper = Paper(
            id=paper_id,
            project_id=DEFAULT_PROJECT_ID,
            title=title,
            dedup_key=f"direct-upload:{paper_id}",
            source="direct_upload",
            file_path=str(dest_path),
        )
        session.add(paper)
        await session.flush()

        ingestion_id = await persist_pdf_provenance(
            db=session,
            paper=paper,
            pages=pages,
            chunks=chunks,
            parser_metadata=processor.parser_metadata(),
        )
        await vector_store_service.add_documents(chunks)
        await session.commit()
        print(f"Ingested paper {paper_id} ({title}) -> ingestion {ingestion_id}, {len(chunks)} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    asyncio.run(ingest(args.pdf_path, args.title))
