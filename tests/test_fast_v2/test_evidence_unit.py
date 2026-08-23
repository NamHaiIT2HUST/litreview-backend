"""Test 2: EvidenceUnit preserves paper/page/source provenance."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit


def _chunk_kwargs(**overrides):
    base = dict(
        paper_id=uuid.uuid4(),
        title="Xu 2010 Study",
        page=4,
        text="The split feasibility problem is formulated in Hilbert space.",
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
        page_char_start=120,
        page_char_end=181,
    )
    base.update(overrides)
    return base


def test_evidence_unit_preserves_paper_page_and_source_provenance():
    """Test 2: every provenance field survives construction unchanged."""
    kwargs = _chunk_kwargs()
    unit = EvidenceUnit.from_chunk(**kwargs)

    assert unit.paper_id == kwargs["paper_id"]
    assert unit.title == kwargs["title"]
    assert unit.page == 4
    assert unit.text == kwargs["text"]
    assert unit.source_chunk_id == kwargs["source_chunk_id"]
    assert unit.page_text_id == kwargs["page_text_id"]
    assert unit.page_char_start == 120
    assert unit.page_char_end == 181


def test_evidence_id_is_distinct_from_source_chunk_id():
    """The hygiene spike was bitten by conflating these two identifiers.

    evidence_id is the canonical dedupe/citation key; source_chunk_id is the
    PDFChunk row. Both are carried, and they are not the same value.
    """
    unit = EvidenceUnit.from_chunk(**_chunk_kwargs())
    assert unit.evidence_id != str(unit.source_chunk_id)
    assert unit.source_chunk_id is not None


def test_evidence_id_is_deterministic_for_the_same_source_chunk():
    """Dedupe across dimensions relies on a stable canonical key."""
    kwargs = _chunk_kwargs()
    assert EvidenceUnit.from_chunk(**kwargs).evidence_id == EvidenceUnit.from_chunk(**kwargs).evidence_id


def test_different_chunks_get_different_evidence_ids():
    a = EvidenceUnit.from_chunk(**_chunk_kwargs())
    b = EvidenceUnit.from_chunk(**_chunk_kwargs())
    assert a.evidence_id != b.evidence_id


def test_evidence_unit_is_reusable_input_not_an_llm_answer():
    """EvidenceUnit text must be verbatim canonical chunk text."""
    kwargs = _chunk_kwargs()
    unit = EvidenceUnit.from_chunk(**kwargs)
    assert unit.text == kwargs["text"]
    # No field exists that could hold a generated/summarised value.
    assert not hasattr(unit, "value")
    assert not hasattr(unit, "generated_text")


def test_retrieval_and_rerank_metadata_round_trip():
    unit = EvidenceUnit.from_chunk(**_chunk_kwargs()).with_scores(
        retrieval_score=0.81, rerank_score=-0.49
    )
    assert unit.retrieval_score == pytest.approx(0.81)
    assert unit.rerank_score == pytest.approx(-0.49)


def test_evidence_unit_serializes_with_provenance():
    unit = EvidenceUnit.from_chunk(**_chunk_kwargs()).with_scores(rerank_score=1.5)
    payload = unit.to_dict()
    for key in (
        "evidence_id",
        "paper_id",
        "title",
        "page",
        "text",
        "source_chunk_id",
        "page_text_id",
        "page_char_start",
        "page_char_end",
        "rerank_score",
    ):
        assert key in payload, key


def test_evidence_unit_rejects_empty_text():
    with pytest.raises(ValueError):
        EvidenceUnit.from_chunk(**_chunk_kwargs(text="   "))
