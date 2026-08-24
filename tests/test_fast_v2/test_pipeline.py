"""Test 1 + pipeline wiring + observability (Task 7 / Task 10).

The headline assertion is :func:`test_fast_v2_makes_zero_extraction_llm_calls`.
"""
from __future__ import annotations

import json
import uuid

import pytest

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.evidence.retrieval import StaticEvidenceRetriever
from src.synthesis.fast_v2.dimensions.facets import QuestionFacetDimensionQueryPlanner
from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
from src.synthesis.fast_v2.observability import PHASES
from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline, FastSynthesisV2Result
from src.synthesis.fast_v2.grounding.semantic import (
    DeterministicFakeSemanticVerifier,
    SemanticVerdict,
)
from src.synthesis.fast_v2.writer import DeterministicFakeLiteratureWriter

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


@pytest.mark.asyncio
async def test_static_retriever_honors_optional_paper_scope(units):
    retriever = StaticEvidenceRetriever(units)

    results = await retriever.retrieve("query", limit=40, paper_id=PAPER_B)

    assert results
    assert {unit.paper_id for unit in results} == {PAPER_B}


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
    assert result.diagnostics["evidence_handle_mapping"] == {
        f"E{index:03d}": unit.evidence_id
        for index, unit in enumerate(result.evidence_bank.evidence, start=1)
    }


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
    assert result.structured_provenance_validation == "passed"
    assert result.semantic_entailment == "unverified"


@pytest.mark.asyncio
async def test_result_metadata_is_serializable(pipeline):
    payload = (await _run(pipeline)).to_dict()
    assert payload["synthesis_mode"] == "fast_v2_experimental"
    assert payload["claim_grounding_status"] == "unvalidated"
    assert payload["grounded"] is False
    assert payload["structured_provenance_validation"] == "passed"
    assert payload["semantic_entailment"] == "unverified"


@pytest.mark.asyncio
async def test_pipeline_batches_semantic_verification_without_extra_generation(units):
    verifier = DeterministicFakeSemanticVerifier()
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        semantic_verifier=verifier,
    )

    result = await _run(pipeline)

    assert verifier.calls == 1
    assert result.timings["generation_calls"] == 1
    assert result.semantic_entailment == "passed"
    assert result.grounded is True
    assert result.diagnostics["semantic_verification_results"]


@pytest.mark.asyncio
async def test_pipeline_finalizes_only_supported_statements_and_keeps_audit():
    supported_text = (
        "The first scientific study formulates a constrained optimization "
        "problem over a closed convex set and reports a convergence result "
        "with an explicit step-size condition and bounded operator."
    )
    unsupported_text = (
        "The second scientific study applies an iterative projection method "
        "under a smoothness assumption and discusses convergence behavior."
    )
    semantic_units = [
        _unit(PAPER_A, "Paper A", 1, supported_text),
        _unit(PAPER_B, "Paper B", 2, unsupported_text),
    ]
    verifier = DeterministicFakeSemanticVerifier(
        verdicts={
            (0, 0): SemanticVerdict.supported,
            (1, 0): SemanticVerdict.unsupported,
        }
    )
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(semantic_units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        semantic_verifier=verifier,
    )

    result = await _run(pipeline)

    assert supported_text in result.text
    assert unsupported_text not in result.text
    assert len(result.citations) == 1
    assert result.semantic_entailment == "partial"
    assert result.grounded is True
    assert len(result.diagnostics["parsed_claim_manifest"]["claims"]) == 2
    provenance_audit = result.diagnostics["semantic_original_provenance_draft"]
    assert provenance_audit["structured_provenance_validation"] == "passed"
    assert len(provenance_audit["validated_claims"]) == 2
    assert provenance_audit["validated_claims"][1]["statements"][0]["claim_text"] == (
        unsupported_text
    )
    assert result.diagnostics["semantic_rejected_statement_details"] == [
        {
            "claim_index": 1,
            "statement_index": 0,
            "claim_text": unsupported_text,
            "paper_id": str(PAPER_B),
            "facet": "problem formulation",
            "evidence_ids": [semantic_units[1].evidence_id],
            "verdict": "unsupported",
            "reason": "",
        }
    ]
    assert [
        item["verdict"]
        for item in result.diagnostics["semantic_verification_results"]
    ] == ["supported", "unsupported"]


