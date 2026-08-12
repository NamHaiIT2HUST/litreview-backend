import asyncio
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import get_settings
from src.services.vector_store_config import build_chroma_connection_kwargs

CHROMA_PERSIST_DIR = ".chroma_db"


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
        gemini_key = settings.gemini_api_key or settings.google_api_key

        # Gemini embeddings first. If the key is missing, keep the app bootable
        # with a lightweight offline fallback so local smoke tests still work.
        if gemini_key:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.embedding_model,
                google_api_key=gemini_key,
            )
        else:
            self.embeddings = LightweightHashEmbeddings()

        chroma_kwargs = build_chroma_connection_kwargs(settings)
        if "persist_directory" in chroma_kwargs and not chroma_kwargs["persist_directory"]:
            chroma_kwargs["persist_directory"] = CHROMA_PERSIST_DIR

        self.vector_store = Chroma(
            collection_name="litreview_papers",
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

    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 4,
        filters: dict | None = None,
    ) -> List[Document]:
        """Tìm đoạn tương đồng; sync Chroma call chạy ở worker thread."""
        kwargs = {"k": top_k}
        if filters:
            kwargs["filter"] = filters
        return await asyncio.to_thread(
            self.vector_store.similarity_search,
            query,
            **kwargs,
        )


vector_store_service = VectorStoreService()
