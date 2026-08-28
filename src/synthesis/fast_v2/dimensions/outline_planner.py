"""Outline-driven dimension-query planner.

Turns a :class:`~src.synthesis.fast_v2.planning.research_lead.LongformOutlinePlan`
into the ``DimensionQuery`` list the pipeline already knows how to run. A
section's ``title`` becomes the pipeline's per-request "dimension", and every
one of that section's ``retrieval_queries`` becomes one standalone
``DimensionQuery`` for that dimension -- so a section with 3 retrieval
queries produces 3 entries sharing one ``dimension``, and
``pipeline.py`` unions/dedupes/caps them into ONE per-section candidate pool
before the single per-section rerank call (see
``pipeline.py::_prepare_dimension_pool``).

Deliberately does not synthesize queries itself (unlike
``dimensions/facets.py``'s lexicon-expansion planners) -- Research Lead
already produced queries specific to what each section needs. This planner
only projects the outline onto the ``DimensionQueryPlanner`` protocol.
"""
from __future__ import annotations

from typing import Sequence

from src.synthesis.fast_v2.dimensions.planner import DimensionQuery
from src.synthesis.fast_v2.planning.research_lead import LongformOutlinePlan


class OutlineDimensionQueryPlanner:
    """Projects a pre-built outline's per-section queries onto ``DimensionQuery``."""

    def __init__(self, outline: LongformOutlinePlan) -> None:
        self._outline = outline

    def plan(
        self, *, research_question: str, dimensions: Sequence[str]
    ) -> list[DimensionQuery]:
        # `dimensions` is accepted for protocol compatibility but ignored --
        # the outline itself is the authoritative section list. Pipeline
        # callers should pass `[s.title for s in outline.sections]` as
        # `dimensions` purely for coverage bookkeeping (bank.coverage).
        queries: list[DimensionQuery] = []
        for section in self._outline.sections:
            for query_text in section.retrieval_queries:
                queries.append(DimensionQuery(dimension=section.title, query_text=query_text))
        return queries
