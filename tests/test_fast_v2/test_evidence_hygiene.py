"""Tests 3/4/5: Evidence Hygiene classifier.

Regression fixtures in ``fixtures/hygiene_spike_fixtures.json`` are the real
recorded outputs of the validated hygiene spike (rq1/rq2_before_after.json).
The scoring function must reproduce the recorded ``hygiene_score`` exactly for
every recorded signal vector.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.synthesis.fast_v2.hygiene.classifier import (
    HYGIENE_REFERENCE_THRESHOLD,
    HygieneClass,
    classify_text,
    filter_evidence_units,
    score_from_signals,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "hygiene_spike_fixtures.json").read_text(
        encoding="utf-8"
    )
)


# --------------------------------------------------------------------------
# Numeric regression against the validated spike
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case",
    [c for c in FIXTURES["scored_signals"] if c["expected_class"] == "reference_like"],
    ids=lambda c: str(c["expected_score"]),
)
def test_score_reproduces_validated_spike_scores(case):
    """The frozen weighting must match the spike's recorded hygiene_score.

    Covers every distinct reference_like signal vector recorded by the spike.
    """
    assert score_from_signals(case["signals"]) == pytest.approx(case["expected_score"])


@pytest.mark.parametrize(
    "case",
    [c for c in FIXTURES["scored_signals"] if c["expected_class"] == "boilerplate"],
    ids=lambda c: str(c["expected_score"]),
)
def test_boilerplate_signal_vectors_score_as_hit_count(case):
    """For boilerplate the spike recorded hygiene_score == boilerplate_hits.

    The reference score for these vectors is separately gated to ~0 because
    they carry no reference entry lines.
    """
    assert case["expected_score"] == pytest.approx(case["signals"]["boilerplate_hits"])
    assert score_from_signals(case["signals"]) < HYGIENE_REFERENCE_THRESHOLD


# --------------------------------------------------------------------------
# Test 3 -- bibliography removed
# --------------------------------------------------------------------------

BIBLIOGRAPHY = """References
[18] Qu B and Xiu N 2005 A note on the CQ algorithm for the split feasibility problem Inverse Problems 21 1655
[19] Rockafellar R T 1970 Convex Analysis (Princeton, NJ: Princeton University Press)
[20] Schopfer F, Schuster T and Louis A K 2008 An iterative regularization method for the solution of the split
feasibility problem in Banach spaces Inverse Problems 24 055008
[21] Sezan M I and Stark H 1987 Applications of convex projection theory to image recovery IEEE Trans. 6 91
"""

SPRINGER_BIBLIOGRAPHY = """29. Davenport, M.A., Duarte, M.F., Eldar, Y.C., Kutyniok, G.: Introduction to compressed sensing. Cambridge University Press (2012)
30. Byrne, C.: Iterative oblique projection onto convex sets. Inverse Probl. 18, 441 (2002)
31. Censor, Y., Elfving, T.: A multiprojection algorithm using Bregman projections. Numer. Algorithms 8, 221 (1994)
"""

MULTI_AUTHOR_COMMA_BIBLIOGRAPHY = """[4] Censor Y, Bortfeld T, Martin B and Trofimov A 2006 A unified approach for inversion problems in
intensity-modulated radiation therapy Phys. Med. Biol. 51 2353
[5] Censor Y, Elfving T, Kopf N and Bortfeld T 2005 The multiple-sets split feasibility problem and its
applications Inverse Problems 21 2071
[6] Censor Y and Segal A 2008 Iterative projection methods Inverse Problems 24 1
"""


def test_bibliography_is_classified_reference_like():
    """Test 3: reference-list chunks are removed from evidence selection."""
    result = classify_text(BIBLIOGRAPHY)
    assert result.hygiene_class is HygieneClass.reference_like
    assert result.hygiene_score >= HYGIENE_REFERENCE_THRESHOLD


def test_springer_style_bibliography_is_classified_reference_like():
    assert classify_text(SPRINGER_BIBLIOGRAPHY).hygiene_class is HygieneClass.reference_like


def test_comma_joined_multi_author_entries_are_detected():
    """Regression from the spike: the first entry regex only matched 2-author
    'Surname I and Surname I' entries, so real 3+ comma-joined entries scored
    zero matched entry lines and a bibliography fragment leaked through."""
    result = classify_text(MULTI_AUTHOR_COMMA_BIBLIOGRAPHY)
    assert result.hygiene_signals["reference_entry_lines"] >= 3
    assert result.hygiene_class is HygieneClass.reference_like


def _reference_previews():
    """Real excluded-chunk previews from the spike.

    NOTE: the spike's report stores 300-char *previews*, not whole chunks. A
    preview that happens to be cut after a single entry line no longer carries
    the structural signal, and the classifier is designed to KEEP in that case.
    Those fragments are asserted separately below; the exact scores of the
    corresponding full chunks are covered by the signal-vector regression.
    """
    from src.synthesis.fast_v2.hygiene.classifier import extract_signals

    full, fragment = [], []
    for case in FIXTURES["excluded_texts"]:
        if case["expected_class"] != "reference_like":
            continue
        signals = extract_signals(case["text"])
        target = full if signals["reference_entry_lines"] >= 2 else fragment
        target.append(case)
    return full, fragment


_FULL_REFERENCE_PREVIEWS, _FRAGMENT_REFERENCE_PREVIEWS = _reference_previews()


@pytest.mark.parametrize(
    "case", _FULL_REFERENCE_PREVIEWS, ids=lambda c: f"{c['paper']}-p{c['page']}"
)
def test_real_excluded_reference_chunks_stay_excluded(case):
    """Every real bibliography preview that retains the structural signal is flagged."""
    assert classify_text(case["text"]).hygiene_class is HygieneClass.reference_like


def test_the_spike_reference_previews_are_mostly_still_detected():
    """Guard against a silent regression that stops detecting bibliographies."""
    assert len(_FULL_REFERENCE_PREVIEWS) >= 7


@pytest.mark.parametrize(
    "case", _FRAGMENT_REFERENCE_PREVIEWS, ids=lambda c: f"{c['paper']}-p{c['page']}"
)
def test_single_entry_fragments_are_kept_by_design(case):
    """Bias to KEEP: one entry line is not enough structural evidence.

    This is the documented trade-off, not a defect -- the full chunks these
    fragments came from score 87.0 and are correctly excluded.
    """
    assert classify_text(case["text"]).hygiene_class is HygieneClass.scientific_content


# --------------------------------------------------------------------------
# Test 4 -- inline citations in scientific prose are retained
# --------------------------------------------------------------------------

PROSE_WITH_INLINE_CITATIONS = """In the split feasibility problem, one is given a smooth function h(x) and two
closed convex sets C and Q [17]. One then seeks a point x simultaneously
satisfying the constraints. Instances of this problem abound in intensity
modulated radiation therapy (IMRT) [9,16,18,20,67], and the classical linear
formulation was studied extensively in 2005 by several authors.
"""


def test_inline_citations_in_prose_are_retained():
    """Test 4: mid-line bracket citations must never trigger reference_like."""
    result = classify_text(PROSE_WITH_INLINE_CITATIONS)
    assert result.hygiene_class is HygieneClass.scientific_content


def test_prose_naming_a_journal_and_a_year_is_not_flagged():
    """Structural gate: vocabulary alone cannot flag prose."""
    text = (
        "This result was first reported in Inverse Problems in 2008, and a related "
        "analysis appeared in IEEE Trans. Signal Process. shortly afterwards. The "
        "authors show that the algorithm converges to a stationary point."
    )
    assert classify_text(text).hygiene_class is HygieneClass.scientific_content


@pytest.mark.parametrize(
    "case",
    FIXTURES["kept_texts"],
    ids=lambda c: f"{c['paper']}-p{c['page']}",
)
def test_real_promoted_chunks_are_kept(case):
    """No false positives: every chunk the spike kept must still be kept."""
    assert classify_text(case["text"]).hygiene_class is HygieneClass.scientific_content


def test_a_standalone_references_heading_alone_does_not_reach_threshold():
    """Ambiguity biases to KEEP; a bare heading scores 5.0, under threshold."""
    result = classify_text("References\n\nWe now summarise the argument above.")
    assert result.hygiene_class is HygieneClass.scientific_content


# --------------------------------------------------------------------------
# Test 5 -- boilerplate removed
# --------------------------------------------------------------------------

BOILERPLATE = """This content was downloaded from IP Address 10.0.0.1 on 12/03/2024 at 09:15.
Please note that terms and conditions apply.
View the table of contents for this issue, or go to the journal homepage for more.
"""


def test_boilerplate_is_classified_boilerplate():
    """Test 5: download/copyright notices are removed."""
    result = classify_text(BOILERPLATE)
    assert result.hygiene_class is HygieneClass.boilerplate


@pytest.mark.parametrize(
    "case",
    [c for c in FIXTURES["excluded_texts"] if c["expected_class"] == "boilerplate"],
    ids=lambda c: f"{c['paper']}-p{c['page']}",
)
def test_real_excluded_boilerplate_chunks_stay_excluded(case):
    assert classify_text(case["text"]).hygiene_class is HygieneClass.boilerplate


def test_boilerplate_score_is_the_hit_count():
    """The spike recorded hygiene_score == boilerplate_hits for boilerplate."""
    result = classify_text(BOILERPLATE)
    assert result.hygiene_score == pytest.approx(result.hygiene_signals["boilerplate_hits"])


# --------------------------------------------------------------------------
# Filtering behaviour
# --------------------------------------------------------------------------

def _unit(text):
    import uuid

    from src.synthesis.fast_v2.evidence.models import EvidenceUnit

    return EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="t",
        page=1,
        text=text,
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
    )


def test_filter_keeps_scientific_content_and_drops_the_rest():
    kept, dropped = filter_evidence_units(
        [_unit(PROSE_WITH_INLINE_CITATIONS), _unit(BIBLIOGRAPHY), _unit(BOILERPLATE)]
    )
    assert len(kept) == 1
    assert len(dropped) == 2


def test_filter_attaches_diagnostics_to_kept_units():
    kept, _ = filter_evidence_units([_unit(PROSE_WITH_INLINE_CITATIONS)])
    unit = kept[0]
    assert unit.hygiene_class == "scientific_content"
    assert unit.hygiene_score is not None
    assert "reference_entry_lines" in unit.hygiene_signals


def test_filter_does_not_mutate_the_input_units():
    """Hygiene is runtime evidence selection -- it never mutates canonical data."""
    original = _unit(BIBLIOGRAPHY)
    filter_evidence_units([original])
    assert original.hygiene_class is None
    assert original.hygiene_signals == {}


def test_empty_input_is_safe():
    assert filter_evidence_units([]) == ([], [])
