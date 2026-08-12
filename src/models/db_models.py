import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import relationship

from src.database import Base

UUID = Uuid
JSONB = JSON().with_variant(PG_JSONB(), "postgresql")


def ARRAY(item_type):
    return JSON().with_variant(PG_ARRAY(item_type), "postgresql")


def _now_utc():
    return datetime.now(UTC)


class RelevanceBucket(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    insufficient_info = "insufficient_info"


class ScreeningDecision(str, enum.Enum):
    keep = "keep"
    remove = "remove"
    maybe = "maybe"
    pending = "pending"


class ScopusStatus(str, enum.Enum):
    indexed = "indexed"
    not_indexed = "not_indexed"
    undetermined = "undetermined"


class CoverageYearStatus(str, enum.Enum):
    ok = "ok"
    out_of_coverage = "out_of_coverage"
    not_applicable = "not_applicable"


class OAStatus(str, enum.Enum):
    gold = "gold"
    hybrid = "hybrid"
    bronze = "bronze"
    green = "green"
    closed = "closed"
    undetermined = "undetermined"


class PDFStatus(str, enum.Enum):
    not_uploaded = "not_uploaded"
    oa_auto_fetched = "oa_auto_fetched"
    user_uploaded = "user_uploaded"


class ExtractionStatus(str, enum.Enum):
    not_extracted = "not_extracted"
    extracted = "extracted"


class SynthesisStatus(str, enum.Enum):
    processing = "processing"
    done = "done"
    failed = "failed"


class GroundingStatus(str, enum.Enum):
    pending = "pending"
    grounded = "grounded"
    rejected = "rejected"


class EntailmentStatus(str, enum.Enum):
    supported = "supported"
    contradicted = "contradicted"
    insufficient = "insufficient"


class EvidenceRelation(str, enum.Enum):
    supports = "supports"
    contradicts = "contradicts"
    context = "context"


class SynthesisClaimType(str, enum.Enum):
    agreement = "agreement"
    disagreement = "disagreement"
    comparison = "comparison"
    trend = "trend"
    gap = "gap"
    descriptive = "descriptive"


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    research_question = Column(Text, nullable=False)
    research_field = Column(String, nullable=False)
    year_from = Column(Integer, nullable=True)
    year_to = Column(Integer, nullable=True)
    criteria_include = Column(ARRAY(Text), nullable=True)
    criteria_exclude = Column(ARRAY(Text), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc)
    updated_at = Column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)

    queries = relationship("SearchQuery", back_populates="project")
    papers = relationship("Paper", back_populates="project")
    synthesis_sessions = relationship("SynthesisSession", back_populates="project")


class SearchQuery(Base):
    __tablename__ = "search_queries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    query_string = Column(Text, nullable=False)
    strategy_label = Column(String, nullable=True)
    result_count = Column(Integer, default=0)
    executed_at = Column(DateTime(timezone=True), default=_now_utc)
    is_duplicated_from = Column(UUID(as_uuid=True), ForeignKey("search_queries.id"), nullable=True)

    project = relationship("Project", back_populates="queries")
    papers = relationship("Paper", back_populates="search_query")


class Paper(Base):
    __tablename__ = "papers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    search_query_id = Column(UUID(as_uuid=True), ForeignKey("search_queries.id"), nullable=True)

    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    authors = Column(ARRAY(Text), nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String, nullable=True)
    issn = Column(String, nullable=True)
    journal = Column(String, nullable=True)
    url = Column(String, nullable=True)
    citations = Column(Integer, default=0)
    lit_score = Column(Integer, default=0)
    source = Column(String, default="scholar")
    dedup_key = Column(String, nullable=False, unique=True)

    # Module 3: AI Screening
    relevance_bucket = Column(SQLEnum(RelevanceBucket), nullable=True)
    relevance_reason = Column(JSONB, nullable=True)
    priority_score = Column(Float, nullable=True)
    screening_decision = Column(SQLEnum(ScreeningDecision), default=ScreeningDecision.pending)

    # Module 4: Quality Verification
    scopus_status = Column(SQLEnum(ScopusStatus), default=ScopusStatus.undetermined)
    scopus_quartile = Column(String, nullable=True)
    coverage_year_status = Column(SQLEnum(CoverageYearStatus), nullable=True)
    oa_status = Column(SQLEnum(OAStatus), default=OAStatus.undetermined)

    # Module 5 & 6: Library & Extraction
    pdf_status = Column(SQLEnum(PDFStatus), default=PDFStatus.not_uploaded)
    extraction_status = Column(SQLEnum(ExtractionStatus), default=ExtractionStatus.not_extracted)
    # Groups the currently indexed PageText/PDFChunk version in Chroma.
    active_ingestion_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_now_utc)

    project = relationship("Project", back_populates="papers")
    search_query = relationship("SearchQuery", back_populates="papers")
    screening_history = relationship("ScreeningHistory", back_populates="paper", cascade="all, delete-orphan")
    extraction = relationship("Extraction", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    pdf_chunks = relationship("PDFChunk", back_populates="paper", cascade="all, delete-orphan")
    page_texts = relationship("PageText", back_populates="paper", cascade="all, delete-orphan")
    evidence_attempts = relationship("EvidenceExtractionAttempt", back_populates="paper")
    evidence_records = relationship("EvidenceRecord", back_populates="paper")
    vector_cleanup_jobs = relationship("VectorCleanupJob", back_populates="paper")


class VectorCleanupJob(Base):
    """Durable outbox record for stale Chroma vector cleanup.

    The row is committed atomically with ``Paper.active_ingestion_id``. Chroma
    deletion happens after that transaction, so a process crash cannot lose the
    knowledge of which stale vector IDs still need garbage collection.
    """

    __tablename__ = "vector_cleanup_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False, index=True)
    ingestion_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    vector_ids = Column(ARRAY(Text), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    paper = relationship("Paper", back_populates="vector_cleanup_jobs")


class ScreeningHistory(Base):
    __tablename__ = "screening_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"))
    decision = Column(SQLEnum(ScreeningDecision), nullable=False)
    ai_reason = Column(JSONB, nullable=True)
    user_note = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), default=_now_utc)

    paper = relationship("Paper", back_populates="screening_history")


