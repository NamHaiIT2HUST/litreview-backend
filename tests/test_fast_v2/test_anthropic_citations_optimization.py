"""TDD coverage for the Citation-stage latency optimization: section-scoped
evidence, targeted (paragraph-level) retry, and configurable batch
size/concurrency. All LLM calls are mocked -- no network, no cost.
"""
import asyncio
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.synthesis.fast_v2.citations.anthropic_citations import (
    attribute_all_prose_paragraphs,
    attribute_paragraph_batch,
    build_paragraph_section_map,
    format_scoped_evidence_context,
    resolve_batch_evidence_scope,
    strip_citations,
    strip_out_of_scope_handles,
)
from src.synthesis.fast_v2.evidence.models import EvidenceUnit


def _unit(evidence_id: str, title: str, text: str) -> EvidenceUnit:
    return EvidenceUnit(
        evidence_id=evidence_id,
        paper_id=uuid.uuid4(),
        title=title,
        page=1,
        text=text,
        source_chunk_id=None,
        page_text_id=None,
    )


def _resp(content: str, output_tokens: int = 50, input_tokens: int = 100):
    r = MagicMock()
    r.content = content
    r.usage_metadata = {"output_tokens": output_tokens, "input_tokens": input_tokens}
    return r


# ---------------------------------------------------------------------------
# 1 & 2: section scoping resolution
# ---------------------------------------------------------------------------

def test_section_paragraph_receives_only_its_section_evidence():
    sections = {
        "sec_1": [_unit("ev-a", "PaperA", "text a")],
        "sec_2": [_unit("ev-b", "PaperB", "text b")],
    }
    scope = resolve_batch_evidence_scope(["sec_1", "sec_1"], sections)
    assert scope == {"ev-a"}


def test_introduction_paragraph_gets_full_union_not_single_section():
    sections = {
        "sec_1": [_unit("ev-a", "PaperA", "text a")],
        "sec_2": [_unit("ev-b", "PaperB", "text b")],
    }
    # None section id == Introduction/Conclusion/unmatched heading
    scope = resolve_batch_evidence_scope([None, None], sections)
    assert scope is None  # None scope == caller falls back to the full evidence pack


def test_batch_spanning_two_sections_unions_both():
    sections = {
        "sec_1": [_unit("ev-a", "PaperA", "text a")],
        "sec_2": [_unit("ev-b", "PaperB", "text b")],
    }
    scope = resolve_batch_evidence_scope(["sec_1", "sec_2"], sections)
    assert scope == {"ev-a", "ev-b"}


def test_batch_spanning_too_many_sections_falls_back_to_full_pack():
    sections = {f"sec_{i}": [_unit(f"ev-{i}", f"Paper{i}", "text")] for i in range(5)}
    scope = resolve_batch_evidence_scope(["sec_0", "sec_1", "sec_2", "sec_3"], sections)
    assert scope is None


def test_no_section_evidence_supplied_means_no_scoping():
    assert resolve_batch_evidence_scope(["sec_1"], None) is None


def test_paragraph_section_map_walks_back_to_nearest_matching_heading():
    blocks = [
        "# Title",
        "## Introduction",
        "intro paragraph text here that is long enough",
        "## Section 1: Foundational Formulations",
        "para under section 1 long enough to be substantive",
        "## Conclusion",
        "closing paragraph long enough to be substantive too",
    ]
    section_map = build_paragraph_section_map(blocks, [("sec_1", "Foundational Formulations")])
    assert section_map[2] is None  # under Introduction, no match
    assert section_map[4] == "sec_1"
    assert section_map[6] is None  # under Conclusion, no match


# ---------------------------------------------------------------------------
# Global handle numbering must survive scoping (property final_bound_citations
# correctness in section_pipeline.py depends on).
# ---------------------------------------------------------------------------

def test_scoped_context_preserves_global_handle_numbers():
    full = [_unit(f"ev-{i}", f"Paper{i}", f"text {i}") for i in range(5)]
    # ev-3 is globally E004 -- scoping to {ev-3} must still label it E004,
    # never renumber it to E001 for the subset.
    context_text, handles = format_scoped_evidence_context(full, {"ev-3"})
    assert handles == {"E004"}
    assert "[E004]" in context_text
    assert "text 3" in context_text
    assert "text 0" not in context_text  # excluded units are not sent


