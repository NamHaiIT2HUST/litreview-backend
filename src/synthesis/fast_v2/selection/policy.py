"""Evidence selection policy -- the relevance gate.

Frozen experimental defaults
----------------------------
* ``max_per_dimension = 3``
* ``relevance_threshold = 0.0`` (i.e. the validated rule "score > 0")

**"score > 0" is NOT a calibrated production threshold.** It is the value the
validated experiments ran with. It is exposed here as configuration precisely
so it can be re-calibrated later without rewriting retrieval logic. See
``docs/architecture/FAST_SYNTHESIS_V2.md`` sections L and M.

Hard rules carried over from the validated experiments
------------------------------------------------------
* ``score <= threshold`` -> reject.
* Accepted evidence is capped at ``max_per_dimension``.
* **Never pad** weak or negative evidence to fill a quota. The quota is a
  ceiling, not a target. Padding is what put -1.47-scored tail evidence into
  the bank during the hygiene spike.
* **Never force per-paper quotas or balance.** The v1 banks were deliberately
  unbalanced (RQ1 7/2, RQ2 4/3) because the strongest evidence won.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.synthesis.fast_v2.evidence.models import EvidenceUnit

DEFAULT_MAX_PER_DIMENSION = 3
#: Experimental, uncalibrated. See module docstring.
DEFAULT_RELEVANCE_THRESHOLD = 0.0


@dataclass(frozen=True)
class EvidenceSelectionPolicy:
    """Decides which retrieved units become evidence for one dimension."""

    max_per_dimension: int = DEFAULT_MAX_PER_DIMENSION
    relevance_threshold: float = DEFAULT_RELEVANCE_THRESHOLD

    def score_of(self, unit: EvidenceUnit) -> float | None:
        """Rerank score is authoritative; retrieval score is the fallback."""
        if unit.rerank_score is not None:
            return unit.rerank_score
        return unit.retrieval_score

    def accepts(self, unit: EvidenceUnit) -> bool:
        score = self.score_of(unit)
        return score is not None and score > self.relevance_threshold

    def select(
        self, units: Sequence[EvidenceUnit], *, dimension: str
    ) -> list[EvidenceUnit]:
        """Return at most ``max_per_dimension`` accepted units, best first.

        Returns fewer -- possibly zero -- when not enough units clear the gate.
        That is the intended behaviour: no padding.
        """
        accepted = [unit for unit in units if self.accepts(unit)]
        accepted.sort(key=lambda unit: self.score_of(unit), reverse=True)

        return [
            unit.with_dimension(dimension, self.score_of(unit))
            for unit in accepted[: self.max_per_dimension]
        ]
