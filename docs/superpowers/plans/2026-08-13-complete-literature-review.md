# Complete Literature Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent two-sentence “done” reviews and generate a traceable multi-paper literature review with useful prose and a comparison table.

**Architecture:** Establish deterministic coverage rules around the existing evidence-first graph. Retrieval remains normalized-exact grounded; missing-paper recovery gets a focused profile extraction pass, overall coverage is checked before claims, drafts get bounded discourse expansion, and the frontend renders a comparison table built only from grounded evidence.

**Tech Stack:** FastAPI, SQLAlchemy, LangGraph, Pydantic, React, Node test runner, pytest.

## Global Constraints

- Never accept fuzzy quotes as grounded evidence.
- Every selected paper must contribute grounded evidence or be explicitly reported as missing.
- A `done` session must not silently omit selected papers.
- Factual sentences remain linked to verified claims and exact evidence spans.
- Work locally without commits.

---

### Task 1: Deterministic review profile and coverage policy

**Files:**
- Modify: `src/services/synthesis_coverage_policy.py`
- Modify: `tests/test_services/test_synthesis_coverage_policy.py`

- [ ] Add failing tests proving canonical method, finding, limitation, and future-work dimensions are retained alongside model dimensions.
- [ ] Add failing tests proving missing selected paper IDs are detected from grounded evidence coverage.
- [ ] Implement the minimal deterministic helpers and run the focused tests.

### Task 2: Focused missing-paper recovery and completion gate

**Files:**
- Modify: `src/services/synthesis_service.py`
- Modify: `src/synthesis/graph.py`
- Modify: `src/services/synthesis_llm_service.py`
- Test: `tests/test_services/test_synthesis_coverage_policy.py`

- [ ] Include the paper title and observable profile field in retrieval queries.
- [ ] After the normal expansion pass, identify papers with zero grounded evidence and run one focused core-contribution extraction pass.
- [ ] Stop with a detailed coverage error rather than marking an incomplete review `done`.
- [ ] Strengthen extraction instructions to return exact copied quotes without weakening the grounding matcher.

### Task 3: Longer traceable prose

**Files:**
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `src/services/synthesis_service.py`

- [ ] Ask for 3–5 sentences per supported section when claims allow it, including traceable discourse transitions.
- [ ] Keep the finalizer’s deterministic guard that drops sentences without claim IDs/evidence.
- [ ] Require multiple supported claims before an ordinary section is considered sufficient.

### Task 4: Grounded comparison table

**Files:**
- Modify: `src/models/synthesis_schemas.py`
- Modify: `src/api/routes.py`
- Modify: `frontend/src/utils/synthesis.js`
- Modify: `frontend/src/components/workspace/SynthesisPanel.jsx`

- [ ] Return a per-paper evidence profile grouped by dimension from the session endpoint.
- [ ] Render Paper, Method, Dataset, Findings, and Limitations columns, using “Chưa đủ bằng chứng” for unavailable cells.
- [ ] Keep sentence-click verification behavior unchanged.

### Task 5: Verification

**Files:**
- Test: `tests/test_services/`
- Test: `frontend/src/utils/`

- [ ] Run focused backend policy, grounding, claim verification, and synthesis tests.
- [ ] Run frontend utility tests and `npm run build`.
- [ ] Restart backend and create a new session; old completed sessions remain immutable historical output.
