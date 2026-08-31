"""Post-generation semantic verification for provenance-valid statements.

This layer is independent from deterministic provenance validation. It never
retrieves, rewrites claims, changes citations, or calls the synthesis generator.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.grounding.interface import GroundedDraft
from src.synthesis.fast_v2.grounding.manifest import (
    ValidatedClaim,
    ValidatedStatement,
)


class SemanticVerdict(str, Enum):
    supported = "supported"
    partial = "partial"
    unsupported = "unsupported"
    unverified = "unverified"


def parse_semantic_verdict(value: Any) -> SemanticVerdict:
    """Parse provider label formatting without changing verdict semantics."""
    if not isinstance(value, str):
        raise ValueError("semantic verdict must be a string")
    verdict = SemanticVerdict(value.strip().casefold())
    if verdict is SemanticVerdict.unverified:
        raise ValueError("provider must not return unverified")
    return verdict


@dataclass(frozen=True)
class SemanticStatementInput:
    claim_index: int
    statement_index: int
    claim_text: str
    paper_id: UUID
    facet: str
    evidence_units: tuple[EvidenceUnit, ...]


@dataclass(frozen=True)
class StatementVerificationResult:
    claim_index: int
    statement_index: int
    verdict: SemanticVerdict
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_index": self.claim_index,
            "statement_index": self.statement_index,
            "verdict": self.verdict.value,
            "reason": self.reason,
        }


@runtime_checkable
class SemanticVerifier(Protocol):
    def verify_batch(
        self,
        statements: tuple[SemanticStatementInput, ...],
    ) -> Sequence[StatementVerificationResult]:
        ...


class SemanticVerifierError(RuntimeError):
    """Hosted semantic verification failed without exposing request secrets."""


SEMANTIC_VERIFIER_MAX_TOKENS = 4000
SEMANTIC_VERIFIER_INSTRUCTIONS = (
    "Evaluate every statement strictly against the COMPLETE SET of evidence "
    "items declared for that statement, considered jointly. Do not require "
    "each evidence item to entail the whole statement. Use supported only "
    "when all substantive factual content is supported by the combined "
    "evidence. Use partial when some substantive content is supported but "
    "some is absent, stronger than, or not established by the evidence. Use "
    "unsupported when the claim is not supported or is contradicted. Do not "
    "use outside knowledge. For each statement, resolve every value in its "
    "evidence_ids array to the evidence_units catalog entry having that exact "
    "evidence_id; ignore catalog entries not referenced by that statement. "
    "Return exactly one result for each input key. Verdict labels are exactly "
    "supported, partial, or unsupported. Return JSON only: "
    '{"results":[{"claim_index":0,"statement_index":0,'
    '"verdict":"supported|partial|unsupported",'
    '"reason":"concise evidence-based reason"}]}'
)


def build_semantic_verifier_context(
    statements: tuple[SemanticStatementInput, ...],
) -> dict[str, Any]:
    """Serialize one batch without repeating referenced evidence text.

    Statement and evidence order both remain first-use deterministic. The
    catalog contains only evidence referenced by at least one statement.
    """
    evidence_units: list[dict[str, Any]] = []
    seen_evidence_ids: set[str] = set()
    statement_payload: list[dict[str, Any]] = []

    for statement in statements:
        evidence_ids: list[str] = []
        for unit in statement.evidence_units:
            evidence_ids.append(unit.evidence_id)
            if unit.evidence_id in seen_evidence_ids:
                continue
            seen_evidence_ids.add(unit.evidence_id)
            evidence_units.append(
                {
                    "evidence_id": unit.evidence_id,
                    "paper_id": str(unit.paper_id),
                    "paper_title": unit.title,
                    "page": unit.page,
                    "text": unit.text,
                }
            )
        statement_payload.append(
            {
                "claim_index": statement.claim_index,
                "statement_index": statement.statement_index,
                "facet": statement.facet,
                "claim_text": statement.claim_text,
                "paper_id": str(statement.paper_id),
                "evidence_ids": evidence_ids,
            }
        )

    return {
        "statements": statement_payload,
        "evidence_units": evidence_units,
    }


class HostedBatchSemanticVerifier:
    """One OpenAI-compatible verification call for all provenance statements."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        connect_timeout_s: float = 10.0,
        verification_timeout_s: float = 240.0,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        missing = [
            name
            for name, value in (
                ("base_url", base_url),
                ("api_key", api_key),
                ("model", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "HostedBatchSemanticVerifier requires " + ", ".join(missing)
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.connect_timeout_s = connect_timeout_s
        self.verification_timeout_s = verification_timeout_s
        self.http_client_factory = http_client_factory
        self.calls = 0
        self.latency_ms: float | None = None
        self.token_usage: dict[str, Any] = {}
        self.finish_reason: str | None = None
        self.last_inputs: tuple[SemanticStatementInput, ...] = ()
        self.last_results: tuple[StatementVerificationResult, ...] = ()

    def _client(self) -> Any:
        if self.http_client_factory is not None:
            return self.http_client_factory()
        import httpx

        return httpx.Client(
            timeout=httpx.Timeout(
                connect=self.connect_timeout_s,
                read=self.verification_timeout_s,
                write=self.verification_timeout_s,
                pool=self.connect_timeout_s,
            )
        )

    def verify_batch(
        self,
        statements: tuple[SemanticStatementInput, ...],
    ) -> tuple[StatementVerificationResult, ...]:
        if self.calls:
            raise SemanticVerifierError("semantic verifier may be called only once")
        self.calls += 1
        self.last_inputs = statements
        context = build_semantic_verifier_context(statements)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict scientific claim-evidence verifier.",
                },
                {
                    "role": "user",
                    "content": (
                        SEMANTIC_VERIFIER_INSTRUCTIONS
                        + "\n\nSTATEMENTS:\n"
                        + json.dumps(
                            context,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                    ),
                },
            ],
            "temperature": 0.0,
            "max_tokens": SEMANTIC_VERIFIER_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        started = time.perf_counter()
        try:
            response = self._client().post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except Exception as exc:
            raise SemanticVerifierError(
                f"semantic verifier request failed: {type(exc).__name__}"
            ) from exc
        self.latency_ms = (time.perf_counter() - started) * 1000.0
        if response.status_code != 200:
            raise SemanticVerifierError(
                f"semantic verifier returned HTTP {response.status_code}"
            )

        try:
            data = response.json()
            choice = data["choices"][0]
            self.finish_reason = choice.get("finish_reason")
            self.token_usage = dict(data.get("usage") or {})
            content = choice["message"]["content"]
            parsed = json.loads(content)
            rows = parsed.get("results")
            if not isinstance(rows, list):
                raise ValueError("missing results list")
            results = tuple(
                StatementVerificationResult(
                    claim_index=int(row["claim_index"]),
                    statement_index=int(row["statement_index"]),
                    verdict=parse_semantic_verdict(row["verdict"]),
                    reason=str(row.get("reason") or ""),
                )
                for row in rows
            )
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise SemanticVerifierError(
                "semantic verifier returned malformed response"
            ) from exc
        self.last_results = results
        return results


class DeterministicFakeSemanticVerifier:
    """CPU-only verifier double. Never performs network or model calls."""

    def __init__(
        self,
        *,
        verdicts: Mapping[tuple[int, int], SemanticVerdict] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.verdicts = dict(verdicts or {})
        self.error = error
        self.calls = 0
        self.last_inputs: tuple[SemanticStatementInput, ...] = ()

    def verify_batch(
        self,
        statements: tuple[SemanticStatementInput, ...],
    ) -> tuple[StatementVerificationResult, ...]:
        self.calls += 1
        self.last_inputs = statements
        if self.error is not None:
            raise self.error
        return tuple(
            StatementVerificationResult(
                claim_index=statement.claim_index,
                statement_index=statement.statement_index,
                verdict=self.verdicts.get(
                    (statement.claim_index, statement.statement_index),
                    SemanticVerdict.supported,
                ),
            )
            for statement in statements
        )


@dataclass(frozen=True)
class SemanticVerificationOutcome:
    original_draft: GroundedDraft
    verified_statements: tuple[ValidatedStatement, ...]
    rejected_statements: tuple[ValidatedStatement, ...]
    verification_results: tuple[StatementVerificationResult, ...]
    claims_for_finalizer: tuple[ValidatedClaim, ...]
    semantic_entailment: str
    grounded: bool
    warning: str
    verification_ms: float
    diagnostics: dict[str, Any]


def _statement_to_dict(statement: ValidatedStatement) -> dict[str, Any]:
    return {
        "claim_text": statement.claim_text,
        "paper_id": str(statement.paper_id),
        "supports": [
            {
                "evidence_id": support.evidence_id,
                "paper_id": str(support.paper_id),
                "support_quote": support.support_quote,
                "quote_char_start": support.quote_char_start,
                "quote_char_end": support.quote_char_end,
                "source_char_start": support.source_char_start,
                "source_char_end": support.source_char_end,
            }
            for support in statement.supports
        ],
    }


def _provenance_draft_to_dict(draft: GroundedDraft) -> dict[str, Any]:
    return {
        "structured_provenance_validation": draft.structured_provenance_validation,
        "semantic_entailment": draft.semantic_entailment,
        "validated_claims": [
            {
                "facet": claim.facet,
                "is_comparative": claim.is_comparative,
                "statements": [
                    _statement_to_dict(statement) for statement in claim.statements
                ],
            }
            for claim in draft.validated_claims
        ],
        "dropped_claims": [
            {
                "claim_index": claim.claim_index,
                "reasons": list(claim.reasons),
            }
            for claim in draft.dropped_claims
        ],
    }


def _semantic_audit_diagnostics(
    *,
    original_draft: GroundedDraft,
    inputs: tuple[SemanticStatementInput, ...],
    results: tuple[StatementVerificationResult, ...],
) -> dict[str, Any]:
    inputs_by_key = {
        (item.claim_index, item.statement_index): item for item in inputs
    }
    rejected = []
    for result in results:
        if result.verdict in {SemanticVerdict.supported, SemanticVerdict.unverified}:
            continue
        item = inputs_by_key[(result.claim_index, result.statement_index)]
        rejected.append(
            {
                "claim_index": item.claim_index,
                "statement_index": item.statement_index,
                "claim_text": item.claim_text,
                "paper_id": str(item.paper_id),
                "facet": item.facet,
                "evidence_ids": [unit.evidence_id for unit in item.evidence_units],
                "verdict": result.verdict.value,
                "reason": result.reason,
            }
        )
    return {
        "semantic_original_provenance_draft": _provenance_draft_to_dict(
            original_draft
        ),
        "semantic_rejected_statement_details": rejected,
    }


def _statement_inputs(
    original_draft: GroundedDraft,
    evidence_bank: GroundedEvidenceBank,
) -> tuple[SemanticStatementInput, ...]:
    evidence_by_id = {unit.evidence_id: unit for unit in evidence_bank.evidence}
    return tuple(
        SemanticStatementInput(
            claim_index=claim_index,
            statement_index=statement_index,
            claim_text=statement.claim_text,
            paper_id=statement.paper_id,
            facet=claim.facet,
            evidence_units=tuple(
                evidence_by_id[support.evidence_id]
                for support in statement.supports
            ),
        )
        for claim_index, claim in enumerate(original_draft.validated_claims)
        for statement_index, statement in enumerate(claim.statements)
    )


def _unverified_outcome(
    *,
    original_draft: GroundedDraft,
    inputs: tuple[SemanticStatementInput, ...],
    started: float,
    reason: str,
    statements_passed_to_verifier: int,
) -> SemanticVerificationOutcome:
    results = tuple(
        StatementVerificationResult(
            claim_index=item.claim_index,
            statement_index=item.statement_index,
            verdict=SemanticVerdict.unverified,
            reason=reason,
        )
        for item in inputs
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    warning = (
        "Semantic verifier unavailable or failed; original provenance-validated "
        "synthesis was preserved, but semantic entailment remains unverified."
    )
    return SemanticVerificationOutcome(
        original_draft=original_draft,
        verified_statements=(),
        rejected_statements=(),
        verification_results=results,
        claims_for_finalizer=original_draft.validated_claims,
        semantic_entailment="unverified",
        grounded=False,
        warning=warning,
        verification_ms=elapsed_ms,
        diagnostics={
            "semantic_verifier_available": False,
            "semantic_verifier_error": reason,
            "statements_passed_to_verifier": statements_passed_to_verifier,
            "semantic_verification_results": [item.to_dict() for item in results],
            **_semantic_audit_diagnostics(
                original_draft=original_draft,
                inputs=inputs,
                results=results,
            ),
        },
    )


def verify_and_filter_statements(
    *,
    original_draft: GroundedDraft,
    evidence_bank: GroundedEvidenceBank,
    verifier: SemanticVerifier | None,
) -> SemanticVerificationOutcome:
    """Verify all statements in one batch and filter only explicit verdicts."""
    started = time.perf_counter()
    inputs = _statement_inputs(original_draft, evidence_bank)
    if verifier is None:
        return _unverified_outcome(
            original_draft=original_draft,
            inputs=inputs,
            started=started,
            reason="semantic_verifier_unavailable",
            statements_passed_to_verifier=0,
        )

    try:
        raw_results = tuple(verifier.verify_batch(inputs))
        expected_keys = {
            (item.claim_index, item.statement_index) for item in inputs
        }
        result_keys = [
            (item.claim_index, item.statement_index) for item in raw_results
        ]
        if len(result_keys) != len(set(result_keys)) or set(result_keys) != expected_keys:
            raise ValueError("semantic verifier returned incomplete or duplicate results")
        if any(item.verdict is SemanticVerdict.unverified for item in raw_results):
            raise ValueError("semantic verifier returned unverified result")
    except Exception as exc:
        return _unverified_outcome(
            original_draft=original_draft,
            inputs=inputs,
            started=started,
            reason=f"{type(exc).__name__}: {exc}",
            statements_passed_to_verifier=len(inputs),
        )

    results_by_key = {
        (item.claim_index, item.statement_index): item for item in raw_results
    }
    verified: list[ValidatedStatement] = []
    rejected: list[ValidatedStatement] = []
    filtered_claims: list[ValidatedClaim] = []
    for claim_index, claim in enumerate(original_draft.validated_claims):
        kept: list[ValidatedStatement] = []
        for statement_index, statement in enumerate(claim.statements):
            result = results_by_key[(claim_index, statement_index)]
            if result.verdict is SemanticVerdict.supported:
                verified.append(statement)
                kept.append(statement)
            else:
                rejected.append(statement)
        if kept:
            filtered_claims.append(
                ValidatedClaim(
                    facet=claim.facet,
                    is_comparative=claim.is_comparative,
                    statements=tuple(kept),
                )
            )

    if verified and not rejected:
        semantic_entailment = "passed"
    elif verified:
        semantic_entailment = "partial"
    else:
        semantic_entailment = "failed"
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return SemanticVerificationOutcome(
        original_draft=original_draft,
        verified_statements=tuple(verified),
        rejected_statements=tuple(rejected),
        verification_results=raw_results,
        claims_for_finalizer=tuple(filtered_claims),
        semantic_entailment=semantic_entailment,
        grounded=bool(verified),
        warning=(
            "Some provenance-valid statements failed semantic verification and "
            "were excluded from the rendered synthesis."
            if rejected
            else ""
        ),
        verification_ms=elapsed_ms,
        diagnostics={
            "semantic_verifier_available": True,
            "semantic_verifier_error": None,
            "statements_passed_to_verifier": len(inputs),
            "semantic_verification_results": [
                item.to_dict() for item in raw_results
            ],
            **_semantic_audit_diagnostics(
                original_draft=original_draft,
                inputs=inputs,
                results=raw_results,
            ),
        },
    )


def build_finalizer_draft(outcome: SemanticVerificationOutcome) -> GroundedDraft:
    """Create finalizer projection without mutating provenance audit data."""
    return replace(
        outcome.original_draft,
        validated_claims=outcome.claims_for_finalizer,
        semantic_entailment=outcome.semantic_entailment,
    )
