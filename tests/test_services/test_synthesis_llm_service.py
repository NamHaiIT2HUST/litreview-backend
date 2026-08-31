import asyncio
import uuid

import pytest

from src.models.synthesis_schemas import (
    EvidenceDeduplicationBatch,
    EvidenceDimension,
    EvidenceExtractionBatch,
    LLMEvidenceItem,
)


class FakeStructuredRunner:
    def __init__(self, schema, responses, calls):
        self.schema = schema
        self.responses = responses
        self.calls = calls

    async def ainvoke(self, messages):
        self.calls.append((self.schema, messages))
        return self.responses[self.schema]


class FakeLLM:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def with_structured_output(self, schema):
        return FakeStructuredRunner(schema, self.responses, self.calls)


class SlowRunner:
    async def ainvoke(self, messages):
        await asyncio.sleep(0.01)
        return object()


class SlowLLM:
    def with_structured_output(self, schema):
        return SlowRunner()


@pytest.mark.asyncio
async def test_provider_concurrency_snapshot_honors_semaphore_limit():
    from src.services.synthesis_llm_service import SynthesisLLMService

    service = SynthesisLLMService(llm=SlowLLM(), max_concurrency=1, retry_delays=())
    await asyncio.gather(*[
        service._invoke_structured(dict, system="s", human=str(i))
        for i in range(3)
    ])

    snapshot = service.concurrency_snapshot()
    assert snapshot["configured_max_concurrency"] == 1
    assert snapshot["max_active_invocations"] == 1


@pytest.mark.asyncio
async def test_semantic_dedupe_prompt_preserves_different_numeric_results():
    from src.services.synthesis_llm_service import SynthesisLLMService

    first, second = uuid.uuid4(), uuid.uuid4()
    fake = FakeLLM(
        {
            EvidenceDeduplicationBatch: EvidenceDeduplicationBatch(groups=[]),
        }
    )
    service = SynthesisLLMService(llm=fake)

    await service.deduplicate_evidence_batch(
        evidence_context=(
            f"[evidence_id={first}] improved accuracy by 5%\n"
            f"[evidence_id={second}] improved accuracy by 12%"
        )
    )

    assert fake.calls[0][0] is EvidenceDeduplicationBatch
    prompt_text = str(fake.calls[0][1])
    assert "different numeric" in prompt_text
    assert "do not merge" in prompt_text.lower()
    assert "reason" in prompt_text.lower()


@pytest.mark.asyncio
async def test_extract_evidence_only_accepts_chunk_ids_from_context_at_business_layer():
    from src.services.synthesis_llm_service import SynthesisLLMService

    chunk_id = uuid.uuid4()
    fake = FakeLLM(
        {
            EvidenceExtractionBatch: EvidenceExtractionBatch(
                items=[
                    LLMEvidenceItem(
                        value="No significant improvement",
                        quote="No significant improvement was observed.",
                        source_chunk_id=chunk_id,
                    )
                ]
            )
        }
    )
    service = SynthesisLLMService(llm=fake)

    result = await service.extract_evidence(
        research_question="RQ",
        dimension=EvidenceDimension.findings,
        indexed_chunks=[(chunk_id, "No significant improvement was observed.")],
        exact_quote_only=False,
    )

    assert result.items[0].source_chunk_id == chunk_id
    prompt_text = str(fake.calls[0][1])
    assert str(chunk_id) in prompt_text
    assert "anchor_chunk_id" in prompt_text
    assert "continuous raw page window" in prompt_text


@pytest.mark.asyncio
async def test_verify_claim_set_uses_joint_evidence_context():
    from src.models.synthesis_schemas import ClaimVerificationDecision
    from src.services.synthesis_llm_service import SynthesisLLMService

    e1, e2 = uuid.uuid4(), uuid.uuid4()
    fake = FakeLLM(
        {
            ClaimVerificationDecision: ClaimVerificationDecision(
                status="supported",
                evidence_ids=[e1, e2],
                reason="The pair jointly shows inconsistent results across studies.",
            )
        }
    )
    service = SynthesisLLMService(llm=fake)

    result = await service.verify_claim_set(
        claim_statement="Results are inconsistent across datasets.",
        evidence_items=[
            (e1, "Transformer outperformed LSTM", "Transformer significantly outperformed LSTM."),
            (e2, "No significant difference", "No significant difference was observed."),
        ],
    )

    assert result.status.value == "supported"
    assert set(result.evidence_ids) == {e1, e2}
    prompt_text = str(fake.calls[0][1])
    assert str(e1) in prompt_text and str(e2) in prompt_text


