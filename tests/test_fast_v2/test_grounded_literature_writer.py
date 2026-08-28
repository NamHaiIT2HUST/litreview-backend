from __future__ import annotations

import json
import uuid

import pytest

from src.synthesis.fast_v2.citations.finalizer import finalize_structured_draft
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
    verify_and_filter_statements,
)
from src.synthesis.fast_v2.writer import (
    DeterministicFakeLiteratureWriter,
    HostedGroundedLiteratureWriter,
    WRITER_PROMPT_PATH,
    WriterClaim,
    WriterValidationError,
    _parse_and_validate,
    apply_grounded_literature_writer,
)


PAPER_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
PAPER_B = uuid.UUID("22222222-2222-2222-2222-222222222222")
FACET = "problem formulation"


def _unit(paper_id: uuid.UUID, title: str, text: str) -> EvidenceUnit:
    return EvidenceUnit.from_chunk(
        paper_id=paper_id,
        title=title,
        page=1,
        text=text,
        source_chunk_id=uuid.uuid4(),
    )


def _semantic_fixture(
    *, second_verdict: SemanticVerdict = SemanticVerdict.supported
):
    units = (
        _unit(PAPER_A, "Paper A", "Paper A defines a convex feasibility model."),
        _unit(PAPER_B, "Paper B", "Paper B defines a non-convex optimization model."),
    )
    bank = GroundedEvidenceBank(
        question="How do the models differ?",
        dimensions=(FACET,),
        evidence=units,
    )
    statements = tuple(
        ValidatedStatement(
            claim_text=unit.text,
            paper_id=unit.paper_id,
            supports=(
                ValidatedSupport(
                    evidence_id=unit.evidence_id,
                    paper_id=unit.paper_id,
                    support_quote=unit.text,
                    quote_char_start=0,
                    quote_char_end=len(unit.text),
                    source_char_start=None,
                    source_char_end=None,
                ),
            ),
        )
        for unit in units
    )
    draft = GroundedDraft(
        draft=GeneratedDraft(
            text="",
            model_name="fake",
            prompt_version="test",
            generation_calls=1,
        ),
        validated_claims=(
            ValidatedClaim(
                facet=FACET,
                is_comparative=True,
                statements=statements,
            ),
        ),
        structured_provenance_validation="passed",
    )
    semantic = verify_and_filter_statements(
        original_draft=draft,
        evidence_bank=bank,
        verifier=DeterministicFakeSemanticVerifier(
            verdicts={(0, 1): second_verdict}
        ),
    )
    return bank, semantic


def _response(*paragraphs: dict) -> str:
    return json.dumps(
        {
            "sections": [
                {
                    "title": "Problem Formulation",
                    "paragraphs": list(paragraphs),
                }
            ]
        }
    )


