import importlib
import sys
import types

from sqlalchemy.orm import DeclarativeBase


def _load_models(monkeypatch):
    fake_db = types.ModuleType("src.database")

    class TestBase(DeclarativeBase):
        pass

    fake_db.Base = TestBase
    monkeypatch.setitem(sys.modules, "src.database", fake_db)
    sys.modules.pop("src.models.db_models", None)
    return importlib.import_module("src.models.db_models")


def test_page_text_has_versioned_source_fields(monkeypatch):
    models = _load_models(monkeypatch)
    names = set(models.PageText.__table__.columns.keys())
    assert {
        "paper_id",
        "page_number",
        "full_text",
        "content_hash",
        "parser_name",
        "parser_version",
        "ingestion_id",
        "ingestion_version",
    }.issubset(names)


def test_pdf_chunk_references_page_text_and_raw_page_offsets(monkeypatch):
    models = _load_models(monkeypatch)
    names = set(models.PDFChunk.__table__.columns.keys())
    assert {
        "page_text_id",
        "chunk_index",
        "page_char_start",
        "page_char_end",
        "ingestion_id",
    }.issubset(names)


def test_extraction_attempt_and_grounded_evidence_are_separate_tables(monkeypatch):
    models = _load_models(monkeypatch)
    assert models.EvidenceExtractionAttempt.__tablename__ == "evidence_extraction_attempts"
    assert models.EvidenceRecord.__tablename__ == "evidence_records"
    assert "grounding_status" in models.EvidenceExtractionAttempt.__table__.columns
    assert "grounding_status" not in models.EvidenceRecord.__table__.columns


def test_claim_entailment_lives_on_link_not_evidence(monkeypatch):
    models = _load_models(monkeypatch)
    assert "entailment_status" in models.ClaimEvidenceLink.__table__.columns
    assert "entailment_status" not in models.EvidenceRecord.__table__.columns


def test_synthesis_claim_tracks_joint_verification_status(monkeypatch):
    models = _load_models(monkeypatch)
    names = set(models.SynthesisClaim.__table__.columns.keys())
    assert {"verification_status", "verification_reason"}.issubset(names)


def test_vector_cleanup_job_is_durable_outbox_record(monkeypatch):
    models = _load_models(monkeypatch)
    assert models.VectorCleanupJob.__tablename__ == "vector_cleanup_jobs"
    names = set(models.VectorCleanupJob.__table__.columns.keys())
    assert {
        "paper_id",
        "ingestion_id",
        "vector_ids",
        "status",
        "attempt_count",
        "last_error",
        "created_at",
        "completed_at",
    }.issubset(names)
