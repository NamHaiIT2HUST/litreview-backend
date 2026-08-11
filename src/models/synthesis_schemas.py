"""Pydantic contracts for the literature-synthesis pipeline.

These models intentionally separate:
- extraction candidates (LLM output, not trusted yet),
- grounded evidence (source span verified against raw page text), and
- claim/evidence entailment (relative to one concrete claim statement).
"""
from __future__ import annotations

import re
import uuid
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class GroundingStatus(str, Enum):
    pending = "pending"
    grounded = "grounded"
    rejected = "rejected"


class EntailmentStatus(str, Enum):
    supported = "supported"
    contradicted = "contradicted"
    insufficient = "insufficient"


class EvidenceRelation(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    context = "context"


class SynthesisClaimType(str, Enum):
    agreement = "agreement"
    disagreement = "disagreement"
    comparison = "comparison"
    trend = "trend"
    gap = "gap"
    descriptive = "descriptive"


class EvidenceExtractionCandidate(BaseModel):
    """Untrusted structured output from the extraction LLM."""

    paper_id: uuid.UUID
    dimension: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    source_chunk_id: uuid.UUID


class GroundedEvidence(EvidenceExtractionCandidate):
    """Evidence whose verbatim quote has been located in a stored PageText.

    Offsets use the raw PyPDFLoader page-text coordinate system, never a
    normalized-text coordinate system.
    """

    page_text_id: uuid.UUID
    page_number: int = Field(ge=0)
    page_char_start: int = Field(ge=0)
    page_char_end: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.page_char_end <= self.page_char_start:
            raise ValueError("page_char_end must be greater than page_char_start")
        return self


class ClaimEvidenceInput(BaseModel):
    """Relationship between one evidence record and one concrete claim.

    `entailment_status` is relative to that claim's exact statement, not an
    absolute truth label attached to the evidence record.
    """

    evidence_id: uuid.UUID
    relation: EvidenceRelation
    entailment_status: EntailmentStatus = EntailmentStatus.insufficient


class SynthesisClaimInput(BaseModel):
    statement: str = Field(min_length=1)
    claim_type: SynthesisClaimType = SynthesisClaimType.descriptive
    evidence: list[ClaimEvidenceInput] = Field(default_factory=list)


class SynthesisSectionInput(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    position: int = Field(ge=0)
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    draft: str | None = None


class LLMEvidenceItem(BaseModel):
    """Evidence item returned by the LLM before paper identity is attached by code."""

    value: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    source_chunk_id: uuid.UUID


class EvidenceExtractionBatch(BaseModel):
    items: list[LLMEvidenceItem] = Field(default_factory=list, max_length=5)


class SynthesisPlanOutput(BaseModel):
    dimensions: list[str] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def normalize_dimensions(self):
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in self.dimensions:
            value = item.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        if not cleaned:
            raise ValueError("At least one non-empty synthesis dimension is required")
        self.dimensions = cleaned
        return self


class ClaimEvidenceProposal(BaseModel):
    evidence_id: uuid.UUID
    relation: EvidenceRelation


class SynthesisClaimProposal(BaseModel):
    statement: str = Field(min_length=1)
    claim_type: SynthesisClaimType = SynthesisClaimType.descriptive
    evidence: list[ClaimEvidenceProposal] = Field(min_length=1)


class SynthesisClaimProposalBatch(BaseModel):
    claims: list[SynthesisClaimProposal] = Field(default_factory=list)


class EntailmentDecision(BaseModel):
    status: EntailmentStatus
    reason: str = Field(min_length=1)


class ClaimVerificationDecision(BaseModel):
    """Verification of a synthesis claim against an evidence *set*.

    Cross-paper/meta claims (for example, disagreement across studies) may only
    be entailed by multiple evidence records jointly. ``evidence_ids`` lists the
    grounded records that actually participate in the verdict.
    """

    status: EntailmentStatus
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_evidence_for_decisive_verdict(self):
        if self.status in {EntailmentStatus.supported, EntailmentStatus.contradicted} and not self.evidence_ids:
            raise ValueError("A supported/contradicted claim verification requires evidence_ids")
        return self


class OutlineSectionProposal(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    position: int = Field(ge=0)
    claim_ids: list[uuid.UUID] = Field(min_length=1)


class SynthesisOutlineOutput(BaseModel):
    sections: list[OutlineSectionProposal] = Field(min_length=1)


class DraftSentence(BaseModel):
    sentence: str = Field(min_length=1)
    claim_ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("sentence")
    @classmethod
    def forbid_numeric_citation_markers(cls, value: str) -> str:
        # Citation markers are owned by deterministic code in finalize_review.
        # Reject LLM-authored [1], [2], ... tokens so the frontend never has to
        # guess which marker came from the resolver.
        if re.search(r"\[\d+\]", value):
            raise ValueError("LLM draft sentences must not contain citation markers")
        return value


class SectionDraftOutput(BaseModel):
    sentences: list[DraftSentence] = Field(min_length=1)


class SynthesisSessionCreateRequest(BaseModel):
    project_id: uuid.UUID
    paper_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class SynthesisSessionCreatedResponse(BaseModel):
    session_id: uuid.UUID
    status: str


class SynthesisCitationResponse(BaseModel):
    id: uuid.UUID
    marker_display: str
    paper_id: uuid.UUID
    review_char_start: int | None
    review_char_end: int | None
    source_page: int | None
    source_page_display: int | None
    source_char_start: int | None
    source_char_end: int | None
    quoted_snippet: str | None


class SynthesisSessionResponse(BaseModel):
    id: uuid.UUID
    status: str
    review_markdown: str | None
    error_message: str | None = None
    citations: list[SynthesisCitationResponse] = Field(default_factory=list)
