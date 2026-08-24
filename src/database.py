"""
Database setup module.
Sử dụng SQLAlchemy async với SQLite (dev) / PostgreSQL (prod).
"""
from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

load_dotenv()
os.makedirs("data", exist_ok=True)


def _resolve_host_to_ipv4(url: str) -> str:
    """Resolve database hostname to IPv4 address to prevent Render's IPv6 limitation with Supabase."""
    if not ("postgresql" in url or "postgres" in url):
        return url
    try:
        scheme_prefix = ""
        parse_url = url
        if url.startswith("postgresql+asyncpg://"):
            scheme_prefix = "postgresql+asyncpg://"
            parse_url = "postgresql://" + url[len("postgresql+asyncpg://") :]
        elif url.startswith("postgres://"):
            scheme_prefix = "postgres://"
            parse_url = "postgresql://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            scheme_prefix = "postgresql://"
            parse_url = url

        parsed = urlparse(parse_url)
        hostname = parsed.hostname
        if not hostname:
            return url

        ip_addresses = socket.getaddrinfo(hostname, parsed.port or 5432, family=socket.AF_INET)
        if ip_addresses:
            ipv4 = ip_addresses[0][4][0]
            # Extract userinfo from netloc to preserve special characters accurately
            if "@" in parsed.netloc:
                userinfo = parsed.netloc.rsplit("@", 1)[0]
                auth = f"{userinfo}@"
            elif parsed.username is not None:
                auth = parsed.username
                if parsed.password is not None:
                    auth += f":{parsed.password}"
                auth += "@"
            else:
                auth = ""

            port_part = f":{parsed.port}" if parsed.port else ""
            netloc = f"{auth}{ipv4}{port_part}"
            new_parsed = parsed._replace(netloc=netloc)
            new_url = urlunparse(new_parsed)
            if scheme_prefix == "postgresql+asyncpg://":
                new_url = "postgresql+asyncpg://" + new_url[len("postgresql://") :]
            elif scheme_prefix == "postgres://":
                new_url = "postgres://" + new_url[len("postgresql://") :]
            return new_url
    except Exception as e:
        print(f"Warning: Could not resolve hostname '{hostname if 'hostname' in locals() else 'Unknown'}' to IPv4: {e}")
    return url


def _normalize_async_database_url(url: str) -> str:
    """Convert common sync-style URLs to SQLAlchemy async-driver URLs."""
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return "sqlite+aiosqlite:///" + url[len("sqlite:///") :]
    return url


DATABASE_URL = _resolve_host_to_ipv4(
    _normalize_async_database_url(
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")
    )
)