def test_scoped_context_none_returns_full_pack_with_all_global_handles():
    full = [_unit(f"ev-{i}", f"Paper{i}", f"text {i}") for i in range(3)]
    context_text, handles = format_scoped_evidence_context(full, None)
    assert handles == {"E001", "E002", "E003"}


def test_out_of_scope_handle_is_stripped_from_prose_not_just_uncounted():
    text = "Byrne (2002) proved convergence [E001, E009]."
    stripped = strip_out_of_scope_handles(text, allowed_handles={"E001"})
    assert "[E001]" in stripped
    assert "E009" not in stripped
    # prose invariant unaffected
    assert strip_citations(stripped) == strip_citations("Byrne (2002) proved convergence.")


def test_out_of_scope_handle_removes_whole_tag_when_nothing_remains():
    text = "A claim with no in-scope support [E009]."
    stripped = strip_out_of_scope_handles(text, allowed_handles={"E001"})
    assert "[E009]" not in stripped
    assert "E009" not in stripped


# ---------------------------------------------------------------------------
# 3 & 4: configurable batch size, 8 paragraphs in one batch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_batch_size_is_configurable_and_eight_paragraphs_fit_one_batch():
    paragraphs = [
        f"This is substantive paragraph number {i} with more than five words in it for sure." for i in range(8)
    ]
    draft = "\n\n".join(paragraphs)
    evidence = [_unit("ev-0", "Paper0", "supporting text")]

    xml_response = "\n".join(
        f'<paragraph id="{i}">\n{p} [E001]\n</paragraph>' for i, p in enumerate(paragraphs)
    )
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=_resp(xml_response, output_tokens=400))

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=draft, evidence=evidence, batch_size=8, concurrency=4,
    )
    assert result.telemetry.number_of_batches == 1
    assert result.telemetry.substantive_paragraphs == 8
    assert fake_llm.ainvoke.await_count == 1  # one batch, no retry needed
    assert result.overall_diff_passed is True


# ---------------------------------------------------------------------------
# 5, 6, 7: targeted retry -- only failed paragraphs resent, with correct scope
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_paragraphs_are_not_resent_on_retry():
    good = "This paragraph will pass on the very first attempt without any issue."
    bad = "This paragraph will be mutated by the model on its first attempt sadly."
    batch_items = [(0, good), (1, bad)]

    first_resp = _resp(
        f'<paragraph id="0">\n{good} [E001]\n</paragraph>\n'
        f'<paragraph id="1">\n{bad.replace("mutated", "changed")} [E001]\n</paragraph>',
        output_tokens=100,
    )
    retry_resp = _resp(f'<paragraph id="1">\n{bad} [E001]\n</paragraph>', output_tokens=30)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[first_resp, retry_resp])
    sem = asyncio.Semaphore(4)

    results_map, attempts, out_tok, in_tok = await attribute_paragraph_batch(
        llm=fake_llm, batch_items=batch_items, context_text="[E001] evidence",
        available_handles={"E001"}, sem=sem,
    )

    assert attempts == 2
    assert results_map[0][1] == "passed_first_attempt"
    assert results_map[1][1] == "passed_after_retry"
    # the retry call's human prompt must contain ONLY the failed paragraph,
    # not the already-passed one -- this is the token-saving lever.
    retry_call_args = fake_llm.ainvoke.await_args_list[1]
    retry_prompt = retry_call_args.args[0][1][1]
    assert "changed" not in retry_prompt  # first-attempt mutated text isn't resent
    assert bad in retry_prompt
    assert good not in retry_prompt


