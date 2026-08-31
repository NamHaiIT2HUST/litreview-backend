from __future__ import annotations

import uuid

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.grounding.interface import GroundedDraft
from src.synthesis.fast_v2.grounding.manifest import (
    ValidatedClaim,
    ValidatedStatement,
    ValidatedSupport,
)
from src.synthesis.fast_v2.grounding.semantic import (
    DeterministicFakeSemanticVerifier,
    HostedBatchSemanticVerifier,
    SemanticStatementInput,
    SemanticVerdict,
    SemanticVerifierError,
    build_finalizer_draft,
    build_semantic_verifier_context,
    parse_semantic_verdict,
    verify_and_filter_statements,
)

PAPER_A = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _unit(text: str, page: int) -> EvidenceUnit:
    return EvidenceUnit.from_chunk(
        paper_id=PAPER_A,
        title="Paper A",
        page=page,
        text=text,
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
        page_char_start=0,
        page_char_end=len(text),
    ).with_dimension("formulation", 1.0)


def _support(unit: EvidenceUnit) -> ValidatedSupport:
    return ValidatedSupport(
        evidence_id=unit.evidence_id,
        paper_id=unit.paper_id,
        support_quote=unit.text,
        quote_char_start=0,
        quote_char_end=len(unit.text),
        source_char_start=unit.page_char_start,
        source_char_end=unit.page_char_end,
    )


def _draft(*statements: ValidatedStatement) -> GroundedDraft:
    return GroundedDraft(
        draft=GeneratedDraft(
            text='{"claims":[]}',
            model_name="fake",
            prompt_version="v2",
        ),
        validated_claims=(
            ValidatedClaim(
                facet="formulation",
                is_comparative=False,
                statements=tuple(statements),
            ),
        ),
        structured_provenance_validation="passed",
        semantic_entailment="unvalidated",
    )


def _bank(*units: EvidenceUnit) -> GroundedEvidenceBank:
    return GroundedEvidenceBank.build(
        question="Q",
        dimensions=("formulation",),
        evidence_by_dimension={"formulation": units},
    )


def test_one_batch_statement_uses_all_declared_evidence_units():
    first = _unit("First source supplies one part.", 1)
    second = _unit("Second source supplies the remaining part.", 2)
    statement = ValidatedStatement(
        claim_text="Combined factual statement.",
        paper_id=PAPER_A,
        supports=(_support(first), _support(second)),
    )
    provenance = _draft(statement)
    verifier = DeterministicFakeSemanticVerifier()

    outcome = verify_and_filter_statements(
        original_draft=provenance,
        evidence_bank=_bank(first, second),
        verifier=verifier,
    )

    assert verifier.calls == 1
    assert len(verifier.last_inputs) == 1
    assert [unit.evidence_id for unit in verifier.last_inputs[0].evidence_units] == [
        first.evidence_id,
        second.evidence_id,
    ]
    assert outcome.original_draft is provenance
    assert outcome.verified_statements == (statement,)
    assert outcome.rejected_statements == ()
    assert outcome.semantic_entailment == "passed"
    assert outcome.grounded is True
    assert outcome.diagnostics["statements_passed_to_verifier"] == 1


def test_shared_verifier_context_dedupes_only_referenced_evidence_in_first_use_order():
    first = _unit("First source supplies one part.", 1)
    second = _unit("Second source supplies the remaining part.", 2)
    unrelated = _unit("This bank evidence is unrelated to both statements.", 3)
    statements = (
        ValidatedStatement(
            claim_text="Combined factual statement.",
            paper_id=PAPER_A,
            supports=(_support(first), _support(second)),
        ),
        ValidatedStatement(
            claim_text="Second factual statement.",
            paper_id=PAPER_A,
            supports=(_support(second),),
        ),
    )
    verifier = DeterministicFakeSemanticVerifier()

    verify_and_filter_statements(
        original_draft=_draft(*statements),
        evidence_bank=_bank(first, second, unrelated),
        verifier=verifier,
    )
    context = build_semantic_verifier_context(verifier.last_inputs)

    assert [item["evidence_ids"] for item in context["statements"]] == [
        [first.evidence_id, second.evidence_id],
        [second.evidence_id],
    ]
    assert [item["evidence_id"] for item in context["evidence_units"]] == [
        first.evidence_id,
        second.evidence_id,
    ]
    assert unrelated.evidence_id not in {
        item["evidence_id"] for item in context["evidence_units"]
    }
    assert context["evidence_units"][0]["text"] == first.text
    assert "evidence" not in context["statements"][0]
    assert verifier.calls == 1


