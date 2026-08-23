"""Tests for src/synthesis/fast_v2/dimensions/facets.py.

Uses a generic comparison question shaped like the validated RQ2 (same
grammatical structure: "How do <A> and <B> differ in their <facet-list>?")
but with different entities/topic so these tests do not depend on, or
reproduce, the frozen benchmark question itself.
"""
from __future__ import annotations

import uuid

from src.synthesis.fast_v2.dimensions.facets import (
    FACET_LEXICON,
    FALLBACK_FACETS,
    QuestionFacetDimensionQueryPlanner,
    detect_facets,
    extract_entities,
    extract_topic_phrase,
)

GENERIC_QUESTION = (
    "How do Chen2015 and Park2020 differ in their formulations of the "
    "gradient descent problem, algorithmic strategies, assumptions, and "
    "convergence guarantees?"
)


def test_detects_all_four_facets_in_question_order():
    facets = detect_facets(GENERIC_QUESTION)
    assert facets == ["formulation", "algorithms", "assumptions", "convergence"]


def test_singular_and_plural_aliases_normalize_to_same_facet():
    singular = detect_facets(
        "How does Lee2019 differ from Kim2021 in assumption and convergence?"
    )
    plural = detect_facets(
        "How does Lee2019 differ from Kim2021 in assumptions and convergence guarantees?"
    )
    assert singular == ["assumptions", "convergence"]
    assert plural == ["assumptions", "convergence"]


def test_does_not_use_legacy_evidence_dimension_enum():
    from src.models.synthesis_schemas import EvidenceDimension

    legacy_values = {d.value for d in EvidenceDimension}
    facet_values = set(FACET_LEXICON.keys()) | set(FALLBACK_FACETS)
    assert facet_values.isdisjoint(legacy_values)


def test_single_incidental_match_falls_back_not_legacy_taxonomy():
    """One facet word alone is not enough signal -- must fall back to the
    Fast-v2 fallback tuple, never silently degrade to zero/one facet."""
    facets = detect_facets("What methods does Baseline2020 use?")
    assert facets == list(FALLBACK_FACETS)


def test_no_facets_falls_back_cleanly():
    facets = detect_facets("What is the capital of France?")
    assert facets == list(FALLBACK_FACETS)


def test_extract_entities_generic_pattern_no_hardcoded_paper():
    assert extract_entities(GENERIC_QUESTION) == ["Chen2015", "Park2020"]
    assert extract_entities("no year-bearing entities here") == []


def test_extract_topic_phrase():
    assert extract_topic_phrase(GENERIC_QUESTION) == "gradient descent problem"
    assert extract_topic_phrase("a question with no matching shape") == ""


def test_planner_builds_standalone_queries_not_bare_facet_label():
    planner = QuestionFacetDimensionQueryPlanner()
    queries = planner.plan(
        research_question=GENERIC_QUESTION,
        dimensions=["formulation", "algorithms", "assumptions", "convergence"],
    )
    assert [q.dimension for q in queries] == ["formulation", "algorithms", "assumptions", "convergence"]
    for query in queries:
        assert query.query_text != query.dimension  # not a bare "{dimension}" template
        assert "Chen2015" in query.query_text
        assert "Park2020" in query.query_text
        assert "gradient descent problem" in query.query_text


def test_planner_never_reproduces_v0_full_question_concatenation():
    """v0 failed exactly because it appended the dimension to the full RQ,
    producing >0.98 cosine-similar queries. This planner must never embed the
    full question verbatim, nor the old 'Focus specifically on' phrasing."""
    planner = QuestionFacetDimensionQueryPlanner()
    queries = planner.plan(
        research_question=GENERIC_QUESTION,
        dimensions=["formulation", "algorithms", "assumptions", "convergence"],
    )
    for query in queries:
        assert GENERIC_QUESTION not in query.query_text
        assert "Focus specifically on" not in query.query_text


def test_queries_are_distinct_per_facet():
    """Standalone per-facet queries must differ from each other (this is
    what made v0's queries useless -- >0.98 cosine similarity)."""
    planner = QuestionFacetDimensionQueryPlanner()
    queries = planner.plan(
        research_question=GENERIC_QUESTION,
        dimensions=["formulation", "algorithms", "assumptions", "convergence"],
    )
    texts = [q.query_text for q in queries]
    assert len(set(texts)) == len(texts)


def test_planner_is_deterministic():
    planner = QuestionFacetDimensionQueryPlanner()
    first = planner.plan(research_question=GENERIC_QUESTION, dimensions=["formulation"])
    second = planner.plan(research_question=GENERIC_QUESTION, dimensions=["formulation"])
    assert first == second


def test_planner_falls_back_to_facet_name_when_no_expansion_defined():
    planner = QuestionFacetDimensionQueryPlanner()
    queries = planner.plan(research_question="no entities or topic here", dimensions=["custom_facet"])
    assert queries[0].dimension == "custom_facet"
    assert "custom_facet" in queries[0].query_text


def test_comparative_planner_expands_facets_by_authoritative_paper_id():
    paper_a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    paper_b = uuid.UUID("22222222-2222-2222-2222-222222222222")
    planner = QuestionFacetDimensionQueryPlanner(paper_ids=[paper_a, paper_b])

    queries = planner.plan(
        research_question=(
            "How do the selected papers differ in their formulations of the "
            "gradient descent problem, algorithmic strategies, assumptions, "
            "and convergence guarantees?"
        ),
        dimensions=["formulation", "algorithms", "assumptions", "convergence"],
    )

    assert [(query.dimension, query.paper_id) for query in queries] == [
        ("formulation", paper_a),
        ("formulation", paper_b),
        ("algorithms", paper_a),
        ("algorithms", paper_b),
        ("assumptions", paper_a),
        ("assumptions", paper_b),
        ("convergence", paper_a),
        ("convergence", paper_b),
    ]
    assert [query.query_text for query in queries] == [
        "gradient descent problem formulation mathematical setting definition spaces mappings constraints linear nonlinear",
        "gradient descent problem formulation mathematical setting definition spaces mappings constraints linear nonlinear",
        "gradient descent problem algorithms iterative methods optimization projection fixed point acceleration",
        "gradient descent problem algorithms iterative methods optimization projection fixed point acceleration",
        "gradient descent problem assumptions conditions convexity smoothness linearity mappings operators",
        "gradient descent problem assumptions conditions convexity smoothness linearity mappings operators",
        "gradient descent problem convergence guarantees theorem weak strong stationary global minimizer",
        "gradient descent problem convergence guarantees theorem weak strong stationary global minimizer",
    ]


def test_multiple_selected_papers_do_not_change_non_comparative_queries():
    paper_a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    paper_b = uuid.UUID("22222222-2222-2222-2222-222222222222")
    question = "What formulation and convergence are reported for Chen2015?"

    baseline = QuestionFacetDimensionQueryPlanner().plan(
        research_question=question,
        dimensions=["formulation", "convergence"],
    )
    with_selected_papers = QuestionFacetDimensionQueryPlanner(
        paper_ids=[paper_a, paper_b]
    ).plan(
        research_question=question,
        dimensions=["formulation", "convergence"],
    )

    assert with_selected_papers == baseline
    assert all(query.paper_id is None for query in with_selected_papers)
