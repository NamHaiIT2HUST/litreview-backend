from __future__ import annotations

import uuid
import json

import pytest

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.grounding.manifest import (
    ClaimManifest,
    ClaimStatement,
    ClaimSupport,
    GeneratedClaim,
    StructuredClaimManifestGuard,
    ClaimManifestParseError,
    parse_claim_manifest,
)
from src.synthesis.fast_v2.generator.base import GeneratedDraft
from src.synthesis.fast_v2.generator.prompt import PROMPT_VERSION, build_prompt
from src.synthesis.fast_v2.grounding.interface import (
    StructuredClaimManifestGroundingService,
)
from src.synthesis.fast_v2.citations.finalizer import finalize_structured_draft


PAPER_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
PAPER_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _unit(*, paper_id: uuid.UUID, title: str, text: str, facet: str) -> EvidenceUnit:
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=title,
        page=4,
        text=text,
        source_chunk_id=uuid.uuid4(),
        page_text_id=uuid.uuid4(),
        page_char_start=100,
        page_char_end=100 + len(text),
    ).with_dimension(facet, 1.0)


def _bank(*units: EvidenceUnit) -> GroundedEvidenceBank:
    by_facet: dict[str, list[EvidenceUnit]] = {}
    for unit in units:
        for facet in unit.selected_for_dimensions:
            by_facet.setdefault(facet, []).append(unit)
    return GroundedEvidenceBank.build(
        question="How do the papers differ?",
        dimensions=list(by_facet),
        evidence_by_dimension=by_facet,
    )


def test_valid_single_paper_claim_gets_unique_exact_quote_offsets():
    unit = _unit(
        paper_id=PAPER_A,
        title="Paper A",
        text="Prefix. The algorithm converges weakly. Suffix.",
        facet="convergence",
    )
    manifest = ClaimManifest(
        claims=(
            GeneratedClaim(
                facet="convergence",
                is_comparative=False,
                statements=(
                    ClaimStatement(
                        claim_text="The algorithm converges weakly.",
                        paper_id=PAPER_A,
                        supports=(
                            ClaimSupport(
                                evidence_id=unit.evidence_id,
                                support_quote="The algorithm converges weakly.",
                            ),
                        ),
                    ),
                ),
            ),
        )
    )

    result = StructuredClaimManifestGuard().validate(
        manifest=manifest,
        evidence_bank=_bank(unit),
    )

    assert result.structured_provenance_validation == "passed"
    assert result.semantic_entailment == "unvalidated"
    assert len(result.valid_claims) == 1
    support = result.valid_claims[0].statements[0].supports[0]
    assert support.quote_char_start == 8
    assert support.quote_char_end == 39
    assert support.source_char_start == 108
    assert support.source_char_end == 139
    assert result.dropped_claims == ()


def _statement(
    *,
    paper_id: uuid.UUID,
    evidence_id: str,
    quote: str,
    text: str = "A factual claim.",
) -> ClaimStatement:
    return ClaimStatement(
        claim_text=text,
        paper_id=paper_id,
        supports=(ClaimSupport(evidence_id=evidence_id, support_quote=quote),),
    )


def _manifest(*statements: ClaimStatement, facet="formulation", comparative=False):
    return ClaimManifest(
        claims=(
            GeneratedClaim(
                facet=facet,
                is_comparative=comparative,
                statements=tuple(statements),
            ),
        )
    )


def _validate(manifest: ClaimManifest, *units: EvidenceUnit):
    return StructuredClaimManifestGuard().validate(
        manifest=manifest,
        evidence_bank=_bank(*units),
    )


def test_valid_comparative_claim_requires_and_accepts_both_papers():
    a = _unit(paper_id=PAPER_A, title="A", text="Paper A uses projections.", facet="algorithms")
    b = _unit(paper_id=PAPER_B, title="B", text="Paper B uses MM.", facet="algorithms")

    result = _validate(
        _manifest(
            _statement(paper_id=PAPER_A, evidence_id=a.evidence_id, quote=a.text),
            _statement(paper_id=PAPER_B, evidence_id=b.evidence_id, quote=b.text),
            facet="algorithms",
            comparative=True,
        ),
        a,
        b,
    )

    assert len(result.valid_claims) == 1
    assert {s.paper_id for s in result.valid_claims[0].statements} == {PAPER_A, PAPER_B}


