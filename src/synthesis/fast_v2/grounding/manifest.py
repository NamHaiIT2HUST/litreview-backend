"""Structured claim provenance contract and deterministic validation.

Validation proves provenance integrity only. It does not prove semantic
entailment between generated claim text and referenced evidence text.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any
from uuid import UUID

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank


@dataclass(frozen=True)
class ClaimSupport:
    evidence_id: str

    def to_dict(self) -> dict[str, Any]:
        return {"evidence_id": self.evidence_id}


@dataclass(frozen=True)
class ClaimStatement:
    claim_text: str
    paper_id: UUID
    supports: tuple[ClaimSupport, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_text": self.claim_text,
            "paper_id": str(self.paper_id),
            "supports": [support.to_dict() for support in self.supports],
        }


@dataclass(frozen=True)
class GeneratedClaim:
    facet: str
    is_comparative: bool
    statements: tuple[ClaimStatement, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "facet": self.facet,
            "is_comparative": self.is_comparative,
            "statements": [statement.to_dict() for statement in self.statements],
        }


@dataclass(frozen=True)
class ClaimManifest:
    claims: tuple[GeneratedClaim, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"claims": [claim.to_dict() for claim in self.claims]}


class ClaimManifestParseError(ValueError):
    """Hosted/local generator output did not match the strict manifest schema."""


def _exact_object(value: Any, keys: set[str], *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ClaimManifestParseError(
            f"{path} must be an object with exactly {sorted(keys)}"
        )
    return value


def _string(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimManifestParseError(f"{path} must be a non-empty string")
    return value


def parse_claim_manifest(raw: str) -> ClaimManifest:
    """Parse strict JSON. Markdown fences and unknown fields fail closed."""
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ClaimManifestParseError("generator output must be one JSON object") from exc

    root = _exact_object(payload, {"claims"}, path="root")
    raw_claims = root["claims"]
    if not isinstance(raw_claims, list):
        raise ClaimManifestParseError("claims must be a list")

    claims: list[GeneratedClaim] = []
    for claim_index, raw_claim in enumerate(raw_claims):
        claim = _exact_object(
            raw_claim,
            {"facet", "is_comparative", "statements"},
            path=f"claims[{claim_index}]",
        )
        if not isinstance(claim["is_comparative"], bool):
            raise ClaimManifestParseError(
                f"claims[{claim_index}].is_comparative must be boolean"
            )
        raw_statements = claim["statements"]
        if not isinstance(raw_statements, list):
            raise ClaimManifestParseError(
                f"claims[{claim_index}].statements must be a list"
            )
        statements: list[ClaimStatement] = []
        for statement_index, raw_statement in enumerate(raw_statements):
            statement_path = f"claims[{claim_index}].statements[{statement_index}]"
            statement = _exact_object(
                raw_statement,
                {"claim_text", "paper_id", "supports"},
                path=statement_path,
            )
            try:
                paper_id = UUID(_string(statement["paper_id"], path=f"{statement_path}.paper_id"))
            except ValueError as exc:
                raise ClaimManifestParseError(
                    f"{statement_path}.paper_id must be a UUID"
                ) from exc
            raw_supports = statement["supports"]
            if not isinstance(raw_supports, list):
                raise ClaimManifestParseError(f"{statement_path}.supports must be a list")
            supports: list[ClaimSupport] = []
            for support_index, raw_support in enumerate(raw_supports):
                support_path = f"{statement_path}.supports[{support_index}]"
                support = _exact_object(
                    raw_support,
                    {"evidence_id"},
                    path=support_path,
                )
                supports.append(
                    ClaimSupport(
                        evidence_id=_string(
                            support["evidence_id"], path=f"{support_path}.evidence_id"
                        ),
                    )
                )
            statements.append(
                ClaimStatement(
                    claim_text=_string(
                        statement["claim_text"], path=f"{statement_path}.claim_text"
                    ),
                    paper_id=paper_id,
                    supports=tuple(supports),
                )
            )
        claims.append(
            GeneratedClaim(
                facet=_string(claim["facet"], path=f"claims[{claim_index}].facet"),
                is_comparative=claim["is_comparative"],
                statements=tuple(statements),
            )
        )
    return ClaimManifest(claims=tuple(claims))


@dataclass(frozen=True)
class ValidatedSupport:
    evidence_id: str
    paper_id: UUID
    support_quote: str
    quote_char_start: int
    quote_char_end: int
    source_char_start: int | None
    source_char_end: int | None


@dataclass(frozen=True)
class ValidatedStatement:
    claim_text: str
    paper_id: UUID
    supports: tuple[ValidatedSupport, ...]


@dataclass(frozen=True)
class ValidatedClaim:
    facet: str
    is_comparative: bool
    statements: tuple[ValidatedStatement, ...]


@dataclass(frozen=True)
class DroppedClaim:
    claim_index: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ManifestValidationResult:
    valid_claims: tuple[ValidatedClaim, ...]
    dropped_claims: tuple[DroppedClaim, ...]
    claim_validation: tuple[dict[str, Any], ...] = ()
    structured_provenance_validation: str = "passed"
    semantic_entailment: str = "unvalidated"


class StructuredClaimManifestGuard:
    """Validate manifest references against one immutable evidence bank."""

    def validate(
        self,
        *,
        manifest: ClaimManifest,
        evidence_bank: GroundedEvidenceBank,
    ) -> ManifestValidationResult:
        evidence_by_id = {
            unit.evidence_id: unit for unit in evidence_bank.evidence
        }
        valid_claims: list[ValidatedClaim] = []
        dropped_claims: list[DroppedClaim] = []
        claim_validation: list[dict[str, Any]] = []

        for claim_index, claim in enumerate(manifest.claims):
            reasons: list[str] = []
            statement_validation: list[dict[str, Any]] = []

            def reject(reason: str) -> None:
                if reason not in reasons:
                    reasons.append(reason)

            if claim.facet not in evidence_bank.dimensions:
                reject("invalid_facet")
            if claim.is_comparative:
                if len({statement.paper_id for statement in claim.statements}) < 2:
                    reject("comparative_paper_coverage")
            elif len(claim.statements) != 1:
                reject("invalid_single_paper_shape")

            statements: list[ValidatedStatement] = []
            for statement_index, statement in enumerate(claim.statements):
                statement_failures: list[str] = []

                def reject_statement(reason: str) -> None:
                    if reason not in statement_failures:
                        statement_failures.append(reason)
                    reject(reason)

                if not statement.claim_text.strip():
                    reject_statement("empty_claim_text")
                if re.search(r"\[\d{1,3}\]", statement.claim_text):
                    reject_statement("native_citation_marker")
                if not statement.supports:
                    reject_statement("missing_support")

                evidence_ids = [support.evidence_id for support in statement.supports]
                if len(evidence_ids) != len(set(evidence_ids)):
                    reject_statement("duplicate_evidence_support")

                supports: list[ValidatedSupport] = []
                support_validation: list[dict[str, Any]] = []
                for support_index, support in enumerate(statement.supports):
                    support_failures: list[str] = []

                    def reject_support(reason: str) -> None:
                        if reason not in support_failures:
                            support_failures.append(reason)
                        reject(reason)

                    unit = evidence_by_id.get(support.evidence_id)
                    if unit is None:
                        reject_support("unknown_evidence_id")
                        support_validation.append(
                            {
                                "support_index": support_index,
                                "evidence_id": support.evidence_id,
                                "failures": support_failures,
                            }
                        )
                        continue
                    if unit.paper_id != statement.paper_id:
                        reject_support("wrong_paper")
                        support_validation.append(
                            {
                                "support_index": support_index,
                                "evidence_id": support.evidence_id,
                                "failures": support_failures,
                            }
                        )
                        continue
                    supports.append(
                        ValidatedSupport(
                            evidence_id=unit.evidence_id,
                            paper_id=unit.paper_id,
                            support_quote=unit.text,
                            quote_char_start=0,
                            quote_char_end=len(unit.text),
                            source_char_start=unit.page_char_start,
                            source_char_end=unit.page_char_end,
                        )
                    )
                    support_validation.append(
                        {
                            "support_index": support_index,
                            "evidence_id": support.evidence_id,
                            "failures": support_failures,
                        }
                    )
                statements.append(
                    ValidatedStatement(
                        claim_text=statement.claim_text,
                        paper_id=statement.paper_id,
                        supports=tuple(supports),
                    )
                )
                statement_validation.append(
                    {
                        "statement_index": statement_index,
                        "paper_id": str(statement.paper_id),
                        "support_count": len(statement.supports),
                        "failures": statement_failures,
                        "supports": support_validation,
                    }
                )
            claim_validation.append(
                {
                    "claim_index": claim_index,
                    "facet": claim.facet,
                    "is_comparative": claim.is_comparative,
                    "statement_count": len(claim.statements),
                    "status": "dropped" if reasons else "validated",
                    "drop_reasons": list(reasons),
                    "statements": statement_validation,
                }
            )
            if reasons:
                dropped_claims.append(
                    DroppedClaim(claim_index=claim_index, reasons=tuple(reasons))
                )
                continue
            valid_claims.append(
                ValidatedClaim(
                    facet=claim.facet,
                    is_comparative=claim.is_comparative,
                    statements=tuple(statements),
                )
            )

        return ManifestValidationResult(
            valid_claims=tuple(valid_claims),
            dropped_claims=tuple(dropped_claims),
            claim_validation=tuple(claim_validation),
        )
