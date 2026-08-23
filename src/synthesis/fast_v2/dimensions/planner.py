"""Dimension query planning.

Validated finding (Dimension-Aware v0 FAILURE)
----------------------------------------------
v0 built each dimension query as ``{full research question} + "Focus
specifically on: {dimension}"``. Because the research question already
contained the dimension terms, every dimension query landed at embedding
cosine similarity >0.98 (RQ1 off-diagonal mean 0.987, RQ2 0.988) and the
queries were effectively identical. Result: RQ1 15 selections -> 3 unique
evidence (80% duplicate), RQ2 12 selections -> 3 unique evidence (75%
duplicate).

Validated fix (Dimension Query v1)
----------------------------------
Build **standalone deterministic dimension queries** from the dimension
itself. Measured query similarity dropped to RQ1 0.656 mean / RQ2 0.595 mean,
and duplicate selection dropped to RQ1 40% / RQ2 41.7%.

OPEN -- general question decomposition
--------------------------------------
fast_v2 requires **explicit** dimensions. There is deliberately no LLM planner
and no weak production heuristic that turns an arbitrary research question
into dimensions. The validated experiments used manually specified dimensions.
Designing general decomposition is the NEXT design decision, tracked as OPEN
in ``docs/architecture/FAST_SYNTHESIS_V2.md`` section L.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class DimensionQuery:
    """One standalone retrieval query for one dimension."""

    dimension: str
    query_text: str


@runtime_checkable
class DimensionQueryPlanner(Protocol):
    """Turns a question plus explicit dimensions into retrieval queries."""

    def plan(
        self, *, research_question: str, dimensions: Sequence[str]
    ) -> list[DimensionQuery]:
        ...


class DeterministicDimensionQueryPlanner:
    """Dimension Query v1: standalone, deterministic, no LLM.

    The research question is accepted for interface completeness and
    diagnostics but is deliberately NOT concatenated into the query text --
    doing so is precisely the v0 failure mode.
    """

    #: Light scientific framing so the query is a phrase rather than a bare
    #: label, without importing any terms from the research question.
    TEMPLATE = "{dimension}"

    def plan(
        self, *, research_question: str, dimensions: Sequence[str]
    ) -> list[DimensionQuery]:
        cleaned: list[str] = []
        for raw in dimensions or []:
            dimension = (raw or "").strip()
            if dimension and dimension not in cleaned:
                cleaned.append(dimension)

        if not cleaned:
            raise ValueError(
                "fast_v2 requires explicit dimensions. General question "
                "decomposition is an OPEN design decision -- see "
                "docs/architecture/FAST_SYNTHESIS_V2.md section L. Supply "
                "dimensions explicitly rather than relying on a heuristic."
            )

        return [
            DimensionQuery(dimension=dimension, query_text=self.TEMPLATE.format(dimension=dimension))
            for dimension in cleaned
        ]