def _get_engine_and_session(url: str):
    connect_args = {}
    if "sqlite" in url:
        connect_args = {"check_same_thread": False, "timeout": 30}
    elif "postgresql" in url or "postgres" in url:
        connect_args = {"statement_cache_size": 0}

    eng = create_async_engine(
        url,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    sess = async_sessionmaker(
        eng,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return eng, sess

engine, AsyncSessionLocal = _get_engine_and_session(DATABASE_URL)


class Base(DeclarativeBase):
    pass


@asynccontextmanager
async def session_scope():
    """Transaction-scoped async session for workers/LangGraph nodes."""
    global engine, AsyncSessionLocal, DATABASE_URL
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
    """Tạo tất cả bảng khi app khởi động (nếu chưa có). Tự động fallback sang SQLite nếu PostgreSQL lỗi kết nối."""
    global engine, AsyncSessionLocal, DATABASE_URL
    from src.models import db_models  # noqa: F401 — register metadata

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL:
            print(f"[Database Warning] Không thể kết nối PostgreSQL ({DATABASE_URL}): {e}")
            print("[Database Fallback] Tự động chuyển sang sử dụng SQLite: sqlite+aiosqlite:///./data/app.db")
            DATABASE_URL = "sqlite+aiosqlite:///./data/app.db"
            engine, AsyncSessionLocal = _get_engine_and_session(DATABASE_URL)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise


async def ensure_local_schema_compatibility():
    """Apply additive compatibility changes for legacy DBs (both SQLite and Postgres)."""
    from sqlalchemy import inspect

    def sync_compat(sync_conn):
        inspector = inspect(sync_conn)
        existing_tables = inspector.get_table_names()

        # Check projects columns
        if "projects" in existing_tables:
            cols = {c["name"] for c in inspector.get_columns("projects")}
            if "user_id" not in cols:
                try:
                    sync_conn.execute(text("ALTER TABLE projects ADD COLUMN user_id CHAR(36)"))
                except Exception as e:
                    print(f"Notice: Could not add user_id column to projects: {e}")

        # Check synthesis_sessions columns
        if "synthesis_sessions" in existing_tables:
            cols = {c["name"] for c in inspector.get_columns("synthesis_sessions")}
            if "research_question" not in cols:
                sync_conn.execute(text("ALTER TABLE synthesis_sessions ADD COLUMN research_question TEXT"))
            if "qa_warning" not in cols:
                sync_conn.execute(text("ALTER TABLE synthesis_sessions ADD COLUMN qa_warning TEXT"))

        # Check evidence_records columns
        if "evidence_records" in existing_tables:
            cols = {c["name"] for c in inspector.get_columns("evidence_records")}
            if "merged_into_id" not in cols:
                sync_conn.execute(text("ALTER TABLE evidence_records ADD COLUMN merged_into_id CHAR(32)"))
            if "merge_reason" not in cols:
                sync_conn.execute(text("ALTER TABLE evidence_records ADD COLUMN merge_reason TEXT"))
            if "applies_to" not in cols:
                sync_conn.execute(text("ALTER TABLE evidence_records ADD COLUMN applies_to VARCHAR(80) NOT NULL DEFAULT 'study'"))

        # Check projects columns
        if "projects" in existing_tables:
            cols = {c["name"] for c in inspector.get_columns("projects")}
            if "user_id" not in cols:
                is_postgres = "postgresql" in DATABASE_URL
                col_type = "UUID" if is_postgres else "CHAR(32)"
                sync_conn.execute(text(f"ALTER TABLE projects ADD COLUMN user_id {col_type}"))

        # Check papers columns
        if "papers" in existing_tables:
            col_info = inspector.get_columns("papers")
            cols = {c["name"] for c in col_info}
            if "file_path" not in cols:
                sync_conn.execute(text("ALTER TABLE papers ADD COLUMN file_path TEXT"))
            if "pdf_status" not in cols:
                sync_conn.execute(text("ALTER TABLE papers ADD COLUMN pdf_status VARCHAR(50) DEFAULT 'not_uploaded'"))
            if "extraction_status" not in cols:
                sync_conn.execute(text("ALTER TABLE papers ADD COLUMN extraction_status VARCHAR(50) DEFAULT 'not_extracted'"))
            if "active_ingestion_id" not in cols:
                is_postgres = "postgresql" in DATABASE_URL
                col_type = "UUID" if is_postgres else "CHAR(36)"
                sync_conn.execute(text(f"ALTER TABLE papers ADD COLUMN active_ingestion_id {col_type}"))
            if "relevance_reason" not in cols:
                sync_conn.execute(text("ALTER TABLE papers ADD COLUMN relevance_reason TEXT"))
            if "tldr" not in cols:
                sync_conn.execute(text("ALTER TABLE papers ADD COLUMN tldr TEXT"))

            # Postgres: fix authors column type if it's ARRAY instead of JSONB
            if "postgresql" in DATABASE_URL:
                for c in col_info:
                    if c["name"] == "authors" and str(c.get("type", "")).upper().startswith("ARRAY"):
                        sync_conn.execute(text("ALTER TABLE papers ALTER COLUMN authors TYPE jsonb USING to_jsonb(authors)"))
                        break

    async with engine.begin() as conn:
        await conn.run_sync(sync_compat)
