"""Claim-grounding boundary -- INTERFACE ONLY.

Real claim-level grounding is **not implemented** and is a future task. This
module exists so the boundary is established now, in the right place, rather
than being retrofitted later.

Why this matters
----------------
The validated OpenScholar generation is fast, but its factual control is NOT
solved. Observed issues in the final controlled run include an unsupported
claim about proximity-function convexity, overclaiming future-work language as
already-investigated, incomplete comparison of convergence assumptions, and
native citation misattribution.

So fast_v2 must never report that its output is grounded. The only
implementation here is a passthrough that says exactly that.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import GeneratedDraft


class ClaimGroundingStatus(str, Enum):
    """Deliberately has no 'validated' member -- nothing can claim that yet."""

    not_evaluated = "not_evaluated"
    unvalidated = "unvalidated"


@dataclass(frozen=True)
class GroundedDraft:
    """A draft plus its (currently always unvalidated) grounding verdict."""

    draft: GeneratedDraft
    claim_grounding_status: ClaimGroundingStatus = ClaimGroundingStatus.not_evaluated
    warning: str = ""
    supported_claims: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    grounding_ms: float | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.draft.text

    @property
    def grounded(self) -> bool:
        """Never True until a real grounding implementation exists."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft": self.draft.to_dict(),
            "claim_grounding_status": self.claim_grounding_status.value,
            "grounded": self.grounded,
            "warning": self.warning,
            "supported_claims": list(self.supported_claims),
            "unsupported_claims": list(self.unsupported_claims),
            "grounding_ms": self.grounding_ms,
            "diagnostics": dict(self.diagnostics),
        }


@runtime_checkable
class ClaimGroundingService(Protocol):
    """Evaluates a draft against the evidence bank that produced it."""

    def evaluate(
        self, *, draft: GeneratedDraft, evidence_bank: GroundedEvidenceBank
    ) -> GroundedDraft:
        ...


class UnvalidatedClaimGroundingPassthrough:
    """Experimental passthrough. Performs NO verification whatsoever.

    It exists only so the fast_v2 path can run end to end. It returns the
    draft unchanged and marks the result ``unvalidated``.
    """

    WARNING = (
        "Claim-level grounding was NOT performed. This draft has not been "
        "verified against the evidence bank; individual claims may be "
        "unsupported or misattributed. Do not present this output as grounded."
    )

    def evaluate(
        self, *, draft: GeneratedDraft, evidence_bank: GroundedEvidenceBank
    ) -> GroundedDraft:
        return GroundedDraft(
            draft=draft,
            claim_grounding_status=ClaimGroundingStatus.unvalidated,
            warning=self.WARNING,
            supported_claims=(),
            unsupported_claims=(),
            grounding_ms=0.0,
            diagnostics={
                "implementation": "UnvalidatedClaimGroundingPassthrough",
                "evidence_count": len(evidence_bank.evidence),
            },
        )
