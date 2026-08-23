"""Phase timings and call counting for fast_v2.

``generation_calls`` counts **LLM synthesis generation calls only**. The
expected value for the frozen architecture is exactly **1**. Deterministic and
local work -- embedding lookups, vector search, hygiene classification,
reranking, dedupe, finalization -- is NOT an LLM call and must never be
counted as one.

``extraction_calls`` exists to make the central invariant observable: it must
stay **0**. Any query-time evidence-extraction LLM call is an architecture
violation, not a performance regression.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

#: Every phase that must be reported.
PHASES = (
    "dimension_query_ms",
    "retrieval_ms",
    "hygiene_ms",
    "rerank_ms",
    "evidence_bank_ms",
    "generation_ms",
    "grounding_ms",
    "finalize_ms",
)


@dataclass
class PhaseTimings:
    """Mutable timing/counter accumulator for one fast_v2 run."""

    timings: dict[str, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    generation_calls: int = 0
    extraction_calls: int = 0
    total_ms: float = 0.0

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """Time one named phase. Unknown names are rejected loudly."""
        if name not in self.timings:
            raise KeyError(f"Unknown fast_v2 phase {name!r}; expected one of {PHASES}")
        started = time.perf_counter()
        try:
            yield
        finally:
            self.timings[name] += (time.perf_counter() - started) * 1000.0

    def record_generation_call(self, count: int = 1) -> None:
        self.generation_calls += count

    def record_extraction_call(self, count: int = 1) -> None:
        """Should never be called. Present so a violation is visible."""
        self.extraction_calls += count

    @contextmanager
    def total(self) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.total_ms = (time.perf_counter() - started) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            **{phase: round(self.timings[phase], 3) for phase in PHASES},
            "total_ms": round(self.total_ms, 3),
            "generation_calls": self.generation_calls,
            "extraction_calls": self.extraction_calls,
        }
