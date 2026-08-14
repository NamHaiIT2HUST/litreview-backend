import uuid

from src.models.synthesis_schemas import ClaimVerificationDecision, EntailmentStatus
from src.services.claim_verification_policy import guard_topic_absence_claim, sanitize_claim_verification


def test_decisive_verdict_with_any_unknown_evidence_id_fails_closed():
    valid_id = uuid.uuid4()
    unknown_id = uuid.uuid4()
    decision = ClaimVerificationDecision(
        status=EntailmentStatus.supported,
        evidence_ids=[valid_id, unknown_id],
        reason="Both records support the claim.",
    )

    sanitized = sanitize_claim_verification(decision, {valid_id})

    assert sanitized.status == EntailmentStatus.insufficient
    assert sanitized.evidence_ids == []
    assert sanitized.had_unknown_ids is True


def test_decisive_verdict_with_only_allowed_ids_is_preserved():
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    decision = ClaimVerificationDecision(
        status=EntailmentStatus.supported,
        evidence_ids=[e1, e2],
        reason="The evidence set jointly supports the claim.",
    )

    sanitized = sanitize_claim_verification(decision, {e1, e2})

    assert sanitized.status == EntailmentStatus.supported
    assert set(sanitized.evidence_ids) == {e1, e2}
    assert sanitized.had_unknown_ids is False


def test_topic_absence_claim_without_positive_evidence_is_rejected():
    assert guard_topic_absence_claim(
        "The papers do not address recommendation systems.",
        ["The model uses orthogonal initialization on CIFAR-10."],
    ) is not None


def test_positive_scientific_claim_is_not_rejected_by_topic_guard():
    assert guard_topic_absence_claim(
        "Orthogonal initialization improves learning speed.",
        ["Orthogonal initialization can improve learning speed."],
    ) is None
