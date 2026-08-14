"""Fail-closed policy for LLM claim-verification evidence identifiers."""
from __future__ import annotations

import uuid
import re
from dataclasses import dataclass

from src.models.synthesis_schemas import ClaimVerificationDecision, EntailmentStatus

_ABSENCE_PATTERN = re.compile(
    r"\b(?:do(?:es)? not|did not|no (?:mention|evidence|discussion) of|"
    r"none of the|not (?:focus|focused|address|addressed|discuss|discussed)|"
    r"fails? to (?:address|discuss|cover|mention))\b",
    re.IGNORECASE,
)
_TOPIC_STOPWORDS = {
    "the", "papers", "paper", "studies", "study", "does", "do", "did", "not",
    "address", "addressed", "discuss", "discussed", "focus", "focused", "mention",
    "evidence", "this", "these", "that", "with", "from", "about",
}


def guard_topic_absence_claim(statement: str, evidence_texts: list[str]) -> str | None:
    if not _ABSENCE_PATTERN.search(statement):
        return None
    topic_words = {
        word.lower() for word in re.findall(r"[A-Za-z]{4,}", statement)
        if word.lower() not in _TOPIC_STOPWORDS
    }
    combined = " ".join(evidence_texts).lower()
    if not topic_words or any(word in combined for word in topic_words):
        return None
    return "Rejected topic-absence claim without positive textual evidence."


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