@pytest.mark.asyncio
async def test_pipeline_writer_receives_only_semantic_supported_claims():
    supported_text = "Paper A defines a constrained convex model."
    partial_text = "Paper B reports a broader model and an additional guarantee."
    semantic_units = [
        _unit(PAPER_A, "Paper A", 1, supported_text),
        _unit(PAPER_B, "Paper B", 2, partial_text),
    ]
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "title": "Problem Formulation",
                        "paragraphs": [
                            {
                                "text": "Paper A defines a constrained convex model.",
                                "supporting_claim_ids": ["claim_0_0"],
                            }
                        ],
                    }
                ]
            }
        ),
        input_tokens=101,
        output_tokens=37,
    )
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(semantic_units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        semantic_verifier=DeterministicFakeSemanticVerifier(
            verdicts={(1, 0): SemanticVerdict.partial}
        ),
        literature_writer=writer,
    )

    result = await _run(pipeline)

    assert [claim.claim_id for claim in writer.last_claims] == ["claim_0_0"]
    assert result.text.startswith("**Problem Formulation**")
    assert supported_text in result.text
    assert partial_text not in result.text
    assert result.diagnostics["writer_calls"] == 1
    assert result.diagnostics["writer_input_tokens"] == 101
    assert result.diagnostics["writer_output_tokens"] == 37
    assert result.diagnostics["writer_fallback_reason"] is None
    assert result.diagnostics["writer_claim_coverage"]["coverage_percent"] == 100.0


@pytest.mark.asyncio
async def test_pipeline_writer_failure_falls_back_without_breaking_synthesis(units):
    baseline_pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        semantic_verifier=DeterministicFakeSemanticVerifier(),
    )
    baseline = await _run(baseline_pipeline)
    writer = DeterministicFakeLiteratureWriter(error=RuntimeError("writer offline"))
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=FakeSynthesisGenerator(),
        semantic_verifier=DeterministicFakeSemanticVerifier(),
        literature_writer=writer,
    )

    result = await _run(pipeline)

    assert result.text
    assert result.text == baseline.text
    assert result.citations == baseline.citations
    assert result.diagnostics["writer_calls"] == 1
    assert "RuntimeError: writer offline" in result.diagnostics[
        "writer_fallback_reason"
    ]


@pytest.mark.asyncio
async def test_pipeline_final_text_is_rendered_from_validated_manifest(pipeline):
    result = await _run(pipeline)
    assert "Drawing on the supplied references" not in result.text
    assert result.citations
    assert all(citation.evidence_id for citation in result.citations)


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


@pytest.mark.asyncio
async def test_scratch_diagnostics_expose_manifest_validation_without_secrets(pipeline):
    pipeline.generator.api_key = "test-api-key-must-not-leak"

    diagnostics = (await _run(pipeline)).diagnostics

    assert diagnostics["parsed_claim_manifest"]["claims"]
    assert diagnostics["claim_validation"][0]["status"] == "dropped"
    assert diagnostics["claim_validation"][0]["drop_reasons"] == [
        "native_citation_marker"
    ]
    serialized = json.dumps(diagnostics)
    assert "test-api-key-must-not-leak" not in serialized
    assert "Authorization" not in serialized


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


@pytest.mark.asyncio
async def test_comparative_scopes_preserve_positive_evidence_without_negative_padding():
    paper_a = uuid.UUID("11111111-1111-1111-1111-111111111111")
    paper_b = uuid.UUID("22222222-2222-2222-2222-222222222222")

    def scored_unit(paper_id, title, page, score):
        text = (
            f"Substantive scientific evidence on page {page} explains the mathematical "
            f"method, assumptions, and convergence result with score marker {score}."
        )
        return _unit(paper_id, title, page, text)

    units_by_paper = {
        paper_a: [scored_unit(paper_a, "Paper A", page, score) for page, score in enumerate((5, 4, 3, 2), 1)],
        paper_b: [scored_unit(paper_b, "Paper B", 1, 1), scored_unit(paper_b, "Paper B", 2, -1)],
    }
    scores = {
        unit.text: float(unit.text.rsplit(" ", 1)[-1].rstrip("."))
        for paper_units in units_by_paper.values()
        for unit in paper_units
    }

    class ScopedRetriever:
        def __init__(self):
            self.calls = []

        async def retrieve(self, query, *, limit, paper_id=None):
            self.calls.append((query, paper_id))
            return list(units_by_paper.get(paper_id, ()))[:limit]

    class FixedReranker:
        def rerank(self, query, texts):
            return sorted(
                [(index, scores[text]) for index, text in enumerate(texts)],
                key=lambda item: item[1],
                reverse=True,
            )

    retriever = ScopedRetriever()
    pipeline = FastSynthesisV2Pipeline(
        retriever=retriever,
        reranker=FixedReranker(),
        generator=FakeSynthesisGenerator(),
        planner=QuestionFacetDimensionQueryPlanner(paper_ids=[paper_a, paper_b]),
    )

    result = await pipeline.run(
        question=(
            "How do the selected papers differ in their formulations of the "
            "gradient descent problem and convergence guarantees?"
        ),
        dimensions=["formulation", "convergence"],
    )

    assert [paper_id for _query, paper_id in retriever.calls] == [
        paper_a,
        paper_b,
        paper_a,
        paper_b,
    ]
    assert result.evidence_bank.dimensions == ("formulation", "convergence")
    assert result.evidence_bank.paper_distribution == {"Paper A": 4, "Paper B": 1}
    assert len(result.evidence_bank.evidence) == 5
    assert all(unit.best_dimension_score > 0 for unit in result.evidence_bank.evidence)
    assert all(
        unit.selected_for_dimensions == ("formulation", "convergence")
        for unit in result.evidence_bank.evidence
    )


