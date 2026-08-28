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

#: Chosen production embedding model -- see docs/superpowers plan (2026-08-25
#: single-grounded-synthesis) for the reasoning: embedding only runs once per
#: chunk at ingest time (cached), so the larger/stronger model costs nothing
#: on the hot query path, unlike a reranker that scores many pairs per call.
#: BAAI/BGE is retired; MiniLM stays available only as the frozen RQ1/RQ2
#: benchmark reference (see selection/cross_encoder.py), never as the default.
FAST_V2_EMBED_MODEL = "Alibaba-NLP/gte-modernbert-base"
FAST_V2_EMBED_DIMENSION = 768
#: Model default is 8192 (its full trained context window). Our PDF chunks
#: are far shorter (measured average ~300-400 tokens); capping this avoids
#: pathological CPU/RAM cost from padding short chunks toward 8192 tokens.
#: See _default_model_factory for the incident this fixes.
FAST_V2_EMBED_MAX_SEQ_LENGTH = 512
#: Pre-quantized int8 ONNX export the model repo already ships (no local
#: export step needed). See _default_model_factory for the measured speedup.
FAST_V2_EMBED_ONNX_FILE = "onnx/model_int8.onnx"
#: Versioned so an embedding-model change never silently mixes dimensions
#: into an existing collection -- see module docstring. Bumped from
#: fast_v2_evidence_minilm_v1 (384-dim) when the embedding model changed to
#: gte-modernbert-base (768-dim); the old collection is left untouched and
#: simply orphaned, never queried by this version.
FAST_V2_COLLECTION_NAME = "fast_v2_evidence_gte_v1"

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
    chunks_reused: int = 0
    stale_chunks_found: int = 0
    action: str = "REUSED"
    model_loaded: bool = False
    encode_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


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

    def warm(self) -> None:
        """Force the embedding model + Chroma collection handle to load now.

        Pure warmup: no behaviour change, just moves the existing lazy-load
        cost (``_load_model``/``_get_collection``) earlier so it does not
        land inside a user request. Safe to call more than once (idempotent
        -- both underlying loads are already memoised).
        """
        self._load_model()
        self._get_collection()

    def _default_model_factory(self, model_name: str) -> Any:
        from sentence_transformers import SentenceTransformer

        # ONNX Runtime (int8) backend instead of raw PyTorch: measured
        # 8.46s/chunk (PyTorch, CPU) -> 0.31s/chunk (ONNX int8) on this
        # corpus's chunks -- ~27x faster, same model/weights/quality, only
        # the inference engine changes. Requires optimum[onnxruntime] (see
        # requirements.txt) and the pre-quantized onnx/model_int8.onnx file
        # the model repo already ships (no local export/quantization step).
        # gte-modernbert-base ships custom modeling code (ModernBERT arch),
        # so it needs trust_remote_code=True to load at all.
        #
        # Falls back to the plain PyTorch backend (same weights, no int8
        # requantization) if the ONNX path can't load -- e.g. an
        # optimum/onnxruntime version whose int4 dtype support outpaces the
        # pinned torch version (`AttributeError: module 'torch' has no
        # attribute 'int4'`, seen with torch==2.5.1 + onnxruntime==1.28),
        # or the ONNX export simply isn't cached yet. Slower, not broken --
        # keeps requests correct while the fast path stays opportunistic.
        try:
            model = SentenceTransformer(
                model_name,
                local_files_only=True,
                trust_remote_code=True,
                backend="onnx",
                model_kwargs={"file_name": FAST_V2_EMBED_ONNX_FILE},
            )
        except Exception:
            model = SentenceTransformer(
                model_name,
                local_files_only=True,
                trust_remote_code=True,
            )
        # ModernBERT's default max_seq_length is 8192 (its trained context
        # window). Left uncapped, encoding even short PDF chunks (our chunks
        # average ~300-400 tokens) triggered catastrophic CPU/RAM blowup --
        # observed as a 20-chunk batch taking 25+ minutes and driving a
        # 16GB machine down to <1GB free (quadratic attention cost scales
        # with the padded sequence length, not the real content length).
        # Our chunks never need anywhere near 8192 tokens; capping this is a
        # pure performance fix with no quality loss for this corpus.
        model.max_seq_length = FAST_V2_EMBED_MAX_SEQ_LENGTH
        return model

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
        """Fail loudly if the collection already holds vectors of a different dimension."""
        count = collection.count()
        if count == 0:
            return
        sample = collection.get(limit=1, include=["embeddings"])
        raw_embs = sample.get("embeddings")
        if raw_embs is None:
            return
        if hasattr(raw_embs, "__len__") and len(raw_embs) > 0:
            actual_dim = len(raw_embs[0])
            if actual_dim != self.expected_dimension:
                raise SemanticIndexDimensionError(
                    f"Collection {self.collection_name} contains {actual_dim}-dim "
                    f"embeddings, but {self.__class__.__name__} is configured for "
                    f"{self.expected_dimension}-dim ({self.model_name})."
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

    def get_indexed_chunk_metadata(self, paper_id: uuid.UUID) -> dict[str, dict[str, Any]]:
        """Fetch the map of existing chunk IDs and their metadatas (including text_hash) for this paper."""
        collection = self._get_collection()
        res = collection.get(where={"paper_id": str(paper_id)}, include=["metadatas"])
        if res and "ids" in res and "metadatas" in res:
            return {cid: meta for cid, meta in zip(res["ids"], res["metadatas"] or [])}
        return {}

    def get_indexed_chunk_ids(self, paper_id: uuid.UUID) -> set[str]:
        """Fetch the set of existing chunk IDs in Chroma for this paper without loading model or embeddings."""
        return set(self.get_indexed_chunk_metadata(paper_id).keys())

    # -- Ingestion -----------------------------------------------------------

    def index_units(self, units: Sequence[EvidenceUnit]) -> IndexStats:
        """Exact-ID and Content-Hash cached ingestion of canonical EvidenceUnits.

        1. Inspects existing Chroma chunk IDs and their text hashes for the target paper.
        2. If all expected chunk IDs exist AND their content hashes match:
           - Returns REUSED immediately (model is NOT loaded, encode is skipped).
        3. If chunk IDs are missing OR chunk text was modified:
           - Encodes and upserts ONLY the missing/modified chunks.
        4. If stale chunk IDs exist in Chroma (no longer in current units), deletes them.
        """
        import hashlib
        import time
        t0_total = time.perf_counter()

        collection = self._get_collection()
        self._validate_dimension(collection)

        chunks_seen = len(units)
        usable = [u for u in units if u.source_chunk_id is not None]
        chunks_skipped_empty = chunks_seen - len(usable)

        if not usable:
            paper_id = units[0].paper_id if units else None
            return IndexStats(
                paper_id=paper_id,
                chunks_seen=chunks_seen,
                chunks_indexed=0,
                chunks_skipped_empty=chunks_skipped_empty,
                chunks_reused=0,
                stale_chunks_found=0,
                action="REUSED",
                model_loaded=self.is_model_loaded,
                encode_latency_ms=0.0,
                total_latency_ms=round((time.perf_counter() - t0_total) * 1000.0, 2),
            )

        paper_id = usable[0].paper_id
        paper_title = usable[0].title
        expected_units = {str(u.source_chunk_id): u for u in usable}
        expected_hashes = {
            str(u.source_chunk_id): hashlib.md5(u.text.encode("utf-8")).hexdigest()
            for u in usable
        }

        existing_meta_map = self.get_indexed_chunk_metadata(paper_id)
        existing_chroma_ids = set(existing_meta_map.keys())

        # Check for missing IDs or modified content (hash mismatch)
        missing_ids = set()
        for cid, exp_hash in expected_hashes.items():
            if cid not in existing_chroma_ids:
                missing_ids.add(cid)
            else:
                existing_hash = existing_meta_map[cid].get("text_hash", "")
                if existing_hash and existing_hash != exp_hash:
                    missing_ids.add(cid)  # Text modified: re-encode needed

        stale_ids = existing_chroma_ids - set(expected_units.keys())

        # Cleanup stale chunks if any
        if stale_ids:
            collection.delete(ids=list(stale_ids))

        # A. Full cache hit
        if not missing_ids and existing_chroma_ids:
            t_total = round((time.perf_counter() - t0_total) * 1000.0, 2)
            print(f"[Index] {paper_title}: {len(usable)}/{len(usable)} exact chunks + hashes matched -> REUSED (model_loaded={self.is_model_loaded}, latency={t_total}ms)")
            return IndexStats(
                paper_id=paper_id,
                chunks_seen=chunks_seen,
                chunks_indexed=0,
                chunks_skipped_empty=chunks_skipped_empty,
                chunks_reused=len(usable),
                stale_chunks_found=len(stale_ids),
                action="REUSED",
                model_loaded=self.is_model_loaded,
                encode_latency_ms=0.0,
                total_latency_ms=t_total,
            )

        # B. Missing chunks to encode
        units_to_encode = [expected_units[cid] for cid in missing_ids]
        action = "FULL_INDEX" if len(units_to_encode) == len(usable) else "PARTIAL_INDEX"
        print(f"[Index] {paper_title}: {len(existing_chroma_ids)}/{len(usable)} found, indexing {len(units_to_encode)} missing chunks (action={action})")

        t0_encode = time.perf_counter()
        model = self._load_model()
        embeddings = model.encode([u.text for u in units_to_encode], convert_to_numpy=True, show_progress_bar=False)
        encode_latency_ms = round((time.perf_counter() - t0_encode) * 1000.0, 2)

        if embeddings.shape[1] != self.expected_dimension:
            raise SemanticIndexDimensionError(
                f"{self.model_name} produced {embeddings.shape[1]}-dim embeddings, "
                f"expected {self.expected_dimension}. Refusing to index."
            )

        ids = [str(u.source_chunk_id) for u in units_to_encode]
        documents = [u.text for u in units_to_encode]
        metadatas = [
            {
                "paper_id": str(u.paper_id),
                "paper_title": u.title,
                "page": u.page if u.page is not None else -1,
                "page_text_id": str(u.page_text_id) if u.page_text_id else "",
                "page_char_start": u.page_char_start if u.page_char_start is not None else -1,
                "page_char_end": u.page_char_end if u.page_char_end is not None else -1,
                "text_hash": hashlib.md5(u.text.encode("utf-8")).hexdigest(),
            }
            for u in units_to_encode
        ]

        collection.upsert(
            ids=ids,
            embeddings=[e.tolist() for e in embeddings],
            documents=documents,
            metadatas=metadatas,
        )

        t_total = round((time.perf_counter() - t0_total) * 1000.0, 2)
        return IndexStats(
            paper_id=paper_id,
            chunks_seen=chunks_seen,
            chunks_indexed=len(units_to_encode),
            chunks_skipped_empty=chunks_skipped_empty,
            chunks_reused=len(usable) - len(units_to_encode),
            stale_chunks_found=len(stale_ids),
            action=action,
            model_loaded=True,
            encode_latency_ms=encode_latency_ms,
            total_latency_ms=t_total,
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

    def keyword_query(
        self, query_text: str, *, limit: int, paper_ids: Sequence[uuid.UUID]
    ) -> list[EvidenceUnit]:
        """BM25 lexical scoring over the same paper-scoped document set.

        Fetches the scoped chunks once and scores in-process (see
        ``evidence/bm25.py``) -- fine for a selected-corpus workload, not a
        full-corpus search engine. No embedding model touched here, so this
        works even before the embedding model has loaded.
        """
        from src.synthesis.fast_v2.evidence.bm25 import bm25_scores

        collection = self._get_collection()

        paper_id_strs = [str(pid) for pid in paper_ids]
        if not paper_id_strs:
            return []
        where = {"paper_id": paper_id_strs[0]} if len(paper_id_strs) == 1 else {"paper_id": {"$in": paper_id_strs}}

        fetched = collection.get(where=where, include=["documents", "metadatas"])
        ids = fetched.get("ids", [])
        documents = fetched.get("documents", [])
        metadatas = fetched.get("metadatas", [])
        if not documents:
            return []

        scores = bm25_scores(query_text, documents)
        ranked_indices = sorted(
            range(len(documents)), key=lambda i: scores[i], reverse=True
        )[:limit]

        units: list[EvidenceUnit] = []
        for i in ranked_indices:
            if scores[i] <= 0.0:
                continue  # no lexical overlap at all -- not a candidate
            chunk_id, text, metadata = ids[i], documents[i], metadatas[i]
            page = metadata.get("page")
            page_text_id = metadata.get("page_text_id") or None
            char_start = metadata.get("page_char_start")
            char_end = metadata.get("page_char_end")
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
                    retrieval_score=scores[i],
                )
            )
        return units