def test_unknown_evidence_id_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Exact quote.", facet="formulation")
    result = _validate(
        _manifest(_statement(paper_id=PAPER_A, evidence_id="ev-missing", quote="Exact quote.")),
        unit,
    )
    assert result.valid_claims == ()
    assert "unknown_evidence_id" in result.dropped_claims[0].reasons


def test_evidence_owned_by_wrong_paper_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Exact quote.", facet="formulation")
    result = _validate(
        _manifest(_statement(paper_id=PAPER_B, evidence_id=unit.evidence_id, quote="Exact quote.")),
        unit,
    )
    assert result.valid_claims == ()
    assert "wrong_paper" in result.dropped_claims[0].reasons


def test_quote_absent_from_evidence_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Actual source text.", facet="formulation")
    result = _validate(
        _manifest(_statement(paper_id=PAPER_A, evidence_id=unit.evidence_id, quote="Fabricated quote.")),
        unit,
    )
    assert result.valid_claims == ()
    assert "support_quote_not_found" in result.dropped_claims[0].reasons


def test_repeated_exact_quote_is_ambiguous_and_drops_claim():
    unit = _unit(
        paper_id=PAPER_A,
        title="A",
        text="same quote; intervening text; same quote",
        facet="formulation",
    )
    result = _validate(
        _manifest(_statement(paper_id=PAPER_A, evidence_id=unit.evidence_id, quote="same quote")),
        unit,
    )
    assert result.valid_claims == ()
    assert "ambiguous_support_quote" in result.dropped_claims[0].reasons


def test_longer_quote_that_occurs_once_resolves_ambiguity():
    unit = _unit(
        paper_id=PAPER_A,
        title="A",
        text="same quote; intervening text; same quote",
        facet="formulation",
    )
    result = _validate(
        _manifest(
            _statement(
                paper_id=PAPER_A,
                evidence_id=unit.evidence_id,
                quote="same quote; intervening text",
            )
        ),
        unit,
    )
    assert len(result.valid_claims) == 1


def test_factual_statement_without_support_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    manifest = _manifest(
        ClaimStatement(claim_text="Uncited fact.", paper_id=PAPER_A, supports=())
    )
    result = _validate(manifest, unit)
    assert result.valid_claims == ()
    assert "missing_support" in result.dropped_claims[0].reasons


def test_comparative_claim_missing_one_paper_side_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Paper A evidence.", facet="formulation")
    result = _validate(
        _manifest(
            _statement(paper_id=PAPER_A, evidence_id=unit.evidence_id, quote=unit.text),
            comparative=True,
        ),
        unit,
    )
    assert result.valid_claims == ()
    assert "comparative_paper_coverage" in result.dropped_claims[0].reasons


def test_invalid_facet_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    result = _validate(
        _manifest(
            _statement(paper_id=PAPER_A, evidence_id=unit.evidence_id, quote=unit.text),
            facet="future_work",
        ),
        unit,
    )
    assert result.valid_claims == ()
    assert "invalid_facet" in result.dropped_claims[0].reasons


def test_duplicate_evidence_support_in_one_statement_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    support = ClaimSupport(evidence_id=unit.evidence_id, support_quote=unit.text)
    manifest = _manifest(
        ClaimStatement(
            claim_text="Fact.",
            paper_id=PAPER_A,
            supports=(support, support),
        )
    )
    result = _validate(manifest, unit)
    assert result.valid_claims == ()
    assert "duplicate_evidence_support" in result.dropped_claims[0].reasons


def test_native_model_citation_marker_in_claim_text_drops_claim():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    result = _validate(
        _manifest(
            _statement(
                paper_id=PAPER_A,
                evidence_id=unit.evidence_id,
                quote=unit.text,
                text="Fabricated native citation [0].",
            )
        ),
        unit,
    )
    assert result.valid_claims == ()
    assert "native_citation_marker" in result.dropped_claims[0].reasons


