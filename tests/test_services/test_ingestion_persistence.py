import importlib
import sys
import types
import uuid
from dataclasses import dataclass, field

import pytest
from sqlalchemy.orm import DeclarativeBase


def _load_service(monkeypatch):
    fake_db = types.ModuleType("src.database")

    class TestBase(DeclarativeBase):
        pass

    fake_db.Base = TestBase
    monkeypatch.setitem(sys.modules, "src.database", fake_db)
    sys.modules.pop("src.models.db_models", None)
    models = importlib.import_module("src.models.db_models")
    monkeypatch.setitem(sys.modules, "src.models.db_models", models)
    sys.modules.pop("src.services.ingestion_service", None)
    service = importlib.import_module("src.services.ingestion_service")
    return models, service


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict = field(default_factory=dict)


class FakeSession:
    def __init__(self):
        self.items = []
        self.flush_count = 0

    def add_all(self, items):
        self.items.extend(items)

    async def flush(self):
        self.flush_count += 1


@pytest.mark.asyncio
async def test_persist_pdf_provenance_keeps_raw_page_text_and_attaches_canonical_ids(monkeypatch):
    models, service = _load_service(monkeypatch)
    paper = models.Paper(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Example",
        dedup_key="example",
    )
    page_text = "Alpha beta gamma. Delta epsilon."
    pages = [FakeDocument(page_text, {"page": 0})]
    chunks = [
        FakeDocument(
            "Alpha beta gamma.",
            {"page": 0, "chunk_index": 0, "page_char_start": 0, "page_char_end": 17},
        )
    ]
    db = FakeSession()

    ingestion_id = await service.persist_pdf_provenance(
        db=db,
        paper=paper,
        pages=pages,
        chunks=chunks,
        parser_metadata={
            "parser_name": "PyPDFLoader",
            "parser_version": "test",
            "ingestion_version": "page-offset-v1",
        },
    )

    page_rows = [item for item in db.items if isinstance(item, models.PageText)]
    chunk_rows = [item for item in db.items if isinstance(item, models.PDFChunk)]
    assert len(page_rows) == 1
    assert len(chunk_rows) == 1
    assert page_rows[0].full_text == page_text
    assert page_rows[0].ingestion_id == ingestion_id
    assert paper.active_ingestion_id == ingestion_id
    assert paper.pdf_status == models.PDFStatus.user_uploaded

    metadata = chunks[0].metadata
    assert metadata["page_text_id"] == str(page_rows[0].id)
    assert metadata["chunk_id"] == str(chunk_rows[0].id)
    assert metadata["ingestion_id"] == str(ingestion_id)
    assert metadata["page_char_start"] == 0
    assert metadata["page_char_end"] == 17
    assert db.flush_count == 1