class ScopusSource(Base):
    __tablename__ = "scopus_sources"
    sourcerecord_id = Column(String, primary_key=True)
    issn = Column(String, nullable=True)
    eissn = Column(String, nullable=True)
    title = Column(String, nullable=False)
    active_status = Column(String, nullable=True)
    coverage_ranges = Column(String, nullable=True) # JSON array of ranges
    quartile = Column(String, nullable=True)


class Extraction(Base):
    """Legacy one-row extraction kept for backwards compatibility."""

    __tablename__ = "extractions"
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), primary_key=True)
    objective = Column(Text, nullable=True)
    method = Column(Text, nullable=True)
    finding = Column(Text, nullable=True)
    limitation = Column(Text, nullable=True)
    research_gap = Column(Text, nullable=True)
    extracted_at = Column(DateTime(timezone=True), default=_now_utc)

    paper = relationship("Paper", back_populates="extraction")


class SynthesisSession(Base):
    __tablename__ = "synthesis_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    paper_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    status = Column(SQLEnum(SynthesisStatus), default=SynthesisStatus.processing)
    review_markdown = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc)

    project = relationship("Project", back_populates="synthesis_sessions")
    citations = relationship("Citation", back_populates="synthesis_session", cascade="all, delete-orphan")
    evidence_attempts = relationship("EvidenceExtractionAttempt", back_populates="synthesis_session", cascade="all, delete-orphan")
    evidence_records = relationship("EvidenceRecord", back_populates="synthesis_session", cascade="all, delete-orphan")
    claims = relationship("SynthesisClaim", back_populates="synthesis_session", cascade="all, delete-orphan")
    sections = relationship("SynthesisSection", back_populates="synthesis_session", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synthesis_session_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sessions.id"))
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"))
    citation_marker = Column(String, nullable=False)
    review_char_start = Column(Integer, nullable=True)
    review_char_end = Column(Integer, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_char_start = Column(Integer, nullable=True)
    source_char_end = Column(Integer, nullable=True)
    quoted_snippet = Column(Text, nullable=True)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence_records.id"), nullable=True)

    synthesis_session = relationship("SynthesisSession", back_populates="citations")
    evidence = relationship("EvidenceRecord", back_populates="citations")


class PageText(Base):
    """Exact raw text extracted for one PDF page in one ingestion version."""

    __tablename__ = "page_texts"
    __table_args__ = (
        UniqueConstraint("paper_id", "ingestion_id", "page_number", name="uq_page_text_ingestion_page"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    ingestion_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    full_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    parser_name = Column(String(120), nullable=False)
    parser_version = Column(String(120), nullable=False)
    ingestion_version = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    paper = relationship("Paper", back_populates="page_texts")
    chunks = relationship("PDFChunk", back_populates="page_text")
    evidence_records = relationship("EvidenceRecord", back_populates="page_text")


class PDFChunk(Base):
    __tablename__ = "pdf_chunks"
    __table_args__ = (
        UniqueConstraint("paper_id", "ingestion_id", "page", "chunk_index", name="uq_pdf_chunk_ingestion_index"),
        CheckConstraint("page_char_start >= 0", name="ck_pdf_chunk_start_nonnegative"),
        CheckConstraint("page_char_end > page_char_start", name="ck_pdf_chunk_offsets_ordered"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    page_text_id = Column(UUID(as_uuid=True), ForeignKey("page_texts.id"), nullable=True)
    ingestion_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    chunk_text = Column(Text, nullable=False)
    page = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    page_char_start = Column(Integer, nullable=True)
    page_char_end = Column(Integer, nullable=True)

    # Legacy columns retained so existing code/migrations do not break abruptly.
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)

    paper = relationship("Paper", back_populates="pdf_chunks")
    page_text = relationship("PageText", back_populates="chunks")
    extraction_attempts = relationship("EvidenceExtractionAttempt", back_populates="suggested_chunk")
    evidence_records = relationship("EvidenceRecord", back_populates="source_chunk")


class EvidenceExtractionAttempt(Base):
    """Audit record for one LLM extraction/grounding attempt.

    Rejected attempts stay here for traceability and never become EvidenceRecord.
    """

    __tablename__ = "evidence_extraction_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number >= 1 AND attempt_number <= 2", name="ck_evidence_attempt_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synthesis_session_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sessions.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    dimension = Column(String(120), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    raw_value = Column(Text, nullable=True)
    raw_quote = Column(Text, nullable=True)
    suggested_chunk_id = Column(UUID(as_uuid=True), ForeignKey("pdf_chunks.id"), nullable=True)
    suggested_chunk_raw = Column(String(80), nullable=True)
    grounding_status = Column(SQLEnum(GroundingStatus), default=GroundingStatus.pending, nullable=False)
    failure_reason = Column(Text, nullable=True)
    model_name = Column(String(160), nullable=True)
    prompt_version = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    synthesis_session = relationship("SynthesisSession", back_populates="evidence_attempts")
    paper = relationship("Paper", back_populates="evidence_attempts")
    suggested_chunk = relationship("PDFChunk", back_populates="extraction_attempts")
    grounded_evidence = relationship("EvidenceRecord", back_populates="created_from_attempt", uselist=False)


class EvidenceRecord(Base):
    """Clean, grounded evidence only. No rejected candidates are stored here."""

    __tablename__ = "evidence_records"
    __table_args__ = (
        CheckConstraint("page_char_start >= 0", name="ck_evidence_start_nonnegative"),
        CheckConstraint("page_char_end > page_char_start", name="ck_evidence_offsets_ordered"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synthesis_session_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sessions.id"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=False)
    page_text_id = Column(UUID(as_uuid=True), ForeignKey("page_texts.id"), nullable=False)
    source_chunk_id = Column(UUID(as_uuid=True), ForeignKey("pdf_chunks.id"), nullable=False)
    created_from_attempt_id = Column(
        UUID(as_uuid=True), ForeignKey("evidence_extraction_attempts.id"), nullable=False, unique=True
    )
    dimension = Column(String(120), nullable=False)
    value = Column(Text, nullable=False)
    quote = Column(Text, nullable=False)
    page_char_start = Column(Integer, nullable=False)
    page_char_end = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    synthesis_session = relationship("SynthesisSession", back_populates="evidence_records")
    paper = relationship("Paper", back_populates="evidence_records")
    page_text = relationship("PageText", back_populates="evidence_records")
    source_chunk = relationship("PDFChunk", back_populates="evidence_records")
    created_from_attempt = relationship("EvidenceExtractionAttempt", back_populates="grounded_evidence")
    claim_links = relationship("ClaimEvidenceLink", back_populates="evidence", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="evidence")


class SynthesisSection(Base):
    __tablename__ = "synthesis_sections"
    __table_args__ = (
        UniqueConstraint("synthesis_session_id", "position", name="uq_synthesis_section_position"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synthesis_session_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sessions.id"), nullable=False)
    title = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    draft = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    synthesis_session = relationship("SynthesisSession", back_populates="sections")
    claims = relationship("SynthesisClaim", back_populates="section")


class SynthesisClaim(Base):
    __tablename__ = "synthesis_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synthesis_session_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sessions.id"), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_sections.id"), nullable=True)
    statement = Column(Text, nullable=False)
    claim_type = Column(SQLEnum(SynthesisClaimType), default=SynthesisClaimType.descriptive, nullable=False)
    # Overall verdict is evaluated against the linked evidence set jointly.
    verification_status = Column(
        SQLEnum(EntailmentStatus), default=EntailmentStatus.insufficient, nullable=False
    )
    verification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now_utc, nullable=False)

    synthesis_session = relationship("SynthesisSession", back_populates="claims")
    section = relationship("SynthesisSection", back_populates="claims")
    evidence_links = relationship("ClaimEvidenceLink", back_populates="claim", cascade="all, delete-orphan")


class ClaimEvidenceLink(Base):
    """Evidence contribution relative to one exact claim statement.

    For cross-paper meta-claims, ``supported`` may mean the evidence participates
    in a jointly sufficient evidence set; it need not entail the claim alone.
    """

    __tablename__ = "claim_evidence_links"
    claim_id = Column(UUID(as_uuid=True), ForeignKey("synthesis_claims.id"), primary_key=True)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence_records.id"), primary_key=True)
    relation = Column(SQLEnum(EvidenceRelation), nullable=False)
    entailment_status = Column(
        SQLEnum(EntailmentStatus), default=EntailmentStatus.insufficient, nullable=False
    )
    verified_at = Column(DateTime(timezone=True), nullable=True)

    claim = relationship("SynthesisClaim", back_populates="evidence_links")
    evidence = relationship("EvidenceRecord", back_populates="claim_links")
