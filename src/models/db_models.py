import uuid
from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum

from src.database import Base

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

    created_at = Column(DateTime(timezone=True), default=_now_utc)

    project = relationship("Project", back_populates="papers")
    search_query = relationship("SearchQuery", back_populates="papers")
    screening_history = relationship("ScreeningHistory", back_populates="paper", cascade="all, delete-orphan")
    extraction = relationship("Extraction", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    pdf_chunks = relationship("PDFChunk", back_populates="paper", cascade="all, delete-orphan")

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
    created_at = Column(DateTime(timezone=True), default=_now_utc)

    project = relationship("Project", back_populates="synthesis_sessions")
    citations = relationship("Citation", back_populates="synthesis_session", cascade="all, delete-orphan")

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

    synthesis_session = relationship("SynthesisSession", back_populates="citations")

class PDFChunk(Base):
    __tablename__ = "pdf_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"))
    chunk_text = Column(Text, nullable=False)
    page = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    # embedding is handled by Qdrant/Chroma, so we don't store it in Postgres

    paper = relationship("Paper", back_populates="pdf_chunks")
