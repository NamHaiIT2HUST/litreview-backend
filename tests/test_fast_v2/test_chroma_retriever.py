"""Tests for FastV2ChromaEvidenceRetriever -- mocked semantic index."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.retrieval import EvidenceRetriever

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()


class _FakeIndex:
    def __init__(self, units):
        self._units = units
        self.calls: list[dict] = []

    def query(self, query_text, *, limit, paper_ids):
        self.calls.append({"query": query_text, "limit": limit, "paper_ids": list(paper_ids)})
        return self._units[:limit]


def _unit(paper_id=PAPER_A):
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title="t",
        page=1,
        text="body",
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
    )


def test_satisfies_evidence_retriever_protocol():
    retriever = FastV2ChromaEvidenceRetriever(_FakeIndex([]), paper_ids=[PAPER_A])
    assert isinstance(retriever, EvidenceRetriever)


@pytest.mark.asyncio
async def test_retrieve_delegates_to_index_query_with_configured_paper_ids():
    index = _FakeIndex([_unit(), _unit()])
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=[PAPER_A, PAPER_B])

    results = await retriever.retrieve("some query", limit=40)

    assert len(results) == 2
    assert index.calls == [{"query": "some query", "limit": 40, "paper_ids": [PAPER_A, PAPER_B]}]


@pytest.mark.asyncio
async def test_retrieve_respects_limit():
    index = _FakeIndex([_unit(), _unit(), _unit()])
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=[PAPER_A])
    results = await retriever.retrieve("q", limit=2)
    assert len(results) == 2
