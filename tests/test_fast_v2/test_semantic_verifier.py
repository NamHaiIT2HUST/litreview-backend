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
    SemanticVerdict,
    build_semantic_verifier_context,
    build_finalizer_draft,
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
