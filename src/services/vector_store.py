import asyncio
import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from src.config import get_settings
from src.services.embedding_manager import (
    EmbeddingIdentity,
    build_embeddings_for,
    chroma_metadata_for,
    collection_name_for,
    identity_from_metadata,
    resolve_runtime_identity,
    verify_identity_match,
)
from src.services.vector_store_config import build_chroma_connection_kwargs

logger = logging.getLogger(__name__)

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

    Real providers either initialize successfully or raise; no provider is ever
    substituted for another. An embedding model defines the coordinate space of
    a persisted index, so swapping one is a schema change that requires
    re-indexing, not a runtime fallback.

    The non-semantic hash backend is reachable only through the explicit
    EMBEDDING_PROVIDER=hash-debug opt-in.
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
            # Deliberately fails instead of substituting another provider.
            #
            # The previous version fell back to Gemini embeddings and then to
            # FakeEmbeddings(size=1536) -- random, non-semantic vectors. Because
            # the collection name is derived from EMBEDDING_PROVIDER rather than
            # from the backend actually built, those vectors were written into a
            # collection named for OpenAI. Documents were chunked, embedded as
            # noise, and persisted to Chroma and Postgres at full storage cost,
            # while every later retrieval against them was meaningless -- with no
            # warning logged anywhere.
            #
            # An embedding model defines the coordinate space of a persisted
            # index, so substituting one is not a fallback: it is an unannounced
            # schema change. Missing credentials must surface as a configuration
            # error.
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai requires OPENAI_EMBEDDING_API_KEY or "
                "OPENAI_API_KEY. Set one in .env, or select a provider you do "
                "have credentials for. Switching EMBEDDING_PROVIDER or "
                "EMBEDDING_MODEL changes the vector space and requires "
                "re-indexing existing documents."
            )

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
                from langchain_huggingface import HuggingFaceEmbeddings

                huggingface_cls = HuggingFaceEmbeddings
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

def _document_ids(documents: list[Document]) -> list[str] | None:
    """Stable Chroma ids taken from the chunk ids the database already assigned.

    Without explicit ids Chroma mints a fresh UUID per call, so re-adding the
    same chunks inserted duplicates instead of overwriting them. Because
    ``ensure_paper_ingested`` re-added every chunk of an already-ingested paper
    on each synthesis run, a paper accumulated one extra copy of itself per run:
    storage grew linearly and top-k retrieval filled up with copies of the same
    passage, crowding out other evidence a little more each time.

    Reusing chunk_id makes the write idempotent. Returns None when the caller
    supplied documents without chunk ids, leaving Chroma's own behaviour intact.
    """
    ids = [str((getattr(doc, "metadata", None) or {}).get("chunk_id") or "") for doc in documents]
    if not all(ids):
        return None
    if len(set(ids)) != len(ids):
        return None
    return ids


