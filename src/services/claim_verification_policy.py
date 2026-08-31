"""Fail-closed policy for LLM claim-verification evidence identifiers, plus
Tier 1 of the tri-layer Evidence Quantification Engine (MODULE_1_PLAN.md):
deterministic near-verbatim matching, no model call of any kind."""
from __future__ import annotations

import difflib
import uuid
import re
from dataclasses import dataclass
from typing import Sequence

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


_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_for_match(text: str) -> str:
    return _WHITESPACE_RUN.sub(" ", text.strip().lower())


def fuzzy_verbatim_match(
    claim_statement: str,
    evidence_items: Sequence[tuple[uuid.UUID, str]],
    threshold: float = 0.9,
) -> uuid.UUID | None:
    """Tier 1: does the claim appear almost word-for-word inside some
    evidence text? If so, no model call (Tier 2 NLI or Tier 3 LLM) is needed
    to confirm it -- a near-verbatim quote is its own evidence.

    Measures the LONGEST CONTIGUOUS matching run between the claim and each
    evidence text, as a fraction of the CLAIM's own length -- not
    ``difflib``'s whole-string ``.ratio()``, which divides by the combined
    length of both strings and would read as a low score here on purpose:
    evidence text is routinely a full paragraph, so a claim that is a
    perfect 40-character quote from inside a 500-character paragraph should
    score high, not get diluted by how much longer the paragraph is.

    Deliberately NOT bag-of-words/set overlap either: "X causes Y" and "X
    does not cause Y" share nearly every word, so a set-overlap ratio would
    call that a near-perfect match -- exactly the failure mode this tier
    must not have. A contiguous-run measure naturally penalizes an inserted
    "not" (or any other edit): it breaks the matching run in two, dropping
    the fraction well below threshold.

    Returns the evidence_id of the first evidence text that clears
    ``threshold``, or None if nothing does (caller escalates to Tier 2/3).
    """
    claim_norm = _normalize_for_match(claim_statement)
    if not claim_norm:
        return None

    for evidence_id, text in evidence_items:
        evidence_norm = _normalize_for_match(text)
        if not evidence_norm:
            continue
        matcher = difflib.SequenceMatcher(None, claim_norm, evidence_norm)
        match = matcher.find_longest_match(0, len(claim_norm), 0, len(evidence_norm))
        if match.size / len(claim_norm) >= threshold:
            return evidence_id

    return None


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
