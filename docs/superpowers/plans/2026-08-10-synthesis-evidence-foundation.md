# Synthesis Evidence Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable page-level provenance and synthesis domain schemas so later evidence extraction can ground every claim to a verifiable source span.

**Architecture:** Keep PyPDFLoader + RecursiveCharacterTextSplitter + ChromaDB. Persist the exact per-page extracted text in PostgreSQL/SQLAlchemy, add page-relative chunk offsets to chunk metadata, and model grounded evidence separately from extraction attempts and claim-evidence entailment links. LangGraph orchestration remains unchanged in this phase.

**Tech Stack:** FastAPI, LangChain PyPDFLoader, langchain-text-splitters, ChromaDB, Pydantic v2, SQLAlchemy 2, Alembic, pytest.

## Global Constraints

- Keep ChromaDB; do not migrate vector stores.
- Page offsets are offsets into the exact PyPDFLoader page text, not PDF bytes or visual coordinates.
- Store raw page text before any normalization.
- Grounded evidence and rejected extraction attempts must live in separate domain tables.
- Entailment status belongs to ClaimEvidenceLink and is relative to the concrete claim statement.
- Do not change the existing chat graph in this phase.

---

### Task 1: Page-aware ingestion metadata

**Files:**
- Modify: `src/services/document_processor.py`
- Create: `tests/test_services/test_document_processor.py`

**Interfaces:**
- Consumes: a PDF path.
- Produces: `(pages, chunks)` where every chunk has `page`, `chunk_index`, `page_char_start`, and `page_char_end`, and each range reconstructs `chunk.page_content` from its source page.

- [ ] Write failing tests for start/end reconstruction, valid ranges, and page identity.
- [ ] Run the tests and verify failure because offset metadata is missing.
- [ ] Enable `add_start_index=True` and enrich chunk metadata without changing chunk content.
- [ ] Run tests on a real bundled PDF and verify all invariants.

### Task 2: PageText persistence model

**Files:**
- Modify: `src/models/db_models.py`
- Create: `tests/test_models/test_synthesis_models.py`
- Create: `alembic/versions/<revision>_add_synthesis_evidence_foundation.py`

**Interfaces:**
- Produces: `PageText` keyed by paper/page/version with exact `full_text`, content hash, parser metadata, and ingestion version.
- `PDFChunk` references `PageText` and stores page-relative offsets.

- [ ] Write model metadata tests first.
- [ ] Add `PageText` SQLAlchemy model and relationships.
- [ ] Extend `PDFChunk` with `page_text_id`, `chunk_index`, `page_char_start`, `page_char_end` while preserving legacy fields for compatibility where necessary.
- [ ] Add Alembic migration.

### Task 3: Persist PageText and PDFChunk during upload

**Files:**
- Modify: `src/api/routes.py`
- Modify: `src/services/document_processor.py`
- Modify: `src/services/vector_store.py`
- Create: `tests/test_services/test_ingestion_persistence.py`

**Interfaces:**
- Upload ingestion persists page text and chunk rows before/alongside vector indexing.
- Chroma metadata includes `paper_id`, `page_text_id`, `page`, `chunk_index`, `page_char_start`, `page_char_end`.

- [ ] Write failing persistence test with a temporary PDF or constructed page/chunk objects.
- [ ] Implement a persistence helper with a single DB transaction.
- [ ] Pass DB dependency into `/workspace/upload` and attach canonical metadata before Chroma insertion.
- [ ] Verify failure leaves no partially persisted provenance rows.

### Task 4: Pydantic synthesis schemas

**Files:**
- Create: `src/models/synthesis_schemas.py`
- Create: `tests/test_models/test_synthesis_schemas.py`

**Interfaces:**
- Produces strict schemas for extraction candidate, grounded evidence, claim, claim-evidence link, and section.

- [ ] Write schema validation tests first.
- [ ] Implement enums and Pydantic models.
- [ ] Require exact quote + source chunk for extraction candidates; grounded evidence additionally requires page text ID and raw page offsets.

### Task 5: SQLAlchemy synthesis domain models

**Files:**
- Modify: `src/models/db_models.py`
- Extend: `tests/test_models/test_synthesis_models.py`
- Extend migration from Task 2 or create a follow-up migration.

**Interfaces:**
- Produces: `EvidenceExtractionAttempt`, `EvidenceRecord`, `SynthesisClaim`, `ClaimEvidenceLink`, `SynthesisSection`.

- [ ] Write relationship/constraint tests first.
- [ ] Implement audit vs clean-domain separation.
- [ ] Add uniqueness/check constraints required to keep attempt numbers and offsets valid.

### Task 6: Verification and handoff

**Files:**
- Modify docs only if implementation details differ from this plan.

- [ ] Run targeted tests for document processing and schemas/models.
- [ ] Run the broader test suite if all runtime dependencies are available.
- [ ] Re-ingest one bundled real PDF and inspect Chroma metadata plus persisted page/chunk provenance.
- [ ] Package the modified project for handoff.
