"""
Database setup module.
Sử dụng SQLAlchemy async với SQLite (dev) / PostgreSQL (prod).
"""
import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Đảm bảo thư mục data/ tồn tại
os.makedirs("data", exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables():
    """Tạo tất cả bảng khi app khởi động (nếu chưa có)."""
    # Import ở đây để tránh circular import
    from src.models import db_models  # noqa: F401 — register metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
