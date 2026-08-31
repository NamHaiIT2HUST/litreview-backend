"""Fast v2 question-facet detection and standalone facet-aware dimension queries.

Two failures observed in the first real product E2E
(``scratch/fast_v2_parity_results/e2e_real_backend_diagnostic.md``, not
committed) are addressed here, deliberately kept separate from everything
already validated:

1. **Wrong dimension list.** The real-product wiring reused Legacy's fixed
   ``EvidenceDimension`` taxonomy (objective/method/dataset/evaluation/
   findings/limitations/future_work) as the fast_v2 "dimensions" for every
   question, regardless of what the question actually asked about. When a
   question names its own comparison facets ("...in their formulations...,
   algorithmic strategies, assumptions, and convergence guarantees"), fast_v2
   should retrieve against THOSE facets, not an unrelated generic taxonomy
   that has nothing to do with the question.

2. **Too-generic dimension queries.** ``DeterministicDimensionQueryPlanner``
   (``dimensions/planner.py``) is still correct and untouched -- it builds a
   standalone (non-v0) query, just from the bare dimension label alone
   (``"{dimension}"``). That is fine for a short, already-specific dimension
   label, but a bare word like "method" or "objective" does not discriminate
   between two similar papers on a comparison question -- the reranker ends
   up preferring whichever paper's text is most generically about that
   single word, and it can sweep every facet for one paper. This module adds
   entity/topic context (extracted from the question, never hardcoded) to
   each facet query without ever concatenating the full question -- that is
   exactly the validated v0 failure mode (RQ1 off-diagonal cosine similarity
   0.987, RQ2 0.988; see ``dimensions/planner.py`` module docstring) and this
   module must never reproduce it.

Both facet detection and query construction are deterministic, CPU-only, and
never call an LLM. Neither hardcodes a benchmark question, a paper id, or a
paper-specific term (CQ/MM/quasi-Newton/etc) -- only a small generic
scientific-facet lexicon and expansion vocabulary, plus whatever entities/
topic the actual input question contains. Comparative scopes use selected
paper IDs as identity; entity strings need not occur in chunk text.
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Sequence

from src.synthesis.fast_v2.dimensions.planner import DimensionQuery

#: Canonical facet -> trigger phrases that map onto it, longest/most-specific
#: phrase first so multi-word triggers win over a shorter substring.
FACET_LEXICON: dict[str, tuple[str, ...]] = {
    "formulation": (
        "problem formulation",
        "mathematical formulation",
        "formulations",
        "formulation",
        "formalization",
    ),
    "algorithms": (
        "algorithmic strategies",
        "algorithmic strategy",
        "iterative methods",
        "algorithms",
        "algorithm",
        "methods",
        "method",
    ),
    "assumptions": (
        "assumptions",
        "assumption",
        "conditions",
        "condition",
    ),
    "convergence": (
        "convergence guarantees",
        "convergence guarantee",
        "convergence",
    ),
}

#: Generic expansion vocabulary per facet -- scientific terms generic to the
#: facet itself, never paper-specific. Combined with question-extracted
#: entities/topic to build one standalone query per facet.
FACET_EXPANSION_TERMS: dict[str, tuple[str, ...]] = {
    "formulation": (
        "formulation",
        "mathematical setting",
        "definition",
        "spaces",
        "mappings",
        "constraints",
        "linear",
        "nonlinear",
    ),
    "algorithms": (
        "algorithms",
        "iterative methods",
        "optimization",
        "projection",
        "fixed point",
        "acceleration",
    ),
    "assumptions": (
        "assumptions",
        "conditions",
        "convexity",
        "smoothness",
        "linearity",
        "mappings",
        "operators",
    ),
    "convergence": (
        "convergence",
        "guarantees",
        "theorem",
        "weak",
        "strong",
        "stationary",
        "global minimizer",
    ),
}

#: Used only when fewer than two explicit facets are detected in the
#: question. Deliberately NOT Legacy's EvidenceDimension values (objective/
#: method/dataset/evaluation/findings/limitations/future_work share zero
#: entries with this tuple) -- a caller must never end up on the Legacy
#: taxonomy "by accident" just because facet detection came up short.
FALLBACK_FACETS: tuple[str, ...] = ("general_topic", "methodology", "outcomes", "constraints")

_ENTITY_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]*)\s?(20\d{2})\b")
_COMPARISON_PATTERN = re.compile(
    r"\b(compare(?:d|s|ing)?|comparison|differ(?:s|ed|ing|ence|ences)?|versus|vs\.?)\b",
    re.IGNORECASE,
)
_TOPIC_PATTERN = re.compile(
    r"\bof the ([a-z][a-z0-9\-]*(?:\s+[a-z][a-z0-9\-]*){0,4}?)\s+"
    r"(problem|framework|algorithm|method|approach|task|model|setting)\b",
    re.IGNORECASE,
)


def extract_entities(research_question: str) -> list[str]:
    """Named comparison entities like "Xu2010"/"Xu 2018" -- generic pattern
    (Capitalized-word + 4-digit year), not any specific paper's identifier."""
    seen: list[str] = []
    for match in _ENTITY_PATTERN.finditer(research_question):
        entity = f"{match.group(1)}{match.group(2)}"
        if entity not in seen:
            seen.append(entity)
    return seen


