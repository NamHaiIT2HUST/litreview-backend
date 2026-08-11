"""Fail-closed policy for LLM claim-verification evidence identifiers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.models.synthesis_schemas import ClaimVerificationDecision, EntailmentStatus


@dataclass(frozen=True, slots=True)
class SanitizedClaimVerification:
    status: EntailmentStatus
    evidence_ids: list[uuid.UUID]
    had_unknown_ids: bool


def sanitize_claim_verification(
    decision: ClaimVerificationDecision,
    allowed_evidence_ids: set[uuid.UUID],
) -> SanitizedClaimVerification:
    """Validate dynamic evidence IDs returned by the verification LLM.

    A decisive verdict is accepted only when *every* referenced evidence ID is
    one of the grounded records supplied to that verification call. If the LLM
    mixes valid IDs with an unknown/hallucinated ID, we cannot know whether the
    valid subset was independently sufficient for its verdict, so the claim is
    downgraded to ``insufficient`` rather than partially trusting the response.
    """
    returned_ids = list(dict.fromkeys(decision.evidence_ids))
    unknown_ids = [item for item in returned_ids if item not in allowed_evidence_ids]
    valid_ids = [item for item in returned_ids if item in allowed_evidence_ids]
    decisive = decision.status in {
        EntailmentStatus.supported,
        EntailmentStatus.contradicted,
    }

    if decisive and (unknown_ids or not valid_ids):
        return SanitizedClaimVerification(
            status=EntailmentStatus.insufficient,
            evidence_ids=[],
            had_unknown_ids=bool(unknown_ids),
        )

    return SanitizedClaimVerification(
        status=decision.status,
        evidence_ids=valid_ids,
        had_unknown_ids=bool(unknown_ids),
    )