def test_real_verdicts_filter_only_supported_statements_and_preserve_audit():
    units = tuple(_unit(f"Source {index}.", index) for index in range(1, 4))
    statements = tuple(
        ValidatedStatement(
            claim_text=f"Claim {index}.",
            paper_id=PAPER_A,
            supports=(_support(unit),),
        )
        for index, unit in enumerate(units)
    )
    provenance = _draft(*statements)
    verifier = DeterministicFakeSemanticVerifier(
        verdicts={
            (0, 0): SemanticVerdict.supported,
            (0, 1): SemanticVerdict.partial,
            (0, 2): SemanticVerdict.unsupported,
        }
    )

    outcome = verify_and_filter_statements(
        original_draft=provenance,
        evidence_bank=_bank(*units),
        verifier=verifier,
    )

    assert outcome.original_draft.validated_claims[0].statements == statements
    assert outcome.verified_statements == (statements[0],)
    assert outcome.rejected_statements == statements[1:]
    assert [result.verdict for result in outcome.verification_results] == [
        SemanticVerdict.supported,
        SemanticVerdict.partial,
        SemanticVerdict.unsupported,
    ]
    assert outcome.claims_for_finalizer[0].statements == (statements[0],)
    assert outcome.semantic_entailment == "partial"
    assert outcome.grounded is True


@pytest.mark.parametrize(
    "verifier",
    [None, DeterministicFakeSemanticVerifier(error=TimeoutError("timeout"))],
)
def test_unavailable_or_failed_verifier_keeps_original_output_unverified(verifier):
    unit = _unit("Canonical evidence.", 1)
    statement = ValidatedStatement(
        claim_text="Original synthesis statement.",
        paper_id=PAPER_A,
        supports=(_support(unit),),
    )
    provenance = _draft(statement)

    outcome = verify_and_filter_statements(
        original_draft=provenance,
        evidence_bank=_bank(unit),
        verifier=verifier,
    )
    finalizer_draft = build_finalizer_draft(outcome)

    assert outcome.original_draft is provenance
    assert outcome.verified_statements == ()
    assert outcome.rejected_statements == ()
    assert outcome.claims_for_finalizer == provenance.validated_claims
    assert outcome.verification_results[0].verdict is SemanticVerdict.unverified
    assert outcome.semantic_entailment == "unverified"
    assert outcome.grounded is False
    assert outcome.warning
    assert outcome.diagnostics["statements_passed_to_verifier"] == (
        0 if verifier is None else 1
    )
    assert finalizer_draft is not provenance
    assert finalizer_draft.validated_claims == provenance.validated_claims
    assert provenance.semantic_entailment == "unvalidated"


def test_no_supported_statements_is_failed_and_not_grounded():
    unit = _unit("Canonical evidence.", 1)
    statement = ValidatedStatement(
        claim_text="Unsupported statement.",
        paper_id=PAPER_A,
        supports=(_support(unit),),
    )
    outcome = verify_and_filter_statements(
        original_draft=_draft(statement),
        evidence_bank=_bank(unit),
        verifier=DeterministicFakeSemanticVerifier(
            verdicts={(0, 0): SemanticVerdict.unsupported}
        ),
    )

    assert outcome.claims_for_finalizer == ()
    assert outcome.semantic_entailment == "failed"
    assert outcome.grounded is False


