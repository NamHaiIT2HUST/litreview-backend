"""
Database setup module.
Sử dụng SQLAlchemy async với SQLite (dev) / PostgreSQL (prod).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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
