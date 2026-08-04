"""
SQLAlchemy ORM models cho Search History feature.

DEFAULT_PROJECT_ID được dùng cho MVP — khi Module 1 (Research Project Setup)
được implement, sẽ thay bằng FK thật tới bảng projects.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, Boolean,
)
from sqlalchemy.orm import relationship

from src.database import Base

# Project ID mặc định cho MVP (thay bằng thật khi làm Module 1)
DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def _now_utc():
    return datetime.now(timezone.utc)


class SearchQuery(Base):
    """Lưu mỗi lần user bấm Search. Spec: search_queries table."""
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, default=DEFAULT_PROJECT_ID, index=True)
    query_string = Column(Text, nullable=False)
    strategy_label = Column(String(255), nullable=True)
    result_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    # FK tự tham chiếu: phục vụ duplicate
    is_duplicated_from = Column(String(36), ForeignKey("search_queries.id"), nullable=True)

    # Relationship sang papers (1 search → N papers)
    papers = relationship("CachedPaper", back_populates="search_query", cascade="all, delete-orphan")


class CachedPaper(Base):
    """
    Cache kết quả paper của mỗi lần search.
    Spec: papers table (một phần field — các field về screening thuộc Module 3+).
    Đặt tên CachedPaper để không trùng với Pydantic schema Paper.
    """
    __tablename__ = "papers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, default=DEFAULT_PROJECT_ID, index=True)
    search_query_id = Column(String(36), ForeignKey("search_queries.id"), nullable=False, index=True)

    # Content fields
    external_id = Column(String(100), nullable=True)  # id gốc từ API (S2_, GS_, ...)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    abstract = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    doi = Column(String(500), nullable=True)
    url = Column(Text, nullable=True)
    citations = Column(Integer, nullable=False, default=0)
    lit_score = Column(Integer, nullable=False, default=0)
    tldr = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)  # 'scholar', 'semanticscholar', ...

    # Deduplication key (spec: dedup_key)
    # Nếu có DOI → normalize(doi); else → "title_norm|author[0]|year"
    dedup_key = Column(String(1000), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    # Relationship ngược lên SearchQuery
    search_query = relationship("SearchQuery", back_populates="papers")
