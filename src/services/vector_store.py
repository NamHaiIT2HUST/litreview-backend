import asyncio
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.config import get_settings
from src.services.vector_store_config import build_chroma_connection_kwargs

CHROMA_PERSIST_DIR = ".chroma_db"


class VectorStoreService:
    def __init__(self):
        settings = get_settings()

        # Nếu dùng OpenRouter hoặc không có OpenAI key xịn, tự động dùng
        # HuggingFace Embeddings local.
        if not settings.openai_api_key or settings.openai_api_key.startswith("sk-or-v1-"):
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        else:
            api_base = settings.get_api_base
            emb_kwargs = {
                "model": settings.embedding_model,
                "api_key": settings.openai_api_key,
            }
            if api_base:
                emb_kwargs["openai_api_base"] = api_base
            self.embeddings = OpenAIEmbeddings(**emb_kwargs)

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