def _manifest_json(unit: EvidenceUnit) -> str:
    return json.dumps(
        {
            "claims": [
                {
                    "facet": "formulation",
                    "is_comparative": False,
                    "statements": [
                        {
                            "claim_text": "A factual claim.",
                            "paper_id": str(unit.paper_id),
                            "supports": [
                                {
                                    "evidence_id": unit.evidence_id,
                                    "support_quote": unit.text,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )


def test_strict_parser_builds_typed_manifest():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    manifest = parse_claim_manifest(_manifest_json(unit))
    assert manifest.claims[0].statements[0].paper_id == PAPER_A
    assert manifest.claims[0].statements[0].supports[0].evidence_id == unit.evidence_id


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        '{"claims": [], "unexpected": true}',
        '{"claims": [{"facet": "formulation"}]}',
        '{"claims": "not-a-list"}',
    ],
)
def test_strict_parser_rejects_malformed_or_extra_fields(payload):
    with pytest.raises(ClaimManifestParseError):
        parse_claim_manifest(payload)


def test_generated_draft_exposes_claim_manifest():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    manifest = parse_claim_manifest(_manifest_json(unit))
    draft = GeneratedDraft(
        text=_manifest_json(unit),
        model_name="fake",
        prompt_version="structured-v1",
        claim_manifest=manifest,
    )
    assert draft.claim_manifest is manifest
    assert draft.to_dict()["claim_manifest"]["claims"][0]["facet"] == "formulation"


def test_structured_prompt_exposes_stable_ids_raw_text_and_manifest_schema():
    unit = _unit(
        paper_id=PAPER_A,
        title="A",
        text="Raw source citation [27] remains exact.",
        facet="formulation",
    )
    prompt = build_prompt(question="Q", evidence=(unit,), dimensions=("formulation",))
    assert unit.evidence_id in prompt
    assert str(PAPER_A) in prompt
    assert unit.text in prompt
    assert '"claims"' in prompt
    assert '"support_quote"' in prompt
    assert "Return exactly one JSON object" in prompt


def test_structured_prompt_has_new_contract_version():
    assert PROMPT_VERSION == "p165_structured_claim_manifest_v1"


def _draft_with_manifest(manifest: ClaimManifest, *, text="untrusted raw [0]"):
    return GeneratedDraft(
        text=text,
        model_name="fake",
        prompt_version=PROMPT_VERSION,
        claim_manifest=manifest,
        native_citation_indices=(0,),
    )


def test_grounding_service_reports_structural_provenance_not_semantic_grounding():
    unit = _unit(paper_id=PAPER_A, title="A", text="Exact source quote.", facet="formulation")
    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(
            _manifest(_statement(paper_id=PAPER_A, evidence_id=unit.evidence_id, quote=unit.text))
        ),
        evidence_bank=_bank(unit),
    )
    assert grounded.structured_provenance_validation == "passed"
    assert grounded.semantic_entailment == "unvalidated"
    assert grounded.grounded is False
    assert len(grounded.validated_claims) == 1


def test_grounding_diagnostics_preserve_manifest_and_nested_validation_failures():
    unit = _unit(
        paper_id=PAPER_A,
        title="A",
        text="Exact source quote.",
        facet="formulation",
    )
    manifest = _manifest(
        ClaimStatement(
            claim_text="Generated claim with native citation [9].",
            paper_id=PAPER_B,
            supports=(
                ClaimSupport(
                    evidence_id="ev-missing",
                    support_quote="Missing source quote.",
                ),
                ClaimSupport(
                    evidence_id=unit.evidence_id,
                    support_quote=unit.text,
                ),
                ClaimSupport(
                    evidence_id=unit.evidence_id,
                    support_quote=unit.text,
                ),
            ),
        )
    )

    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(manifest),
        evidence_bank=_bank(unit),
    )

    assert grounded.diagnostics["parsed_claim_manifest"] == manifest.to_dict()
    assert grounded.diagnostics["claim_validation"] == [
        {
            "claim_index": 0,
            "facet": "formulation",
            "is_comparative": False,
            "statement_count": 1,
            "status": "dropped",
            "drop_reasons": [
                "native_citation_marker",
                "duplicate_evidence_support",
                "unknown_evidence_id",
                "wrong_paper",
            ],
            "statements": [
                {
                    "statement_index": 0,
                    "paper_id": str(PAPER_B),
                    "support_count": 3,
                    "failures": [
                        "native_citation_marker",
                        "duplicate_evidence_support",
                    ],
                    "supports": [
                        {
                            "support_index": 0,
                            "evidence_id": "ev-missing",
                            "failures": ["unknown_evidence_id"],
                        },
                        {
                            "support_index": 1,
                            "evidence_id": unit.evidence_id,
                            "failures": ["wrong_paper"],
                        },
                        {
                            "support_index": 2,
                            "evidence_id": unit.evidence_id,
                            "failures": ["wrong_paper"],
                        },
                    ],
                }
            ],
        }
    ]


def test_grounding_service_fails_closed_when_manifest_is_missing():
    unit = _unit(paper_id=PAPER_A, title="A", text="Exact source quote.", facet="formulation")
    draft = GeneratedDraft(text="free prose [0]", model_name="fake", prompt_version="old")
    with pytest.raises(ValueError, match="claim manifest"):
        StructuredClaimManifestGroundingService().evaluate(
            draft=draft,
            evidence_bank=_bank(unit),
        )


def test_structured_finalizer_ignores_raw_text_and_uses_validated_support_only():
    unit = _unit(
        paper_id=PAPER_A,
        title="A",
        text="Prefix. Exact support. Suffix.",
        facet="formulation",
    )
    manifest = _manifest(
        _statement(
            paper_id=PAPER_A,
            evidence_id=unit.evidence_id,
            quote="Exact support.",
            text="Validated claim.",
        )
    )
    bank = _bank(unit)
    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(manifest), evidence_bank=bank
    )
    finalized = finalize_structured_draft(grounded=grounded, evidence_bank=bank)

    assert "Validated claim." in finalized.text
    assert "untrusted raw" not in finalized.text
    assert finalized.text.count("[1]") == 1
    assert finalized.citation_authority == "p165_deterministic_finalizer"
    assert finalized.citations[0].evidence_id == unit.evidence_id
    assert finalized.citations[0].quoted_snippet == "Exact support."
    assert finalized.citations[0].source_char_start == 108
    assert finalized.citations[0].source_char_end == 122
    assert finalized.rejected_native_indices == (0,)
    citation = finalized.citations[0]
    assert finalized.text[citation.review_char_start:citation.review_char_end] == "[1]"
    replay = finalize_structured_draft(grounded=grounded, evidence_bank=bank)
    assert replay.text == finalized.text
    assert replay.citations == finalized.citations


def test_structured_finalizer_places_each_comparative_side_citation_locally():
    a = _unit(paper_id=PAPER_A, title="A", text="A exact quote.", facet="algorithms")
    b = _unit(paper_id=PAPER_B, title="B", text="B exact quote.", facet="algorithms")
    manifest = _manifest(
        _statement(
            paper_id=PAPER_A,
            evidence_id=a.evidence_id,
            quote=a.text,
            text="Paper A uses projections.",
        ),
        _statement(
            paper_id=PAPER_B,
            evidence_id=b.evidence_id,
            quote=b.text,
            text="Paper B uses MM.",
        ),
        facet="algorithms",
        comparative=True,
    )
    bank = _bank(a, b)
    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(manifest, text="{}"), evidence_bank=bank
    )
    finalized = finalize_structured_draft(grounded=grounded, evidence_bank=bank)
    assert "Paper A uses projections. [1]" in finalized.text
    assert "Paper B uses MM. [2]" in finalized.text
    assert [citation.paper_id for citation in finalized.citations] == [PAPER_A, PAPER_B]


def test_structured_finalizer_groups_and_exact_dedupes_realistic_comparison():
    facet_order = ("formulation", "algorithms", "assumptions", "convergence")
    source_text = {
        "formulation": (
            "Xu2010 studies a split feasibility model with a linear operator.",
            "Xu2018 formulates the model using a smooth nonlinear mapping.",
        ),
        "algorithms": (
            "Xu2010 applies a projection-based iteration.",
            "Xu2018 instead uses a majorization-minimization iteration.",
        ),
        "assumptions": (
            "Xu2010 assumes closed convex constraint sets and a linear operator.",
            "Xu2018 allows a smooth nonlinear mapping between closed convex sets.",
        ),
        "convergence": (
            "Xu2010 establishes convergence for its linear setting.",
            "Xu2018 states global convergence under mild assumptions.",
        ),
    }
    units_by_facet = {
        facet: (
            _unit(paper_id=PAPER_A, title="Xu2010", text=texts[0], facet=facet),
            _unit(paper_id=PAPER_B, title="Xu2018", text=texts[1], facet=facet),
        )
        for facet, texts in source_text.items()
    }
    bank = GroundedEvidenceBank.build(
        question="How do Xu2010 and Xu2018 differ?",
        dimensions=facet_order,
        evidence_by_dimension={facet: units_by_facet[facet] for facet in facet_order},
    )

    def comparative_claim(facet: str) -> GeneratedClaim:
        a, b = units_by_facet[facet]
        return GeneratedClaim(
            facet=facet,
            is_comparative=True,
            statements=(
                _statement(
                    paper_id=PAPER_A,
                    evidence_id=a.evidence_id,
                    quote=a.text,
                    text=source_text[facet][0],
                ),
                _statement(
                    paper_id=PAPER_B,
                    evidence_id=b.evidence_id,
                    quote=b.text,
                    text=source_text[facet][1],
                ),
            ),
        )

    # Deliberately interleaved with an exact duplicate formulation group:
    # renderer must use bank facet order and render the group only once.
    manifest = ClaimManifest(
        claims=(
            comparative_claim("algorithms"),
            comparative_claim("formulation"),
            comparative_claim("assumptions"),
            comparative_claim("convergence"),
            comparative_claim("formulation"),
        )
    )
    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(manifest, text="untrusted raw prose"),
        evidence_bank=bank,
    )

    finalized = finalize_structured_draft(grounded=grounded, evidence_bank=bank)

    expected = """**Formulation**

Xu2010 studies a split feasibility model with a linear operator. [1] Xu2018 formulates the model using a smooth nonlinear mapping. [2]

**Algorithms**

Xu2010 applies a projection-based iteration. [1] Xu2018 instead uses a majorization-minimization iteration. [2]

**Assumptions**

Xu2010 assumes closed convex constraint sets and a linear operator. [1] Xu2018 allows a smooth nonlinear mapping between closed convex sets. [2]

**Convergence**

Xu2010 establishes convergence for its linear setting. [1] Xu2018 states global convergence under mild assumptions. [2]"""
    assert finalized.text == expected
    for facet in facet_order:
        assert finalized.text.count(f"**{facet.title()}**") == 1
    assert "By contrast" not in finalized.text
    assert "untrusted raw prose" not in finalized.text
    assert [citation.paper_id for citation in finalized.citations] == [
        PAPER_A,
        PAPER_B,
        PAPER_A,
        PAPER_B,
        PAPER_A,
        PAPER_B,
        PAPER_A,
        PAPER_B,
    ]


def test_all_invalid_claims_render_insufficient_information_without_citations():
    unit = _unit(paper_id=PAPER_A, title="A", text="Source.", facet="formulation")
    invalid = _manifest(
        _statement(paper_id=PAPER_A, evidence_id="ev-unknown", quote="Source.")
    )
    bank = _bank(unit)
    grounded = StructuredClaimManifestGroundingService().evaluate(
        draft=_draft_with_manifest(invalid), evidence_bank=bank
    )
    finalized = finalize_structured_draft(grounded=grounded, evidence_bank=bank)
    assert finalized.text == "Insufficient validated evidence to answer the question."
    assert finalized.citations == ()
