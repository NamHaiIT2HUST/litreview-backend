from __future__ import annotations

from src.agents.slr_swarm.grounding import locate_claim, tokenize, verify_claims
from src.agents.slr_swarm.ports import PageText

PAGES = [
    PageText(
        page=1,
        lines=[
            "Introduction to the study design",
            "In this retrospective cohort study we evaluated 500 patients with ECG recordings.",
            "The convolutional neural network reached an accuracy of 0.94 on the test set.",
        ],
    ),
    PageText(page=2, lines=["A limitation is that this is single center data."]),
]


def test_tokenize_drops_stopwords():
    assert "the" not in tokenize("The study of the patients")
    assert "patients" in tokenize("The study of the patients")


def test_locate_claim_returns_exact_page_and_lines():
    span = locate_claim("we evaluated 500 patients with ECG recordings", "P1", PAGES)

    assert span is not None
    assert span.page == 1
    assert span.line_start == 2 and span.line_end == 2
    assert "500 patients" in span.quote
    assert span.score >= 0.9


def test_locate_claim_finds_evidence_on_later_pages():
    span = locate_claim("single center data limitation", "P1", PAGES)

    assert span is not None
    assert span.page == 2


def test_locate_claim_rejects_fabricated_claim():
    """Claim bịa hoàn toàn phải trả None — đây là lõi chống bịa nguồn."""
    span = locate_claim("the trial enrolled 12000 diabetic children in Brazil", "P1", PAGES)

    assert span is None


def test_locate_claim_rejects_scattered_word_matches():
    """Trúng vài từ rời rạc nhưng sai ngữ cảnh thì không được tính là grounded."""
    span = locate_claim("patients recordings accuracy limitation network study", "P1", PAGES)

    assert span is None or span.score < 0.9


def test_verify_claims_scores_by_ratio_not_average():
    claims = [
        "we evaluated 500 patients with ECG recordings",  # có thật
        "the model was trained on 9 million cats",        # bịa
    ]
    spans, score = verify_claims(claims, "P1", PAGES)

    assert len(spans) == 1
    assert score == 0.5


def test_verify_claims_with_no_fulltext_scores_zero():
    spans, score = verify_claims(["we evaluated 500 patients"], "P1", [])

    assert spans == []
    assert score == 0.0
