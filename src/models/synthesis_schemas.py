"""Pydantic contracts for the literature-synthesis pipeline.

These models intentionally separate:
- extraction candidates (LLM output, not trusted yet),
- grounded evidence (source span verified against raw page text), and
- claim/evidence entailment (relative to one concrete claim statement).
"""
from __future__ import annotations

from typing import Any
import re
import uuid
from datetime import datetime
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


class EvidenceDimension(str, Enum):
    objective = "objective"
    method = "method"
    dataset = "dataset"
    evaluation = "evaluation"
    findings = "findings"
    limitations = "limitations"
    future_work = "future_work"


class EvidenceSubjectScope(str, Enum):
    proposed_method = "proposed_method"
    study = "study"
    baseline = "baseline"
    general = "general"


class SynthesisClaimType(str, Enum):
    agreement = "agreement"
    disagreement = "disagreement"
    comparison = "comparison"
    trend = "trend"
    gap = "gap"
    descriptive = "descriptive"


class SentenceType(str, Enum):
    claim = "claim"
    discourse = "discourse"


class SectionCoverage(BaseModel):
    status: str
    evidence_count: int = Field(ge=0)
    paper_count: int = Field(ge=0)
    retrieval_attempts: int = Field(default=1, ge=1, le=2)
    reasons: list[str] = Field(default_factory=list)


class EvidenceExtractionCandidate(BaseModel):
    """Untrusted structured output from the extraction LLM."""

    paper_id: uuid.UUID
    dimension: EvidenceDimension
    value: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    source_chunk_id: uuid.UUID

    @field_validator("dimension", mode="before")
    @classmethod
    def normalize_legacy_dimension(cls, value):
        return "findings" if value in {"finding", "main_finding"} else value


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


class StructuredPaperEvidence(BaseModel):
    """Paper-level container around normal, source-grounded evidence items."""

    paper_id: uuid.UUID
    dimensions: dict[EvidenceDimension, list[GroundedEvidence]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def include_every_dimension(self):
        self.dimensions = {
            dimension: list(self.dimensions.get(dimension, []))
            for dimension in EvidenceDimension
        }
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
    applies_to: EvidenceSubjectScope = EvidenceSubjectScope.study


class SynthesisPlanOutput(BaseModel):
    """Legacy planner boundary retained for stored/checkpointed payloads."""

    dimensions: list[str]

    @field_validator("dimensions")
    @classmethod
    def clean_dimensions(cls, values):
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        if not cleaned:
            raise ValueError("dimensions must not be empty")
        return list(dict.fromkeys(cleaned))


class StructuredEvidenceItem(LLMEvidenceItem):
    dimension: EvidenceDimension


class PaperEvidenceExtractionOutput(BaseModel):
    items: list[StructuredEvidenceItem] = Field(default_factory=list)


class EvidenceExtractionBatch(BaseModel):
    items: list[LLMEvidenceItem] = Field(default_factory=list, max_length=5)


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


class ClaimVerificationBatchItem(ClaimVerificationDecision):
    claim_id: uuid.UUID


class ClaimVerificationBatchOutput(BaseModel):
    decisions: list[ClaimVerificationBatchItem] = Field(default_factory=list)


class OutlineSectionProposal(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    position: int = Field(ge=0)
    claim_ids: list[uuid.UUID] = Field(min_length=1)


class SynthesisOutlineOutput(BaseModel):
    sections: list[OutlineSectionProposal] = Field(min_length=1)


class DraftSentence(BaseModel):
    sentence: str = Field(min_length=1)
    claim_ids: list[uuid.UUID] = Field(min_length=1)
    sentence_type: SentenceType = SentenceType.claim

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


class QAVerdict(str, Enum):
    passed = "pass"
    warning = "warning"
    blocked = "blocked"


class QASentenceCheck(BaseModel):
    sentence_id: str
    verdict: QAVerdict
    reason: str = Field(min_length=1)


class ReviewQABatchOutput(BaseModel):
    sentence_checks: list[QASentenceCheck] = Field(default_factory=list)


class EvidenceDuplicateGroup(BaseModel):
    """One definite semantic-duplicate decision within a supplied evidence group."""

    keep_id: uuid.UUID
    duplicate_ids: list[uuid.UUID] = Field(min_length=1)
    reason: str = Field(min_length=1)


class EvidenceDeduplicationBatch(BaseModel):
    groups: list[EvidenceDuplicateGroup] = Field(default_factory=list)


class SynthesisSessionCreateRequest(BaseModel):
    project_id: uuid.UUID
    paper_ids: list[Any] = Field(min_length=1, max_length=100)
    research_question: str | None = None

    @field_validator("research_question")
    @classmethod
    def normalize_optional_question(cls, value):
        cleaned = (value or "").strip()
        return cleaned or None


class SynthesisSessionCreatedResponse(BaseModel):
    session_id: uuid.UUID
    status: str


class SynthesisCitationResponse(BaseModel):
    id: uuid.UUID
    marker_display: str
    paper_id: uuid.UUID
    title: str | None = None
    filename: str | None = None
    review_char_start: int | None
    review_char_end: int | None
    source_page: int | None
    source_page_display: int | None
    source_char_start: int | None
    source_char_end: int | None
    quoted_snippet: str | None


class SynthesisSentenceResponse(BaseModel):
    text: str
    sentence_type: SentenceType
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    citation_ids: list[uuid.UUID] = Field(default_factory=list)


class SynthesisSectionResponse(BaseModel):
    id: uuid.UUID
    title: str
    position: int
    tldr: str | None = None
    coverage: SectionCoverage
    sentences: list[SynthesisSentenceResponse] = Field(default_factory=list)


class SynthesisEvidenceProfileItem(BaseModel):
    id: uuid.UUID
    paper_id: uuid.UUID
    dimension: str
    value: str
    quote: str


class SynthesisDimensionStatusItem(BaseModel):
    paper_id: uuid.UUID
    dimension: EvidenceDimension
    status: str


class SynthesisSessionResponse(BaseModel):
    id: uuid.UUID
    status: str
    research_question: str | None = None
    qa_warning: str | None = None
    review_markdown: str | None
    error_message: str | None = None
    citations: list[SynthesisCitationResponse] = Field(default_factory=list)
    sections: list[SynthesisSectionResponse] = Field(default_factory=list)
    evidence_profile: list[SynthesisEvidenceProfileItem] = Field(default_factory=list)
    dimension_statuses: list[SynthesisDimensionStatusItem] = Field(default_factory=list)
    # fast_v2's CitationCoverageTelemetry.to_dict() snapshot (see
    # src/synthesis/fast_v2/citations/anthropic_citations.py), persisted at
    # execution time. None for Legacy (non-fast_v2) sessions.
    citation_coverage_telemetry: dict | None = None


class SynthesisSessionSummary(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime
    paper_count: int
