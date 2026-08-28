import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.synthesis.fast_v2.planning.research_lead import (
    RESEARCH_LEAD_SYSTEM_PROMPT,
    LongformOutlinePlan,
    SectionPlan,
    _extract_json_object,
    _parse_outline,
    plan_longform_outline,
)


def test_research_lead_prompt_contains_corpus_grounding_rules():
    """Verify that the system prompt strictly instructs the LLM not to introduce
    unsupported technical concepts from outside the supplied paper abstracts/titles."""
    prompt = RESEARCH_LEAD_SYSTEM_PROMPT
    assert "STRICT CORPUS GROUNDING" in prompt
    assert "Do not introduce a specific algorithm family" in prompt
    assert "supported by the supplied skim for at least one selected paper" in prompt
    assert "PAPERS_TO_COMPARE AS SUPPORT MAPPING" in prompt
    assert "RETRIEVAL QUERIES GROUNDED IN CORPUS" in prompt
    assert "Do NOT generate speculative queries" in prompt
    assert "inertial" not in prompt.lower()
    assert "momentum" not in prompt.lower()


@pytest.mark.asyncio
async def test_plan_longform_outline_makes_exactly_one_llm_call():
    """Verify that planning executes exactly ONE LLM call (with bounded retry)
    and does not add extra verifier or sub-agent calls."""
    fake_response = MagicMock()
    fake_response.content = json.dumps({
        "research_question": "Comparative analysis of SFP stepsize strategies",
        "sections": [
            {
                "id": "sec_1",
                "title": "Self-Adaptive Projection Stepsizes",
                "purpose": "Analyze stepsize choice without prior operator norm estimation.",
                "target_words": 1000,
                "papers_to_compare": ["Li2012", "Xu2010"],
                "retrieval_queries": [
                    "Li 2012 self-adaptive stepsize split feasibility",
                    "Xu 2010 stepsize operator norm condition",
                ],
            },
            {
                "id": "sec_2",
                "title": "Averaged Operator Convergence Guarantees",
                "purpose": "Examine weak and strong convergence theorems under nonexpansive mappings.",
                "target_words": 1000,
                "papers_to_compare": ["Byrne2002", "Xu2010"],
                "retrieval_queries": [
                    "Byrne 2002 CQ algorithm convergence proof",
                    "Xu 2010 strong convergence averaged mappings",
                ],
            },
            {
                "id": "sec_3",
                "title": "Non-Convex Generalizations of Split Feasibility",
                "purpose": "Evaluate extensions to non-convex constraints and proximal gradient formulations.",
                "target_words": 1000,
                "papers_to_compare": ["Gibali2020"],
                "retrieval_queries": [
                    "non-convex split feasibility problem projection",
                    "Gibali 2020 proximal gradient convergence",
                ],
            },
            {
                "id": "sec_4",
                "title": "Majorization-Minimization and Multi-Set Formulations",
                "purpose": "Compare product space and majorization-minimization approaches.",
                "target_words": 1000,
                "papers_to_compare": ["Censor1994", "Xu2018"],
                "retrieval_queries": [
                    "Censor Elfving 1994 multi-set split feasibility",
                    "Xu 2018 majorization-minimization algorithm SFP",
                ],
            },
        ],
    })

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)

    paper_metadata = [
        {"title": "Li 2012", "abstract": "A self-adaptive projection-type method for split feasibility."},
        {"title": "Xu 2010", "abstract": "Iterative methods for SFP in Hilbert spaces using averaged operators."},
        {"title": "Byrne 2002", "abstract": "CQ algorithm for split feasibility and weak convergence."},
        {"title": "Gibali 2020", "abstract": "Nonconvex split feasibility problem via proximal gradient."},
        {"title": "Censor 1994", "abstract": "Original formulation of the split feasibility problem."},
        {"title": "Xu 2018", "abstract": "A majorization-minimization algorithm for split feasibility problems."},
    ]

    plan = await plan_longform_outline(
        llm=fake_llm,
        research_question="Comparative analysis of SFP stepsize strategies",
        paper_metadata=paper_metadata,
    )

    # Verify exactly 1 ainvoke call was made
    assert fake_llm.ainvoke.call_count == 1

    # Verify prompt contents passed to LLM
    call_args = fake_llm.ainvoke.call_args[0][0]
    system_msg = call_args[0][1]
    user_msg = call_args[1][1]

    assert "STRICT CORPUS GROUNDING" in system_msg
    assert "Li 2012" in user_msg
    assert "A self-adaptive projection-type method" in user_msg

    # Verify plan structure
    assert isinstance(plan, LongformOutlinePlan)
    assert len(plan.sections) == 4
    assert plan.sections[0].id == "sec_1"
    assert plan.sections[0].title == "Self-Adaptive Projection Stepsizes"
    assert "Li2012" in plan.sections[0].papers_to_compare
    assert len(plan.sections[0].retrieval_queries) == 2


def test_schema_and_parsing_compatibility():
    """Verify SectionPlan and LongformOutlinePlan serialization and parsing."""
    raw_json = {
        "research_question": "SFP Evolution",
        "sections": [
            {
                "id": "sec_1",
                "title": "Foundational Formulations",
                "purpose": "Trace original formulation",
                "target_words": 1000,
                "papers_to_compare": ["Censor1994", "Byrne2002"],
                "retrieval_queries": ["Censor 1994 SFP", "Byrne 2002 CQ"],
            }
        ]
    }
    plan = _parse_outline(raw_json, "SFP Evolution")
    assert len(plan.sections) == 1
    d = plan.to_dict()
    assert d["research_question"] == "SFP Evolution"
    assert len(d["sections"]) == 1
    assert d["sections"][0]["papers_to_compare"] == ["Censor1994", "Byrne2002"]
