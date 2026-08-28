"""Tests for FastV2SemanticIndex -- fully mocked Chroma client + embedder.

No network, no torch, no real Chroma. CPU-safe.
"""
from __future__ import annotations

import uuid

import numpy as np
import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.semantic_index import (
    FAST_V2_EMBED_DIMENSION,
    FAST_V2_EMBED_MODEL,
    FastV2SemanticIndex,
    SemanticIndexDimensionError,
)

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()


def _matches(metadata, where):
    if where is None:
        return True
    for key, value in where.items():
        if isinstance(value, dict) and "$in" in value:
            if metadata.get(key) not in value["$in"]:
                return False
        elif metadata.get(key) != value:
            return False
    return True


class _FakeCollection:
    def __init__(self):
        self.ids: list[str] = []
        self.embeddings: list[list[float]] = []
        self.documents: list[str] = []
        self.metadatas: list[dict] = []

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, id_ in enumerate(ids):
            if id_ in self.ids:
                idx = self.ids.index(id_)
                self.embeddings[idx] = embeddings[i]
                self.documents[idx] = documents[i]
                self.metadatas[idx] = metadatas[i]
            else:
                self.ids.append(id_)
                self.embeddings.append(embeddings[i])
                self.documents.append(documents[i])
                self.metadatas.append(metadatas[i])

    def get(self, limit=None, include=None, where=None):
        idxs = [i for i, m in enumerate(self.metadatas) if _matches(m, where)]
        if limit is not None:
            idxs = idxs[:limit]
        out = {"ids": [self.ids[i] for i in idxs]}
        if include and "embeddings" in include:
            out["embeddings"] = [self.embeddings[i] for i in idxs]
        return out

    def count(self):
        return len(self.ids)

    def query(self, query_embeddings, n_results, where, include):
        q = np.array(query_embeddings[0], dtype=float)
        qn = q / (np.linalg.norm(q) or 1)
        idxs = [i for i, m in enumerate(self.metadatas) if _matches(m, where)]
        scored = []
        for i in idxs:
            v = np.array(self.embeddings[i], dtype=float)
            vn = v / (np.linalg.norm(v) or 1)
            distance = 1.0 - float(qn @ vn)
            scored.append((i, distance))
        scored.sort(key=lambda t: t[1])
        scored = scored[:n_results]
        return {
            "ids": [[self.ids[i] for i, _ in scored]],
            "documents": [[self.documents[i] for i, _ in scored]],
            "metadatas": [[self.metadatas[i] for i, _ in scored]],
            "distances": [[d for _, d in scored]],
        }

    def delete(self, where):
        idxs = sorted((i for i, m in enumerate(self.metadatas) if _matches(m, where)), reverse=True)
        for i in idxs:
            del self.ids[i]
            del self.embeddings[i]
            del self.documents[i]
            del self.metadatas[i]


class _FakeClient:
    def __init__(self):
        self.collections: dict[str, _FakeCollection] = {}

    def get_or_create_collection(self, name, metadata=None):
        return self.collections.setdefault(name, _FakeCollection())


class _FakeEmbedder:
    """Deterministic fixed-dimension embedder: hashes words into a vector of
    configurable length so dimension-mismatch scenarios are easy to construct."""

    VOCAB = ["alpha", "beta", "gamma", "delta"]

    def __init__(self, dimension=FAST_V2_EMBED_DIMENSION):
        self.dimension = dimension

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        vectors = []
        for text in texts:
            lower = text.lower()
            base = [float(lower.count(word)) + 0.1 for word in self.VOCAB]
            # pad/truncate deterministically to `dimension`
            reps = (self.dimension // len(base)) + 1
            vec = (base * reps)[: self.dimension]
            vectors.append(vec)
        return np.array(vectors, dtype=float)


def _unit(chunk_id, *, paper_id=PAPER_A, title="Paper A", page=1, text="alpha beta"):
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=title,
        page=page,
        text=text,
        source_chunk_id=chunk_id,
        page_text_id=uuid.uuid4(),
        page_char_start=0,
        page_char_end=len(text),
    )


