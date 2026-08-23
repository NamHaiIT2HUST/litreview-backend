"""Tests 6, 9, 10, 11: dimension queries and the evidence selection policy."""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.dimensions.planner import (
    DeterministicDimensionQueryPlanner,
    DimensionQuery,
    DimensionQueryPlanner,
)
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy

QUESTION = (
    "How do Xu2010 and Xu2018 differ in their formulations of the split "
    "feasibility problem, algorithmic strategies, assumptions, and convergence "
    "guarantees?"
)
DIMENSIONS = [
    "problem formulation",
    "algorithmic strategy",
    "assumptions",
    "convergence guarantees",
]


# --------------------------------------------------------------------------
# Test 6 -- distinct supplied dimensions create distinct queries
# --------------------------------------------------------------------------

def test_distinct_dimensions_produce_distinct_queries():
    """Test 6."""
    planner = DeterministicDimensionQueryPlanner()
    queries = planner.plan(research_question=QUESTION, dimensions=DIMENSIONS)

    assert len(queries) == len(DIMENSIONS)
    texts = [q.query_text for q in queries]
    assert len(set(texts)) == len(texts)


def test_query_text_does_not_embed_the_full_research_question():
    """v0 failed exactly because it appended the dimension to the full RQ.

    That made every dimension query >0.98 cosine-similar (RQ1 mean 0.987) and
    produced an 80% duplicate selection rate. v1 builds standalone queries.
    """
    planner = DeterministicDimensionQueryPlanner()
    for query in planner.plan(research_question=QUESTION, dimensions=DIMENSIONS):
        assert QUESTION not in query.query_text
        assert "Focus specifically on" not in query.query_text


def test_query_text_is_derived_from_the_dimension():
    planner = DeterministicDimensionQueryPlanner()
    queries = planner.plan(research_question=QUESTION, dimensions=DIMENSIONS)
    for dimension, query in zip(DIMENSIONS, queries):
        assert query.dimension == dimension
        assert dimension.lower() in query.query_text.lower()


def test_planner_is_deterministic():
    planner = DeterministicDimensionQueryPlanner()
    first = planner.plan(research_question=QUESTION, dimensions=DIMENSIONS)
    second = planner.plan(research_question=QUESTION, dimensions=DIMENSIONS)
    assert [q.query_text for q in first] == [q.query_text for q in second]


def test_planner_requires_explicit_dimensions():
    """General question decomposition is explicitly NOT solved.

    The planner must refuse to invent dimensions rather than fall back to a
    weak production heuristic.
    """
    planner = DeterministicDimensionQueryPlanner()
    with pytest.raises(ValueError):
        planner.plan(research_question=QUESTION, dimensions=[])


def test_planner_deduplicates_repeated_dimensions():
    planner = DeterministicDimensionQueryPlanner()
    queries = planner.plan(
        research_question=QUESTION, dimensions=["assumptions", "assumptions "]
    )
    assert len(queries) == 1


def test_deterministic_planner_satisfies_the_interface():
    assert isinstance(DeterministicDimensionQueryPlanner(), DimensionQueryPlanner)


def _executable_source(path):
    """Return the file's code with comments and string literals removed.

    Benchmark identifiers are legitimate in prose (documenting which corpus a
    threshold was calibrated against). They are NOT legitimate in executable
    logic. This strips tokens that cannot influence behaviour.
    """
    import io
    import tokenize

    kept = []
    with open(path, "rb") as handle:
        for token in tokenize.tokenize(io.BytesIO(handle.read()).readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            kept.append(token.string)
    return " ".join(kept)


def test_no_benchmark_identifiers_are_hardcoded():
    """RQ1/RQ2/Xu2010/Xu2018 were benchmark labels, never production logic."""
    from pathlib import Path

    import src.synthesis.fast_v2 as pkg

    checked = 0
    for path in Path(pkg.__file__).parent.rglob("*.py"):
        source = _executable_source(path)
        checked += 1
        for banned in ("Xu2010", "Xu2018", "RQ1", "RQ2"):
            assert banned not in source, f"{banned} leaked into executable code in {path.name}"
    assert checked > 0


# --------------------------------------------------------------------------
# Selection policy -- tests 9, 10, 11
# --------------------------------------------------------------------------

def _unit(score: float, *, title: str = "Paper A", paper_id=None) -> EvidenceUnit:
    return EvidenceUnit.from_chunk(
        paper_id=paper_id or uuid.uuid4(),
        title=title,
        page=1,
        text=f"evidence text with score {score}",
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
    ).with_scores(rerank_score=score)


def test_negative_and_zero_scores_are_rejected():
    """Test 9: score <= threshold is rejected."""
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    selected = policy.select(
        [_unit(1.5), _unit(0.0), _unit(-0.49)], dimension="assumptions"
    )
    assert len(selected) == 1
    assert selected[0].rerank_score == pytest.approx(1.5)


def test_no_padding_up_to_max_per_dimension():
    """Test 10: a quota is a ceiling, never a target."""
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    selected = policy.select([_unit(0.8), _unit(-1.47), _unit(-0.04)], dimension="d")
    assert len(selected) == 1, "weak/negative evidence must never pad to the quota"


def test_selection_is_capped_at_max_per_dimension():
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    selected = policy.select([_unit(s) for s in (5.0, 4.0, 3.0, 2.0, 1.0)], dimension="d")
    assert len(selected) == 3
    assert [u.rerank_score for u in selected] == [5.0, 4.0, 3.0]


def test_no_forced_paper_balance():
    """Test 11: the strongest evidence wins even if it is all one paper."""
    paper_a, paper_b = uuid.uuid4(), uuid.uuid4()
    units = [
        _unit(5.0, title="A", paper_id=paper_a),
        _unit(4.0, title="A", paper_id=paper_a),
        _unit(3.0, title="A", paper_id=paper_a),
        _unit(0.5, title="B", paper_id=paper_b),
    ]
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    selected = policy.select(units, dimension="d")
    assert {u.paper_id for u in selected} == {paper_a}


def test_all_below_threshold_yields_nothing():
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    assert policy.select([_unit(-1.0), _unit(-2.0)], dimension="d") == []


def test_threshold_is_configurable_without_touching_retrieval():
    strict = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=2.0)
    assert len(strict.select([_unit(5.0), _unit(1.0)], dimension="d")) == 1


def test_selected_units_carry_dimension_metadata():
    policy = EvidenceSelectionPolicy(max_per_dimension=3, relevance_threshold=0.0)
    selected = policy.select([_unit(1.25)], dimension="convergence guarantees")
    assert selected[0].selected_for_dimensions == ("convergence guarantees",)
    assert selected[0].dimension_scores["convergence guarantees"] == pytest.approx(1.25)


def test_policy_defaults_are_the_frozen_experimental_values():
    policy = EvidenceSelectionPolicy()
    assert policy.max_per_dimension == 3
    assert policy.relevance_threshold == 0.0


def test_units_without_a_rerank_score_fall_back_to_retrieval_score():
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="t",
        page=1,
        text="body",
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
    ).with_scores(retrieval_score=0.9)
    policy = EvidenceSelectionPolicy()
    assert len(policy.select([unit], dimension="d")) == 1
