"""Claim-grounding boundary: interface only, explicitly unvalidated."""
from __future__ import annotations

import uuid

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.grounding.interface import (
    ClaimGroundingService,
    ClaimGroundingStatus,
    UnvalidatedClaimGroundingPassthrough,
)


def _bank():
    unit = EvidenceUnit.from_chunk(
        paper_id=uuid.uuid4(),
        title="Paper A",
        page=1,
        text="body",
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
    ).with_dimension("d", 1.0)
    return GroundedEvidenceBank.build(
        question="q", dimensions=["d"], evidence_by_dimension={"d": [unit]}
    )


def _draft():
    return GeneratedDraft(text="An answer [0].", model_name="fake", prompt_version="v")


def test_passthrough_satisfies_the_interface():
    assert isinstance(UnvalidatedClaimGroundingPassthrough(), ClaimGroundingService)


def test_grounding_status_is_unvalidated():
    result = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=_draft(), evidence_bank=_bank()
    )
    assert result.claim_grounding_status == ClaimGroundingStatus.unvalidated
    assert result.claim_grounding_status.value == "unvalidated"


def test_passthrough_never_reports_grounded_true():
    """The single most important property of this placeholder."""
    result = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=_draft(), evidence_bank=_bank()
    )
    assert result.grounded is False


def test_passthrough_preserves_the_draft_text_verbatim():
    draft = _draft()
    result = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=draft, evidence_bank=_bank()
    )
    assert result.text == draft.text
    assert result.draft is draft


def test_passthrough_makes_no_claim_level_assertions():
    result = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=_draft(), evidence_bank=_bank()
    )
    assert result.supported_claims == ()
    assert result.unsupported_claims == ()


def test_result_carries_an_explicit_warning():
    result = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=_draft(), evidence_bank=_bank()
    )
    assert "not" in result.warning.lower()
    assert result.warning


def test_grounded_draft_serializes_its_status():
    payload = UnvalidatedClaimGroundingPassthrough().evaluate(
        draft=_draft(), evidence_bank=_bank()
    ).to_dict()
    assert payload["claim_grounding_status"] == "unvalidated"
    assert payload["grounded"] is False


def test_no_status_value_claims_validation():
    """There is deliberately no 'validated'/'grounded' status to select yet."""
    assert {status.value for status in ClaimGroundingStatus} == {
        "unvalidated",
        "not_evaluated",
    }


def test_grounded_draft_is_not_constructible_as_grounded_by_the_passthrough():
    service: ClaimGroundingService = UnvalidatedClaimGroundingPassthrough()
    for _ in range(3):
        assert service.evaluate(draft=_draft(), evidence_bank=_bank()).grounded is False
