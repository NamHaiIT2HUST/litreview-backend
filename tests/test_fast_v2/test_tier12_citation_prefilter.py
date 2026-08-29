"""Tier 1 (deterministic near-verbatim match) + Tier 2 (local NLI
cross-encoder) pre-filter, wired into fast_v2's real Citation Agent
(anthropic_citations.py) so the UI's actual synthesis pipeline benefits from
Module 1, not just the Legacy `cross_paper_analysis()` path. Settings-gated
(NLI_EVIDENCE_ENABLED) and coverage-preserving: an unresolved/contradicted
span always still reaches the LLM exactly as it would with the flag off.
"""
from __future__ import annotations

import asyncio
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.synthesis_schemas import EntailmentStatus
from src.services.nli_checker import NLIModelUnavailableError, NLIVerdict
from src.synthesis.fast_v2.citations import anthropic_citations as m
from src.synthesis.fast_v2.evidence.models import EvidenceUnit


def _unit(evidence_id: str, text: str) -> EvidenceUnit:
    return EvidenceUnit(evidence_id=evidence_id, paper_id=uuid.uuid4(), title="Paper",
                         page=1, text=text, source_chunk_id=None, page_text_id=None)


def _resp(assignments: dict, output_tokens: int = 10, input_tokens: int = 20):
    r = MagicMock()
    r.content = json.dumps({"assignments": assignments})
    r.usage_metadata = {"output_tokens": output_tokens, "input_tokens": input_tokens}
    return r


class FakeNLIChecker:
    """Same shape as tests/test_services/test_nli_checker.py's double: scripted
    verdicts keyed by the exact premise string check_many receives."""

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


# ---------------------------------------------------------------------------
# _resolve_tier12_assignments (unit-level, no LLM/batch machinery involved)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier1_near_verbatim_match_resolves_without_touching_nli():
    handle_to_unit = {"E001": _unit("ev-1", "The CQ algorithm converges under a Lipschitz condition on the gradient.")}
    span_texts = {"p0_s0": "The CQ algorithm converges under a Lipschitz condition on the gradient."}
    checker = FakeNLIChecker({})  # would KeyError if Tier 2 were reached

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=checker)

    assert resolved == {"p0_s0": ["E001"]}
    assert checker.calls == []  # Tier 1 settled it; Tier 2 never ran


@pytest.mark.asyncio
async def test_tier2_high_confidence_support_resolves_when_tier1_misses():
    handle_to_unit = {"E001": _unit("ev-1", "Gradient projection methods guarantee convergence.")}
    span_texts = {"p0_s0": "The method is guaranteed to converge."}  # not a verbatim match
    checker = FakeNLIChecker({
        "Gradient projection methods guarantee convergence. ": _verdict(EntailmentStatus.supported, 0.9),
    })

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=checker)

    assert resolved == {"p0_s0": ["E001"]}


@pytest.mark.asyncio
async def test_unresolved_span_is_left_out_for_tier3_llm():
    handle_to_unit = {"E001": _unit("ev-1", "Unrelated evidence about a different topic entirely.")}
    span_texts = {"p0_s0": "The method is guaranteed to converge."}
    checker = FakeNLIChecker({
        "Unrelated evidence about a different topic entirely. ": _verdict(EntailmentStatus.insufficient, 0.6),
    })

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=checker)

    assert resolved == {}


@pytest.mark.asyncio
async def test_contradicted_verdict_never_auto_assigns_a_handle():
    handle_to_unit = {"E001": _unit("ev-1", "The method is known to diverge under these conditions.")}
    span_texts = {"p0_s0": "The method is guaranteed to converge."}
    checker = FakeNLIChecker({
        "The method is known to diverge under these conditions. ": _verdict(EntailmentStatus.contradicted, 0.9),
    })

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=checker)

    assert resolved == {}  # Tier 1/2 only ever settles SUPPORT; contradiction falls through to Tier 3


@pytest.mark.asyncio
async def test_nli_model_unavailable_falls_through_gracefully():
    handle_to_unit = {"E001": _unit("ev-1", "Some evidence text that is not a verbatim match.")}
    span_texts = {"p0_s0": "A claim sentence."}

    class RaisingChecker:
        async def check_many(self, pairs):
            raise NLIModelUnavailableError("no checkpoint")

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=RaisingChecker())

    assert resolved == {}


