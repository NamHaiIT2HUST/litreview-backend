"""
Database setup module.
Sử dụng SQLAlchemy async với SQLite (dev) / PostgreSQL (prod).
"""
from __future__ import annotations

import logging
import os
import socket
from contextlib import asynccontextmanager
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import ENV_FILE, PROJECT_ROOT

# Scoped to this project's root; see src/config.py for why a bare load_dotenv()
# is unsafe here.
load_dotenv(ENV_FILE)

logger = logging.getLogger(__name__)

# Relative to the project root, not the working directory: this runs at import
# time, so a process started from another directory used to create its data
# folder somewhere else entirely.
os.makedirs(PROJECT_ROOT / "data", exist_ok=True)


def _resolve_host_to_ipv4(url: str) -> str:
    """Supabase Pooler and modern cloud hosts need domain name for SNI tenant routing."""
    if "pooler.supabase.com" in url or "supabase" in url:
        return url
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


def _redact_dsn(url: str) -> str:
    """Strip credentials so a DSN can appear in an error message or a log."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    return f"{scheme}://***@{rest.rsplit('@', 1)[1]}"


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
        connect_args = {"check_same_thread": False, "timeout": 60}
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
    # No `global` declaration: engine, AsyncSessionLocal and DATABASE_URL are
    # now fixed at import. They used to be reassigned by the SQLite fallback in
    # create_all_tables(), which left modules that imported DATABASE_URL at
    # module scope -- src/synthesis/graph.py and src/tasks/synthesis_tasks.py --
    # holding the dead Postgres DSN while the rest of the app had moved on.
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


class DatabaseUnavailableError(RuntimeError):
    """The configured database could not be reached."""


async def create_all_tables():
    """Tạo tất cả bảng khi app khởi động (nếu chưa có).

    Fails rather than falling back. This used to switch to a local SQLite file
    whenever PostgreSQL refused a connection, announcing it with a bare print().
    Because .env.example points DATABASE_URL at a Postgres container, whoever
    had that container running used Postgres and whoever did not silently used
    SQLite -- same commit, same .env, two different databases, and nothing in
    /health said which. Anything written during such a session was lost on the
    next restart.

    To develop against SQLite, say so: DATABASE_URL=sqlite:///./data/app.db
    """
    from src.models import db_models  # noqa: F401 — register metadata

    try:
        async with engine.begin() as conn:
            if "sqlite" in str(DATABASE_URL):
                await conn.execute(text("PRAGMA journal_mode=WAL;"))
                await conn.execute(text("PRAGMA busy_timeout=60000;"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        raise DatabaseUnavailableError(
            f"Could not connect to the configured database ({_redact_dsn(DATABASE_URL)}): {e}\n"
            "Start it (for the default local setup: `docker compose up -d db`), "
            "or point DATABASE_URL at a database you can reach. To use a local "
            "SQLite file instead, set DATABASE_URL=sqlite:///./data/app.db "
            "explicitly -- it is no longer selected for you."
        ) from e


async def ensure_local_schema_compatibility():
    """Apply additive compatibility changes for legacy DBs (both SQLite and Postgres).

    This is a hand-rolled patcher that runs alongside ``Base.metadata.create_all``.
    Alembic exists in this repository but nothing invokes it, and
    ``alembic upgrade head`` currently fails outright on SQLite because the
    initial revision still creates ARRAY columns the models no longer use.
    Consolidating on Alembic requires regenerating a baseline revision first;
    see docs/architecture/SYSTEM_CONTRACTS.md section 12.3.
    """
    from sqlalchemy import inspect

    def sync_compat(sync_conn):
        inspector = inspect(sync_conn)
        existing_tables = inspector.get_table_names()
        is_postgres = "postgresql" in str(DATABASE_URL) or "postgres" in str(DATABASE_URL)

        def safe_exec(stmt_str: str):
            try:
                sync_conn.execute(text(stmt_str))
            except Exception as e:
                # Intended to absorb "column already exists". It also absorbed
                # permission, type and syntax errors, so each machine ended up
                # with a different accumulated schema and no record of which
                # statements had failed. Log instead of discarding.
                logger.warning("Schema compatibility statement failed: %s -- %s", stmt_str, e)

        # Check projects columns
        if "projects" in existing_tables:
            if is_postgres:
                safe_exec("ALTER TABLE projects ADD COLUMN IF NOT EXISTS user_id UUID")
            else:
                cols = {c["name"] for c in inspector.get_columns("projects")}
                if "user_id" not in cols:
                    safe_exec("ALTER TABLE projects ADD COLUMN user_id CHAR(36)")

        # Check synthesis_sessions columns
        if "synthesis_sessions" in existing_tables:
            if is_postgres:
                safe_exec("ALTER TABLE synthesis_sessions ADD COLUMN IF NOT EXISTS research_question TEXT")
                safe_exec("ALTER TABLE synthesis_sessions ADD COLUMN IF NOT EXISTS qa_warning TEXT")
            else:
                cols = {c["name"] for c in inspector.get_columns("synthesis_sessions")}
                if "research_question" not in cols:
                    safe_exec("ALTER TABLE synthesis_sessions ADD COLUMN research_question TEXT")
                if "qa_warning" not in cols:
                    safe_exec("ALTER TABLE synthesis_sessions ADD COLUMN qa_warning TEXT")

        # Check evidence_records columns
        if "evidence_records" in existing_tables:
            if is_postgres:
                safe_exec("ALTER TABLE evidence_records ADD COLUMN IF NOT EXISTS merged_into_id CHAR(32)")
                safe_exec("ALTER TABLE evidence_records ADD COLUMN IF NOT EXISTS merge_reason TEXT")
                safe_exec("ALTER TABLE evidence_records ADD COLUMN IF NOT EXISTS applies_to VARCHAR(80) NOT NULL DEFAULT 'study'")
            else:
                cols = {c["name"] for c in inspector.get_columns("evidence_records")}
                if "merged_into_id" not in cols:
                    safe_exec("ALTER TABLE evidence_records ADD COLUMN merged_into_id CHAR(32)")
                if "merge_reason" not in cols:
                    safe_exec("ALTER TABLE evidence_records ADD COLUMN merge_reason TEXT")
                if "applies_to" not in cols:
                    safe_exec("ALTER TABLE evidence_records ADD COLUMN applies_to VARCHAR(80) NOT NULL DEFAULT 'study'")

        # Check papers columns
        if "papers" in existing_tables:
            if is_postgres:
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS file_path TEXT")
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS pdf_status VARCHAR(50) DEFAULT 'not_uploaded'")
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(50) DEFAULT 'not_extracted'")
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS active_ingestion_id UUID")
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS relevance_reason TEXT")
                safe_exec("ALTER TABLE papers ADD COLUMN IF NOT EXISTS tldr TEXT")
            else:
                cols = {c["name"] for c in inspector.get_columns("papers")}
                if "file_path" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN file_path TEXT")
                if "pdf_status" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN pdf_status VARCHAR(50) DEFAULT 'not_uploaded'")
                if "extraction_status" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN extraction_status VARCHAR(50) DEFAULT 'not_extracted'")
                if "active_ingestion_id" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN active_ingestion_id CHAR(36)")
                if "relevance_reason" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN relevance_reason TEXT")
                if "tldr" not in cols:
                    safe_exec("ALTER TABLE papers ADD COLUMN tldr TEXT")

            # Postgres: fix authors column type if it's ARRAY instead of JSONB
            if is_postgres:
                col_info = inspector.get_columns("papers")
                for c in col_info:
                    if c["name"] == "authors" and str(c.get("type", "")).upper().startswith("ARRAY"):
                        safe_exec("ALTER TABLE papers ALTER COLUMN authors TYPE jsonb USING to_jsonb(authors)")
                        break

    async with engine.begin() as conn:
        await conn.run_sync(sync_compat)
