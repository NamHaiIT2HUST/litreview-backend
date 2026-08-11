import uuid

import pytest

from src.models.synthesis_schemas import (
    EvidenceExtractionBatch,
    LLMEvidenceItem,
    SynthesisPlanOutput,
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


@pytest.mark.asyncio
async def test_plan_dimensions_uses_structured_output():
    from src.services.synthesis_llm_service import SynthesisLLMService

    fake = FakeLLM({SynthesisPlanOutput: SynthesisPlanOutput(dimensions=["method", "finding"])})
    service = SynthesisLLMService(llm=fake)

    result = await service.plan_dimensions("How do RAG systems reduce hallucination?")

    assert result.dimensions == ["method", "finding"]
    assert fake.calls[0][0] is SynthesisPlanOutput


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
        dimension="finding",
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
