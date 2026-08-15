import uuid

from src.models.synthesis_schemas import EvidenceDuplicateGroup
from src.services.evidence_deduplication_policy import sanitize_evidence_deduplication


def test_accepts_duplicate_ids_only_within_the_same_paper_dimension_group():
    keep_id, duplicate_id = uuid.uuid4(), uuid.uuid4()
    group_key = (uuid.uuid4(), "limitations")

    result = sanitize_evidence_deduplication(
        decisions=[EvidenceDuplicateGroup(keep_id=keep_id, duplicate_ids=[duplicate_id], reason="Same finding repeated in the conclusion.")],
        group_by_id={keep_id: group_key, duplicate_id: group_key},
    )

    assert result == {duplicate_id: (keep_id, "Same finding repeated in the conclusion.")}


def test_rejects_cross_dimension_and_unknown_duplicate_ids_fail_safe():
    keep_id, other_dimension_id, unknown_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    paper_id = uuid.uuid4()

    result = sanitize_evidence_deduplication(
        decisions=[
            EvidenceDuplicateGroup(
                keep_id=keep_id,
                duplicate_ids=[other_dimension_id, unknown_id],
                reason="Appears duplicated.",
            )
        ],
        group_by_id={
            keep_id: (paper_id, "findings"),
            other_dimension_id: (paper_id, "limitations"),
        },
    )

    assert result == {}


def test_rejects_conflicting_or_chained_merge_decisions():
    first, second, third = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    group_key = (uuid.uuid4(), "dataset")

    result = sanitize_evidence_deduplication(
        decisions=[
            EvidenceDuplicateGroup(keep_id=first, duplicate_ids=[second], reason="Same dataset."),
            EvidenceDuplicateGroup(keep_id=second, duplicate_ids=[third], reason="Same dataset."),
        ],
        group_by_id={first: group_key, second: group_key, third: group_key},
    )

    assert result == {}


def test_evidence_records_keep_an_auditable_self_reference_instead_of_deletion():
    from src.models.db_models import EvidenceRecord

    assert "merged_into_id" in EvidenceRecord.__table__.columns
    assert EvidenceRecord.__table__.columns["merged_into_id"].nullable is True
    assert "merge_reason" in EvidenceRecord.__table__.columns
    assert EvidenceRecord.__table__.columns["merge_reason"].nullable is True
