# Asta-style Evidence-first Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a structured long-form literature review from uploaded papers where scientific claims are grounded, discourse sentences remain traceable, weak sections are flagged, and clicking a sentence reveals nearby evidence.

**Architecture:** Add coverage policy before drafting, enrich section drafts with typed sentences, retry an invalid draft once against existing evidence, and expose section coverage plus sentence-level citation provenance through the synthesis API. Preserve the `origin/main` Workspace, direct upload, search, screening, and export flows; update only synthesis contracts, orchestration, and presentation.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, LangGraph, React/Vite, pytest, Node test runner

## Global Constraints

- Claim-bearing sentences require verified claims and grounded evidence.
- Discourse sentences may omit direct citations but must reference verified claim IDs and introduce no new scientific facts.
- A section requires at least two grounded evidence records and two papers for comparative claims.
- Retry drafting once when sentence validation fails; expand retrieval only when section evidence coverage is insufficient.
- After one expanded retrieval attempt, merge or flag weak sections instead of inventing model knowledge.
- Preserve all functionality already present on `origin/main`.
- Do not push remotely.

---

### Task 1: Coverage and sentence contracts

**Files:**
- Modify: `src/models/synthesis_schemas.py`
- Create: `src/services/synthesis_coverage_policy.py`
- Test: `tests/test_services/test_synthesis_coverage_policy.py`

- [ ] Add failing tests for sufficient, limited, and comparative coverage.
- [ ] Add `SentenceType`, typed draft sentences, and coverage response contracts.
- [ ] Implement deterministic coverage evaluation and verify tests pass.

### Task 2: Evidence expansion and draft retry

**Files:**
- Modify: `src/services/synthesis_service.py`
- Modify: `src/services/synthesis_llm_service.py`
- Test: `tests/test_services/test_synthesis_service.py`
- Test: `tests/test_services/test_synthesis_llm_service.py`

- [ ] Add failing tests for expanded retrieval only on insufficient coverage.
- [ ] Add failing tests for one draft retry and dropping a second invalid draft.
- [ ] Implement expanded per-section retrieval, retry, and limited-evidence flagging.

### Task 3: Sentence provenance API

**Files:**
- Modify: `src/models/db_models.py`
- Modify: `src/models/synthesis_schemas.py`
- Modify: `src/api/routes.py`
- Test: `tests/test_api/test_synthesis_routes.py`

- [ ] Add failing response-contract tests for sections and typed sentences.
- [ ] Return sentence text, type, claim IDs, citations, and coverage metadata.
- [ ] Preserve legacy `review_markdown` and citation fields for compatibility.

### Task 4: Asta-style reader

**Files:**
- Modify: `frontend/src/components/workspace/SynthesisPanel.jsx`
- Modify: `frontend/src/components/workspace/VerificationPanel.jsx`
- Modify: `frontend/src/components/workspace/WorkspaceTab.jsx`
- Modify: `frontend/src/utils/synthesis.js`
- Test: `frontend/src/utils/synthesis.test.mjs`

- [ ] Add failing tests for continuous section prose and sentence provenance mapping.
- [ ] Render sections with TLDR, coverage badges, and continuous clickable sentences.
- [ ] Anchor the evidence popover beside the selected sentence.
- [ ] Show limited-evidence warnings and discourse traceability without AI-generated facts.

### Task 5: Verification

**Files:**
- Test: synthesis backend suite
- Build: `frontend/`

- [ ] Run targeted backend synthesis tests.
- [ ] Run frontend utility tests, lint, and production build.
- [ ] Run the broader backend suite and report unrelated baseline failures separately.
