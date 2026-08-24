"""Tests 7/8: Evidence Bank deterministic merge/dedupe and diagnostics."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank, merge_evidence
from src.synthesis.fast_v2.evidence.models import EvidenceUnit

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()
CHUNK_1 = uuid.uuid4()
CHUNK_2 = uuid.uuid4()


def _unit(chunk_id, *, paper_id=PAPER_A, title="Paper A", page=1, text="body text"):
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


# --------------------------------------------------------------------------
# Test 7 -- multi-dimension selection dedupes once
# --------------------------------------------------------------------------

def test_same_evidence_selected_by_multiple_dimensions_dedupes_once():
    """Test 7."""
    per_dimension = {
        "formulation": [_unit(CHUNK_1).with_dimension("formulation", 2.0)],
        "convergence": [_unit(CHUNK_1).with_dimension("convergence", 1.0)],
    }
    merged = merge_evidence(per_dimension)
    assert len(merged) == 1


def test_dedupe_key_is_the_canonical_evidence_id():
    a = _unit(CHUNK_1).with_dimension("d1", 1.0)
    b = _unit(CHUNK_1).with_dimension("d2", 2.0)
    assert a.evidence_id == b.evidence_id
    assert len(merge_evidence({"d1": [a], "d2": [b]})) == 1


def test_distinct_evidence_is_not_collapsed():
    merged = merge_evidence(
        {"d1": [_unit(CHUNK_1).with_dimension("d1", 1.0)],
         "d2": [_unit(CHUNK_2).with_dimension("d2", 1.0)]}
    )
    assert len(merged) == 2


# --------------------------------------------------------------------------
# Test 8 -- dimension metadata is preserved through the merge
# --------------------------------------------------------------------------

def test_dimension_metadata_is_preserved():
    """Test 8: selected_for_dimensions, dimension_scores, best_dimension_score."""
    merged = merge_evidence(
        {
            "formulation": [_unit(CHUNK_1).with_dimension("formulation", 2.0)],
            "convergence": [_unit(CHUNK_1).with_dimension("convergence", 3.5)],
            "assumptions": [_unit(CHUNK_1).with_dimension("assumptions", 1.0)],
        }
    )
    unit = merged[0]
    assert set(unit.selected_for_dimensions) == {"formulation", "convergence", "assumptions"}
    assert unit.dimension_scores == pytest.approx(
        {"formulation": 2.0, "convergence": 3.5, "assumptions": 1.0}
    )
    assert unit.best_dimension_score == pytest.approx(3.5)


def test_merge_preserves_first_seen_order_not_score_order():
    """Validated v1 behaviour: dimension-iteration order, NOT score order.

    A prior version of this module re-sorted by ``best_dimension_score``
    descending after merging, which does not match the original experiment --
    the generator's context order is part of the validated input.
    """
    merged = merge_evidence(
        {
            "d1": [_unit(CHUNK_1).with_dimension("d1", 0.5)],
            "d2": [_unit(CHUNK_2).with_dimension("d2", 4.0)],
        }
    )
    # CHUNK_1 was seen first (dimension d1 iterated first), despite scoring
    # lower than CHUNK_2 -- it must stay first in the output.
    assert [u.source_chunk_id for u in merged] == [CHUNK_1, CHUNK_2]
    assert [u.best_dimension_score for u in merged] == [0.5, 4.0]


def test_merge_first_occurrence_fixes_position_later_occurrences_only_append_metadata():
    """Test: duplicate evidence appears once; first-seen position is fixed;
    later dimension metadata is still recorded onto that same position."""
    per_dimension = {
        "d1": [_unit(CHUNK_2).with_dimension("d1", 9.0)],  # highest score, seen first
        "d2": [_unit(CHUNK_1).with_dimension("d2", 1.0)],  # seen second, lower score
        "d3": [_unit(CHUNK_1).with_dimension("d3", 5.0)],  # same evidence as d2, third dimension
    }
    merged = merge_evidence(per_dimension)

    assert len(merged) == 2
    # CHUNK_2 was first-seen (dimension d1 iterated first) and keeps position 0
    # even though CHUNK_1's best score (5.0) exceeds neither here -- position
    # is purely about iteration order, not score.
    assert merged[0].source_chunk_id == CHUNK_2
    assert merged[1].source_chunk_id == CHUNK_1
    # Later dimension metadata (d3) is preserved onto the first-seen CHUNK_1 unit.
    assert set(merged[1].selected_for_dimensions) == {"d2", "d3"}
    assert merged[1].dimension_scores == pytest.approx({"d2": 1.0, "d3": 5.0})


def test_merge_does_not_use_llm_semantic_dedup():
    """Near-identical but distinct chunks stay distinct -- dedupe is by ID only."""
    merged = merge_evidence(
        {
            "d1": [_unit(CHUNK_1, text="The method converges.").with_dimension("d1", 1.0)],
            "d2": [_unit(CHUNK_2, text="The method converges.").with_dimension("d2", 1.0)],
        }
    )
    assert len(merged) == 2


# --------------------------------------------------------------------------
# GroundedEvidenceBank
# --------------------------------------------------------------------------

def _bank():
    return GroundedEvidenceBank.build(
        question="How do the two papers differ?",
        dimensions=["formulation", "convergence"],
        evidence_by_dimension={
            "formulation": [_unit(CHUNK_1).with_dimension("formulation", 2.0)],
            "convergence": [
                _unit(CHUNK_1).with_dimension("convergence", 3.5),
                _unit(CHUNK_2, paper_id=PAPER_B, title="Paper B", page=7).with_dimension(
                    "convergence", 1.5
                ),
            ],
        },
    )


def test_bank_exposes_question_dimensions_and_evidence():
    bank = _bank()
    assert bank.question == "How do the two papers differ?"
    assert bank.dimensions == ("formulation", "convergence")
    assert len(bank.evidence) == 2


def test_bank_reports_paper_distribution_and_pages():
    bank = _bank()
    assert bank.paper_distribution == {"Paper A": 1, "Paper B": 1}
    assert bank.pages_represented == {"Paper A": [1], "Paper B": [7]}


def test_bank_reports_coverage_diagnostics():
    bank = _bank()
    assert bank.coverage["dimensions_requested"] == 2
    assert bank.coverage["dimensions_with_evidence"] == 2
    assert bank.coverage["evidence_count"] == 2
    assert bank.coverage["paper_count"] == 2


def test_bank_flags_dimensions_with_no_evidence():
    bank = GroundedEvidenceBank.build(
        question="q",
        dimensions=["covered", "uncovered"],
        evidence_by_dimension={"covered": [_unit(CHUNK_1).with_dimension("covered", 1.0)]},
    )
    assert bank.coverage["dimensions_without_evidence"] == ["uncovered"]
    assert bank.coverage["dimensions_with_evidence"] == 1


def test_bank_carries_timings():
    bank = GroundedEvidenceBank.build(
        question="q",
        dimensions=["d"],
        evidence_by_dimension={"d": [_unit(CHUNK_1).with_dimension("d", 1.0)]},
        query_ms=1.5,
        retrieval_ms=10.0,
        rerank_ms=20.0,
    )
    assert bank.query_ms == pytest.approx(1.5)
    assert bank.retrieval_ms == pytest.approx(10.0)
    assert bank.rerank_ms == pytest.approx(20.0)


def test_bank_is_serializable():
    payload = _bank().to_dict()
    for key in (
        "question",
        "dimensions",
        "evidence",
        "coverage",
        "paper_distribution",
        "pages_represented",
    ):
        assert key in payload
    assert isinstance(payload["evidence"][0], dict)


def test_bank_never_pads_to_reach_a_quota():
    bank = GroundedEvidenceBank.build(
        question="q", dimensions=["d"], evidence_by_dimension={"d": []}
    )
    assert bank.evidence == ()
    assert bank.coverage["evidence_count"] == 0
