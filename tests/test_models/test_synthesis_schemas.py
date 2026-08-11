import uuid

import pytest
from pydantic import ValidationError


def test_grounded_evidence_requires_ordered_raw_offsets():
    from src.models.synthesis_schemas import GroundedEvidence

    data = {
        "paper_id": uuid.uuid4(),
        "dimension": "main_finding",
        "value": "No significant improvement",
        "quote": "No significant improvement was observed.",
        "source_chunk_id": uuid.uuid4(),
        "page_text_id": uuid.uuid4(),
        "page_number": 3,
        "page_char_start": 120,
        "page_char_end": 160,
    }
    evidence = GroundedEvidence(**data)
    assert evidence.page_char_end > evidence.page_char_start

    data["page_char_end"] = 100
    with pytest.raises(ValidationError):
        GroundedEvidence(**data)


def test_claim_evidence_entailment_is_relative_link_state():
    from src.models.synthesis_schemas import ClaimEvidenceInput, EntailmentStatus

    link = ClaimEvidenceInput(
        evidence_id=uuid.uuid4(),
        relation="supports",
        entailment_status=EntailmentStatus.supported,
    )
    assert link.entailment_status is EntailmentStatus.supported


def test_plan_dimensions_are_deduplicated_and_nonempty():
    from src.models.synthesis_schemas import SynthesisPlanOutput

    plan = SynthesisPlanOutput(dimensions=["method", "finding", "method", "  "])
    assert plan.dimensions == ["method", "finding"]


def test_draft_sentence_requires_at_least_one_claim():
    from src.models.synthesis_schemas import DraftSentence

    with pytest.raises(ValidationError):
        DraftSentence(sentence="Unsupported prose.", claim_ids=[])


def test_supported_claim_verification_requires_joint_evidence_ids():
    from src.models.synthesis_schemas import ClaimVerificationDecision

    with pytest.raises(ValidationError):
        ClaimVerificationDecision(
            status="supported",
            evidence_ids=[],
            reason="Claim supposedly supported without evidence.",
        )

    evidence_ids = [uuid.uuid4(), uuid.uuid4()]
    decision = ClaimVerificationDecision(
        status="supported",
        evidence_ids=evidence_ids,
        reason="The two studies jointly establish the cross-paper pattern.",
    )
    assert decision.evidence_ids == evidence_ids

def test_draft_sentence_rejects_llm_generated_numeric_citation_markers():
    import pytest
    from src.models.synthesis_schemas import DraftSentence

    with pytest.raises(ValueError):
        DraftSentence(sentence="The method improved accuracy [1].", claim_ids=[uuid.uuid4()])

def test_synthesis_request_schema_allows_runtime_configured_limits_above_15():
    from src.models.synthesis_schemas import SynthesisSessionCreateRequest

    request = SynthesisSessionCreateRequest(
        project_id=uuid.uuid4(),
        paper_ids=[uuid.uuid4() for _ in range(16)],
    )
    assert len(request.paper_ids) == 16
