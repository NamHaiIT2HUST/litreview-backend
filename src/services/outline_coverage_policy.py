"""Deterministic repair of LLM outlines that omit supported papers."""
from __future__ import annotations

import uuid
from copy import deepcopy

from src.models.synthesis_schemas import OutlineSectionProposal, SynthesisOutlineOutput


def flag_single_paper_multi_claim(*, claim_ids: list[uuid.UUID], paper_ids_by_claim: dict[uuid.UUID, set[uuid.UUID]]) -> bool:
    """Diagnostic only: identify sections that could not compare multiple papers."""
    papers = {paper_id for claim_id in claim_ids for paper_id in paper_ids_by_claim.get(claim_id, set())}
    return len(claim_ids) > 1 and len(papers) == 1


def ensure_paper_outline_coverage(
    *,
    outline: SynthesisOutlineOutput,
    paper_ids_by_claim: dict[uuid.UUID, set[uuid.UUID]],
) -> SynthesisOutlineOutput:
    repaired = deepcopy(outline)
    assigned = {claim_id for section in repaired.sections for claim_id in section.claim_ids}
    covered_papers = {
        paper_id for claim_id in assigned for paper_id in paper_ids_by_claim.get(claim_id, set())
    }
    all_papers = {paper_id for values in paper_ids_by_claim.values() for paper_id in values}
    missing = all_papers - covered_papers
    if not missing:
        return repaired

    fallback_claims: list[uuid.UUID] = []
    for paper_id in sorted(missing, key=str):
        representative = next(
            (
                claim_id for claim_id, paper_ids in paper_ids_by_claim.items()
                if paper_id in paper_ids and claim_id not in assigned
            ),
            None,
        )
        if representative is not None:
            fallback_claims.append(representative)
            assigned.add(representative)

    if fallback_claims:
        repaired.sections.append(
            OutlineSectionProposal(
                title="Additional Supported Evidence",
                position=len(repaired.sections),
                claim_ids=fallback_claims,
            )
        )
    return repaired
