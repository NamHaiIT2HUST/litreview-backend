"""Test 1 + pipeline wiring + observability (Task 7 / Task 10).

The headline assertion is :func:`test_fast_v2_makes_zero_extraction_llm_calls`.
"""
from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
from src.synthesis.fast_v2.observability import PHASES
from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline, FastSynthesisV2Result

PAPER_A = uuid.uuid4()
PAPER_B = uuid.uuid4()

QUESTION = "How do the two papers differ in formulation and convergence?"
DIMENSIONS = ["problem formulation", "convergence guarantees"]

PROSE_A = (
    "The problem is formulated over a Hilbert space with bounded linear operators [17]. "
    "We derive the corresponding variational inequality and show it is well posed."
)
PROSE_B = (
    "Convergence to a stationary point is established under a Lipschitz gradient "
    "assumption, and the rate is characterised in terms of the step size."
)
BIBLIOGRAPHY = """References
[18] Qu B and Xiu N 2005 A note on the CQ algorithm Inverse Problems 21 1655
[19] Rockafellar R T 1970 Convex Analysis (Princeton University Press)
[20] Schopfer F, Schuster T and Louis A K 2008 An iterative regularization method
Inverse Problems 24 055008
"""
BOILERPLATE = (
    "This content was downloaded from IP Address 10.0.0.1. "
    "Please note that terms and conditions apply. See the journal homepage for more."
)


def _unit(paper_id, title, page, text):
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=title,
        page=page,
        text=text,
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
        page_char_start=0,
        page_char_end=len(text),
    )


class ScoringReranker:
    """Deterministic stand-in: longer prose scores higher, bibliography negative."""

    def __init__(self):
        self.calls = 0

    def rerank(self, query, texts):
        self.calls += 1
        scored = []
        for index, text in enumerate(texts):
            score = 1.0 + len(text) / 1000.0
            if "References" in text:
                score = -1.0
            scored.append((index, score))
        return sorted(scored, key=lambda pair: pair[1], reverse=True)


class CountingLLM:
    """Any call to this is an architecture violation."""

    def __init__(self):
        self.calls = 0

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self.calls += 1
            raise AssertionError(
                f"fast_v2 invoked an evidence-extraction LLM ({name}); "
                "query-time extraction LLM calls must be zero."
            )

        return _record


@pytest.fixture
def units():
    return [
        _unit(PAPER_A, "Paper A", 3, PROSE_A),
        _unit(PAPER_B, "Paper B", 9, PROSE_B),
        _unit(PAPER_A, "Paper A", 17, BIBLIOGRAPHY),
        _unit(PAPER_A, "Paper A", 0, BOILERPLATE),
    ]


@pytest.fixture
def pipeline(units):
    return FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
    )


async def _run(pipeline):
    return await pipeline.run(question=QUESTION, dimensions=DIMENSIONS)


# --------------------------------------------------------------------------
# Test 1 -- the central invariant
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fast_v2_makes_zero_extraction_llm_calls(units):
    """Test 1: no query-time evidence-extraction LLM call may happen."""
    extraction_llm = CountingLLM()
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        # Injected purely so any accidental use is caught and counted.
        extraction_llm=extraction_llm,
    )
    result = await _run(pipeline)

    assert extraction_llm.calls == 0
    assert result.timings["extraction_calls"] == 0


@pytest.mark.asyncio
async def test_exactly_one_generation_call(pipeline):
    result = await _run(pipeline)
    assert result.timings["generation_calls"] == 1
    assert pipeline.generator.calls == 1


@pytest.mark.asyncio
async def test_deterministic_retrieval_is_not_counted_as_an_llm_call(pipeline):
    result = await _run(pipeline)
    # Two dimensions -> two retrieval queries, still one generation call.
    assert len(pipeline.retriever.queries) == 2
    assert result.timings["generation_calls"] == 1


# --------------------------------------------------------------------------
# Pipeline wiring
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_returns_a_result_with_the_expected_shape(pipeline):
    result = await _run(pipeline)
    assert isinstance(result, FastSynthesisV2Result)
    assert result.text
    assert result.evidence_bank is not None


@pytest.mark.asyncio
async def test_hygiene_removes_bibliography_and_boilerplate(pipeline):
    result = await _run(pipeline)
    banked = {unit.text for unit in result.evidence_bank.evidence}
    assert BIBLIOGRAPHY not in banked
    assert BOILERPLATE not in banked


@pytest.mark.asyncio
async def test_dimension_queries_are_distinct(pipeline):
    await _run(pipeline)
    assert len(set(pipeline.retriever.queries)) == 2


@pytest.mark.asyncio
async def test_dimension_queries_do_not_contain_the_research_question(pipeline):
    await _run(pipeline)
    for query in pipeline.retriever.queries:
        assert QUESTION not in query


@pytest.mark.asyncio
async def test_evidence_selected_by_both_dimensions_appears_once(pipeline):
    result = await _run(pipeline)
    ids = [unit.evidence_id for unit in result.evidence_bank.evidence]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_dimension_metadata_survives_the_pipeline(pipeline):
    result = await _run(pipeline)
    for unit in result.evidence_bank.evidence:
        assert unit.selected_for_dimensions
        assert unit.best_dimension_score is not None


@pytest.mark.asyncio
async def test_generator_receives_the_bank_that_the_pipeline_built(pipeline):
    result = await _run(pipeline)
    assert pipeline.generator.last_bank is result.evidence_bank


@pytest.mark.asyncio
async def test_pipeline_requires_explicit_dimensions(pipeline):
    with pytest.raises(ValueError):
        await pipeline.run(question=QUESTION, dimensions=[])


# --------------------------------------------------------------------------
# Task 21 -- experimental status metadata
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_result_declares_the_experimental_synthesis_mode(pipeline):
    result = await _run(pipeline)
    assert result.synthesis_mode == "fast_v2_experimental"


@pytest.mark.asyncio
async def test_result_declares_grounding_as_unvalidated(pipeline):
    result = await _run(pipeline)
    assert result.claim_grounding_status == "unvalidated"
    assert result.grounded is False


@pytest.mark.asyncio
async def test_result_metadata_is_serializable(pipeline):
    payload = (await _run(pipeline)).to_dict()
    assert payload["synthesis_mode"] == "fast_v2_experimental"
    assert payload["claim_grounding_status"] == "unvalidated"
    assert payload["grounded"] is False


# --------------------------------------------------------------------------
# Task 10 -- observability
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_required_phase_timings_are_exposed(pipeline):
    timings = (await _run(pipeline)).timings
    for phase in PHASES:
        assert phase in timings, phase
    assert "total_ms" in timings


@pytest.mark.asyncio
async def test_timings_are_numeric_and_non_negative(pipeline):
    timings = (await _run(pipeline)).timings
    for phase in PHASES:
        assert isinstance(timings[phase], (int, float))
        assert timings[phase] >= 0


@pytest.mark.asyncio
async def test_generation_calls_is_reported(pipeline):
    assert (await _run(pipeline)).timings["generation_calls"] == 1


# --------------------------------------------------------------------------
# Citations
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_final_citations_resolve_to_bank_evidence_ids(pipeline):
    result = await _run(pipeline)
    valid = {unit.evidence_id for unit in result.evidence_bank.evidence}
    for citation in result.citations:
        assert citation.evidence_id in valid


@pytest.mark.asyncio
async def test_no_negative_scored_evidence_reaches_the_bank(pipeline):
    result = await _run(pipeline)
    for unit in result.evidence_bank.evidence:
        assert unit.best_dimension_score > 0