def extract_topic_phrase(research_question: str) -> str:
    """Main scientific topic phrase, e.g. "split feasibility problem" out of
    "...of the split feasibility problem...". Empty string when the question
    doesn't match this common "of the X <noun>" scientific-RQ shape --
    facet queries still work without it (entities + facet expansion alone)."""
    match = _TOPIC_PATTERN.search(research_question)
    if not match:
        return ""
    return f"{match.group(1)} {match.group(2)}".lower()


def has_comparison_language(research_question: str) -> bool:
    """Whether the question explicitly asks for a comparison."""
    return bool(_COMPARISON_PATTERN.search(research_question or ""))


def detect_facets(research_question: str) -> list[str]:
    """Detect explicit comparison/review facets named in the question.

    Returns facets in the order they first appear in the question. Falls
    back to :data:`FALLBACK_FACETS` when fewer than two facets are detected
    -- one incidental match is not enough signal that the question is
    facet-structured at all.
    """
    question_lower = (research_question or "").lower()

    best_position: dict[str, int] = {}
    for facet, triggers in FACET_LEXICON.items():
        for trigger in triggers:
            match = re.search(rf"\b{re.escape(trigger)}\b", question_lower)
            if match and (facet not in best_position or match.start() < best_position[facet]):
                best_position[facet] = match.start()
                break  # first (most specific) trigger hit for this facet wins

    if len(best_position) < 2:
        return list(FALLBACK_FACETS)

    return sorted(best_position, key=lambda facet: best_position[facet])


class QuestionFacetDimensionQueryPlanner:
    """Fast-v2-specific standalone dimension-query builder.

    Successor to ``DeterministicDimensionQueryPlanner`` for the real product
    runtime only -- that class is untouched and still used wherever a bare
    facet-label query is wanted (tests, the original Dimension-Aware v1
    parity harness). For ordinary questions this planner combines
    question-extracted entities + topic phrase with a small generic per-facet
    expansion vocabulary. For an explicit comparison with multiple selected
    papers, it emits facet-major paper-scoped queries using topic + facet
    vocabulary; the paper-ID filter supplies entity identity.

    Never concatenates the full research question into a query -- that is
    the validated v0 failure mode.
    """

    def __init__(self, *, paper_ids: Sequence[uuid.UUID] = ()) -> None:
        self._paper_ids = tuple(dict.fromkeys(paper_ids))

    def plan(
        self, *, research_question: str, dimensions: Sequence[str]
    ) -> list[DimensionQuery]:
        cleaned: list[str] = []
        for raw in dimensions or []:
            facet = (raw or "").strip()
            if facet and facet not in cleaned:
                cleaned.append(facet)

        if not cleaned:
            raise ValueError(
                "fast_v2 requires explicit dimensions/facets. Supply the "
                "output of detect_facets() (or an explicit facet list) "
                "rather than relying on this planner to invent one."
            )

        entities = extract_entities(research_question)
        topic = extract_topic_phrase(research_question)
        comparison_scopes = (
            self._paper_ids
            if len(self._paper_ids) > 1 and has_comparison_language(research_question)
            else ()
        )

        queries: list[DimensionQuery] = []
        for facet in cleaned:
            expansion = FACET_EXPANSION_TERMS.get(facet, (facet,))
            if comparison_scopes:
                parts = [topic] if topic else []
                parts.extend(expansion)
                query_text = " ".join(parts)
                queries.extend(
                    DimensionQuery(
                        dimension=facet,
                        query_text=query_text,
                        paper_id=paper_id,
                    )
                    for paper_id in comparison_scopes
                )
                continue

            parts: list[str] = list(entities)
            if topic:
                parts.append(topic)
            parts.extend(expansion)
            queries.append(DimensionQuery(dimension=facet, query_text=" ".join(parts)))

        return queries
