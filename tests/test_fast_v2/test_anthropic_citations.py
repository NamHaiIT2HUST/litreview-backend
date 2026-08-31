"""Structured, span-level citation attribution: the LLM never sees or
reproduces paragraph prose (see anthropic_citations.py module docstring
for the real-run failure -- an em-dash whitespace mutation -- that this
design eliminates by construction). All model calls are mocked; no
network/real model calls in this file.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.synthesis.fast_v2.citations.anthropic_citations import (
    STRUCTURED_CITATION_SYSTEM_PROMPT,
    attribute_all_prose_paragraphs,
    attribute_paragraph_batch,
    format_scoped_evidence_context,
    insert_citations_at_spans,
    resolve_batch_evidence_scope,
    split_paragraph_into_spans,
    strip_citations,
    strip_out_of_scope_handles,
)
from src.synthesis.fast_v2.evidence.models import EvidenceUnit

PARAGRAPH_CQ = (
    "The CQ algorithm represented a paradigm shift because it connected the SFP to the well-established theory of "
    "gradient-projection methods. In fact, as Xu (2010) later demonstrated, the CQ algorithm is a special case of the "
    "gradient-projection algorithm in convex minimization. The algorithm could be viewed as minimizing the proximity function:\n"
    "$$f(x) = \\frac{1}{2}\\|Ax - P_Q Ax\\|^2,$$\n"
    "with the constraint $x \\in C$. The CQ iteration is precisely the projected gradient descent step:\n"
    "$$x^{k+1} = P_C(x^k - \\gamma \\nabla f(x^k)).$$"
)


def _unit(evidence_id: str, title: str, text: str) -> EvidenceUnit:
    return EvidenceUnit(evidence_id=evidence_id, paper_id=uuid.uuid4(), title=title, page=1,
                         text=text, source_chunk_id=None, page_text_id=None)


def _resp(assignments: dict, output_tokens: int = 50, input_tokens: int = 100):
    r = MagicMock()
    r.content = json.dumps({"assignments": assignments})
    r.usage_metadata = {"output_tokens": output_tokens, "input_tokens": input_tokens}
    return r


def _malformed_resp():
    r = MagicMock()
    r.content = "not json at all"
    r.usage_metadata = {"output_tokens": 5, "input_tokens": 20}
    return r


# ---------------------------------------------------------------------------
# Span splitting / deterministic insertion (the structural core)
# ---------------------------------------------------------------------------

def test_split_paragraph_into_spans_covers_two_sentences():
    p = "Xu uses A. This obtains B."
    spans = split_paragraph_into_spans(p)
    assert [t.strip() for _s, _e, t in spans] == ["Xu uses A.", "This obtains B."]


def test_split_preserves_latex_formula_as_one_span_not_broken_mid_formula():
    spans = split_paragraph_into_spans(PARAGRAPH_CQ)
    "".join(PARAGRAPH_CQ[s:e] for s, e, _t in spans)
    # every span's raw slice must be a verbatim substring of the original
    for start, end, text in spans:
        assert PARAGRAPH_CQ[start:end] == text


def test_insert_citations_at_spans_is_identity_with_no_handles():  # test A (construction proof)
    p = "Xu uses A. This obtains B."
    spans = split_paragraph_into_spans(p)
    out = insert_citations_at_spans(p, spans, [[] for _ in spans])
    assert out == p


def test_insert_citations_at_spans_places_marker_right_after_span_end():
    p = "Xu uses A. This obtains B."
    spans = split_paragraph_into_spans(p)
    out = insert_citations_at_spans(p, spans, [["E001"], ["E002", "E003"]])
    assert out == "Xu uses A. [E001] This obtains B. [E002, E003]"


def test_insert_citations_never_touches_text_outside_insertion_points():
    out = insert_citations_at_spans(PARAGRAPH_CQ, split_paragraph_into_spans(PARAGRAPH_CQ),
                                     [[] for _ in split_paragraph_into_spans(PARAGRAPH_CQ)])
    assert out == PARAGRAPH_CQ
    assert "\\frac{1}{2}\\|Ax - P_Q Ax\\|^2" in out


# ---------------------------------------------------------------------------
# A. Two factual sentences with different evidence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_A_two_factual_sentences_get_different_evidence_assignments():
    p0 = "Xu uses gradient descent. Li instead uses a fixed-point iteration."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": ["E002"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, attempts, out_tok, in_tok, _batch_record = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="evidence pack", available_handles={"E001", "E002"}, sem=sem,
    )
    text, status, emitted = results_map[0]
    assert text == "Xu uses gradient descent. [E001] Li instead uses a fixed-point iteration. [E002]"
    assert status == "passed_first_attempt"
    assert attempts == 1
    assert fake_llm.ainvoke.await_count == 1  # test J: no extra LLM request


# ---------------------------------------------------------------------------
# B. Same evidence supports adjacent sentences
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_B_same_evidence_can_support_adjacent_sentences_unambiguously():
    p0 = "The model uses gradient descent. It converges under Lipschitz continuity."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": ["E001"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, _status, _emitted = results_map[0]
    assert text == "The model uses gradient descent. [E001] It converges under Lipschitz continuity. [E001]"


# ---------------------------------------------------------------------------
# C. Factual sentence + discourse/transition sentence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_C_discourse_sentence_gets_empty_list_only_factual_cited():
    p0 = "Byrne (2002) introduces the CQ algorithm. This connection enabled powerful analytical tools."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": []})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, _status, _emitted = results_map[0]
    assert text == "Byrne (2002) introduces the CQ algorithm. [E001] This connection enabled powerful analytical tools."


# ---------------------------------------------------------------------------
# D. Multi-paper comparison sentence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_D_multi_paper_comparison_cites_both_papers():
    p0 = "Unlike Li, who uses a fixed-point scheme, Xu removes the bounded-domain assumption entirely."
    resp = _resp({"p0_s0": ["E001", "E002"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001", "E002"}, sem=sem,
    )
    text, _status, emitted = results_map[0]
    assert "[E001, E002]" in text
    assert emitted == ["[E001, E002]"]


# ---------------------------------------------------------------------------
# E. Multi-sentence paragraph, one sentence unsupported -- must not borrow
# a neighboring citation.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_E_unsupported_sentence_stays_uncited_not_hidden_by_neighbors():
    p0 = "Xu proves weak convergence. This later approach also removes the bounded-domain assumption."
    resp = _resp({"p0_s0": ["E001"], "p0_s1": []})  # second sentence genuinely unsupported
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, _status, _emitted = results_map[0]
    assert "weak convergence. [E001]" in text
    assert text.rstrip().endswith("bounded-domain assumption.")
    assert "bounded-domain assumption. [E" not in text


# ---------------------------------------------------------------------------
# F. LaTeX/equations preserved exactly (structural guarantee, not a retry)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_F_latex_preserved_exactly_by_construction():
    spans = split_paragraph_into_spans(PARAGRAPH_CQ)
    assignments = {f"p0_s{i}": (["E001"] if i == 0 else []) for i in range(len(spans))}
    resp = _resp(assignments)
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, PARAGRAPH_CQ)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, _status, _emitted = results_map[0]
    assert "\\frac{1}{2}\\|Ax - P_Q Ax\\|^2" in text
    assert "x^{k+1} = P_C(x^k - \\gamma \\nabla f(x^k))" in text
    assert strip_citations(text) == strip_citations(PARAGRAPH_CQ)


# ---------------------------------------------------------------------------
# G. invalid/out-of-scope handles rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_G_out_of_scope_and_invalid_handles_rejected_end_to_end():
    evidence = [_unit("ev-a", "PaperA", "text a"), _unit("ev-b", "PaperB", "text b")]
    section_evidence = {"sec_1": [evidence[0]]}  # only E001 in scope for sec_1
    draft = "## Section 1: Foo\n\nThis substantive claim cites something specific here."
    resp = _resp({"p0_s0": ["E001", "E002", "E999"]})  # E002 out-of-scope, E999 never exists
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=draft, evidence=evidence, batch_size=8, concurrency=4,
        section_evidence=section_evidence, sections=[("sec_1", "Foo")],
    )
    assert result.telemetry.valid_handles == 1
    assert result.telemetry.out_of_scope_handles_rejected == 1
    assert result.telemetry.invalid_handles_rejected == 1
    assert "E002" not in result.attributed_markdown
    assert "E999" not in result.attributed_markdown
    assert "[E001]" in result.attributed_markdown


# ---------------------------------------------------------------------------
# H. Batched behavior preserved: multiple paragraphs, one call, span ids
# stay scoped per-paragraph (p{local_id}_s{n})
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_H_batch_of_multiple_paragraphs_one_call_correct_span_routing():
    p0 = "Paragraph zero makes claim A."
    p1 = "Paragraph one makes claim B."
    resp = _resp({"p0_s0": ["E001"], "p1_s0": ["E002"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, attempts, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0), (1, p1)], context_text="pack",
        available_handles={"E001", "E002"}, sem=sem,
    )
    assert fake_llm.ainvoke.await_count == 1
    assert "[E001]" in results_map[0][0]
    assert "[E002]" in results_map[1][0]
    assert "[E001]" not in results_map[1][0]
    assert "[E002]" not in results_map[0][0]


@pytest.mark.asyncio
async def test_batch_size_is_configurable_and_reflected_in_number_of_batches():
    paragraphs = [f"This is substantive paragraph number {i} with more than five words for sure." for i in range(8)]
    draft = "\n\n".join(paragraphs)
    evidence = [_unit("ev-0", "Paper0", "supporting text")]
    resp = _resp({f"p{i}_s0": ["E001"] for i in range(8)})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=draft, evidence=evidence, batch_size=8, concurrency=4,
    )
    assert result.telemetry.number_of_batches == 1
    assert fake_llm.ainvoke.await_count == 1


# ---------------------------------------------------------------------------
# I. empty section / single-section paths still work
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_batch_never_touches_the_model():
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock()
    result = await attribute_all_prose_paragraphs(llm=fake_llm, draft_markdown="", evidence=[], batch_size=8, concurrency=4)
    assert fake_llm.ainvoke.await_count == 0
    assert result.overall_diff_passed is True


@pytest.mark.asyncio
async def test_single_paragraph_path_still_works():
    p0 = "This is a single substantive paragraph with one supported claim."
    resp = _resp({"p0_s0": ["E001"]})
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    evidence = [_unit("ev-1", "PaperA", "t1")]

    result = await attribute_all_prose_paragraphs(llm=fake_llm, draft_markdown=p0, evidence=evidence, batch_size=8, concurrency=4)
    assert result.overall_diff_passed is True
    assert "[E001]" in result.attributed_markdown
    assert result.telemetry.passed_first_attempt == 1


# ---------------------------------------------------------------------------
# J. no extra LLM request introduced (already asserted inline above); plus
# malformed-JSON retry-then-fail-closed-safe behavior.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_malformed_json_retries_once_then_succeeds():
    p0 = "This paragraph has one factual claim in it for sure."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[_malformed_resp(), _resp({"p0_s0": ["E001"]})])
    sem = asyncio.Semaphore(4)

    results_map, attempts, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    assert attempts == 2
    assert fake_llm.ainvoke.await_count == 2
    text, status, _emitted = results_map[0]
    assert status == "passed_after_retry"
    assert "[E001]" in text


@pytest.mark.asyncio
async def test_malformed_json_both_attempts_fails_closed_prose_unchanged_not_hidden():
    p0 = "This paragraph has one factual claim that will end up uncited."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[_malformed_resp(), _malformed_resp()])
    sem = asyncio.Semaphore(4)

    results_map, attempts, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    assert attempts == 2
    assert fake_llm.ainvoke.await_count == 2
    text, status, emitted = results_map[0]
    assert status == "failed_closed_kept_uncited"
    assert text == p0  # byte-identical, by construction -- nothing was ever mutated
    assert emitted == []


@pytest.mark.asyncio
async def test_inference_transport_failure_surfaced_as_fail_closed_not_raised():
    p0 = "This paragraph has one factual claim in it for testing failure."
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=RuntimeError("network down"))
    sem = asyncio.Semaphore(4)

    results_map, attempts, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, status, emitted = results_map[0]
    assert status == "failed_closed_kept_uncited"
    assert text == p0
    assert emitted == []


# ---------------------------------------------------------------------------
# Missing span id in response defaults to unsupported ([]), never crashes,
# never invents a citation.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_span_id_in_response_defaults_to_uncited_not_a_crash():
    p0 = "Sentence one is here. Sentence two is here too."
    resp = _resp({"p0_s0": ["E001"]})  # p0_s1 omitted entirely
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(4)

    results_map, *_ = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=[(0, p0)], context_text="pack", available_handles={"E001"}, sem=sem,
    )
    text, status, _emitted = results_map[0]
    assert status == "passed_first_attempt"
    assert "Sentence one is here. [E001]" in text
    assert text.rstrip().endswith("Sentence two is here too.")


# ---------------------------------------------------------------------------
# Section-scoped evidence + global handle numbering still integrate
# correctly through the structured path (regression from the batching/
# scoping optimization work).
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_section_scoping_and_global_handle_numbers_preserved():
    evidence = [_unit(f"ev-{i}", f"Paper{i}", f"text {i}") for i in range(4)]
    section_evidence = {"sec_1": [evidence[2]]}  # evidence[2] is globally E003
    context_text, handles = format_scoped_evidence_context(evidence, {"ev-2"})
    assert handles == {"E003"}
    assert "[E003]" in context_text

    scope = resolve_batch_evidence_scope(["sec_1"], section_evidence)
    assert scope == {"ev-2"}


# ---------------------------------------------------------------------------
# Local retrieval, global provenance (claim_034/Chu audit fix): a section
# may cite evidence retrieval selected for a DIFFERENT section, as long as
# that evidence's paper is listed in THIS section's own papers_to_compare.
# An unrelated paper's evidence from another section must still be excluded.
# ---------------------------------------------------------------------------

def test_same_paper_evidence_from_another_section_is_now_in_scope_the_chu_case():
    chu_limitation = _unit("ev-chu-limit", "Chu", "single-location design restricts generalizability")
    chu_abstract = _unit("ev-chu-abstract", "Chu", "background and methods abstract")
    unrelated = _unit("ev-other-paper", "SomeOtherPaper", "unrelated methodology text")

    # sec_4/sec_5 retrieved the Chu limitation passage; sec_6 only got Chu's
    # abstract in its own top-8, plus an unrelated paper's evidence.
    section_evidence = {
        "sec_4": [chu_limitation],
        "sec_5": [chu_limitation],
        "sec_6": [chu_abstract, unrelated],
    }
    section_papers_to_compare = {
        "sec_6": ["Chu", "Wang"],  # Chu is a listed paper for sec_6; SomeOtherPaper's origin is irrelevant here
    }

    scope = resolve_batch_evidence_scope(["sec_6"], section_evidence, section_papers_to_compare)

    assert "ev-chu-limit" in scope  # now reachable: same paper (Chu), listed in sec_6's papers_to_compare
    assert "ev-chu-abstract" in scope  # sec_6's own evidence, unaffected
    assert "ev-other-paper" in scope  # sec_6's own evidence, unaffected (not filtered out either)


def test_unrelated_paper_evidence_from_another_section_stays_excluded():
    chu_limitation = _unit("ev-chu-limit", "Chu", "single-location design restricts generalizability")
    section_evidence = {
        "sec_4": [chu_limitation],
        "sec_6": [],
    }
    # Chu is NOT in sec_6's papers_to_compare (e.g. the Wu case: paper never
    # targeted for this section at all) -- must stay excluded, not widened.
    section_papers_to_compare = {"sec_6": ["Wang", "Liu"]}

    scope = resolve_batch_evidence_scope(["sec_6"], section_evidence, section_papers_to_compare)

    assert "ev-chu-limit" not in scope


def test_no_papers_to_compare_supplied_keeps_old_strict_section_only_behavior():
    chu_limitation = _unit("ev-chu-limit", "Chu", "single-location design restricts generalizability")
    section_evidence = {"sec_4": [chu_limitation], "sec_6": []}

    scope = resolve_batch_evidence_scope(["sec_6"], section_evidence, None)

    assert scope == set()  # omitting the new param reproduces the original strict behavior exactly


def test_prompt_declares_structured_json_only_no_prose_reproduction():
    assert "NEVER reproduce, rewrite, paraphrase, normalize, or output any part of the paragraph prose" in STRUCTURED_CITATION_SYSTEM_PROMPT
    assert '"assignments"' in STRUCTURED_CITATION_SYSTEM_PROMPT


def test_strip_out_of_scope_handles_still_works_as_defensive_layer():
    text = "Some claim [E001, E999]."
    assert strip_out_of_scope_handles(text, {"E001"}) == "Some claim [E001]."
