"""Claim-grounding boundary.

Structured provenance validation checks identities, ownership, facets, and
comparative paper coverage, then derives citation spans from canonical evidence.
It deliberately does not
claim semantic entailment. The older unvalidated passthrough remains available
for explicit compatibility tests; production Fast v2 uses the structured
service.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.grounding.manifest import (
    ClaimManifest,
    DroppedClaim,
    ManifestValidationResult,
    StructuredClaimManifestGuard,
    ValidatedClaim,
)


_PROVENANCE_REASON_CATEGORIES = {
    "missing_support": "missing_evidence",
    "unknown_evidence_id": "unknown_evidence_id",
    "wrong_paper": "paper_ownership_mismatch",
    "invalid_facet": "facet_mismatch",
    "comparative_paper_coverage": "comparative_validation_failure",
}


def _generated_manifest_statistics(manifest: ClaimManifest) -> dict[str, Any]:
    statements = [
        statement
        for claim in manifest.claims
        for statement in claim.statements
    ]
    evidence_ids = list(
        dict.fromkeys(
            support.evidence_id
            for statement in statements
            for support in statement.supports
        )
    )
    return {
        "generated_claim_groups": len(manifest.claims),
        "generated_statements": len(statements),
        "statements_with_evidence_ids": sum(
            bool(statement.supports) for statement in statements
        ),
        "evidence_ids_referenced": evidence_ids,
    }


def _provenance_validation_statistics(
    manifest: ClaimManifest,
    validation: ManifestValidationResult,
) -> dict[str, Any]:
    reason_counts = {
        "missing_evidence": 0,
        "unknown_evidence_id": 0,
        "paper_ownership_mismatch": 0,
        "facet_mismatch": 0,
        "comparative_validation_failure": 0,
        "other": 0,
    }
    rejected_statements = 0
    for dropped in validation.dropped_claims:
        rejected_statements += len(manifest.claims[dropped.claim_index].statements)
        categories = {
            _PROVENANCE_REASON_CATEGORIES.get(reason, "other")
            for reason in dropped.reasons
        }
        for category in categories:
            reason_counts[category] += 1

    return {
        "accepted_statements": sum(
            len(claim.statements) for claim in validation.valid_claims
        ),
        "rejected_statements": rejected_statements,
        "rejection_reasons_by_category": reason_counts,
    }


class ClaimGroundingStatus(str, Enum):
    """Deliberately has no 'validated' member -- nothing can claim that yet."""

    not_evaluated = "not_evaluated"
    unvalidated = "unvalidated"


@dataclass(frozen=True)
class GroundedDraft:
    """Draft plus exact provenance status and unvalidated entailment status."""

    draft: GeneratedDraft
    claim_grounding_status: ClaimGroundingStatus = ClaimGroundingStatus.not_evaluated
    warning: str = ""
    supported_claims: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    validated_claims: tuple[ValidatedClaim, ...] = ()
    dropped_claims: tuple[DroppedClaim, ...] = ()
    structured_provenance_validation: str = "not_evaluated"
    semantic_entailment: str = "unvalidated"
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
            "structured_provenance_validation": self.structured_provenance_validation,
            "semantic_entailment": self.semantic_entailment,
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


class StructuredClaimManifestGroundingService:
    """Validate claim provenance without asserting semantic entailment."""

    WARNING = (
        "Structured provenance passed deterministic validation. Semantic "
        "entailment between claim text and referenced evidence remains unvalidated."
    )

    def __init__(self, guard: StructuredClaimManifestGuard | None = None) -> None:
        self.guard = guard or StructuredClaimManifestGuard()

    def evaluate(
        self, *, draft: GeneratedDraft, evidence_bank: GroundedEvidenceBank
    ) -> GroundedDraft:
        import time

        if draft.claim_manifest is None:
            raise ValueError("structured claim manifest is required; failing closed")
        started = time.perf_counter()
        validation = self.guard.validate(
            manifest=draft.claim_manifest,
            evidence_bank=evidence_bank,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return GroundedDraft(
            draft=draft,
            claim_grounding_status=ClaimGroundingStatus.unvalidated,
            warning=self.WARNING,
            supported_claims=tuple(
                statement.claim_text
                for claim in validation.valid_claims
                for statement in claim.statements
            ),
            unsupported_claims=tuple(
                f"claim[{claim.claim_index}]" for claim in validation.dropped_claims
            ),
            validated_claims=validation.valid_claims,
            dropped_claims=validation.dropped_claims,
            structured_provenance_validation=(
                validation.structured_provenance_validation
            ),
            semantic_entailment=validation.semantic_entailment,
            grounding_ms=elapsed_ms,
            diagnostics={
                "implementation": "StructuredClaimManifestGroundingService",
                "evidence_count": len(evidence_bank.evidence),
                "valid_claims": len(validation.valid_claims),
                "dropped_claims": len(validation.dropped_claims),
                "generated_manifest_statistics": _generated_manifest_statistics(
                    draft.claim_manifest
                ),
                "provenance_validation_statistics": (
                    _provenance_validation_statistics(
                        draft.claim_manifest,
                        validation,
                    )
                ),
                "parsed_claim_manifest": draft.claim_manifest.to_dict(),
                "claim_validation": list(validation.claim_validation),
            },
        )
