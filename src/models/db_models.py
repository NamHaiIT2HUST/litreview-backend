"""
SQLAlchemy ORM models cho Search History feature + Module 4 (Quality Verification).

DEFAULT_PROJECT_ID được dùng cho MVP — khi Module 1 (Research Project Setup)
được implement, sẽ thay bằng FK thật tới bảng projects.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.database import Base

# Project ID mặc định cho MVP (thay bằng thật khi làm Module 1)
DEFAULT_PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def _now_utc():
    return datetime.now(UTC)


class SearchQuery(Base):
    """Lưu mỗi lần user bấm Search. Spec: search_queries table."""
    __tablename__ = "search_queries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, default=DEFAULT_PROJECT_ID, index=True)
    query_string = Column(Text, nullable=False)
    strategy_label = Column(String(255), nullable=True)
    result_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    is_duplicated_from = Column(String(36), ForeignKey("search_queries.id"), nullable=True)

    papers = relationship("CachedPaper", back_populates="search_query", cascade="all, delete-orphan")


class CachedPaper(Base):
    """
    Cache kết quả paper của mỗi lần search.
    Spec: papers table — field cơ bản (Module 2) + field Quality Check (Module 4).
    Đặt tên CachedPaper để không trùng với Pydantic schema Paper.
    """
    __tablename__ = "papers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, default=DEFAULT_PROJECT_ID, index=True)
    search_query_id = Column(String(36), ForeignKey("search_queries.id"), nullable=False, index=True)

    external_id = Column(String(100), nullable=True)
    title = Column(Text, nullable=False)
    authors = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    abstract = Column(Text, nullable=True)
    journal = Column(String(500), nullable=True)
    doi = Column(String(500), nullable=True)
    issn = Column(String(20), nullable=True)
    url = Column(Text, nullable=True)
    citations = Column(Integer, nullable=False, default=0)
    lit_score = Column(Integer, nullable=False, default=0)
    tldr = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)

    dedup_key = Column(String(1000), nullable=False, index=True)

    # ── Module 4: Quality Verification ────────────────────────────────────
    scopus_status = Column(String(20), nullable=False, default="undetermined")
    # scopus_quartile: LUÔN None ở bản này — file Source title list của Elsevier
    # KHÔNG chứa Quartile (cần file CiteScore riêng, theo subject category, chưa
    # tích hợp). Giữ field để tương thích schema, không xoá, nhưng không suy diễn.
    scopus_quartile = Column(String(2), nullable=True)
    coverage_year_status = Column(String(20), nullable=True)  # ok / out_of_coverage / not_applicable
    oa_status = Column(String(20), nullable=False, default="undetermined")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    search_query = relationship("SearchQuery", back_populates="papers")


class ScopusSource(Base):
    """
    Danh mục Tạp chí Scopus chính thức — import từ file "Source title list"
    (Elsevier, https://www.elsevier.com/products/scopus/content, cập nhật hàng
    tháng, job nội bộ — KHÔNG phải API user-facing).

    Khớp đúng cấu trúc file thật (6 cột): Sourcerecord ID, Source Title, ISSN,
    EISSN, Active or Inactive, Coverage.

    sourcerecord_id dùng làm PK (định danh ổn định từ Elsevier) thay vì ISSN,
    vì 1 tạp chí có thể có cả ISSN in và EISSN riêng biệt — cần match được cả 2,
    nên issn/eissn tách thành 2 cột có index riêng, không dùng làm PK.

    coverage_ranges lưu dạng JSON text — vd "[[2019,2024],[2016,2017]]" — vì
    1 tạp chí có thể có NHIỀU khoảng năm được index rời rạc (bị gián đoạn giữa
    chừng), không phải luôn luôn 1 khoảng liên tục duy nhất.
    """
    __tablename__ = "scopus_sources"

    sourcerecord_id = Column(String(30), primary_key=True)
    title = Column(String(500), nullable=True)
    issn = Column(String(20), nullable=True, index=True)
    eissn = Column(String(20), nullable=True, index=True)
    active_status = Column(String(20), nullable=True)  # "Active" | "Inactive" — nguyên văn từ file
    coverage_ranges = Column(Text, nullable=True)  # JSON list các [start, end]
    # quartile: LUÔN None hiện tại, xem ghi chú ở CachedPaper.scopus_quartile
    quartile = Column(String(2), nullable=True)