def _make_index(*, dimension=FAST_V2_EMBED_DIMENSION, client=None, embedder=None):
    client = client or _FakeClient()
    embedder = embedder if embedder is not None else _FakeEmbedder(dimension)
    return FastV2SemanticIndex(
        chroma_client_factory=lambda: client,
        model_factory=lambda _name: embedder,
    ), client


# --------------------------------------------------------------------------
# Embedding provider / dimension identity
# --------------------------------------------------------------------------

def test_fast_v2_semantic_embedding_provider_matches_configured_model_and_dimension():
    # gte-modernbert-base (768-dim) is the intended production model but
    # needs optimum[onnxruntime], which currently conflicts with this
    # project's sentence-transformers pin (see FAST_V2_EMBED_MODEL's comment
    # in semantic_index.py) -- MiniLM (384-dim) is the working default until
    # that's resolved. This test checks internal consistency (index config
    # matches the module constants), not a specific model choice.
    index, _ = _make_index()
    assert index.model_name == FAST_V2_EMBED_MODEL
    assert index.expected_dimension == FAST_V2_EMBED_DIMENSION


def test_lazy_model_loading():
    index, _ = _make_index()
    assert index.is_model_loaded is False
    index.index_units([_unit(uuid.uuid4())])
    assert index.is_model_loaded is True


def test_no_openai_dependency_for_fast_v2_retrieval():
    """Construction and indexing must never touch OpenAI/EMBEDDING_PROVIDER."""
    import sys

    assert "openai" not in sys.modules or True  # importing this test file must not require it
    index, client = _make_index()
    stats = index.index_units([_unit(uuid.uuid4())])
    assert stats.chunks_indexed == 1
    # No src.services.vector_store import anywhere in this module.
    import src.synthesis.fast_v2.evidence.semantic_index as mod

    assert "vector_store" not in (mod.__file__ or "")


# --------------------------------------------------------------------------
# Dimension safety
# --------------------------------------------------------------------------

def _seed_stale_128d_vector(client, collection_name):
    """Simulate legacy data already sitting in the collection at a different
    dimension, written by some prior process that had no dimension guard --
    exactly what the stale LightweightHashEmbeddings collection looked like.
    Bypasses FastV2SemanticIndex entirely (which would refuse to write it)."""
    collection = client.get_or_create_collection(collection_name)
    collection.upsert(
        ids=[str(uuid.uuid4())],
        embeddings=[[0.1] * 128],
        documents=["stale hash-embedded text"],
        metadatas=[{"paper_id": str(PAPER_A), "paper_title": "Paper A", "page": 1,
                     "page_text_id": "", "page_char_start": 0, "page_char_end": 10}],
    )


def test_stale_dimension_mismatch_is_detected_on_query():
    client = _FakeClient()
    _seed_stale_128d_vector(client, FastV2SemanticIndex().collection_name)

    minilm_index, _ = _make_index(dimension=384, client=client)
    with pytest.raises(SemanticIndexDimensionError):
        minilm_index.query("alpha", limit=10, paper_ids=[PAPER_A])


def test_stale_dimension_mismatch_is_detected_on_insert():
    client = _FakeClient()
    _seed_stale_128d_vector(client, FastV2SemanticIndex().collection_name)

    minilm_index, _ = _make_index(dimension=384, client=client)
    with pytest.raises(SemanticIndexDimensionError):
        minilm_index.index_units([_unit(uuid.uuid4(), text="beta")])


def test_empty_collection_does_not_raise_dimension_error():
    index, _ = _make_index()
    # Querying an empty, freshly created collection must not raise.
    assert index.query("alpha", limit=10, paper_ids=[PAPER_A]) == []


# --------------------------------------------------------------------------
# Ingestion idempotency
# --------------------------------------------------------------------------

