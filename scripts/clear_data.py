import os
import shutil
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete as sql_delete
from dotenv import load_dotenv

load_dotenv()

from src.database import AsyncSessionLocal, engine
from src.models.db_models import (
    Project,
    Paper,
    SearchQuery,
    SearchQueryPaper,
    ScreeningHistory,
    Extraction,
    SynthesisSession,
    Citation,
    PageText,
    PDFChunk,
    EvidenceExtractionAttempt,
    EvidenceRecord,
    GenericEvidenceCache,
    GenericEvidenceCacheItem,
    SynthesisSection,
    SynthesisClaim,
    ClaimEvidenceLink,
    RetrievalLog,
    LLMCallLog,
    SynthesisMetrics,
    VectorCleanupJob,
)
from src.services.vector_store import vector_store_service


async def clear_database():
    print("Clearing database tables...")
    async with AsyncSessionLocal() as session:
        try:
            # Delete in order of foreign key dependencies
            await session.execute(sql_delete(SynthesisMetrics))
            await session.execute(sql_delete(LLMCallLog))
            await session.execute(sql_delete(RetrievalLog))
            await session.execute(sql_delete(ClaimEvidenceLink))
            await session.execute(sql_delete(SynthesisClaim))
            await session.execute(sql_delete(SynthesisSection))
            await session.execute(sql_delete(Citation))
            await session.execute(sql_delete(GenericEvidenceCacheItem))
            await session.execute(sql_delete(GenericEvidenceCache))
            await session.execute(sql_delete(EvidenceRecord))
            await session.execute(sql_delete(EvidenceExtractionAttempt))
            await session.execute(sql_delete(SynthesisSession))
            await session.execute(sql_delete(PDFChunk))
            await session.execute(sql_delete(PageText))
            await session.execute(sql_delete(Extraction))
            await session.execute(sql_delete(ScreeningHistory))
            await session.execute(sql_delete(VectorCleanupJob))
            await session.execute(sql_delete(SearchQueryPaper))
            await session.execute(sql_delete(Paper))
            await session.execute(sql_delete(SearchQuery))
            await session.commit()
            print("Database tables cleared successfully.")
        except Exception as e:
            await session.rollback()
            print(f"Error clearing database: {e}")
            raise


def clear_uploaded_files():
    print("Clearing uploaded files...")
    uploads_dir = os.path.abspath("uploads")
    if os.path.exists(uploads_dir):
        for root, dirs, files in os.walk(uploads_dir):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception as e:
                    print(f"Error deleting file {f}: {e}")
    print("Uploaded files cleared.")


async def clear_chroma():
    print("Clearing ChromaDB...")
    try:
        if hasattr(vector_store_service, "vector_store") and vector_store_service.vector_store is not None:
            # Delete all documents in collection
            try:
                col = vector_store_service.vector_store._collection
                all_items = col.get()
                if all_items and all_items.get("ids"):
                    col.delete(ids=all_items["ids"])
                    print(f"Deleted {len(all_items['ids'])} vectors from ChromaDB collection.")
            except Exception as e:
                print(f"Note on Chroma clear: {e}")
    except Exception as e:
        print(f"Error interacting with vector store: {e}")

    # Also clean local chroma dir if exists
    for c_dir in ["./data/chroma", ".chroma_db"]:
        if os.path.exists(c_dir):
            try:
                shutil.rmtree(c_dir, ignore_errors=True)
                os.makedirs(c_dir, exist_ok=True)
                print(f"Cleaned directory: {c_dir}")
            except Exception as e:
                print(f"Error cleaning {c_dir}: {e}")


async def main():
    await clear_database()
    clear_uploaded_files()
    await clear_chroma()
    print("\n>>> DATA MEMORY CLEARED COMPLETELY. Ready for re-uploading PDFs! <<<")


if __name__ == "__main__":
    asyncio.run(main())
