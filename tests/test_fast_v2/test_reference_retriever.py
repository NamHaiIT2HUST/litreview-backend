"""Tests for InMemoryCosineEvidenceRetriever -- parity/reproducibility only.

Not the production retriever. Fully mocked: a fake session factory and a fake
embedding model, so these tests run on CPU with no DB and no torch import.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import numpy as np
import pytest

from src.synthesis.fast_v2.evidence.reference_retriever import (
    InMemoryCosineEvidenceRetriever,
)

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()


class _FakeChunk:
    def __init__(self, id_, paper_id, text, page):
        self.id = id_
        self.paper_id = paper_id
        self.chunk_text = text
        self.page = page
        self.page_text_id = uuid.uuid4()
        self.page_char_start = 0
        self.page_char_end = len(text)


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeSession:
    """Answers PDFChunk/Paper selects with canned rows, in call order."""

    def __init__(self, chunk_rows, paper_rows):
        self._chunk_rows = chunk_rows
        self._paper_rows = paper_rows
        self._call = 0

    async def execute(self, _query):
        self._call += 1
        return _FakeResult(self._chunk_rows if self._call == 1 else self._paper_rows)


def _fake_session_factory(chunks, papers):
    @asynccontextmanager
    async def factory():
        yield _FakeSession(chunks, papers)

    return factory


class _FakeEmbedder:
    """Deterministic bag-of-words-ish embedder: encodes by simple keyword hashing.

    Good enough to produce a stable, inspectable cosine ranking without torch.
    """

    VOCAB = ["alpha", "beta", "gamma", "delta"]

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append([float(lower.count(word)) for word in self.VOCAB])
        return np.array(vectors, dtype=float)


def _make_retriever(chunks, papers, *, model=None):
    model = model or _FakeEmbedder()
    return InMemoryCosineEvidenceRetriever(
        _fake_session_factory(chunks, papers),
        paper_ids=[PAPER_A, PAPER_B],
        model_factory=lambda _name: model,
    )


@pytest.mark.asyncio
async def test_lazy_model_load_does_not_happen_at_construction():
    retriever = _make_retriever([], [])
    assert retriever.is_loaded is False


@pytest.mark.asyncio
async def test_lazy_model_load_happens_on_first_retrieve():
    chunks = [_FakeChunk(uuid.uuid4(), PAPER_A, "alpha alpha alpha", 1)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    retriever = _make_retriever(chunks, papers)
    assert retriever.is_loaded is False
    await retriever.retrieve("alpha", limit=10)
    assert retriever.is_loaded is True


@pytest.mark.asyncio
async def test_cosine_ordering_best_first():
    chunks = [
        _FakeChunk(uuid.uuid4(), PAPER_A, "gamma gamma gamma", 1),  # weakest match for "alpha"
        _FakeChunk(uuid.uuid4(), PAPER_A, "alpha alpha alpha alpha", 2),  # strongest
        _FakeChunk(uuid.uuid4(), PAPER_A, "alpha beta", 3),  # partial
    ]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    retriever = _make_retriever(chunks, papers)

    results = await retriever.retrieve("alpha", limit=10)

    assert [r.page for r in results] == [2, 3, 1]
    assert results[0].retrieval_score >= results[1].retrieval_score >= results[2].retrieval_score


@pytest.mark.asyncio
async def test_top_candidate_pool_limit_is_respected():
    chunks = [_FakeChunk(uuid.uuid4(), PAPER_A, f"alpha {i}", i) for i in range(10)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    retriever = _make_retriever(chunks, papers)

    results = await retriever.retrieve("alpha", limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_corpus_is_fetched_and_embedded_once_across_multiple_retrieve_calls():
    calls = {"encode": 0}

    class _CountingEmbedder(_FakeEmbedder):
        def encode(self, texts, **kwargs):
            calls["encode"] += 1
            return super().encode(texts, **kwargs)

    chunks = [_FakeChunk(uuid.uuid4(), PAPER_A, "alpha beta", 1)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    retriever = _make_retriever(chunks, papers, model=_CountingEmbedder())

    await retriever.retrieve("alpha", limit=5)
    await retriever.retrieve("beta", limit=5)

    # 1 corpus-embedding call + 1 query-embedding call per retrieve = 3 total,
    # NOT 2 corpus embeds -- the corpus must not be re-fetched/re-embedded.
    assert calls["encode"] == 3


@pytest.mark.asyncio
async def test_empty_corpus_returns_empty_without_error():
    retriever = _make_retriever([], [])
    assert await retriever.retrieve("anything", limit=10) == []


@pytest.mark.asyncio
async def test_retrieved_units_carry_provenance():
    chunk_id = uuid.uuid4()
    chunks = [_FakeChunk(chunk_id, PAPER_A, "alpha alpha", 7)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    retriever = _make_retriever(chunks, papers)

    results = await retriever.retrieve("alpha", limit=5)
    assert results[0].source_chunk_id == chunk_id
    assert results[0].paper_id == PAPER_A
    assert results[0].title == "Paper A"
    assert results[0].page == 7
