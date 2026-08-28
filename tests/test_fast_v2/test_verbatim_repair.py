"""Targeted verbatim repair: structural guards, not model trust. All LLM
calls mocked. Covers acceptance, and every rejection path (numeric changed,
still verbatim after rewrite, span-count mismatch, no response, transport
failure) -- each must leave the ORIGINAL text untouched and be reported,
never silently applied or silently dropped.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from src.synthesis.fast_v2.citations.verbatim_gate import VerbatimGateRecord, VERBATIM_RISK
from src.synthesis.fast_v2.citations.verbatim_repair import repair_verbatim_claims


def _resp(repairs: dict):
    r = MagicMock()
    r.content = json.dumps({"repairs": repairs})
    return r


def _make_record(claim_id, paragraph_id, text, handle="E001"):
    return VerbatimGateRecord(
        claim_id=claim_id, section_id="sec_1", paragraph_id=paragraph_id, text=text,
        handle=handle, run_words=13, overlap_ratio=0.6, matched_phrase="some copied phrase here now",
        status=VERBATIM_RISK,
    )


def test_accepted_repair_replaces_only_the_flagged_span():
    pre = "Fact A stays the same. Control days represent the counterfactual exposure of each case."
    post = pre + " [E001]"  # citation lands after the whole paragraph's last span in this simple case
    # Two spans: "Fact A stays the same." (s0) and "Control days ... case." (s1, flagged)
    record = _make_record("p0_s1", 0, "Control days represent the counterfactual exposure of each case.")

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s1": "Referent days capture the counterfactual exposure profile of each subject."
    }))

    result = asyncio.run(repair_verbatim_claims(
        fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "unrelated evidence text with no overlap at all"}
    ))

    assert result.repaired_count == 1
    assert "Fact A stays the same." in result.repaired_markdown  # untouched span preserved verbatim
    assert "Referent days capture the counterfactual exposure profile of each subject." in result.repaired_markdown
    assert "Control days represent the counterfactual exposure of each case." not in result.repaired_markdown


def test_rejected_when_numeric_content_changed():
    pre = "The relative risk was 1.05 with a 95% CI reported across the full cohort in this analysis."
    post = pre + " [E001]"
    record = _make_record("p0_s0", 0, pre)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s0": "The relative risk was 2.71 with a 90% CI reported across the full cohort in this analysis."
    }))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "x"}))

    assert result.repaired_count == 0
    assert result.outcomes[0].status == "UNSAFE_NUMERIC_CHANGED"
    assert result.repaired_markdown == post  # original preserved exactly


def test_rejected_when_replacement_still_near_verbatim_to_source():
    pre = "Control days represent the counterfactual exposure experience of each case in this design."
    post = pre + " [E001]"
    record = _make_record("p0_s0", 0, pre)
    source = "Control days represent the counterfactual exposure experience of each case independently."

    fake_llm = MagicMock()
    # The model's "rewrite" is itself still near-verbatim to the source -- must be rejected.
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s0": "Control days represent the counterfactual exposure experience of each case here."
    }))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": source}))

    assert result.repaired_count == 0
    assert result.outcomes[0].status == "UNSAFE_STILL_VERBATIM"
    assert result.repaired_markdown == post


def test_rejected_when_span_count_changes():
    pre = "Control days represent the counterfactual exposure experience of each case in this design."
    post = pre + " [E001]"
    record = _make_record("p0_s0", 0, pre)

    fake_llm = MagicMock()
    # Replacement introduces a sentence boundary -> span count would change from 1 to 2.
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s0": "Referent days serve as the counterfactual. They represent unexposed comparison periods."
    }))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "no overlap text"}))

    assert result.repaired_count == 0
    assert result.outcomes[0].status == "UNSAFE_SPAN_COUNT_MISMATCH"
    assert result.repaired_markdown == post


def test_rejected_when_llm_returns_no_usable_response():
    pre = "Control days represent the counterfactual exposure experience of each case in this design."
    post = pre + " [E001]"
    record = _make_record("p0_s0", 0, pre)

    fake_llm = MagicMock()
    bad_resp = MagicMock()
    bad_resp.content = "not json at all"
    fake_llm.ainvoke = AsyncMock(return_value=bad_resp)

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "x"}))

    assert result.repaired_count == 0
    assert result.outcomes[0].status == "TRANSPORT_FAILED"
    assert result.repaired_markdown == post


def test_transport_exception_reported_not_raised():
    pre = "Control days represent the counterfactual exposure experience of each case in this design."
    post = pre + " [E001]"
    record = _make_record("p0_s0", 0, pre)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=RuntimeError("connection reset"))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "x"}))

    assert result.outcomes[0].status == "TRANSPORT_FAILED"
    assert result.repaired_markdown == post


def test_untouched_paragraphs_pass_through_byte_identical():
    pre = "Paragraph zero untouched.\n\nControl days represent the counterfactual exposure experience of each case."
    post = "Paragraph zero untouched.\n\nControl days represent the counterfactual exposure experience of each case. [E001]"
    record = _make_record("p1_s0", 1, "Control days represent the counterfactual exposure experience of each case.")

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=_resp({"p1_s0": "Referent days capture the counterfactual exposure profile per case in this design."}))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [record], handle_to_evidence_text={"E001": "no overlap"}))

    assert result.repaired_markdown.split("\n\n")[0] == "Paragraph zero untouched."


def test_rejected_when_replacement_still_verbatim_against_a_DIFFERENT_cited_handle():
    """Regression for a real case found running repair on the frozen
    artifact: a span cites TWO handles; the repair's own safety check must
    not only re-check against the single worst-offender handle
    verbatim_gate originally reported -- it must check the rewrite against
    every handle actually cited on that span."""
    pre = "Wang et al. (2019) adopt the calendar month as the time stratum in their design for this study."
    post = pre + " [E007, E008]"
    record = _make_record("p0_s0", 0, pre, handle="E008")  # verbatim_gate's reported worst offender is E008

    fake_llm = MagicMock()
    # Rewrite is clean against E008 (Chu's paper) but still near-verbatim against E007 (Wang's paper).
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s0": "Wang et al. (2019) employ the calendar month as the time stratum to structure their analysis."
    }))

    result = asyncio.run(repair_verbatim_claims(
        fake_llm, pre, post, [record],
        handle_to_evidence_text={
            "E007": "adopt the calendar month as the time stratum to control long-term trend",
            "E008": "completely unrelated Chu paper text with zero shared wording whatsoever here",
        },
    ))

    assert result.repaired_count == 0
    assert result.outcomes[0].status == "UNSAFE_STILL_VERBATIM"
    assert result.repaired_markdown == post


def test_one_llm_call_per_paragraph_not_per_span():
    pre = "First flagged sentence goes here for testing purposes today. Second flagged sentence goes here for testing too."
    post = pre + " [E001, E002]"
    r1 = _make_record("p0_s0", 0, "First flagged sentence goes here for testing purposes today.")
    r2 = _make_record("p0_s1", 0, "Second flagged sentence goes here for testing too.", handle="E002")

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=_resp({
        "p0_s0": "An initial rewritten clause appears at this position for evaluation purposes now.",
        "p0_s1": "A subsequent rewritten clause appears at this position for evaluation purposes.",
    }))

    result = asyncio.run(repair_verbatim_claims(fake_llm, pre, post, [r1, r2], handle_to_evidence_text={"E001": "x", "E002": "y"}))

    assert fake_llm.ainvoke.await_count == 1
    assert result.repaired_count == 2
