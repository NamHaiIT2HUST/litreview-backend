"""
Database setup module.
Sử dụng SQLAlchemy async với SQLite (dev) / PostgreSQL (prod).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

load_dotenv()
os.makedirs("data", exist_ok=True)


def _normalize_async_database_url(url: str) -> str:
    """Convert common sync-style URLs to SQLAlchemy async-driver URLs."""
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return "sqlite+aiosqlite:///" + url[len("sqlite:///") :]
    return url


DATABASE_URL = _normalize_async_database_url(
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def session_scope():
    """Transaction-scoped async session for workers/LangGraph nodes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with session_scope() as session:
        yield session


async def create_all_tables():
    """Tạo tất cả bảng khi app khởi động (nếu chưa có)."""
    from src.models import db_models  # noqa: F401 — register metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_local_schema_compatibility():
    """Apply additive SQLite-only compatibility changes for legacy demo DBs."""
    if "sqlite" not in DATABASE_URL:
        return
    async with engine.begin() as conn:
        rows = await conn.execute(text("PRAGMA table_info(synthesis_sessions)"))
        columns = {row[1] for row in rows}
        if columns and "research_question" not in columns:
            await conn.execute(
                text("ALTER TABLE synthesis_sessions ADD COLUMN research_question TEXT")
            )
        if columns and "qa_warning" not in columns:
            await conn.execute(
                text("ALTER TABLE synthesis_sessions ADD COLUMN qa_warning TEXT")
            )
        evidence_rows = await conn.execute(text("PRAGMA table_info(evidence_records)"))
        evidence_columns = {row[1] for row in evidence_rows}
        if evidence_columns and "merged_into_id" not in evidence_columns:
            await conn.execute(
                text("ALTER TABLE evidence_records ADD COLUMN merged_into_id CHAR(32)")
            )
        if evidence_columns and "merge_reason" not in evidence_columns:
            await conn.execute(
                text("ALTER TABLE evidence_records ADD COLUMN merge_reason TEXT")
            )
        if evidence_columns and "applies_to" not in evidence_columns:
            await conn.execute(
                text("ALTER TABLE evidence_records ADD COLUMN applies_to VARCHAR(80) NOT NULL DEFAULT 'study'")
            )
