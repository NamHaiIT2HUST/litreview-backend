# Semantic Evidence Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove semantic duplicates within one paper and evidence dimension while preserving every extracted record for audit and rollback.

**Architecture:** Add an auditable `merged_into_id` self-reference to evidence records. Before cross-paper claim generation, batch active evidence by `(paper_id, dimension)`, ask the existing synthesis LLM to identify only definite duplicates, validate its IDs fail-safely, then mark duplicate records. All synthesis and comparison-table queries consume only active records.

**Tech Stack:** Python, Pydantic, SQLAlchemy async, SQLite/PostgreSQL-compatible migration, pytest.

## Global Constraints

- Never compare or merge evidence across dimensions or papers.
- Never delete evidence records.
- Invalid, uncertain, or failed QA output leaves evidence unchanged.
- Preserve materially different numeric results even when wording is similar.

---

### Task 1: Pure deduplication decision policy

**Files:**
- Create: `src/services/evidence_deduplication_policy.py`
- Create: `tests/test_services/test_evidence_deduplication_policy.py`

**Interfaces:**
- Produces: `sanitize_evidence_deduplication(groups, allowed_ids) -> dict[UUID, UUID]`

- [ ] Write failing tests for valid merges, cross-group rejection, unknown IDs, cycles, and distinct numeric findings.
- [ ] Run the focused test and confirm the missing policy fails.
- [ ] Implement the minimal fail-safe sanitizer.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Structured LLM batch contract

**Files:**
- Modify: `src/models/synthesis_schemas.py`
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `tests/test_services/test_synthesis_llm_service.py`

**Interfaces:**
- Produces: `EvidenceDuplicateGroup`, `EvidenceDeduplicationBatch`, and `deduplicate_evidence_batch`.

- [ ] Write a failing structured-output test.
- [ ] Confirm RED.
- [ ] Add the schemas and strict prompt forbidding merges of differing numbers, populations, datasets, metrics, or conclusions.
- [ ] Confirm GREEN.

### Task 3: Persist audit marker and filter downstream data

**Files:**
- Modify: `src/models/db_models.py`
- Modify: `src/database.py`
- Modify: `alembic/versions/c2a4f7e91d03_add_session_research_question.py`
- Modify: `src/services/synthesis_service.py`
- Modify: `src/api/routes.py`
- Test: `tests/test_services/test_synthesis_service.py`

**Interfaces:**
- Produces: `EvidenceRecord.merged_into_id` and `SynthesisService.deduplicate_evidence`.

- [ ] Write failing service tests proving duplicates are marked, originals remain stored, and invalid/provider results preserve all records.
- [ ] Confirm RED.
- [ ] Add the nullable self-reference and local schema compatibility.
- [ ] Run one dedupe batch per paper/dimension before cross-paper analysis.
- [ ] Filter `merged_into_id IS NULL` in synthesis and evidence-profile queries.
- [ ] Confirm focused and regression tests pass.

### Task 4: Pipeline integration and verification

**Files:**
- Modify: `src/synthesis/graph.py`
- Modify: `src/synthesis/state.py`

- [ ] Add the dedupe node after evidence expansion and before cross-paper analysis.
- [ ] Make provider failure fail open and continue with all active evidence.
- [ ] Compile the graph, run backend tests, frontend utility tests, and frontend build.
