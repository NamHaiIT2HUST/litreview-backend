"""Fast v2 persistent semantic Evidence-First index.

A dedicated, versioned Chroma collection -- completely decoupled from the
Legacy vector store (``src/services/vector_store.py``) and from
``EMBEDDING_PROVIDER``. This module never imports ``VectorStoreService`` and
never depends on an OpenAI key.

Why a separate collection instead of reusing ``litreview_papers_v2``
----------------------------------------------------------------------
That collection was found (Fast v2 parity repair diagnostic) to hold stale
128-dimension ``LightweightHashEmbeddings`` vectors -- non-semantic, and
incompatible with any real embedding model. Querying it with a 384-dim MiniLM
query vector would either error or silently return meaningless results.
Fast v2 gets its own collection, named and versioned so a future embedding
change creates ``fast_v2_evidence_minilm_v2`` rather than silently mixing
dimensions in one collection.

Embedding is computed here directly with ``sentence-transformers`` and passed
to Chroma as raw vectors (``collection.add(embeddings=...)``), not through
Chroma's embedding-function abstraction. This is what makes Fast v2 retrieval
independent of ``EMBEDDING_PROVIDER``/OpenAI: nothing here asks Chroma to
compute an embedding for us.

Dimension safety
-----------------
Before any insert or query, the collection's recorded dimension (peeked from
an existing vector, or from collection metadata on an empty collection) is
checked against ``FAST_V2_EMBED_DIMENSION``. A mismatch raises
``SemanticIndexDimensionError`` rather than silently querying/inserting into
an incompatible collection -- this is the exact failure mode (128d hash
vectors under a 384d query) this module exists to prevent.

Multi-paper filtering
----------------------
Uses Chroma's native ``where={"paper_id": {"$in": [...]}}`` directly against
``collection.query``/``collection.get``. This is the fix for the bug found
during the parity repair: the Legacy retriever's ``VectorStoreEvidenceRetriever
._filters()`` built the same ``{"$in": [...]}`` shape but the caller
(``VectorStoreService.search_similar_documents``) mishandled it by passing the
whole filter dict into ``recover_vectors_for_paper(pid)``, which expects a
single paper UUID. This module talks to Chroma directly and never goes
through that code path, so the bug does not apply here -- there is no
Python-side post-filtering, the ``$in`` filter is Chroma's own native
mechanism.

No LLM anywhere in this module, at ingestion or query time.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit

FAST_V2_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FAST_V2_EMBED_DIMENSION = 384
#: Versioned so an embedding-model change never silently mixes dimensions
#: into an existing collection -- see module docstring.
FAST_V2_COLLECTION_NAME = "fast_v2_evidence_minilm_v1"

DEFAULT_CHROMA_HOST = "localhost"
DEFAULT_CHROMA_PORT = 8001


class SemanticIndexDimensionError(RuntimeError):
    """Raised instead of silently querying/inserting into an incompatible collection."""


@dataclass(frozen=True)
class IndexStats:
    paper_id: uuid.UUID
    chunks_seen: int
    chunks_indexed: int
    chunks_skipped_empty: int


def _default_chroma_client_factory(host: str = DEFAULT_CHROMA_HOST, port: int = DEFAULT_CHROMA_PORT) -> Any:
    import chromadb

    return chromadb.HttpClient(host=host, port=port)


class FastV2SemanticIndex:
    """Owns the dedicated Fast v2 Chroma collection: ingestion + dimension safety.

    Model and Chroma client are both lazy -- constructing this class must not
    import torch or open a network connection.
    """

    def __init__(
        self,
        *,
        collection_name: str = FAST_V2_COLLECTION_NAME,
        model_name: str = FAST_V2_EMBED_MODEL,
        expected_dimension: int = FAST_V2_EMBED_DIMENSION,
        chroma_client_factory: Callable[[], Any] | None = None,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.model_name = model_name
        self.expected_dimension = expected_dimension
        self._chroma_client_factory = chroma_client_factory or _default_chroma_client_factory
        self._model_factory = model_factory
        self._client: Any = None
        self._model: Any = None
        self._collection: Any = None

    @property
    def is_model_loaded(self) -> bool:
        return self._model is not None

    def _default_model_factory(self, model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    def _load_model(self) -> Any:
        if self._model is None:
            factory = self._model_factory or self._default_model_factory
            self._model = factory(self.model_name)
        return self._model

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._chroma_client_factory()
        return self._client

    def _get_collection(self) -> Any:
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                self.collection_name,
                metadata={
                    "embedding_model": self.model_name,
                    "embedding_dimension": str(self.expected_dimension),
                    "hnsw:space": "cosine",
                },
            )
        return self._collection

    def _validate_dimension(self, collection: Any) -> None:
        """Fail loudly if the collection already holds vectors of a different
        dimension. Never silently query/insert into an incompatible collection."""
        peeked = collection.get(limit=1, include=["embeddings"])
        embeddings = peeked.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return  # empty collection: nothing to validate against yet
        actual_dim = len(embeddings[0])
        if actual_dim != self.expected_dimension:
            raise SemanticIndexDimensionError(
                f"Collection {self.collection_name!r} holds {actual_dim}-dimension vectors, "
                f"but Fast v2 expects {self.expected_dimension} ({self.model_name}). "
                "Refusing to query/insert -- this is exactly the stale-128d-hash-embedding "
                "failure mode the dedicated Fast v2 collection exists to prevent. "
                "Use a differently-named/versioned collection or rebuild this one."
            )

    def collection_info(self) -> dict[str, Any]:
        collection = self._get_collection()
        peeked = collection.get(limit=1, include=["embeddings"])
        embeddings = peeked.get("embeddings")
        actual_dim = len(embeddings[0]) if embeddings is not None and len(embeddings) else None
        return {
            "collection_name": self.collection_name,
            "count": collection.count(),
            "embedding_dimension": actual_dim,
            "expected_dimension": self.expected_dimension,
            "dimension_ok": actual_dim is None or actual_dim == self.expected_dimension,
        }

    # -- Ingestion -----------------------------------------------------------

    def index_units(self, units: Sequence[EvidenceUnit]) -> IndexStats:
        """Upsert a batch of canonical EvidenceUnits into the collection.

        Upsert (not add) makes this idempotent: re-indexing a paper overwrites
        existing rows for the same chunk id rather than duplicating them --
        this is what "reindex one paper" and "avoid duplicate chunk records"
        reduce to.
        """
        collection = self._get_collection()
        self._validate_dimension(collection)

        # EvidenceUnit.from_chunk already refuses empty/whitespace-only text
        # at construction time, so the only way `usable` can shrink here is a
        # missing source_chunk_id (a unit not backed by a canonical chunk row,
        # which cannot be cited and must not be indexed).
        chunks_seen = len(units)
        usable = [u for u in units if u.source_chunk_id is not None]
        chunks_skipped_empty = chunks_seen - len(usable)

        if not usable:
            paper_id = units[0].paper_id if units else None
            return IndexStats(paper_id=paper_id, chunks_seen=chunks_seen, chunks_indexed=0, chunks_skipped_empty=chunks_skipped_empty)

        model = self._load_model()
        embeddings = model.encode([u.text for u in usable], convert_to_numpy=True, show_progress_bar=False)
        if embeddings.shape[1] != self.expected_dimension:
            raise SemanticIndexDimensionError(
                f"{self.model_name} produced {embeddings.shape[1]}-dim embeddings, "
                f"expected {self.expected_dimension}. Refusing to index."
            )

        ids = [str(u.source_chunk_id) for u in usable]
        documents = [u.text for u in usable]
        metadatas = [
            {
                "paper_id": str(u.paper_id),
                "paper_title": u.title,
                "page": u.page if u.page is not None else -1,
                "page_text_id": str(u.page_text_id) if u.page_text_id else "",
                "page_char_start": u.page_char_start if u.page_char_start is not None else -1,
                "page_char_end": u.page_char_end if u.page_char_end is not None else -1,
            }
            for u in usable
        ]

        collection.upsert(
            ids=ids,
            embeddings=[e.tolist() for e in embeddings],
            documents=documents,
            metadatas=metadatas,
        )

        return IndexStats(
            paper_id=usable[0].paper_id,
            chunks_seen=chunks_seen,
            chunks_indexed=len(usable),
            chunks_skipped_empty=chunks_skipped_empty,
        )

    def delete_paper(self, paper_id: uuid.UUID) -> None:
        collection = self._get_collection()
        collection.delete(where={"paper_id": str(paper_id)})

    # -- Query -----------------------------------------------------------------

    def query(self, query_text: str, *, limit: int, paper_ids: Sequence[uuid.UUID]) -> list[EvidenceUnit]:
        collection = self._get_collection()
        self._validate_dimension(collection)

        paper_id_strs = [str(pid) for pid in paper_ids]
        if not paper_id_strs:
            return []
        where = {"paper_id": paper_id_strs[0]} if len(paper_id_strs) == 1 else {"paper_id": {"$in": paper_id_strs}}

        model = self._load_model()
        query_embedding = model.encode([query_text], convert_to_numpy=True)[0]
        if len(query_embedding) != self.expected_dimension:
            raise SemanticIndexDimensionError(
                f"Query embedding is {len(query_embedding)}-dim, expected {self.expected_dimension}."
            )

        result = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        units: list[EvidenceUnit] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            page = metadata.get("page")
            page_text_id = metadata.get("page_text_id") or None
            char_start = metadata.get("page_char_start")
            char_end = metadata.get("page_char_end")
            # Cosine space in Chroma: distance = 1 - cosine_similarity, so
            # similarity = 1 - distance -- directly comparable to the reference
            # retriever's raw normalized-dot-product cosine score.
            similarity = 1.0 - float(distance)
            units.append(
                EvidenceUnit.from_chunk(
                    paper_id=uuid.UUID(metadata["paper_id"]),
                    title=metadata.get("paper_title", "Unknown Title"),
                    page=None if page in (None, -1) else int(page),
                    text=text,
                    source_chunk_id=uuid.UUID(chunk_id),
                    page_text_id=uuid.UUID(page_text_id) if page_text_id else None,
                    page_char_start=None if char_start in (None, -1) else int(char_start),
                    page_char_end=None if char_end in (None, -1) else int(char_end),
                    retrieval_score=similarity,
                )
            )
        return units
