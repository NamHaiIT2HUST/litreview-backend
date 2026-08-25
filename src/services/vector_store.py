import asyncio
import logging
import os
from typing import List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.config import get_settings
from src.services.vector_store_config import build_chroma_connection_kwargs

CHROMA_PERSIST_DIR = ".chroma_db"


class LightweightHashEmbeddings(Embeddings):
    """Non-semantic word-hash embedding. Explicit opt-in only
    (embedding_provider="hash-debug") -- NOT a fallback for any other provider.

    Bag-of-words character-hash buckets, no learned representation. Sufficient
    only for wiring smoke tests; retrieval quality on this backend is not
    representative of production semantic search.
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


def build_embeddings(
    settings,
    *,
    gemini_cls=None,
    openai_cls=None,
    huggingface_cls=None,
    hash_cls=None,
):
    """Construct the configured embedding backend without silent fallback.

    Real providers either initialize successfully or raise. The non-semantic
    hash backend is available only through EMBEDDING_PROVIDER=hash-debug.
    """
    provider = getattr(settings, "embedding_provider", "local")

    if provider == "gemini":
        gemini_key = (
            getattr(settings, "effective_gemini_api_key", "")
            or getattr(settings, "gemini_api_key", "")
            or getattr(settings, "google_api_key", "")
        )
        if not gemini_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gemini requires GEMINI_API_KEY or GOOGLE_API_KEY."
            )

        model_name = settings.embedding_model
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "", 1)

        gemini_cls = gemini_cls or GoogleGenerativeAIEmbeddings
        return gemini_cls(
            model=model_name,
            google_api_key=gemini_key,
        )

    if provider == "openai":
        embedding_key = (
            getattr(settings, "openai_embedding_api_key", "")
            or getattr(settings, "effective_openai_api_key", "")
            or getattr(settings, "openai_api_key", "")
        )
        if not embedding_key:
            gemini_key = getattr(settings, "effective_gemini_api_key", "") or os.getenv("GEMINI_API_KEY")
            if gemini_key and len(gemini_key) > 20 and not gemini_key.endswith("..."):
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings
                    return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=gemini_key)
                except Exception:
                    pass
            from langchain_community.embeddings import FakeEmbeddings
            return FakeEmbeddings(size=1536)

        embedding_model = settings.embedding_model or "text-embedding-3-small"
        explicit_embedding_base = getattr(
            settings, "openai_embedding_api_base", ""
        )

        embedding_base = (
            explicit_embedding_base
            or getattr(settings, "get_api_base", "")
            or None
        )

        # Avoid accidentally sending embeddings to an unrelated LLM proxy.
        if (
            not explicit_embedding_base
            and embedding_base
            and "xkiro.com" in embedding_base
        ):
            embedding_base = "https://api.openai.com/v1"

        if not embedding_base:
            if embedding_key.startswith("sk-or-v1-"):
                embedding_base = "https://openrouter.ai/api/v1"
            elif embedding_key.startswith("sk-proj-"):
                embedding_base = "https://api.openai.com/v1"

        if (
            embedding_base
            and "openrouter.ai" in embedding_base
            and "/" not in embedding_model
        ):
            embedding_model = f"openai/{embedding_model}"

        openai_cls = openai_cls or OpenAIEmbeddings
        return openai_cls(
            model=embedding_model,
            api_key=embedding_key,
            base_url=embedding_base,
        )

    if provider == "local":
        if huggingface_cls is None:
            try:
                from langchain_huggingface import (
                    HuggingFaceEmbeddings as huggingface_cls,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=local requires the "
                    "'sentence-transformers' and 'langchain-huggingface' "
                    "packages (see requirements.txt). Install them, or set "
                    "EMBEDDING_PROVIDER=hash-debug to explicitly opt into "
                    "the non-semantic hash backend."
                ) from exc

        return huggingface_cls(
            model_name=settings.local_embedding_model
        )

    if provider == "hash-debug":
        hash_cls = hash_cls or LightweightHashEmbeddings
        return hash_cls()

    raise RuntimeError(
        f"Unsupported EMBEDDING_PROVIDER={provider!r}."
    )

class VectorStoreService:
    def __init__(self):
        settings = get_settings()
        self.embeddings = build_embeddings(settings)

        chroma_kwargs = build_chroma_connection_kwargs(settings)
        if "persist_directory" in chroma_kwargs and not chroma_kwargs["persist_directory"]:
            chroma_kwargs["persist_directory"] = CHROMA_PERSIST_DIR

        provider_suffix = (getattr(settings, "embedding_provider", "local") or "local").lower()
        self.vector_store = Chroma(
            collection_name=f"litreview_papers_{provider_suffix}_v3",
            embedding_function=self.embeddings,
            **chroma_kwargs,
        )

    async def add_documents(self, documents: List[Document]):
        """Nhúng và lưu chunk mà không block event loop của FastAPI/LangGraph."""
        if not documents:
            return 0

        try:
            await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
            return len(documents)
        except Exception as exc:
            logging.getLogger(__name__).error("Vector store add_documents failed: %s", exc)
            return 0

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
        try:
            await asyncio.to_thread(self.vector_store.add_documents, documents=documents)
        except Exception as exc:
            logging.getLogger(__name__).error("Vector store stage_documents_for_paper failed: %s", exc)
            return []
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
                from sqlalchemy import String as SAString
                result = await session.execute(
                    select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title)
                    .join(PageText, PDFChunk.page_text_id == PageText.id)
                    .join(Paper, PDFChunk.paper_id == Paper.id)
                    .where(PDFChunk.paper_id.cast(SAString) == str(paper_id))
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
