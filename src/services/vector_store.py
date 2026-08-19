import asyncio
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.config import get_settings
from src.services.vector_store_config import build_chroma_connection_kwargs

CHROMA_PERSIST_DIR = ".chroma_db"


def should_use_gemini_embeddings(settings) -> bool:
    return (
        getattr(settings, "embedding_provider", "local") == "gemini"
        and bool(
            getattr(settings, "gemini_api_key", "")
            or getattr(settings, "google_api_key", "")
        )
    )


def should_use_openai_embeddings(settings) -> bool:
    return getattr(settings, "embedding_provider", "local") == "openai" and bool(
        getattr(settings, "openai_api_key", "")
    )


class LightweightHashEmbeddings(Embeddings):
    """Small offline fallback embeddings for local/Docker runs without OpenAI.

    This keeps the app bootable without downloading sentence-transformers/torch.
    It is sufficient for smoke tests and local demos; production-quality semantic
    search should use OpenAI embeddings or another real embedding provider.
    """

    dimension = 128

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        words = (text or "").lower().split()
        if not words:
            return vector
        for word in words:
            bucket = sum(ord(char) for char in word) % self.dimension
            vector[bucket] += 1.0
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]


class VectorStoreService:
    def __init__(self):
        settings = get_settings()
        gemini_key = getattr(settings, "gemini_api_key", "") or getattr(
            settings, "google_api_key", ""
        )

        # Pick the embedding provider the caller configured. If its key is
        # missing, keep the app bootable with a lightweight offline fallback
        # so local smoke tests still work.
        if should_use_gemini_embeddings(settings):
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=gemini_key,
            )
        elif should_use_openai_embeddings(settings):
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key,
                base_url=settings.get_api_base or None,
            )
        else:
            self.embeddings = LightweightHashEmbeddings()

        chroma_kwargs = build_chroma_connection_kwargs(settings)
        if "persist_directory" in chroma_kwargs and not chroma_kwargs["persist_directory"]:
            chroma_kwargs["persist_directory"] = CHROMA_PERSIST_DIR

        self.vector_store = Chroma(
            collection_name="litreview_papers_v2",
            embedding_function=self.embeddings,
            **chroma_kwargs,
        )

    async def add_documents(self, documents: List[Document]):
        """Nhúng và lưu chunk mà không block event loop của FastAPI/LangGraph."""
        if not documents:
            return 0

        await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
        return len(documents)

    async def stage_documents_for_paper(
        self, paper_id: str, documents: List[Document]
    ) -> list[str]:
        """Add a new ingestion without deleting the previously committed vectors.

        The caller commits the matching PostgreSQL ingestion first, then invokes
        :meth:`delete_document_ids` for the returned old IDs. This avoids a
        distributed-transaction hole where old vectors disappear before the DB
        can commit the new ``active_ingestion_id``.
        """
        if not documents:
            return []

        existing = await asyncio.to_thread(
            self.vector_store.get,
            where={"paper_id": str(paper_id)},
        )
        old_ids = list(existing.get("ids", []) or [])
        await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
        return old_ids

    async def delete_document_ids(self, ids: list[str]) -> int:
        """Delete a known set of Chroma IDs after the DB commit succeeds."""
        clean_ids = list(dict.fromkeys(ids or []))
        if not clean_ids:
            return 0
        await asyncio.to_thread(self.vector_store.delete, ids=clean_ids)
        return len(clean_ids)

    async def replace_documents_for_paper(self, paper_id: str, documents: List[Document]) -> int:
        """Compatibility wrapper for callers that do not coordinate a DB commit.

        Provenance-aware ingestion should use ``stage_documents_for_paper`` and
        ``delete_document_ids`` explicitly.
        """
        old_ids = await self.stage_documents_for_paper(paper_id, documents)
        await self.delete_document_ids(old_ids)
        return len(documents)

    async def delete_documents_by_ingestion(self, ingestion_id: str) -> int:
        """Best-effort compensation helper khi ingestion lỗi sau lúc indexing."""
        existing = await asyncio.to_thread(
            self.vector_store.get,
            where={"ingestion_id": str(ingestion_id)},
        )
        ids = list(existing.get("ids", []) or [])
        if ids:
            await asyncio.to_thread(self.vector_store.delete, ids=ids)
        return len(ids)

    async def recover_vectors_for_paper(self, paper_id: str):
        """Phục hồi vector từ bảng pdf_chunks trong PostgreSQL lên ChromaDB nếu đĩa ảo bị xóa."""
        from src.database import AsyncSessionLocal
        from src.models.db_models import PDFChunk, PageText, Paper
        from sqlalchemy import select
        
        print(f"[vector-recovery] Auto-recovering vector store for paper {paper_id}...", flush=True)
        async with AsyncSessionLocal() as session:
            try:
                # Query all chunks for this paper
                result = await session.execute(
                    select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title)
                    .join(PageText, PDFChunk.page_text_id == PageText.id)
                    .join(Paper, PDFChunk.paper_id == Paper.id)
                    .where(PDFChunk.paper_id == paper_id)
                )
                rows = result.fetchall()
                if not rows:
                    print(f"[vector-recovery] No chunks found in DB for paper {paper_id}. Cannot recover.", flush=True)
                    return
                
                documents = []
                for chunk_row, page_num, file_path, title in rows:
                    doc = Document(
                        page_content=chunk_row.chunk_text,
                        metadata={
                            "paper_id": str(paper_id),
                            "page_text_id": str(chunk_row.page_text_id),
                            "chunk_id": str(chunk_row.id),
                            "ingestion_id": str(chunk_row.ingestion_id),
                            "page": page_num,
                            "chunk_index": chunk_row.chunk_index,
                            "page_char_start": chunk_row.page_char_start,
                            "page_char_end": chunk_row.page_char_end,
                            "source": str(file_path) if file_path else f"paper_{paper_id}.pdf",
                            "paper_title": str(title) if title else "Unknown Title"
                        }
                    )
                    documents.append(doc)
                
                await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
                print(f"[vector-recovery] Successfully recovered {len(documents)} vectors for paper {paper_id}.", flush=True)
            except Exception as e:
                print(f"[vector-recovery] ERROR: Failed to recover vectors for paper {paper_id}: {e}", flush=True)

    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 4,
        filters: dict | None = None,
    ) -> List[Document]:
        """Tìm đoạn tương đồng; sync Chroma call chạy ở worker thread."""
        if filters and "paper_id" in filters:
            pid = filters["paper_id"]
            existing = await asyncio.to_thread(self.vector_store.get, where={"paper_id": str(pid)}, limit=1)
            if not existing or not existing.get("ids"):
                await self.recover_vectors_for_paper(pid)
                
        kwargs = {"k": top_k}
        if filters:
            kwargs["filter"] = filters
        return await asyncio.to_thread(
            self.vector_store.similarity_search,
            query,
            **kwargs,
        )

    async def search_similar_documents_with_scores(
        self, query: str, top_k: int = 4, filters: dict | None = None,
    ) -> list[tuple[Document, float]]:
        if filters and "paper_id" in filters:
            pid = filters["paper_id"]
            existing = await asyncio.to_thread(self.vector_store.get, where={"paper_id": str(pid)}, limit=1)
            if not existing or not existing.get("ids"):
                await self.recover_vectors_for_paper(pid)
                
        kwargs = {"k": top_k}
        if filters:
            kwargs["filter"] = filters
        return await asyncio.to_thread(
            self.vector_store.similarity_search_with_relevance_scores,
            query,
            **kwargs,
        )


vector_store_service = VectorStoreService()
