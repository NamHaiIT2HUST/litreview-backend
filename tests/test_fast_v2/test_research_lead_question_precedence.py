"""TDD coverage for research_question precedence in plan_longform_outline:
a non-empty user-supplied question is authoritative and must never be
silently overwritten by whatever the Planner echoes/rewords in its own
JSON response; an empty/None user question falls back to the Planner's
own generated question; both empty is a clear failure, never a fabricated
generic fallback topic.
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.synthesis.fast_v2.planning.research_lead import plan_longform_outline

_VALID_SECTIONS = [
    {
        "id": "sec_1",
        "title": "Foundational Formulations",
        "purpose": "Trace the original problem formulation across the corpus.",
        "target_words": 1000,
        "papers_to_compare": ["PaperA"],
        "retrieval_queries": ["query one", "query two"],
    },
]


def _fake_llm(response_json: dict):
    fake_response = MagicMock()
    fake_response.content = json.dumps(response_json)
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)
    return fake_llm


@pytest.mark.asyncio
async def test_nonempty_user_question_wins_over_llm_generated_question():
    """The Planner may echo a DIFFERENT (reworded) research_question in its
    JSON -- the user's exact input must win regardless."""
    llm = _fake_llm({
        "research_question": "A completely different, LLM-reworded question",
        "sections": _VALID_SECTIONS,
    })
    plan = await plan_longform_outline(
        llm=llm, research_question="Exact user question, byte for byte",
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    assert plan.research_question == "Exact user question, byte for byte"


@pytest.mark.asyncio
async def test_empty_string_user_question_uses_llm_generated_question():
    llm = _fake_llm({
        "research_question": "Planner-derived question from the corpus skim",
        "sections": _VALID_SECTIONS,
    })
    plan = await plan_longform_outline(
        llm=llm, research_question="",
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    assert plan.research_question == "Planner-derived question from the corpus skim"


@pytest.mark.asyncio
async def test_null_user_question_uses_llm_generated_question():
    llm = _fake_llm({
        "research_question": "Planner-derived question from the corpus skim",
        "sections": _VALID_SECTIONS,
    })
    plan = await plan_longform_outline(
        llm=llm, research_question=None,
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    assert plan.research_question == "Planner-derived question from the corpus skim"


@pytest.mark.asyncio
async def test_whitespace_only_user_question_treated_as_empty():
    llm = _fake_llm({
        "research_question": "Planner-derived question from the corpus skim",
        "sections": _VALID_SECTIONS,
    })
    plan = await plan_longform_outline(
        llm=llm, research_question="   \n  ",
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    assert plan.research_question == "Planner-derived question from the corpus skim"


@pytest.mark.asyncio
async def test_both_missing_raises_explicit_error_not_a_generic_fallback():
    llm = _fake_llm({
        "research_question": "",
        "sections": _VALID_SECTIONS,
    })
    with pytest.raises(ValueError, match="research_question"):
        await plan_longform_outline(
            llm=llm, research_question=None,
            paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
        )


@pytest.mark.asyncio
async def test_both_missing_when_llm_omits_the_field_entirely_also_raises():
    llm = _fake_llm({"sections": _VALID_SECTIONS})  # no research_question key at all
    with pytest.raises(ValueError, match="research_question"):
        await plan_longform_outline(
            llm=llm, research_question="",
            paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
        )


@pytest.mark.asyncio
async def test_still_exactly_one_planner_llm_call_regardless_of_question_source():
    llm = _fake_llm({
        "research_question": "Planner-derived question",
        "sections": _VALID_SECTIONS,
    })
    await plan_longform_outline(
        llm=llm, research_question=None,
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    assert llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_empty_question_prompt_asks_planner_to_derive_one():
    llm = _fake_llm({
        "research_question": "Planner-derived question",
        "sections": _VALID_SECTIONS,
    })
    await plan_longform_outline(
        llm=llm, research_question="",
        paper_metadata=[{"title": "PaperA", "abstract": "abstract text"}],
    )
    user_msg = llm.ainvoke.call_args[0][0][1][1]
    assert "Derive a specific, comparative research question" in user_msg