class VectorStoreService:
    def __init__(self, identity: EmbeddingIdentity | None = None, version: int = 1):
        """Open the collection belonging to one embedding identity.

        ``identity`` defaults to the configured one. Callers repairing
        historical data pass the identity recorded for that index instead, so
        the current configuration cannot decide which model rebuilds old
        vectors.
        """
        settings = get_settings()
        self.identity = identity or resolve_runtime_identity(settings)
        self.version = version
        self.embeddings = build_embeddings_for(self.identity, settings)

        chroma_kwargs = build_chroma_connection_kwargs(settings)
        if "persist_directory" in chroma_kwargs and not chroma_kwargs["persist_directory"]:
            chroma_kwargs["persist_directory"] = CHROMA_PERSIST_DIR

        self.collection_name = collection_name_for(self.identity, self.version)
        self.vector_store = Chroma(
            # Named after what is inside it. The old name embedded only the
            # configured provider, so vectors written by a fallback backend
            # landed in a collection still claiming the configured one.
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            # Chroma carries its own copy of the identity, so a collection can
            # be checked rather than trusted.
            collection_metadata=chroma_metadata_for(self.identity, self.version),
            **chroma_kwargs,
        )
        self._verify_collection_identity()

    def _verify_collection_identity(self) -> None:
        """Refuse to use a collection built with a different embedding model.

        A collection created before identities were recorded reports nothing;
        that is treated as unknown and left alone rather than assumed to match.
        """
        try:
            stored = self.vector_store._collection.metadata  # noqa: SLF001 - no public accessor
        except Exception:
            return

        recorded = identity_from_metadata(stored)
        if recorded is None:
            logger.warning(
                "Chroma collection %r carries no embedding identity. It predates "
                "identity tracking, so it cannot be checked against the current "
                "configuration (%s/%s). Re-index it to make it verifiable.",
                self.collection_name,
                self.identity.provider,
                self.identity.model,
            )
            return

        verify_identity_match(
            collection_name=self.collection_name,
            expected=recorded,
            actual=self.identity,
        )

    async def add_documents(self, documents: list[Document]):
        """Nhúng và lưu chunk mà không block event loop của FastAPI/LangGraph.

        Raises on failure. Returning 0 on error made a failed write
        indistinguishable from "nothing to write", so callers committed the
        surrounding ingestion as successful while Chroma held no vectors.
        """
        if not documents:
            return 0

        ids = _document_ids(documents)
        await asyncio.to_thread(
            self.vector_store.add_documents, documents=documents, ids=ids
        )
        return len(documents)

    async def stage_documents_for_paper(
        self, paper_id: str, documents: list[Document]
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
        new_ids = _document_ids(documents)
        # Propagates on failure. Swallowing the error here returned an empty
        # old-id list, which the caller could not distinguish from "there were
        # no previous vectors" -- so the DB recorded a successful ingestion for
        # documents that were never indexed.
        await asyncio.to_thread(
            self.vector_store.add_documents, documents=documents, ids=new_ids
        )
        # Never report an id we just wrote as stale: a re-ingestion that reuses
        # a chunk id would otherwise have its new vector deleted by the caller's
        # cleanup step.
        written = set(new_ids or ())
        return [old_id for old_id in existing.get("ids", []) or [] if old_id not in written]

    async def delete_document_ids(self, ids: list[str]) -> int:
        """Delete a known set of Chroma IDs after the DB commit succeeds."""
        clean_ids = list(dict.fromkeys(ids or []))
        if not clean_ids:
            return 0
        await asyncio.to_thread(self.vector_store.delete, ids=clean_ids)
        return len(clean_ids)

    async def replace_documents_for_paper(self, paper_id: str, documents: list[Document]) -> int:
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
        """Rebuild this paper's vectors in *this* index from its stored chunks.

        The chunk text in PostgreSQL is the durable copy; Chroma is a derived
        store that can be cleared. Rebuilding from the text is therefore sound,
        but only within one embedding space.

        This is the fix for the most dangerous version of the embedding problem.
        The previous implementation embedded the recovered text with whatever
        model happened to be configured at that moment, and wrote the result
        into whichever collection was open. Change EMBEDDING_PROVIDER and the
        next cache miss quietly mixed a second coordinate space into an existing
        collection. Nothing failed: the request succeeded, the log said
        "Successfully recovered N vectors", the data was really there, and
        search kept returning results. Only their meaning was gone. That is
        harder to catch than an obviously fake backend, because it looks like a
        reliability feature.

        Repair now happens through ``self`` -- an instance pinned to one
        identity, whose collection has already been checked against the identity
        recorded in Chroma. A caller repairing a historical index constructs the
        service with that index's identity and gets the right model by
        construction; the ambient configuration never enters into it.

        Raises on failure rather than printing. A silent failure here leaves the
        paper with no vectors while the caller proceeds as though it has them.
        """
        from sqlalchemy import String as SAString
        from sqlalchemy import select

        from src.database import AsyncSessionLocal
        from src.models.db_models import PageText, Paper, PDFChunk

        logger.info(
            "Recovering vectors for paper %s in collection %s (%s/%s).",
            paper_id,
            self.collection_name,
            self.identity.provider,
            self.identity.model,
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PDFChunk, PageText.page_number, Paper.file_path, Paper.title)
                .join(PageText, PDFChunk.page_text_id == PageText.id)
                .join(Paper, PDFChunk.paper_id == Paper.id)
                .where(PDFChunk.paper_id.cast(SAString) == str(paper_id))
            )
            rows = result.fetchall()

        if not rows:
            logger.warning(
                "No stored chunks for paper %s; nothing to recover. The paper "
                "needs re-ingesting from its source document.",
                paper_id,
            )
            return 0

        documents = [
            Document(
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
                    "paper_title": str(title) if title else "Unknown Title",
                },
            )
            for chunk_row, page_num, file_path, title in rows
        ]

        await self.add_documents(documents)
        logger.info("Recovered %d vectors for paper %s.", len(documents), paper_id)
        return len(documents)

    async def search_similar_documents(
        self,
        query: str,
        top_k: int = 4,
        filters: dict | None = None,
    ) -> list[Document]:
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


class _LazyVectorStoreService:
    """Process-wide vector store, constructed on first use rather than on import.

    ``VectorStoreService.__init__`` resolves embedding credentials. Now that
    ``build_embeddings`` fails loudly on a missing key instead of silently
    substituting a fake backend, building the singleton at import time would
    turn a configuration problem into an import-time crash in every module that
    merely imports this one -- including tests that never touch retrieval.

    Deferring construction keeps the error where it belongs: at the point
    something actually tries to embed or search.
    """

    _instance: VectorStoreService | None = None

    def _resolve(self) -> VectorStoreService:
        if _LazyVectorStoreService._instance is None:
            _LazyVectorStoreService._instance = VectorStoreService()
        return _LazyVectorStoreService._instance

    def __getattr__(self, name: str):
        return getattr(self._resolve(), name)


vector_store_service = _LazyVectorStoreService()
