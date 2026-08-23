"""Tests for FastV2IndexingService -- mocked DB session, real FastV2SemanticIndex
against a mocked Chroma client (no network, no torch)."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import numpy as np
import pytest

from src.synthesis.fast_v2.evidence.indexing_service import FastV2IndexingService
from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex

from tests.test_fast_v2.test_semantic_index import _FakeClient, _FakeEmbedder

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
    def __init__(self, chunk_rows, paper_rows):
        self._chunk_rows = chunk_rows
        self._paper_rows = paper_rows
        self._call = 0

    async def execute(self, _query):
        self._call += 1
        return _FakeResult(self._chunk_rows if self._call == 1 else self._paper_rows)


def _session_factory(chunks, papers):
    @asynccontextmanager
    async def factory():
        yield _FakeSession(chunks, papers)

    return factory


def _make_service(chunks, papers):
    client = _FakeClient()
    index = FastV2SemanticIndex(
        chroma_client_factory=lambda: client,
        model_factory=lambda _name: _FakeEmbedder(),
    )
    service = FastV2IndexingService(_session_factory(chunks, papers), index)
    return service, index, client


@pytest.mark.asyncio
async def test_index_paper_indexes_all_its_chunks():
    chunks = [_FakeChunk(uuid.uuid4(), PAPER_A, "alpha beta", i) for i in range(3)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    service, index, client = _make_service(chunks, papers)

    stats = await service.index_paper(PAPER_A)

    assert stats.chunks_indexed == 3
    assert client.collections[index.collection_name].count() == 3


@pytest.mark.asyncio
async def test_index_paper_is_idempotent():
    chunks = [_FakeChunk(uuid.uuid4(), PAPER_A, "alpha beta", 1)]
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    service, index, client = _make_service(chunks, papers)

    await service.index_paper(PAPER_A)
    await service.index_paper(PAPER_A)  # re-run, same chunk ids

    assert client.collections[index.collection_name].count() == 1


@pytest.mark.asyncio
async def test_reindex_paper_clears_stale_chunks_no_longer_upstream():
    old_chunk = _FakeChunk(uuid.uuid4(), PAPER_A, "alpha", 1)
    papers = [SimpleNamespace(id=PAPER_A, title="Paper A")]
    service, index, client = _make_service([old_chunk], papers)
    await service.index_paper(PAPER_A)
    assert client.collections[index.collection_name].count() == 1

    # Simulate re-chunking: the old chunk id no longer exists upstream.
    new_chunk = _FakeChunk(uuid.uuid4(), PAPER_A, "beta gamma", 1)
    service._session_factory = _session_factory([new_chunk], papers)

    await service.reindex_paper(PAPER_A)

    collection = client.collections[index.collection_name]
    assert collection.count() == 1
    assert collection.ids == [str(new_chunk.id)]


@pytest.mark.asyncio
async def test_rebuild_collection_indexes_every_given_paper():
    """rebuild_collection calls reindex_paper once per paper id.

    The fake session factory here isn't paper-filtered (real SQLAlchemy
    filters by ``paper_id.in_([paper_id])``; the fake just returns a fixed
    row set), so this asserts the call count / aggregate behaviour rather
    than per-paper chunk isolation -- that isolation is exercised for real
    against Postgres in the parity harness, not here.
    """
    chunk_a = _FakeChunk(uuid.uuid4(), PAPER_A, "alpha", 1)
    chunk_b = _FakeChunk(uuid.uuid4(), PAPER_B, "beta", 1)
    papers = [SimpleNamespace(id=PAPER_A, title="A"), SimpleNamespace(id=PAPER_B, title="B")]

    client = _FakeClient()
    index = FastV2SemanticIndex(chroma_client_factory=lambda: client, model_factory=lambda _n: _FakeEmbedder())
    service = FastV2IndexingService(_session_factory([chunk_a, chunk_b], papers), index)

    stats = await service.rebuild_collection([PAPER_A, PAPER_B])

    assert len(stats) == 2
    assert client.collections[index.collection_name].count() >= 1


@pytest.mark.asyncio
async def test_no_query_time_llm_extraction():
    """Ingestion computes an embedding from existing text -- it never calls
    an LLM to extract/summarise/classify anything."""
    import inspect

    from src.synthesis.fast_v2.evidence import indexing_service as mod

    source = inspect.getsource(mod)
    for banned in ("openai", "ChatOpenAI", "extract_paper", "llm.", "LLM("):
        assert banned not in source
