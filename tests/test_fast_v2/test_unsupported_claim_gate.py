"""Deterministic unsupported-claim gate: no LLM, no prose edits, only
classification. Regression-covers the exact Chu/Wang paragraph pattern from
the claim_034 retrieval audit -- one factual span cited, one not, in the
SAME paragraph -- to prove the gate reports per-claim status, not
per-paragraph "has some citation somewhere" status.
"""
from src.synthesis.fast_v2.citations.unsupported_gate import (
    CLEAN,
    DISCOURSE_TRANSITION,
    FACTUAL_TECHNICAL,
    GROUNDED,
    NON_FACTUAL_UNCITED_OK,
    PASS_WITH_ISSUES,
    UNSUPPORTED,
    ProseInvariantViolation,
    classify_span_type,
    evaluate_unsupported_claims,
    extract_span_citations,
)


def test_classify_span_type_discourse_opener():
    assert classify_span_type("In summary, the corpus is unified by a shared design.") == DISCOURSE_TRANSITION


def test_classify_span_type_short_fragment_is_discourse():
    assert classify_span_type("This matters too.") == DISCOURSE_TRANSITION


def test_classify_span_type_factual():
    assert classify_span_type(
        "Chu et al. (2025) found that PM2.5 was significantly associated with daily DED cases."
    ) == FACTUAL_TECHNICAL


def test_extract_span_citations_recovers_exact_handles():
    pre = "Fact A happened. Fact B happened too."
    post = "Fact A happened. [E001] Fact B happened too. [E002, E003]"
    result = extract_span_citations(pre, post)
    assert result == [["E001"], ["E002", "E003"]]


def test_extract_span_citations_no_citations_returns_empty_lists():
    pre = "Fact A happened. Fact B happened too."
    post = pre
    result = extract_span_citations(pre, post)
    assert result == [[], []]


def test_extract_span_citations_raises_on_prose_mismatch():
    pre = "Fact A happened. Fact B happened too."
    post = "Fact A occurred. Fact B happened too."  # mutated prose, not just a tag insert
    try:
        extract_span_citations(pre, post)
        assert False, "expected ProseInvariantViolation"
    except ProseInvariantViolation:
        pass


# --- The exact Chu/Wang regression case from the claim_034 retrieval audit ---
def test_chu_wang_paragraph_flags_chu_unsupported_wang_grounded():
    pre = (
        "Wang et al. (2019) explicitly motivate their Shenzhen study by observing that heterogeneity "
        "in prior results may be partially explained by differences across studies in regions and "
        "populations studied, in pollution levels and constituents, and in sample size. "
        "Chu et al. (2025) reinforce this concern from the opposite direction, identifying their "
        "single-location design as a limitation that restricts generalizability and calling for future "
        "multicenter studies encompassing cities and regions with varying pollution levels, climatic "
        "characteristics, and developmental stages."
    )
    post = (
        "Wang et al. (2019) explicitly motivate their Shenzhen study by observing that heterogeneity "
        "in prior results may be partially explained by differences across studies in regions and "
        "populations studied, in pollution levels and constituents, and in sample size. [E031] "
        "Chu et al. (2025) reinforce this concern from the opposite direction, identifying their "
        "single-location design as a limitation that restricts generalizability and calling for future "
        "multicenter studies encompassing cities and regions with varying pollution levels, climatic "
        "characteristics, and developmental stages."
    )

    result = evaluate_unsupported_claims(pre, post)

    assert len(result.records) == 2
    wang_claim, chu_claim = result.records

    assert wang_claim.type == FACTUAL_TECHNICAL
    assert wang_claim.status == GROUNDED
    assert wang_claim.evidence == ["E031"]

    assert chu_claim.type == FACTUAL_TECHNICAL
    assert chu_claim.status == UNSUPPORTED
    assert chu_claim.evidence == []

    # The paragraph MUST NOT be counted as fully grounded merely because
    # [E031] exists somewhere in it -- claim-level, not paragraph-level.
    assert result.unsupported_factual_claims == 1
    assert result.grounded_factual_claims == 1
    assert result.quality_status == PASS_WITH_ISSUES
    assert "p0_s1" in result.unsupported_claim_ids
    assert "p0_s0" not in result.unsupported_claim_ids


def test_all_grounded_and_discourse_yields_clean_status():
    pre = "In summary, the corpus converges. Chu et al. (2025) found a significant association with PM2.5."
    post = "In summary, the corpus converges. Chu et al. (2025) found a significant association with PM2.5. [E001]"

    result = evaluate_unsupported_claims(pre, post)
    types = [r.type for r in result.records]
    assert DISCOURSE_TRANSITION in types
    assert FACTUAL_TECHNICAL in types
    assert result.unsupported_factual_claims == 0
    assert result.quality_status == CLEAN
    discourse_record = next(r for r in result.records if r.type == DISCOURSE_TRANSITION)
    assert discourse_record.status == NON_FACTUAL_UNCITED_OK


def test_non_substantive_blocks_are_skipped():
    pre = "## Section 6: Title\n\nChu et al. (2025) found a significant association with PM2.5."
    post = "## Section 6: Title\n\nChu et al. (2025) found a significant association with PM2.5. [E001]"

    result = evaluate_unsupported_claims(pre, post)
    assert result.total_claim_spans == 1  # heading block skipped, not counted


def test_section_ids_are_attached_per_paragraph():
    pre = "Para zero.\n\nChu et al. (2025) found a significant association with PM2.5."
    post = "Para zero.\n\nChu et al. (2025) found a significant association with PM2.5. [E001]"

    result = evaluate_unsupported_claims(pre, post, paragraph_section_ids={0: None, 1: "sec_6"})
    assert result.records[0].section_id == "sec_6"


def test_gate_makes_no_prose_changes():
    """The gate is read-only: it must not be capable of altering the input
    text at all -- it has no return path that includes modified prose."""
    import inspect

    from src.synthesis.fast_v2.citations import unsupported_gate
    source = inspect.getsource(unsupported_gate)
    assert "ainvoke" not in source
    assert "ChatOpenAI" not in source
    assert ".delete(" not in source
