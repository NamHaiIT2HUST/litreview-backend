"""Tests 17/18: P-165 owns citation authority, not the generator."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.citations.finalizer import (
    FinalCitation,
    finalize_draft,
)
from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.base import GeneratedDraft

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()


def _unit(paper_id, title, page, text, start, end):
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=title,
        page=page,
        text=text,
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
        page_char_start=start,
        page_char_end=end,
    ).with_dimension("d", 1.0)


def _bank():
    return GroundedEvidenceBank.build(
        question="q",
        dimensions=["d"],
        evidence_by_dimension={
            "d": [
                _unit(PAPER_A, "Paper A", 4, "formulation evidence", 100, 140),
                _unit(PAPER_B, "Paper B", 9, "convergence evidence", 200, 250),
            ]
        },
    )


def _draft(text):
    return GeneratedDraft(text=text, model_name="fake", prompt_version="v")


# --------------------------------------------------------------------------
# Test 17 -- native OpenScholar citation IDs are not authoritative
# --------------------------------------------------------------------------

def test_native_citation_indices_do_not_become_final_citations():
    """Test 17."""
    bank = _bank()
    result = finalize_draft(draft=_draft("Claim one [0]. Claim two [1]."), evidence_bank=bank)

    for citation in result.citations:
        assert isinstance(citation, FinalCitation)
        assert citation.evidence_id in {u.evidence_id for u in bank.evidence}


def test_out_of_range_native_citations_are_discarded_not_published():
    """The generator's known failure mode: citing an index that does not exist."""
    result = finalize_draft(
        draft=_draft("A bogus claim [7]."), evidence_bank=_bank()
    )
    assert result.citations == ()
    assert 7 in result.rejected_native_indices


def test_native_indices_are_retained_only_as_diagnostics():
    result = finalize_draft(draft=_draft("Claim [0] and [9]."), evidence_bank=_bank())
    assert result.native_citation_indices == (0, 9)
    assert result.rejected_native_indices == (9,)
    # ...but the published citations never include the bogus one.
    assert len(result.citations) == 1


def test_citation_authority_is_reported_as_p165():
    result = finalize_draft(draft=_draft("Claim [0]."), evidence_bank=_bank())
    assert result.citation_authority == "p165_deterministic_finalizer"


# --------------------------------------------------------------------------
# Test 18 -- final provenance resolves via P-165 evidence IDs
# --------------------------------------------------------------------------

def test_final_provenance_resolves_through_the_evidence_unit():
    """Test 18: evidence_id -> paper/page/source offsets."""
    bank = _bank()
    result = finalize_draft(draft=_draft("Claim [1]."), evidence_bank=bank)

    citation = result.citations[0]
    source = bank.evidence[1]
    assert citation.evidence_id == source.evidence_id
    assert citation.paper_id == source.paper_id
    assert citation.source_page == source.page
    assert citation.source_char_start == source.page_char_start
    assert citation.source_char_end == source.page_char_end
    assert citation.quoted_snippet == source.text


def test_citation_marker_is_a_stable_per_paper_display_number():
    bank = _bank()
    result = finalize_draft(draft=_draft("A [0]. B [1]."), evidence_bank=bank)
    markers = {c.paper_id: c.citation_marker for c in result.citations}
    assert markers[bank.evidence[0].paper_id] == "[1]"
    assert markers[bank.evidence[1].paper_id] == "[2]"


def test_markers_point_at_real_offsets_in_the_final_text():
    result = finalize_draft(draft=_draft("Claim one [0]."), evidence_bank=_bank())
    citation = result.citations[0]
    assert (
        result.text[citation.review_char_start : citation.review_char_end]
        == citation.citation_marker
    )


def test_repeated_citation_of_the_same_paper_yields_one_marker_per_occurrence():
    result = finalize_draft(draft=_draft("A [0]. B [0]."), evidence_bank=_bank())
    assert len(result.citations) == 2
    assert {c.citation_marker for c in result.citations} == {"[1]"}


def test_finalizer_is_deterministic():
    draft, bank = _draft("Claim [0] and [1]."), _bank()
    first = finalize_draft(draft=draft, evidence_bank=bank)
    second = finalize_draft(draft=draft, evidence_bank=bank)
    assert first.text == second.text
    assert [c.evidence_id for c in first.citations] == [c.evidence_id for c in second.citations]


def test_response_markers_are_stripped_from_the_final_text():
    result = finalize_draft(
        draft=_draft("[Response_Start]The answer [0].[Response_End]"),
        evidence_bank=_bank(),
    )
    assert "[Response_Start]" not in result.text
    assert "[Response_End]" not in result.text


def test_finalizer_calls_no_llm():
    """Deterministic by construction -- no generation happens here."""
    result = finalize_draft(draft=_draft("Claim [0]."), evidence_bank=_bank())
    assert result.generation_calls == 0


def test_empty_bank_produces_no_citations():
    bank = GroundedEvidenceBank.build(question="q", dimensions=["d"], evidence_by_dimension={"d": []})
    result = finalize_draft(draft=_draft("Unsupported prose [0]."), evidence_bank=bank)
    assert result.citations == ()


def test_result_is_serializable():
    payload = finalize_draft(draft=_draft("Claim [0]."), evidence_bank=_bank()).to_dict()
    for key in ("text", "citations", "citation_authority", "native_citation_indices"):
        assert key in payload
    assert payload["citations"][0]["evidence_id"]