@pytest.mark.asyncio
async def test_batched_cross_encoder_is_byte_for_byte_equivalent_to_sequential_path():
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    class PairScoreModel:
        def __init__(self):
            self.predict_calls = 0
            self.seen_pairs = []

        def predict(self, pairs):
            pairs = list(pairs)
            self.predict_calls += 1
            self.seen_pairs.extend(pairs)
            return [
                float(len(query) * 1000 + len(text))
                for query, text in pairs
            ]

    class SequentialOnlyReranker:
        def __init__(self, delegate):
            self.delegate = delegate

        def rerank(self, query, texts):
            return self.delegate.rerank(query, texts)

    parity_units = [
        _unit(
            PAPER_A,
            "Paper A",
            1,
            "A substantive formulation statement with mathematical constraints.",
        ),
        _unit(
            PAPER_B,
            "Paper B",
            2,
            "A substantive algorithm statement with convergence conditions.",
        ),
        _unit(
            PAPER_A,
            "Paper A",
            3,
            "A substantive assumptions statement for the optimization method.",
        ),
    ]
    sequential_model = PairScoreModel()
    batched_model = PairScoreModel()
    sequential_generator = FakeSynthesisGenerator()
    batched_generator = FakeSynthesisGenerator()
    sequential = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(parity_units),
        reranker=SequentialOnlyReranker(
            CrossEncoderReranker(model_factory=lambda name: sequential_model)
        ),
        generator=sequential_generator,
    )
    batched = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(parity_units),
        reranker=CrossEncoderReranker(model_factory=lambda name: batched_model),
        generator=batched_generator,
    )

    sequential_result = await _run(sequential)
    batched_result = await _run(batched)

    sequential_evidence = [
        unit.to_dict() for unit in sequential_result.evidence_bank.evidence
    ]
    batched_evidence = [
        unit.to_dict() for unit in batched_result.evidence_bank.evidence
    ]
    assert batched_evidence == sequential_evidence
    assert [unit.evidence_id for unit in batched_result.evidence_bank.evidence] == [
        unit.evidence_id for unit in sequential_result.evidence_bank.evidence
    ]
    assert [
        (unit.evidence_id, unit.rerank_score)
        for unit in batched_result.evidence_bank.evidence
    ] == [
        (unit.evidence_id, unit.rerank_score)
        for unit in sequential_result.evidence_bank.evidence
    ]
    assert batched_generator.last_prompt == sequential_generator.last_prompt
    assert sequential_model.predict_calls == len(DIMENSIONS)
    assert batched_model.predict_calls == 1
    assert batched_model.seen_pairs == sequential_model.seen_pairs

# --------------------------------------------------------------------------
# Event-loop safety
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_reranker_runs_off_event_loop_thread(units):
    import threading

    class ThreadRecordingReranker(ScoringReranker):
        def __init__(self):
            super().__init__()
            self.thread_id = None

        def rerank(self, query, texts):
            self.thread_id = threading.get_ident()
            return super().rerank(query, texts)

    reranker = ThreadRecordingReranker()
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=reranker,
        generator=FakeSynthesisGenerator(),
    )

    event_loop_thread_id = threading.get_ident()
    await _run(pipeline)

    assert reranker.thread_id != event_loop_thread_id


@pytest.mark.asyncio
async def test_sync_generator_runs_off_event_loop_thread(units):
    import threading

    class ThreadRecordingGenerator(FakeSynthesisGenerator):
        def __init__(self):
            super().__init__()
            self.thread_id = None

        def generate(self, *, question, evidence_bank):
            self.thread_id = threading.get_ident()
            return super().generate(
                question=question,
                evidence_bank=evidence_bank,
            )

    generator = ThreadRecordingGenerator()
    pipeline = FastSynthesisV2Pipeline(
        retriever=StaticEvidenceRetriever(units),
        reranker=ScoringReranker(),
        generator=generator,
    )

    event_loop_thread_id = threading.get_ident()
    await _run(pipeline)

    assert generator.thread_id != event_loop_thread_id
