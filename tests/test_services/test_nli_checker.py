import uuid

import pytest

from src.models.synthesis_schemas import EntailmentStatus
from src.services.nli_checker import NLIVerdict, resolve_claims_via_nli


class FakeNLIChecker:
    """Returns pre-scripted verdicts by (premise, hypothesis) pair, in the
    exact order requested -- avoids loading a real model in unit tests."""

    def __init__(self, verdict_by_premise: dict[str, NLIVerdict]):
        self.verdict_by_premise = verdict_by_premise
        self.calls: list[list[tuple[str, str]]] = []

    async def check_many(self, pairs):
        self.calls.append(list(pairs))
        return [self.verdict_by_premise[premise] for premise, _hypothesis in pairs]


def _verdict(status: EntailmentStatus, confidence: float) -> NLIVerdict:
    scores = {"supported": 0.0, "contradicted": 0.0, "insufficient": 0.0}
    scores[status.value] = confidence
    return NLIVerdict(status=status, confidence=confidence, scores=scores)


@pytest.mark.asyncio
async def test_high_confidence_contradiction_resolves_without_llm():
    claim_id = uuid.uuid4()
    e1 = uuid.uuid4()
    checker = FakeNLIChecker({
        "evidence one text": _verdict(EntailmentStatus.contradicted, 0.9),
    })

    resolved = await resolve_claims_via_nli(
        [(claim_id, "The claim statement.", [(e1, "evidence one", "text")])],
        checker=checker,
    )

    assert resolved[claim_id].status == EntailmentStatus.contradicted
    assert resolved[claim_id].evidence_ids == [e1]


@pytest.mark.asyncio
async def test_high_confidence_support_with_no_contradiction_signal_resolves():
    claim_id = uuid.uuid4()
    e1 = uuid.uuid4()
    checker = FakeNLIChecker({
        "evidence one text": _verdict(EntailmentStatus.supported, 0.85),
    })

    resolved = await resolve_claims_via_nli(
        [(claim_id, "The claim statement.", [(e1, "evidence one", "text")])],
        checker=checker,
    )

    assert resolved[claim_id].status == EntailmentStatus.supported
    assert resolved[claim_id].evidence_ids == [e1]


@pytest.mark.asyncio
async def test_low_confidence_verdict_is_left_unresolved_for_tier3():
    claim_id = uuid.uuid4()
    e1 = uuid.uuid4()
    checker = FakeNLIChecker({
        "evidence one text": _verdict(EntailmentStatus.supported, 0.55),  # below threshold
    })

    resolved = await resolve_claims_via_nli(
        [(claim_id, "The claim statement.", [(e1, "evidence one", "text")])],
        checker=checker,
    )

    assert claim_id not in resolved


@pytest.mark.asyncio
async def test_weak_contradiction_signal_prevents_a_support_auto_decision():
    claim_id = uuid.uuid4()
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    checker = FakeNLIChecker({
        "evidence one text": _verdict(EntailmentStatus.supported, 0.9),
        "evidence two text": _verdict(EntailmentStatus.contradicted, 0.4),  # weak, below threshold
    })

    resolved = await resolve_claims_via_nli(
        [(claim_id, "The claim statement.", [
            (e1, "evidence one", "text"),
            (e2, "evidence two", "text"),
        ])],
        checker=checker,
    )

    # Neither branch fires: contradiction is below threshold (can't settle as
    # contradicted), but its mere presence blocks the support auto-decision too.
    assert claim_id not in resolved


@pytest.mark.asyncio
async def test_multiple_claims_each_resolved_independently():
    claim_a = uuid.uuid4()
    claim_b = uuid.uuid4()
    ea = uuid.uuid4()
    eb = uuid.uuid4()
    checker = FakeNLIChecker({
        "evidence a text": _verdict(EntailmentStatus.supported, 0.95),
        "evidence b text": _verdict(EntailmentStatus.insufficient, 0.6),
    })

    resolved = await resolve_claims_via_nli(
        [
            (claim_a, "Claim A.", [(ea, "evidence a", "text")]),
            (claim_b, "Claim B.", [(eb, "evidence b", "text")]),
        ],
        checker=checker,
    )

    assert resolved[claim_a].status == EntailmentStatus.supported
    assert claim_b not in resolved  # insufficient never auto-resolves


@pytest.mark.asyncio
async def test_claim_with_no_evidence_items_is_skipped():
    claim_id = uuid.uuid4()
    checker = FakeNLIChecker({})

    resolved = await resolve_claims_via_nli(
        [(claim_id, "Claim with nothing to check.", [])],
        checker=checker,
    )

    assert claim_id not in resolved
    assert checker.calls == []