@pytest.mark.asyncio
async def test_only_failed_paragraph_appears_in_retry_payload_with_scoped_evidence():
    p0 = "Paragraph zero cites paper A with a formula and passes cleanly first try."
    p1 = "Paragraph one cites paper B and gets mutated by the model unfortunately here."
    batch_items = [(0, p0), (1, p1)]

    first_resp = _resp(
        f'<paragraph id="0">\n{p0} [E001]\n</paragraph>\n'
        f'<paragraph id="1">\n{p1.upper()} [E002]\n</paragraph>',
    )
    retry_resp = _resp(f'<paragraph id="1">\n{p1} [E002]\n</paragraph>')
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[first_resp, retry_resp])
    sem = asyncio.Semaphore(4)

    await attribute_paragraph_batch(
        llm=fake_llm, batch_items=batch_items, context_text="[E001][E002] evidence",
        available_handles={"E001", "E002"}, sem=sem,
    )
    retry_prompt = fake_llm.ainvoke.await_args_list[1].args[0][1][1]
    assert 'id="1"' in retry_prompt
    assert 'id="0"' not in retry_prompt


# ---------------------------------------------------------------------------
# 8, 9, 10, 11: safety invariants still hold with the new code paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_handles_still_rejected_with_section_scoping():
    evidence = [_unit("ev-a", "PaperA", "text a"), _unit("ev-b", "PaperB", "text b")]
    section_evidence = {"sec_1": [evidence[0]]}  # only E001 in scope for sec_1
    draft = "## Section 1: Foo\n\nThis substantive paragraph cites something specific here."

    # Model hallucinates E002, which exists globally but was never shown to this scoped batch.
    resp = _resp('<paragraph id="0">\nThis substantive paragraph cites something specific here. [E001, E002]\n</paragraph>')
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=draft, evidence=evidence, batch_size=8, concurrency=4,
        section_evidence=section_evidence, sections=[("sec_1", "Foo")],
    )
    assert result.telemetry.invalid_handles_rejected == 1
    assert result.telemetry.valid_handles == 1
    assert "E002" not in result.attributed_markdown  # stripped, not just uncounted


@pytest.mark.asyncio
async def test_prose_mutation_still_rejected_in_targeted_retry_path():
    p0 = "Some paragraph that will be mutated by the model on every single attempt sadly."
    mutated = p0.replace("mutated", "CHANGED")
    resp = _resp(f'<paragraph id="0">\n{mutated} [E001]\n</paragraph>')
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)  # same mutation both times
    sem = asyncio.Semaphore(2)

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=p0, evidence=[_unit("ev-a", "PaperA", "t")],
        batch_size=8, concurrency=2,
    )
    assert result.overall_diff_passed is True  # fail-closed keeps original prose byte-identical
    assert p0 in result.attributed_markdown
    assert "CHANGED" not in result.attributed_markdown


@pytest.mark.asyncio
async def test_latex_mutation_still_rejected():
    p0 = "The gradient is $\\nabla f(x) = A^T(I - P_Q)Ax$ which is Lipschitz continuous for sure."
    mutated = p0.replace("\\nabla", "\\Delta")
    resp = _resp(f'<paragraph id="0">\n{mutated} [E001]\n</paragraph>')
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)
    sem = asyncio.Semaphore(2)

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=p0, evidence=[_unit("ev-a", "PaperA", "t")],
        batch_size=8, concurrency=2,
    )
    assert "\\nabla" in result.attributed_markdown
    assert "\\Delta f" not in result.attributed_markdown


@pytest.mark.asyncio
async def test_failed_second_attempt_still_fails_closed():
    p0 = "This paragraph fails both the batch attempt and the single-paragraph fallback retry sadly."
    batch_resp = _resp(f'<paragraph id="0">\n{p0.upper()} [E001]\n</paragraph>')  # mutated, batch fails
    retry_resp = _resp(f'<paragraph id="0">\n{p0.upper()} [E001]\n</paragraph>')  # still mutated on batch retry
    single_resp1 = _resp(f"{p0.upper()} [E001]")  # fallback attempt 1 also mutated
    single_resp2 = _resp(f"{p0.upper()} [E001]")  # fallback attempt 2 also mutated
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[batch_resp, retry_resp, single_resp1, single_resp2])

    result = await attribute_all_prose_paragraphs(
        llm=fake_llm, draft_markdown=p0, evidence=[_unit("ev-a", "PaperA", "t")],
        batch_size=8, concurrency=2,
    )
    assert result.telemetry.failed_closed == 1
    assert p0 in result.attributed_markdown
    assert result.overall_diff_passed is True