@pytest.mark.asyncio
async def test_verify_claim_set_batch_returns_claim_scoped_decisions():
    from src.models.synthesis_schemas import (
        ClaimVerificationBatchItem,
        ClaimVerificationBatchOutput,
    )
    from src.services.synthesis_llm_service import SynthesisLLMService

    claim_id, evidence_id = uuid.uuid4(), uuid.uuid4()
    output = ClaimVerificationBatchOutput(
        decisions=[
            ClaimVerificationBatchItem(
                claim_id=claim_id,
                status="supported",
                evidence_ids=[evidence_id],
                reason="The supplied quote directly supports the claim.",
            )
        ]
    )
    fake = FakeLLM({ClaimVerificationBatchOutput: output})

    result = await SynthesisLLMService(llm=fake).verify_claim_set_batch(
        claims_with_evidence=[
            (
                claim_id,
                "Accuracy improved.",
                [(evidence_id, "Accuracy improved", "Accuracy improved by five points.")],
            )
        ]
    )

    assert result.decisions[0].claim_id == claim_id
    assert fake.calls[0][0] is ClaimVerificationBatchOutput
    prompt = str(fake.calls[0][1])
    assert str(claim_id) in prompt and str(evidence_id) in prompt
    assert "only evidence IDs listed inside that claim" in prompt


@pytest.mark.asyncio
async def test_draft_depth_scales_with_supported_evidence():
    from src.models.synthesis_schemas import DraftSentence, SectionDraftOutput
    from src.services.synthesis_llm_service import SynthesisLLMService

    claim_id = uuid.uuid4()
    fake = FakeLLM(
        {
            SectionDraftOutput: SectionDraftOutput(
                sentences=[DraftSentence(sentence="Grounded result.", claim_ids=[claim_id])]
            )
        }
    )
    await SynthesisLLMService(llm=fake).draft_section(
        research_question="RQ",
        section_title="Findings",
        claims_context=f"[claim_id={claim_id}] Grounded result.",
    )

    prompt = str(fake.calls[0][1]).lower()
    assert "3-5 coherent sentences" not in prompt
    assert "250" in prompt and "500" in prompt
    assert "sparse" in prompt
    assert "compare" in prompt


@pytest.mark.asyncio
async def test_extract_paper_evidence_batch_uses_one_structured_call():
    from src.models.synthesis_schemas import (
        EvidenceDimension,
        PaperEvidenceExtractionOutput,
        StructuredEvidenceItem,
    )
    from src.services.synthesis_llm_service import SynthesisLLMService

    chunk_id = uuid.uuid4()
    output = PaperEvidenceExtractionOutput(items=[StructuredEvidenceItem(
        dimension=EvidenceDimension.findings,
        value="Improved accuracy",
        quote="Accuracy improved by five points.",
        source_chunk_id=chunk_id,
    )])
    fake = FakeLLM({PaperEvidenceExtractionOutput: output})
    result = await SynthesisLLMService(llm=fake).extract_paper_evidence_batch(
        research_question="General review",
        contexts_by_dimension={EvidenceDimension.findings: [(chunk_id, "Accuracy improved by five points.")]},
    )
    assert result.items[0].dimension is EvidenceDimension.findings
    assert len(fake.calls) == 1
    prompt = str(fake.calls[0][1])
    assert "findings" in prompt and str(chunk_id) in prompt


@pytest.mark.asyncio
async def test_custom_batch_extraction_lists_dimension_allowed_chunk_ids():
    from src.models.synthesis_schemas import EvidenceDimension, PaperEvidenceExtractionOutput
    from src.services.synthesis_llm_service import SynthesisLLMService

    chunk_id = uuid.uuid4()
    fake = FakeLLM({PaperEvidenceExtractionOutput: PaperEvidenceExtractionOutput(items=[])})
    await SynthesisLLMService(llm=fake).extract_paper_evidence_batch(
        research_question="Custom RQ",
        contexts_by_dimension={EvidenceDimension.method: [(chunk_id, "method text")]},
        strict_dimension_ids=True,
    )
    prompt = str(fake.calls[0][1])
    assert "Allowed source_chunk_id values for this dimension" in prompt
    assert "Never use a source_chunk_id outside its allowed ID list" in prompt
    assert f"<source_chunk_id={chunk_id}>" in prompt
    assert "Do not paraphrase" in prompt
    assert "insert ellipses" in prompt