@pytest.mark.asyncio
async def test_tier2_skipped_when_evidence_scope_exceeds_max(monkeypatch):
    monkeypatch.setattr(m, "TIER2_MAX_EVIDENCE_PER_BATCH", 1)
    handle_to_unit = {
        "E001": _unit("ev-1", "First unrelated evidence text."),
        "E002": _unit("ev-2", "Second unrelated evidence text."),
    }
    span_texts = {"p0_s0": "A claim that matches nothing verbatim."}
    checker = FakeNLIChecker({})  # would KeyError if Tier 2 ran

    resolved = await m._resolve_tier12_assignments(span_texts, handle_to_unit, checker=checker)

    assert resolved == {}
    assert checker.calls == []


# ---------------------------------------------------------------------------
# attribute_paragraph_batch end-to-end: settings-gated wiring + LLM-skip
# ---------------------------------------------------------------------------

class _Settings:
    def __init__(self, enabled: bool):
        self.nli_evidence_enabled = enabled


@pytest.mark.asyncio
async def test_flag_off_never_calls_tier12_and_behaves_exactly_as_before(monkeypatch):
    monkeypatch.setattr(m, "get_settings", lambda: _Settings(False))
    p0 = "The CQ algorithm converges under a Lipschitz condition on the gradient."
    resp = _resp({"p0_s0": ["E001"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)
    handle_to_unit = {"E001": _unit("ev-1", p0)}  # would Tier-1-match if the flag were on

    results_map, attempts, *_ = await m.attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"},
        sem=sem, handle_to_unit=handle_to_unit,
    )

    text, status, _emitted = results_map[0]
    assert text == f"{p0} [E001]"
    assert fake_llm.ainvoke.await_count == 1  # still went through the LLM, unchanged


@pytest.mark.asyncio
async def test_tier1_resolved_span_skips_llm_call_entirely_when_batch_fully_resolved(monkeypatch):
    monkeypatch.setattr(m, "get_settings", lambda: _Settings(True))
    p0 = "The CQ algorithm converges under a Lipschitz condition on the gradient."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=AssertionError("LLM should not be called"))
    sem = asyncio.Semaphore(4)
    handle_to_unit = {"E001": _unit("ev-1", p0)}

    results_map, attempts, out_tok, in_tok, batch_record = await m.attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"},
        sem=sem, handle_to_unit=handle_to_unit,
    )

    text, status, emitted = results_map[0]
    assert text == f"{p0} [E001]"
    assert status == "passed_first_attempt"
    assert fake_llm.ainvoke.await_count == 0
    assert batch_record["llm_call_skipped"] is True
    assert batch_record["tier1_2_resolved_claims"] == 1


@pytest.mark.asyncio
async def test_partial_tier1_resolution_only_sends_remaining_spans_to_llm(monkeypatch):
    monkeypatch.setattr(m, "get_settings", lambda: _Settings(True))
    p0 = "The CQ algorithm converges under a Lipschitz condition. It generalizes prior work."
    resp = _resp({"p0_s1": ["E002"]})  # LLM only ever sees/answers for the unresolved span
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)
    handle_to_unit = {
        "E001": _unit("ev-1", "The CQ algorithm converges under a Lipschitz condition."),
        "E002": _unit("ev-2", "Something about generalizing prior work."),
    }
    checker = FakeNLIChecker({
        "The CQ algorithm converges under a Lipschitz condition. ": _verdict(EntailmentStatus.insufficient, 0.5),
        "Something about generalizing prior work. ": _verdict(EntailmentStatus.insufficient, 0.5),
    })

    results_map, attempts, *_ = await m.attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001", "E002"},
        sem=sem, handle_to_unit=handle_to_unit, nli_checker_override=checker,
    )

    text, status, emitted = results_map[0]
    assert text == (
        "The CQ algorithm converges under a Lipschitz condition. [E001] It generalizes prior work. [E002]"
    )
    assert fake_llm.ainvoke.await_count == 1
    human_prompt = fake_llm.ainvoke.await_args.args[0][1][1]
    # only the unresolved span ("It generalizes prior work.") was sent to the LLM
    assert '"claim_id": "p0_s1"' in human_prompt
    assert '"claim_id": "p0_s0"' not in human_prompt