@pytest.mark.parametrize(
    ("provider_value", "expected"),
    [
        ("supported", SemanticVerdict.supported),
        (" SUPPORTED ", SemanticVerdict.supported),
        ("Partial", SemanticVerdict.partial),
        ("unsupported\n", SemanticVerdict.unsupported),
    ],
)
def test_provider_verdict_formatting_preserves_valid_semantic_labels(
    provider_value, expected
):
    assert parse_semantic_verdict(provider_value) is expected


def test_provider_verdict_parser_still_rejects_unknown_labels():
    with pytest.raises(ValueError):
        parse_semantic_verdict("mostly_supported")


def test_previously_supported_claim_with_all_referenced_evidence_survives():
    formulation = _unit(
        "The split feasibility problem seeks x in C such that Ax belongs to Q.",
        1,
    )
    setting = _unit(
        "C and Q are nonempty closed convex subsets of Hilbert spaces.",
        2,
    )
    statement = ValidatedStatement(
        claim_text=(
            "The split feasibility problem seeks x in a closed convex set C "
            "such that Ax belongs to a closed convex set Q in Hilbert spaces."
        ),
        paper_id=PAPER_A,
        supports=(_support(formulation), _support(setting)),
    )

    outcome = verify_and_filter_statements(
        original_draft=_draft(statement),
        evidence_bank=_bank(formulation, setting),
        verifier=DeterministicFakeSemanticVerifier(
            verdicts={(0, 0): parse_semantic_verdict(" SUPPORTED ")}
        ),
    )

    assert outcome.semantic_entailment == "passed"
    assert outcome.verified_statements == (statement,)


class _HostedVerifierResponse:
    status_code = 200

    def json(self):
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": (
                            '{"results":['
                            '{"claim_index":0,"statement_index":0,'
                            '"verdict":" SUPPORTED ","reason":"Fully supported."}'
                            "]}"
                        )
                    },
                }
            ],
            "usage": {"prompt_tokens": 321, "completion_tokens": 45},
        }


class _HostedVerifierClient:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []

    def post(self, url, *, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.error is not None:
            raise self.error
        return _HostedVerifierResponse()


def test_hosted_semantic_verifier_uses_one_compact_batch_and_parses_supported():
    evidence = _unit("The stated formulation is supported by this evidence.", 1)
    statement = SemanticStatementInput(
        claim_index=0,
        statement_index=0,
        claim_text="The stated formulation is supported.",
        paper_id=PAPER_A,
        facet="formulation",
        evidence_units=(evidence,),
    )
    client = _HostedVerifierClient()
    verifier = HostedBatchSemanticVerifier(
        base_url="https://verifier.invalid/v1",
        api_key="verifier-secret",
        model="verifier-model",
        http_client_factory=lambda: client,
    )

    results = verifier.verify_batch((statement,))

    assert verifier.calls == 1
    assert len(client.calls) == 1
    assert results[0].verdict is SemanticVerdict.supported
    assert verifier.finish_reason == "stop"
    assert verifier.token_usage == {"prompt_tokens": 321, "completion_tokens": 45}
    payload = client.calls[0]["json"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["temperature"] == 0.0
    user_content = payload["messages"][1]["content"]
    assert "resolve every value in its evidence_ids array" in user_content
    assert user_content.count(evidence.text) == 1


def test_hosted_semantic_verifier_failure_never_exposes_secret():
    evidence = _unit("Evidence.", 1)
    statement = SemanticStatementInput(
        claim_index=0,
        statement_index=0,
        claim_text="Claim.",
        paper_id=PAPER_A,
        facet="formulation",
        evidence_units=(evidence,),
    )
    secret = "verifier-secret-do-not-leak"
    client = _HostedVerifierClient(
        error=RuntimeError(f"Authorization: Bearer {secret}")
    )
    verifier = HostedBatchSemanticVerifier(
        base_url="https://verifier.invalid/v1",
        api_key=secret,
        model="verifier-model",
        http_client_factory=lambda: client,
    )

    with pytest.raises(SemanticVerifierError) as exc_info:
        verifier.verify_batch((statement,))

    assert secret not in str(exc_info.value)
    assert "Authorization" not in str(exc_info.value)