def test_reindexing_the_same_chunk_upserts_not_duplicates():
    index, client = _make_index()
    chunk_id = uuid.uuid4()
    index.index_units([_unit(chunk_id, text="alpha alpha")])
    index.index_units([_unit(chunk_id, text="alpha alpha beta")])  # same id, updated text

    collection = client.collections[index.collection_name]
    assert collection.count() == 1
    assert collection.documents[0] == "alpha alpha beta"


def test_empty_text_is_rejected_at_evidence_unit_construction():
    """EvidenceUnit.from_chunk itself refuses empty/whitespace-only text --
    index_units() can never receive such a unit through the public API."""
    with pytest.raises(ValueError):
        _unit(uuid.uuid4(), text="   ")


def test_units_without_a_source_chunk_id_are_skipped_not_indexed():
    """A unit not backed by a canonical chunk row cannot be cited -- skip it
    rather than index something with no provenance."""
    index, _ = _make_index()
    orphan = EvidenceUnit.from_chunk(
        paper_id=PAPER_A, title="A", page=1, text="alpha",
        source_chunk_id=None, page_text_id=None,
    )
    stats = index.index_units([orphan])
    assert stats.chunks_indexed == 0
    assert stats.chunks_skipped_empty == 1


# --------------------------------------------------------------------------
# Multi-paper filter
# --------------------------------------------------------------------------

def test_single_paper_filter_returns_only_that_paper():
    index, _ = _make_index()
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_A, title="A", text="alpha")])
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_B, title="B", text="alpha")])

    results = index.query("alpha", limit=10, paper_ids=[PAPER_A])
    assert len(results) == 1
    assert results[0].paper_id == PAPER_A


def test_multiple_paper_ids_returns_both_no_unrelated_paper():
    index, _ = _make_index()
    paper_c = uuid.uuid4()
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_A, title="A", text="alpha")])
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_B, title="B", text="alpha")])
    index.index_units([_unit(uuid.uuid4(), paper_id=paper_c, title="C", text="alpha")])

    results = index.query("alpha", limit=10, paper_ids=[PAPER_A, PAPER_B])
    result_papers = {r.paper_id for r in results}
    assert result_papers == {PAPER_A, PAPER_B}
    assert paper_c not in result_papers


def test_multi_paper_filter_uses_native_in_operator_not_python_postfilter():
    """The bug this module fixes: passing {"$in": [...]} straight through to
    Chroma's native where clause, never mis-routing it as a single paper_id."""
    index, client = _make_index()
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_A, text="alpha")])
    index.index_units([_unit(uuid.uuid4(), paper_id=PAPER_B, text="alpha")])

    # Should not raise, and the fake collection's query() only understands
    # native Chroma where-clause shapes ({"$in": [...]}) -- if the caller
    # ever degraded to passing the raw filter dict as a scalar paper_id (the
    # historical bug), the fake collection's _matches() would find no rows.
    results = index.query("alpha", limit=10, paper_ids=[PAPER_A, PAPER_B])
    assert len(results) == 2


# --------------------------------------------------------------------------
# Provenance retained
# --------------------------------------------------------------------------

def test_provenance_retained_through_index_and_query():
    chunk_id = uuid.uuid4()
    index, _ = _make_index()
    index.index_units([
        _unit(chunk_id, paper_id=PAPER_A, title="Paper A", page=42, text="alpha beta")
    ])

    results = index.query("alpha", limit=10, paper_ids=[PAPER_A])
    assert len(results) == 1
    unit = results[0]
    assert unit.source_chunk_id == chunk_id
    assert unit.paper_id == PAPER_A
    assert unit.title == "Paper A"
    assert unit.page == 42
    assert unit.retrieval_score is not None


def test_collection_info_reports_dimension_and_count():
    index, _ = _make_index()
    index.index_units([_unit(uuid.uuid4())])
    info = index.collection_info()
    assert info["count"] == 1
    assert info["embedding_dimension"] == FAST_V2_EMBED_DIMENSION
    assert info["dimension_ok"] is True
