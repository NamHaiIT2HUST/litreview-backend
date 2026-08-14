import uuid

from src.models.synthesis_schemas import OutlineSectionProposal, SynthesisOutlineOutput
from src.services.outline_coverage_policy import ensure_paper_outline_coverage


def test_adds_representative_claims_for_supported_papers_omitted_by_llm():
    c1, c2, c3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    outline = SynthesisOutlineOutput(
        sections=[OutlineSectionProposal(title="Methods", position=0, claim_ids=[c1, c3])]
    )

    repaired = ensure_paper_outline_coverage(
        outline=outline,
        paper_ids_by_claim={c1: {p1}, c2: {p2}, c3: {p3}},
    )

    assert c2 in repaired.sections[-1].claim_ids
    assert repaired.sections[-1].title == "Additional Supported Evidence"


def test_does_not_add_fallback_when_every_supported_paper_is_covered():
    c1, c2 = uuid.uuid4(), uuid.uuid4()
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    outline = SynthesisOutlineOutput(
        sections=[OutlineSectionProposal(title="Methods", position=0, claim_ids=[c1, c2])]
    )

    repaired = ensure_paper_outline_coverage(
        outline=outline,
        paper_ids_by_claim={c1: {p1}, c2: {p2}},
    )

    assert len(repaired.sections) == 1
