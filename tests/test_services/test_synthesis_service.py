import uuid
from types import SimpleNamespace

import pytest

from src.models.db_models import SynthesisClaimType
from src.models.synthesis_schemas import (
    DraftSentence,
    OutlineSectionProposal,
    SectionDraftOutput,
    SentenceType,
    SynthesisOutlineOutput,
)
from src.services.synthesis_service import SynthesisService
from src.services.synthesis_service import batch_verification_is_complete
from src.models.synthesis_schemas import ClaimVerificationBatchOutput, ClaimVerificationBatchItem, EntailmentStatus


class _Result:
    def __init__(self, *, rows=None, scalar=None):
        self._rows = rows or []
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._scalar


class _DB:
    def __init__(self, results):
        self._results = iter(results)
        self.added = []

    async def execute(self, _statement):
        return next(self._results)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


def test_batch_verification_retry_completion_requires_unique_decisions():
    claim_id = uuid.uuid4()
    decision = ClaimVerificationBatchItem(
        claim_id=claim_id, status=EntailmentStatus.supported,
        evidence_ids=[uuid.uuid4()], reason="ok",
    )
    assert not batch_verification_is_complete(ClaimVerificationBatchOutput(decisions=[]), 1)
    assert batch_verification_is_complete(ClaimVerificationBatchOutput(decisions=[decision]), 1)
    assert not batch_verification_is_complete(ClaimVerificationBatchOutput(decisions=[decision, decision]), 1)


@pytest.mark.asyncio
async def test_draft_section_keeps_section_coverage_without_outline_scope_nameerror(monkeypatch):
    section_id = uuid.uuid4()
    session_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    section = SimpleNamespace(
        id=section_id,
        synthesis_session_id=session_id,
        title="Findings",
        position=0,
    )
    claim = SimpleNamespace(
        id=claim_id,
        statement="The intervention improved accuracy.",
        claim_type=SynthesisClaimType.descriptive,
    )
    evidence = SimpleNamespace(
        paper_id=paper_id,
        value="Accuracy improved.",
        quote="Accuracy improved by five points.",
    )
    paper = SimpleNamespace(title="Paper A")
    db = _DB([
        _Result(scalar=section),
        _Result(rows=[(claim, SimpleNamespace(), evidence, paper)]),
    ])

    async def fake_draft_section(**_kwargs):
        return SectionDraftOutput(
            sentences=[
                DraftSentence(
                    sentence="The intervention improved accuracy.",
                    claim_ids=[claim_id],
                    sentence_type=SentenceType.claim,
                )
            ]
        )

    monkeypatch.setattr(
        "src.services.synthesis_service.synthesis_llm_service.draft_section",
        fake_draft_section,
    )

    payload = await SynthesisService().draft_section(
        db,
        section_id=section_id,
        research_question="What works?",
    )

    assert payload["coverage"]["evidence_count"] == 1
    assert payload["sentences"][0]["claim_ids"] == [str(claim_id)]


@pytest.mark.asyncio
async def test_build_outline_repairs_omitted_supported_paper_before_persistence(monkeypatch):
    session_id = uuid.uuid4()
    claim_a_id, claim_b_id = uuid.uuid4(), uuid.uuid4()
    paper_a_id, paper_b_id = uuid.uuid4(), uuid.uuid4()
    claim_a = SimpleNamespace(
        id=claim_a_id,
        statement="Paper A reports improvement.",
        claim_type=SynthesisClaimType.descriptive,
        section_id=None,
    )
    claim_b = SimpleNamespace(
        id=claim_b_id,
        statement="Paper B reports no improvement.",
        claim_type=SynthesisClaimType.descriptive,
        section_id=None,
    )
    evidence_a = SimpleNamespace(id=uuid.uuid4(), paper_id=paper_a_id, dimension="findings")
    evidence_b = SimpleNamespace(id=uuid.uuid4(), paper_id=paper_b_id, dimension="findings")
    db = _DB([
        _Result(rows=[
            (claim_a, SimpleNamespace(), evidence_a),
            (claim_b, SimpleNamespace(), evidence_b),
        ]),
        _Result(),
        _Result(),
        _Result(),
    ])

    async def fake_build_outline(**_kwargs):
        return SynthesisOutlineOutput(
            sections=[
                OutlineSectionProposal(
                    title="Main Findings",
                    position=0,
                    claim_ids=[claim_a_id],
                )
            ]
        )

    monkeypatch.setattr(
        "src.services.synthesis_service.synthesis_llm_service.build_outline",
        fake_build_outline,
    )

    await SynthesisService().build_outline(
        db,
        session_id=session_id,
        research_question="What works?",
    )

    persisted_sections = [item for item in db.added if hasattr(item, "title")]
    assert [section.title for section in persisted_sections] == [
        "Main Findings",
        "Additional Supported Evidence",
    ]
    assert claim_a.section_id == persisted_sections[0].id
    assert claim_b.section_id == persisted_sections[1].id


def test_batch_decision_reconciliation_selects_only_unique_known_claims():
    from src.models.synthesis_schemas import (
        ClaimVerificationBatchItem,
        ClaimVerificationBatchOutput,
    )
    from src.services.synthesis_service import reconcile_claim_verification_batch

    claim_a, claim_b, unknown = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    evidence_id = uuid.uuid4()
    output = ClaimVerificationBatchOutput(
        decisions=[
            ClaimVerificationBatchItem(
                claim_id=claim_a,
                status="supported",
                evidence_ids=[evidence_id],
                reason="First decision.",
            ),
            ClaimVerificationBatchItem(
                claim_id=claim_a,
                status="supported",
                evidence_ids=[evidence_id],
                reason="Duplicate decision.",
            ),
            ClaimVerificationBatchItem(
                claim_id=unknown,
                status="insufficient",
                reason="Unknown claim.",
            ),
        ]
    )

    accepted, fallback_ids = reconcile_claim_verification_batch(
        output,
        {claim_a, claim_b},
    )

    assert accepted == {}
    assert fallback_ids == {claim_a, claim_b}
