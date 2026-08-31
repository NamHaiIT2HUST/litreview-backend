"""Final production Citation Agent fix: full-paragraph context, failure-type
telemetry (transport_timeout / transport_http_error / parse_failed /
semantic_empty_assignment are distinct, never conflated), 120s timeout,
duplicate-handle dedup, unknown-claim-id rejection. All calls mocked.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.synthesis.fast_v2.citations.anthropic_citations import (
    CITATION_BATCH_TIMEOUT_SECONDS,
    PARSE_FAILED,
    TRANSPORT_HTTP_ERROR,
    TRANSPORT_TIMEOUT,
    attribute_paragraph_batch,
)


def _resp(assignments: dict, output_tokens: int = 50, input_tokens: int = 100):
    r = MagicMock()
    r.content = json.dumps({"assignments": assignments})
    r.usage_metadata = {"output_tokens": output_tokens, "input_tokens": input_tokens}
    return r


# Test A: full paragraph is actually included in model input
@pytest.mark.asyncio
async def test_A_full_paragraph_context_included_in_prompt():
    p0 = "Xu uses A. This obtains B, referring back to A."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": ["E001"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    await attribute_paragraph_batch(llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem)
    human_msg = fake_llm.ainvoke.await_args_list[0].args[0][1][1]
    assert p0 in human_msg  # the FULL paragraph is present, not just isolated spans
    assert "full_paragraph" in human_msg


def test_timeout_is_120_seconds_not_35_or_90():
    assert CITATION_BATCH_TIMEOUT_SECONDS == 120.0


# Test C: exact offsets point into original prose
@pytest.mark.asyncio
async def test_C_claim_spans_carry_exact_char_offsets_into_original_prose():
    p0 = "Fact A. Fact B."
    resp = _resp({"p0_s0": [], "p0_s1": []})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    await attribute_paragraph_batch(llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles=set(), sem=sem)
    human_msg = fake_llm.ainvoke.await_args_list[0].args[0][1][1]
    payload = json.loads(human_msg.split("):\n", 1)[1].rsplit("\n\nReturn", 1)[0])
    spans = payload[0]["claim_spans"]
    assert spans[0]["char_start"] == 0
    assert p0[spans[0]["char_start"]:spans[0]["char_end"]] == spans[0]["text"]
    assert p0[spans[1]["char_start"]:spans[1]["char_end"]] == spans[1]["text"]


# Test N: duplicate handle inside same claim is deduplicated
@pytest.mark.asyncio
async def test_N_duplicate_handle_within_one_claim_deduplicated():
    p0 = "This claim is supported twice by the same paper."
    resp = _resp({"p0_s0": ["E001", "E001", "E001"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem)
    text, _status, emitted = results_map[0]
    assert emitted == ["[E001]"]
    assert text.count("E001") == 1


# Test L: unknown claim ID in response is rejected (ignored), not crashed on
@pytest.mark.asyncio
async def test_L_unknown_claim_id_in_response_is_rejected_not_a_crash():
    p0 = "This is the only claim in this paragraph for sure."
    resp = _resp({"p0_s0": ["E001"], "p99_s5": ["E002"]})  # p99_s5 doesn't exist
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, attempts, _out, _in, batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001", "E002"}, sem=sem,
    )
    assert "[E001]" in results_map[0][0]
    assert "E002" not in results_map[0][0]
    assert batch_record["unknown_claim_ids_rejected"] == 1


# Test X: TimeoutError -> transport_timeout, never mistaken for unsupported
@pytest.mark.asyncio
async def test_X_timeout_classified_as_transport_timeout():
    p0 = "This paragraph would have had a supportable claim."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=TimeoutError())
    sem = asyncio.Semaphore(4)

    results_map, attempts, _out, _in, batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles=set(), sem=sem,
    )
    assert batch_record["failure_type"] == TRANSPORT_TIMEOUT
    assert batch_record["timeout_flag"] is True
    assert results_map[0][1] == "failed_closed_kept_uncited"


# Test Y: HTTP/transport error -> transport_http_error, distinct from timeout
@pytest.mark.asyncio
async def test_Y_http_error_classified_as_transport_http_error_not_timeout():
    p0 = "This paragraph would have had a supportable claim too."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=RuntimeError("HTTP 429 rate limited"))
    sem = asyncio.Semaphore(4)

    results_map, attempts, _out, _in, batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles=set(), sem=sem,
    )
    assert batch_record["failure_type"] == TRANSPORT_HTTP_ERROR
    assert batch_record["timeout_flag"] is False


# Test AA: JSON parse failure distinct from transport failure
@pytest.mark.asyncio
async def test_AA_parse_failure_distinct_from_transport_failure():
    p0 = "This paragraph gets a syntactically broken response."
    bad_resp = MagicMock()
    bad_resp.content = "not json at all"
    bad_resp.usage_metadata = {"output_tokens": 5, "input_tokens": 20}
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=bad_resp)
    sem = asyncio.Semaphore(4)

    results_map, attempts, _out, _in, batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles=set(), sem=sem,
    )
    assert batch_record["failure_type"] == PARSE_FAILED
    assert batch_record["failure_type"] != TRANSPORT_TIMEOUT
    assert batch_record["failure_type"] != TRANSPORT_HTTP_ERROR


# Test Z: a valid [] assignment is semantic_empty_assignment, NOT failed_closed
@pytest.mark.asyncio
async def test_Z_valid_empty_assignment_is_semantic_not_failed_closed():
    p0 = "This claim genuinely has no supporting evidence in scope."
    resp = _resp({"p0_s0": []})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, attempts, _out, _in, batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles=set(), sem=sem,
    )
    assert results_map[0][1] == "passed_first_attempt"  # NOT failed_closed_kept_uncited
    assert batch_record["failure_type"] is None
    assert batch_record["semantic_empty_assignments"] == 1


# Test M: missing assignment (claim_id never returned) becomes explicit []
@pytest.mark.asyncio
async def test_M_missing_assignment_becomes_explicit_empty_not_omitted():
    p0 = "Sentence one is here. Sentence two is here too."
    resp = _resp({"p0_s0": ["E001"]})  # p0_s1 never mentioned by the model
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem)
    text, status, _emitted = results_map[0]
    assert status == "passed_first_attempt"
    assert "Sentence one is here. [E001]" in text
    assert text.rstrip().endswith("Sentence two is here too.")


# Test O/P: multiple citations inserted into the same paragraph preserve
# offsets regardless of insertion order (ascending cursor-based construction,
# not offset-shifting insertion -- equivalent guarantee, different mechanism).
@pytest.mark.asyncio
async def test_OP_multiple_insertions_preserve_all_offsets_correctly():
    p0 = "First claim here. Second claim here. Third claim here."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": ["E002"], "p0_s2": ["E003"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001", "E002", "E003"}, sem=sem)
    text, _status, _emitted = results_map[0]
    assert text == "First claim here. [E001] Second claim here. [E002] Third claim here. [E003]"


# AB/AC/AD/AE: batching/concurrency/no-extra-calls preserved
@pytest.mark.asyncio
async def test_AB_AD_batch_is_one_call_for_multiple_paragraphs_no_per_sentence_calls():
    p0, p1, p2 = "Para zero claim.", "Para one claim.", "Para two claim."
    resp = _resp({"p0_s0": ["E001"], "p1_s0": ["E002"], "p2_s0": []})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(6)  # AC: concurrency 6 preserved at call site (section_pipeline.py default)

    results_map, attempts, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0), (1, p1), (2, p2)], context_text="pack",
        available_handles={"E001", "E002"}, sem=sem,
    )
    assert fake_llm.ainvoke.await_count == 1
    assert attempts == 1


def test_batch_record_contains_all_required_telemetry_fields():
    required = {
        "batch_id", "section_id", "paragraph_ids", "paragraph_count", "claim_count",
        "evidence_count", "input_tokens", "output_tokens", "attempt_number",
        "provider_latency_seconds", "result_status", "failure_type", "timeout_flag",
        "invalid_assignment_entries", "unknown_claim_ids_rejected", "semantic_empty_assignments",
    }

    async def _run():
        fake_llm = MagicMock()
        fake_llm.ainvoke = AsyncMock(return_value=_resp({"p0_s0": ["E001"]}))
        sem = asyncio.Semaphore(4)
        _r, _a, _o, _i, batch_record = await attribute_paragraph_batch(
            llm=fake_llm, batch_items=[(0, "This is a single test claim right here.")],
            context_text="pack", available_handles={"E001"}, sem=sem, section_id="sec_1", batch_id=3,
        )
        return batch_record

    batch_record = asyncio.run(_run())
    assert required.issubset(batch_record.keys())
    assert batch_record["batch_id"] == 3
    assert batch_record["section_id"] == "sec_1"
