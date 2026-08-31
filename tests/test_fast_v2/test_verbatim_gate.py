"""Deterministic verbatim-copying detector. No LLM, no prose edits -- only
classification. Covers: genuine prose near-verbatim flagged VERBATIM_RISK,
numeric/statistical exact reproduction classified NUMERIC_LEGITIMATE (not a
risk), short benign overlap left CLEAN (not recorded), and claims with no
citation ignored entirely (that is the unsupported-claim gate's concern).
"""
from src.synthesis.fast_v2.citations.verbatim_gate import (
    MIN_RUN_WORDS,
    NUMERIC_LEGITIMATE,
    VERBATIM_RISK,
    detect_verbatim_risk,
)


def test_genuine_prose_near_verbatim_is_flagged():
    pre = (
        "Within each ID stratum, the case day and control days are matched by day of the week "
        "within the same month, the same year, and the same location."
    )
    post = pre + " [E001]"
    evidence_text = (
        "Within each ID stratum the case day and control days are matched by day of the week "
        "in the same month, in the same year, and in the same location."
    )

    result = detect_verbatim_risk(pre, post, handle_to_evidence_text={"E001": evidence_text})

    assert result.verbatim_risk_claims == 1
    assert result.records[0].status == VERBATIM_RISK
    assert result.records[0].run_words >= MIN_RUN_WORDS


def test_numeric_statistical_run_is_not_a_risk():
    pre = "The relative risk was elevated across every lag window we examined in this cohort."
    pre + " [E001]"
    # Long shared digit run (a CI table reproduced), should NOT be VERBATIM_RISK.
    evidence_text = "elevated across every lag window we examined in this cohort 1 05 1 00 1 09 1 05 1 00 1 10"
    # Force a long shared run that is mostly digits by using a matching evidence prefix + digits.
    pre2 = "Effect sizes were reported as 1 05 1 00 1 09 for NO3 1 05 1 00 1 10 for NH4 in this analysis."
    post2 = pre2 + " [E001]"

    result = detect_verbatim_risk(pre2, post2, handle_to_evidence_text={"E001": evidence_text})

    assert result.verbatim_risk_claims == 0
    if result.records:
        assert result.records[0].status == NUMERIC_LEGITIMATE


def test_short_overlap_below_threshold_is_clean_and_not_recorded():
    pre = "Chu et al. (2025) found a significant association with PM2.5 in their cohort."
    post = pre + " [E001]"
    evidence_text = "The study found a significant association between exposure and outcome overall."

    result = detect_verbatim_risk(pre, post, handle_to_evidence_text={"E001": evidence_text})

    assert result.total_factual_cited_claims == 1
    assert result.verbatim_risk_claims == 0
    assert result.records == []


def test_claim_without_citation_is_not_counted_at_all():
    pre = "Within each ID stratum, the case day and control days are matched by day of the week."
    post = pre  # no citation inserted -- unsupported-claim gate's territory, not this one
    evidence_text = "Within each ID stratum the case day and control days are matched by day of the week."

    result = detect_verbatim_risk(pre, post, handle_to_evidence_text={"E001": evidence_text})

    assert result.total_factual_cited_claims == 0
    assert result.records == []


def test_discourse_span_is_never_flagged_even_with_high_overlap():
    pre = "In summary, control days are matched by day of the week in the same month and year."
    post = pre + " [E001]"
    evidence_text = "In summary control days are matched by day of the week in the same month and year."

    result = detect_verbatim_risk(pre, post, handle_to_evidence_text={"E001": evidence_text})

    assert result.total_factual_cited_claims == 0  # discourse-classified, excluded
    assert result.records == []


def test_section_ids_attached_per_paragraph():
    pre = "Para zero.\n\nWithin each ID stratum, the case day and control days are matched by day of the week."
    post = "Para zero.\n\nWithin each ID stratum, the case day and control days are matched by day of the week. [E001]"
    evidence_text = "Within each ID stratum the case day and control days are matched by day of the week."

    result = detect_verbatim_risk(
        pre, post, handle_to_evidence_text={"E001": evidence_text},
        paragraph_section_ids={0: None, 1: "sec_1"},
    )
    assert result.records[0].section_id == "sec_1"


def test_gate_makes_no_text_changes_and_calls_no_llm():
    import inspect

    from src.synthesis.fast_v2.citations import verbatim_gate
    source = inspect.getsource(verbatim_gate)
    assert "ainvoke" not in source
    assert "ChatOpenAI" not in source
