import asyncio
import re
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.synthesis.fast_v2.citations.anthropic_citations import (
    CITATIONS_AGENT_SYSTEM_PROMPT,
    BATCHED_CITATIONS_AGENT_SYSTEM_PROMPT,
    strip_citations,
    attribute_single_paragraph,
    attribute_paragraph_batch,
    attribute_all_prose_paragraphs,
)
from src.synthesis.fast_v2.evidence.models import EvidenceUnit

PARAGRAPH_14_TEXT = (
    "The CQ algorithm represented a paradigm shift because it connected the SFP to the well-established theory of "
    "gradient-projection methods. In fact, as Xu (2010) later demonstrated, the CQ algorithm is a special case of the "
    "gradient-projection algorithm in convex minimization. This connection enabled the application of powerful analytical "
    "tools from convex optimization, including the theory of averaged operators and nonexpansive mappings. The algorithm "
    "could be viewed as minimizing the proximity function:\n"
    "$$f(x) = \\frac{1}{2}\\|Ax - P_Q Ax\\|^2,$$\n"
    "with the constraint $x \\in C$. In this formulation, the gradient of $f$ is $\\nabla f(x) = A^T(I - P_Q)Ax$, which "
    "is $L$-Lipschitz continuous with $L = \\|A^T A\\|$. The CQ iteration is precisely the projected gradient descent step:\n"
    "$$x^{k+1} = P_C(x^k - \\gamma \\nabla f(x^k)).$$"
)


def test_strip_citations_preserves_latex_and_text_invariants():
    """Test A & E: Valid citation-only insertion into LaTeX-heavy paragraph passes invariant."""
    cited_paragraph = (
        PARAGRAPH_14_TEXT
        .replace("gradient-projection methods.", "gradient-projection methods [E001].")
        .replace("convex minimization.", "convex minimization [E002].")
        .replace("$L = \\|A^T A\\|$.", "$L = \\|A^T A\\|$ [E001].")
        + " [E002]"
    )
    assert strip_citations(PARAGRAPH_14_TEXT) == strip_citations(cited_paragraph)


def test_strip_citations_rejects_latex_token_mutation():
    """Test B: Candidate that mutates a LaTeX token (e.g. \\nabla -> \\partial) is REJECTED."""
    mutated = PARAGRAPH_14_TEXT.replace("\\nabla", "\\partial")
    cited_mutated = mutated + " [E001]"
    assert strip_citations(PARAGRAPH_14_TEXT) != strip_citations(cited_mutated)


def test_strip_citations_rejects_delimiter_mutation():
    """Test C: Candidate that mutates display delimiters ($$...$$ -> \\[...\\]) is REJECTED."""
    mutated = PARAGRAPH_14_TEXT.replace("$$", "\\[", 1).replace("$$", "\\]", 1)
    cited_mutated = mutated + " [E001]"
    assert strip_citations(PARAGRAPH_14_TEXT) != strip_citations(cited_mutated)


def test_strip_citations_rejects_prose_punctuation_or_word_mutation():
    """Test D: Candidate that alters words or punctuation is REJECTED."""
    mutated = PARAGRAPH_14_TEXT.replace("well-established", "well established")
    cited_mutated = mutated + " [E001]"
    assert strip_citations(PARAGRAPH_14_TEXT) != strip_citations(cited_mutated)

    mutated_punct = PARAGRAPH_14_TEXT.replace("convex minimization.", "convex minimization,")
    cited_punct = mutated_punct + " [E001]"
    assert strip_citations(PARAGRAPH_14_TEXT) != strip_citations(cited_punct)


@pytest.mark.asyncio
async def test_attribute_single_paragraph_retry_success():
    """Test F: First attempt mutates LaTeX token, second attempt preserves exact text + citations -> passed_after_retry."""
    sem = asyncio.Semaphore(1)
    
    # Attempt 1 mutates \nabla to \partial
    resp1 = MagicMock()
    resp1.content = PARAGRAPH_14_TEXT.replace("\\nabla", "\\partial") + " [E001]"
    resp1.usage_metadata = {"output_tokens": 150}

    # Attempt 2 corrects and preserves exact bytes + citations
    resp2 = MagicMock()
    resp2.content = PARAGRAPH_14_TEXT + " [E001]"
    resp2.usage_metadata = {"output_tokens": 150}

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[resp1, resp2])

    attr_text, p_first, p_retry, attempts, tokens, in_tokens, emitted = await attribute_single_paragraph(
        llm=fake_llm,
        paragraph=PARAGRAPH_14_TEXT,
        context_text="[E001] Byrne 2002 CQ algorithm evidence",
        available_handles={"E001"},
        sem=sem,
    )

    assert p_first is False
    assert p_retry is True
    assert attempts == 2
    assert any("E001" in tag for tag in emitted)
    assert strip_citations(attr_text) == strip_citations(PARAGRAPH_14_TEXT)


@pytest.mark.asyncio
async def test_attribute_single_paragraph_fails_closed_when_both_mutate():
    """Test G: When both attempts mutate text, fail closed and return exact original text without citations."""
    sem = asyncio.Semaphore(1)

    resp1 = MagicMock()
    resp1.content = PARAGRAPH_14_TEXT.replace("represented", "marked") + " [E001]"
    resp1.usage_metadata = {"output_tokens": 150}

    resp2 = MagicMock()
    resp2.content = PARAGRAPH_14_TEXT.replace("\\gamma", "\\lambda") + " [E001]"
    resp2.usage_metadata = {"output_tokens": 150}

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=[resp1, resp2])

    attr_text, p_first, p_retry, attempts, tokens, in_tokens, emitted = await attribute_single_paragraph(
        llm=fake_llm,
        paragraph=PARAGRAPH_14_TEXT,
        context_text="[E001] Byrne 2002 CQ algorithm evidence",
        available_handles={"E001"},
        sem=sem,
    )

    assert p_first is False
    assert p_retry is False
    assert attempts == 2
    assert emitted == []
    # Fail closed guarantees exact byte identity with original
    assert attr_text == PARAGRAPH_14_TEXT


@pytest.mark.asyncio
async def test_batch_attribution_retry_and_handles():
    """Test batch attribution with XML parsing and byte-exact verification."""
    sem = asyncio.Semaphore(1)

    batch_items = [(14, PARAGRAPH_14_TEXT)]
    
    # First response preserves exact paragraph inside XML
    resp = MagicMock()
    resp.content = f'<paragraph id="0">\n{PARAGRAPH_14_TEXT} [E001]\n</paragraph>'
    resp.usage_metadata = {"output_tokens": 200}

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=resp)

    results_map, attempts, tokens, in_tokens = await attribute_paragraph_batch(
        llm=fake_llm,
        batch_items=batch_items,
        context_text="[E001] Byrne 2002 CQ evidence",
        available_handles={"E001"},
        sem=sem,
    )

    assert 14 in results_map
    attributed_text, status, emitted = results_map[14]
    assert status == "passed_first_attempt"
    assert any("E001" in tag for tag in emitted)
    assert strip_citations(attributed_text) == strip_citations(PARAGRAPH_14_TEXT)