def test_valid_writer_json_is_accepted_and_projected_for_existing_finalizer():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=_response(
            {
                "text": "The verified works use convex and non-convex formulations.",
                "supporting_claim_ids": ["claim_0_0", "claim_0_1"],
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.writer_fallback_reason is None
    assert outcome.writer_calls == 1
    assert outcome.finalizer_draft.validated_claims[0].statements[0].claim_text == (
        "The verified works use convex and non-convex formulations."
    )
    assert {
        support.evidence_id
        for support in outcome.finalizer_draft.validated_claims[0].statements[0].supports
    } == {unit.evidence_id for unit in bank.evidence}
    assert outcome.claim_coverage == {
        "expected": 2,
        "used_unique": 2,
        "references_total": 2,
        "missing": [],
        "duplicates": [],
        "coverage_percent": 100.0,
    }
    finalized = finalize_structured_draft(
        grounded=outcome.finalizer_draft,
        evidence_bank=bank,
    )
    assert {citation.paper_id for citation in finalized.citations} == {
        PAPER_A,
        PAPER_B,
    }


def test_writer_claim_includes_only_its_verified_evidence_snippet():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=_response(
            {
                "text": "Paper A defines a convex feasibility model.",
                "supporting_claim_ids": ["claim_0_0"],
            },
            {
                "text": "Paper B defines a non-convex optimization model.",
                "supporting_claim_ids": ["claim_0_1"],
            },
        )
    )

    apply_grounded_literature_writer(
        semantic=semantic, evidence_bank=bank, writer=writer
    )

    payload = [claim.to_prompt_dict() for claim in writer.last_claims]
    assert payload[0]["evidence_snippets"] == [
        {"evidence_id": bank.evidence[0].evidence_id, "page": 1, "text": bank.evidence[0].text}
    ]
    assert payload[1]["evidence_snippets"] == [
        {"evidence_id": bank.evidence[1].evidence_id, "page": 1, "text": bank.evidence[1].text}
    ]


def test_section_title_alias_normalizes_before_strict_validation():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "section_title": "Problem Formulation",
                        "paragraphs": [
                            {
                                "text": "The verified works use convex and non-convex formulations.",
                                "supporting_claim_ids": [
                                    "claim_0_0",
                                    "claim_0_1",
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.writer_fallback_reason is None
    assert outcome.document.sections[0].title == "Problem Formulation"


def test_unknown_section_field_still_fails_strict_validation():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "title": "Problem Formulation",
                        "heading": "Unexpected alias",
                        "paragraphs": [
                            {
                                "text": "The verified works use convex and non-convex formulations.",
                                "supporting_claim_ids": [
                                    "claim_0_0",
                                    "claim_0_1",
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert "invalid_schema" in outcome.writer_fallback_reason


@pytest.mark.parametrize(
    ("claim_ids", "reason"),
    [
        (["claim_0_0", "claim_unknown"], "unknown_claim_id"),
        (["claim_0_0"], "missing_claim_coverage"),
        (["claim_0_0", "claim_0_0", "claim_0_1"], "duplicate_claim_id"),
    ],
)
def test_invalid_claim_references_fail_closed_to_provenance_draft(claim_ids, reason):
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=_response(
            {
                "text": "A conservative synthesis sentence.",
                "supporting_claim_ids": claim_ids,
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.finalizer_draft == semantic.original_draft.__class__(
        **{
            **semantic.original_draft.__dict__,
            "validated_claims": semantic.claims_for_finalizer,
            "semantic_entailment": semantic.semantic_entailment,
        }
    )
    assert reason in outcome.writer_fallback_reason


def test_unsupported_section_title_triggers_fallback():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "title": "A Revolutionary Historical Breakthrough",
                        "paragraphs": [
                            {
                                "text": "The works use two formulations.",
                                "supporting_claim_ids": [
                                    "claim_0_0",
                                    "claim_0_1",
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert "unsupported_section_title" in outcome.writer_fallback_reason


@pytest.mark.parametrize(
    "title",
    [
        "Problem Formulations",
        "Methodological Approaches",
        "Algorithmic Approaches",
        "Theoretical Analysis",
        "Theoretical Results and Applications",
        "Convergence Analysis",
        "Experimental Settings",
        "Evaluation Results",
        "Dataset Characteristics",
        "Limitations",
    ],
)
def test_domain_neutral_academic_section_titles_pass(title):
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "title": title,
                        "paragraphs": [
                            {
                                "text": "The verified works use convex and non-convex formulations.",
                                "supporting_claim_ids": [
                                    "claim_0_0",
                                    "claim_0_1",
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.writer_fallback_reason is None


def test_facet_title_with_spaces_matches_snake_case_facet():
    claim = WriterClaim(
        claim_id="claim_0_0",
        facet="general_topic",
        claim_text="A verified general-topic claim.",
        paper_id=PAPER_A,
        paper_title="Paper A",
    )
    content = json.dumps(
        {
            "sections": [
                {
                    "title": "General Topic",
                    "paragraphs": [
                        {
                            "text": claim.claim_text,
                            "supporting_claim_ids": [claim.claim_id],
                        }
                    ],
                }
            ]
        }
    )

    document, coverage = _parse_and_validate(content, (claim,))

    assert document.sections[0].title == "General Topic"
    assert coverage["coverage_percent"] == 100.0


@pytest.mark.parametrize(
    "title",
    [
        "Research Evolution",
        "Historical Development",
        "Advances in the Field",
        "Progress Over Time",
        "Future Directions",
        "Superior Methods",
        "Best Methods",
        "Research Roadmap",
        "Breakthrough Results",
    ],
)
def test_unsupported_historical_or_evaluative_section_titles_fail(title):
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=json.dumps(
            {
                "sections": [
                    {
                        "title": title,
                        "paragraphs": [
                            {
                                "text": "The verified works use convex and non-convex formulations.",
                                "supporting_claim_ids": [
                                    "claim_0_0",
                                    "claim_0_1",
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert "unsupported_section_title" in outcome.writer_fallback_reason


@pytest.mark.parametrize(
    "excluded_verdict",
    [SemanticVerdict.partial, SemanticVerdict.unsupported],
)
def test_writer_receives_only_supported_claims_and_no_evidence_payload(
    excluded_verdict,
):
    bank, semantic = _semantic_fixture(second_verdict=excluded_verdict)
    writer = DeterministicFakeLiteratureWriter(
        content=_response(
            {
                "text": "Paper A defines a convex feasibility model.",
                "supporting_claim_ids": ["claim_0_0"],
            }
        )
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.writer_fallback_reason is None
    assert [claim.claim_id for claim in writer.last_claims] == ["claim_0_0"]
    payload = [claim.to_prompt_dict() for claim in writer.last_claims]
    serialized = json.dumps(payload)
    assert set(payload[0]) == {
        "claim_id",
        "facet",
        "claim_text",
        "paper_id",
        "paper_title",
    }
    assert "evidence_id" not in serialized
    assert "claim_0_1" not in serialized


def test_writer_failure_preserves_existing_finalizer_draft():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(error=RuntimeError("writer offline"))

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert outcome.finalizer_draft.validated_claims == semantic.claims_for_finalizer
    assert outcome.writer_calls == 1
    assert "RuntimeError: writer offline" in outcome.writer_fallback_reason
    assert outcome.writer_input_tokens is None
    assert outcome.writer_output_tokens is None


def test_validation_fallback_preserves_writer_usage_diagnostics():
    bank, semantic = _semantic_fixture()
    writer = DeterministicFakeLiteratureWriter(
        content=_response(
            {
                "text": "Incomplete coverage.",
                "supporting_claim_ids": ["claim_0_0"],
            }
        ),
        input_tokens=123,
        output_tokens=45,
    )

    outcome = apply_grounded_literature_writer(
        semantic=semantic,
        evidence_bank=bank,
        writer=writer,
    )

    assert "missing_claim_coverage" in outcome.writer_fallback_reason
    assert outcome.writer_latency_ms == 0.0
    assert outcome.writer_input_tokens == 123
    assert outcome.writer_output_tokens == 45


class _Response:
    status_code = 200

    def json(self):
        return {
            "choices": [{"message": {"content": '{"sections":[]}'}}],
            "usage": {"prompt_tokens": 88, "completion_tokens": 12},
        }


class _RecordingClient:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls = []

    def post(self, url, *, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.error is not None:
            raise self.error
        return _Response()


def test_hosted_writer_makes_one_call_with_claim_metadata_only():
    client = _RecordingClient()
    writer = HostedGroundedLiteratureWriter(
        base_url="https://writer.invalid/v1",
        api_key="writer-secret",
        model="writer-model",
        http_client_factory=lambda: client,
    )
    claim = WriterClaim(
        claim_id="claim_0_0",
        facet=FACET,
        claim_text="A verified scientific claim.",
        paper_id=PAPER_A,
        paper_title="Paper A",
    )

    generation = writer.write((claim,))

    assert writer.calls == 1
    assert len(client.calls) == 1
    request = client.calls[0]["json"]
    assert request["response_format"] == {"type": "json_object"}
    user_content = request["messages"][1]["content"]
    assert "claim_0_0" in user_content
    assert "evidence_id" not in user_content
    assert "EvidenceUnit" not in user_content
    assert generation.input_tokens == 88
    assert generation.output_tokens == 12


def test_writer_prompt_explicitly_allows_grounded_neutral_aggregation():
    prompt = WRITER_PROMPT_PATH.read_text(encoding="utf-8")

    assert "MAY combine multiple verified claims" in prompt
    assert (
        "Existing studies investigate the split feasibility problem through "
        "convex, nonlinear, and non-convex formulations."
    ) in prompt
    assert (
        "The literature covers several problem settings, including "
        "finite-dimensional spaces, Hilbert spaces, and nonlinear mappings."
    ) in prompt


def test_writer_prompt_forbids_unsupported_relationships_while_requesting_synthesis():
    prompt = WRITER_PROMPT_PATH.read_text(encoding="utf-8")

    assert "Later studies extended earlier formulations." in prompt
    assert "Xu generalized Byrne's approach." in prompt
    assert "multiple papers represented in each section where possible" in prompt


def test_writer_prompt_requires_one_declared_facet_per_paragraph():
    prompt = WRITER_PROMPT_PATH.read_text(encoding="utf-8")

    assert "Every paragraph must use claim IDs from exactly one declared facet" in prompt
    assert "Do not move a claim into another facet" in prompt


def test_writer_rejects_exact_cross_facet_paragraph_regression():
    claims = (
        WriterClaim(
            claim_id="claim_0_1",
            facet="general_topic",
            claim_text="Presented the CQ algorithm for solving the SFP.",
            paper_id=PAPER_A,
            paper_title="Byrne 2002",
        ),
        WriterClaim(
            claim_id="claim_1_0",
            facet="methodology",
            claim_text="Used a multiprojection algorithm with oblique projections.",
            paper_id=PAPER_B,
            paper_title="Censor 1994",
        ),
    )
    content = json.dumps(
        {
            "sections": [
                {
                    "title": "Methodological Approaches",
                    "paragraphs": [
                        {
                            "text": "The studies use CQ and multiprojection algorithms.",
                            "supporting_claim_ids": ["claim_0_1", "claim_1_0"],
                        }
                    ],
                }
            ]
        }
    )

    with pytest.raises(WriterValidationError, match="mixed_facet_paragraph"):
        _parse_and_validate(content, claims)


def test_hosted_writer_request_failure_does_not_expose_authorization_secret():
    client = _RecordingClient(
        error=RuntimeError("Authorization: Bearer writer-secret")
    )
    writer = HostedGroundedLiteratureWriter(
        base_url="https://writer.invalid/v1",
        api_key="writer-secret",
        model="writer-model",
        http_client_factory=lambda: client,
    )
    claim = WriterClaim(
        claim_id="claim_0_0",
        facet=FACET,
        claim_text="A verified scientific claim.",
        paper_id=PAPER_A,
        paper_title="Paper A",
    )

    with pytest.raises(Exception) as exc_info:
        writer.write((claim,))

    assert "writer-secret" not in str(exc_info.value)
    assert "Authorization" not in str(exc_info.value)
