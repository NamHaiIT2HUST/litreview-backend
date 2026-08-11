import importlib
import sys
import types
import uuid

import pytest
from sqlalchemy.orm import DeclarativeBase


def _load_cleanup_service(monkeypatch):
    fake_db = types.ModuleType("src.database")

    class TestBase(DeclarativeBase):
        pass

    fake_db.Base = TestBase
    monkeypatch.setitem(sys.modules, "src.database", fake_db)
    sys.modules.pop("src.models.db_models", None)
    sys.modules.pop("src.services.vector_cleanup_service", None)
    return importlib.import_module("src.services.vector_cleanup_service")


class FakeDB:
    def __init__(self):
        self.added = []
        self.flushed = False

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_cleanup_job_deduplicates_ids_and_is_pending_until_external_delete(monkeypatch):
    service = _load_cleanup_service(monkeypatch)
    db = FakeDB()
    paper_id = uuid.uuid4()
    ingestion_id = uuid.uuid4()

    job = await service.create_vector_cleanup_job(
        db,
        paper_id=paper_id,
        ingestion_id=ingestion_id,
        vector_ids=["old-1", "old-1", "old-2"],
    )

    assert job is not None
    assert job.paper_id == paper_id
    assert job.ingestion_id == ingestion_id
    assert job.vector_ids == ["old-1", "old-2"]
    assert job.status == "pending"
    assert db.added == [job]
    assert db.flushed is True
