# P-165 Synthesis Pipeline Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce synthesis LLM calls and latency while retaining session-owned evidence provenance, fail-closed claim verification, QA, coverage, semantic deduplication, and deterministic citations.

**Architecture:** Add a session-independent generic grounded-evidence cache, materialize cache hits into new session evidence, batch generic extraction and claim verification with targeted safe fallbacks, and aggregate existing observability. Preserve the graph topology and custom-RQ extraction path.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async ORM, Alembic, Pydantic v2, LangGraph, LangChain structured output, pytest/pytest-asyncio, SQLite/PostgreSQL.

## Global Constraints

- Do not rewrite `src/synthesis/graph.py`.
- Do not remove or weaken evidence provenance, quote grounding, `ClaimEvidenceLink`, entailment, scope/dimension guards, semantic LLM dedupe, coverage expansion, QA, or citation checks.
- Generic cache identity is `paper_id + content_hash + extraction_fingerprint` and applies only to `GENERAL_LITERATURE_REVIEW_OBJECTIVE`.
- Custom RQs bypass generic cache.
- Cache materialization creates new evidence and attempt IDs for each synthesis session.
- Generic precompute failure never fails an otherwise successful ingestion.
- Write a failing regression test before each production behavior change.
- Do not overwrite unrelated uncommitted work.

---

### Task 1: Move outline coverage enforcement to `build_outline` (A–B)

**Files:**
- Modify: `src/services/synthesis_service.py`
- Create: `tests/test_services/test_synthesis_service.py`

**Interfaces:**
- Consumes: `ensure_paper_outline_coverage(outline, paper_ids_by_claim)`.
- Produces: `build_outline()` persists the repaired outline; `draft_section()` only evaluates section coverage and drafts.

- [ ] **Step 1: Write failing service regressions**

Create async tests with a minimal fake async DB and patched LLM service. One calls `draft_section()` with a valid section/claim/evidence result and asserts it returns a payload instead of raising `NameError`. A second supplies an LLM outline omitting a supported paper and asserts `build_outline()` persists an `Additional Supported Evidence` section containing that paper's representative claim.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_services/test_synthesis_service.py -q`

Expected: draft regression fails with undefined `outline`; outline integration fails because repair is not invoked.

- [ ] **Step 3: Apply the minimal fix**

Delete the misplaced block from `draft_section()`:

```python
outline = ensure_paper_outline_coverage(
    outline=outline,
    paper_ids_by_claim=dict(paper_ids_by_claim),
)
```

In `build_outline()`, immediately after the LLM result, add:

```python
outline = ensure_paper_outline_coverage(
    outline=outline,
    paper_ids_by_claim=dict(paper_ids_by_claim),
)
```

- [ ] **Step 4: Verify GREEN and focused regressions**

Run: `pytest tests/test_services/test_synthesis_service.py tests/test_services/test_outline_coverage_policy.py tests/test_services/test_synthesis_coverage_policy.py -q`

Expected: all pass.

---

### Task 2: Add persistent generic cache schema and models (C)

**Files:**
- Create: `alembic/versions/b91c2d3e4f50_add_generic_evidence_cache.py`
- Modify: `src/models/db_models.py`
- Modify: `tests/test_models/test_synthesis_models.py`
- Create: `tests/test_services/test_generic_evidence_cache.py`

**Interfaces:**
- Produces: `GenericEvidenceCache`, `GenericEvidenceCacheItem`, and `GenericEvidenceCacheStatus`.
- Cache unique key: `(paper_id, content_hash, extraction_fingerprint)`.

- [ ] **Step 1: Write failing model contract tests**

Assert cache header columns, status enum, unique constraint, item provenance columns, page/chunk FKs, and absence of `synthesis_session_id` on both cache tables. Assert `EvidenceRecord` remains session-owned and unchanged.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_models/test_synthesis_models.py tests/test_services/test_generic_evidence_cache.py -q`

Expected: imports fail because cache models do not exist.

- [ ] **Step 3: Add ORM models**

Add status values `processing`, `ready`, `failed`. Add header fields `id`, `paper_id`, `ingestion_id`, `content_hash`, `extraction_fingerprint`, `status`, `failure_reason`, `created_at`, `updated_at`; add the three-column unique constraint. Add item fields `id`, `cache_id`, `paper_id`, `dimension`, `applies_to`, `value`, `quote`, `page_text_id`, `source_chunk_id`, `page_char_start`, `page_char_end`, `created_at` and ordered-offset checks.

- [ ] **Step 4: Add Alembic migration**

Create revision `b91c2d3e4f50` whose `down_revision` is `e8f6b0d24c53`. Create both tables, indexes for cache lookup and cache items, FK constraints, uniqueness, checks, and a downgrade that drops items before headers.

- [ ] **Step 5: Verify migration and models**

Run: `pytest tests/test_models/test_synthesis_models.py tests/test_services/test_generic_evidence_cache.py -q`

Run: `alembic heads`

Expected: tests pass and exactly one new head is shown.

---

### Task 3: Add structured paper evidence schemas and automatic fingerprinting (D)

**Files:**
- Modify: `src/models/synthesis_schemas.py`
- Create: `src/services/generic_evidence_cache_service.py`
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `tests/test_models/test_synthesis_schemas.py`
- Modify: `tests/test_services/test_generic_evidence_cache.py`

**Interfaces:**
- Produces: `StructuredEvidenceItem`, `StructuredPaperEvidence`, `PaperEvidenceExtractionOutput`.
- Produces: `paper_content_hash(page_text_rows) -> str` and `extraction_fingerprint(settings) -> str`.

- [ ] **Step 1: Write failing schema and fingerprint tests**

Assert structured output groups all `EvidenceDimension` keys and each item retains value, quote, source chunk, and scope. Assert content hash is order-stable but changes with page content. Assert fingerprint is deterministic and changes when prompt, rule, schema, provider, or model input changes.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_models/test_synthesis_schemas.py tests/test_services/test_generic_evidence_cache.py -q`

Expected: missing schemas/helpers.

- [ ] **Step 3: Centralize extraction prompt semantics**

Expose pure prompt-builder functions from `synthesis_llm_service.py` and reuse them in both single-dimension extraction and fingerprint generation so fingerprint inputs cannot drift from actual prompts.

- [ ] **Step 4: Implement schemas and hashes**

Use `model_json_schema()` serialized with sorted keys. Normalize all dimensions' `dimension_extraction_rules()` and `dimension_retrieval_hint()` values. Hash ordered page number/content-hash pairs and extraction semantics with SHA-256.

- [ ] **Step 5: Verify GREEN**

Run: `pytest tests/test_models/test_synthesis_schemas.py tests/test_services/test_generic_evidence_cache.py tests/test_services/test_synthesis_llm_service.py -q`

Expected: all pass.

---

### Task 4: Implement one-call generic paper extraction (E)

**Files:**
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `src/services/synthesis_service.py`
- Modify: `tests/test_services/test_synthesis_llm_service.py`
- Modify: `tests/test_services/test_synthesis_service.py`

**Interfaces:**
- Produces: `extract_paper_evidence_batch(research_question, contexts_by_dimension) -> PaperEvidenceExtractionOutput`.
- Preserves: `extract_evidence(...)` for custom RQ and targeted fallback.

- [ ] **Step 1: Write failing LLM adapter test**

Pass contexts for all dimensions and assert one `_invoke_structured` call, explicit dimension labels, per-context chunk IDs, all dimension rules, exact-quote requirement, and `PaperEvidenceExtractionOutput` schema.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_services/test_synthesis_llm_service.py::test_extract_paper_evidence_batch_uses_one_structured_call -q`

Expected: method missing.

- [ ] **Step 3: Implement the batch adapter**

Build one system prompt that preserves the existing quote, scope, allowed-ID, and dimension-specific rules. Build a human context grouped by dimension. Do not change `extract_evidence()`.

- [ ] **Step 4: Write failing service routing test**

Assert generic RQ calls the batch adapter once after dimension-specific retrieval contexts are assembled; assert custom RQ continues to call `extract_evidence()` per dimension and never calls the batch adapter.

- [ ] **Step 5: Implement generic/custom routing**

Extract context retrieval into a private helper without changing query formation or `RetrievalLog`. Route only the default objective through the primary batch call.

- [ ] **Step 6: Verify GREEN**

Run: `pytest tests/test_services/test_synthesis_llm_service.py tests/test_services/test_synthesis_service.py tests/test_services/test_synthesis_coverage_policy.py -q`

Expected: all pass.

---

### Task 5: Ground per item and retry only failed dimensions (F)

**Files:**
- Modify: `src/services/synthesis_service.py`
- Modify: `src/services/evidence_extraction_policy.py`
- Modify: `tests/test_services/test_synthesis_service.py`
- Modify: `tests/test_services/test_evidence_extraction_policy.py`
- Modify: `tests/test_services/test_synthesis_dimension_policy.py`

**Interfaces:**
- Consumes: batch items plus allowed chunk IDs by dimension.
- Produces: accepted grounded items and `failed_dimensions`.

- [ ] **Step 1: Write failing partial-grounding regression**

Return valid findings and invalid dataset/limitation candidates. Assert valid findings are persisted, retries occur only for dataset and limitation, retry queries include each existing dimension hint, and successful retries merge without replacing findings.

- [ ] **Step 2: Write failing scope regression**

Return a baseline-scoped limitation and assert it is rejected before grounding and triggers only the limitation recovery path. Assert similar wording in different dimensions remains separate.

- [ ] **Step 3: Verify RED**

Run: `pytest tests/test_services/test_synthesis_service.py tests/test_services/test_evidence_extraction_policy.py tests/test_services/test_synthesis_dimension_policy.py -q`

Expected: generic path retries the wrong unit or is not implemented.

- [ ] **Step 4: Implement item-level processing**

Reuse the existing attempt creation, scope validation, allowed-chunk check, grounding service, and idempotent insertion. Track failures by dimension. Invoke the unchanged single-dimension exact-quote extractor only for failed dimensions, with `dimension_retrieval_hint()` retrieval.

- [ ] **Step 5: Verify GREEN**

Run: focused command from Step 3.

Expected: all pass.

---

### Task 6: Implement cache lookup, population, and session materialization (C–F)

**Files:**
- Modify: `src/services/generic_evidence_cache_service.py`
- Modify: `src/services/synthesis_service.py`
- Modify: `tests/test_services/test_generic_evidence_cache.py`
- Modify: `tests/test_services/test_synthesis_service.py`

**Interfaces:**
- Produces: `lookup_ready_cache(...)`, `materialize_cache(...)`, `store_grounded_cache(...)`, `mark_cache_failed(...)`.

- [ ] **Step 1: Write failing cache behavior tests**

Cover ready hit, miss, changed content hash, changed fingerprint, custom-RQ bypass, stale page/chunk ingestion rejection, and failed cache fallback.

- [ ] **Step 2: Write failing materialization test**

Assert cloned attempts/evidence have new IDs and current `synthesis_session_id`, while quote, value, dimension, page/chunk IDs, and offsets match cache items. Repeat materialization and assert idempotency.

- [ ] **Step 3: Verify RED**

Run: `pytest tests/test_services/test_generic_evidence_cache.py tests/test_services/test_synthesis_service.py -q`

Expected: service methods missing.

- [ ] **Step 4: Implement cache service and generic routing**

Use exact three-part cache identity. Validate active ingestion ownership on hits. Populate only grounded results. Log hit/miss and fall back to extraction on lookup/materialization error.

- [ ] **Step 5: Verify GREEN**

Run: focused command from Step 3 plus `pytest tests/test_services/test_grounding_service.py -q`.

Expected: all pass.

---

### Task 7: Batch claim verification with selective fail-closed fallback (G)

**Files:**
- Modify: `src/models/synthesis_schemas.py`
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `src/services/synthesis_service.py`
- Modify: `src/services/claim_verification_policy.py` only if typing requires a shared protocol/model
- Modify: `tests/test_models/test_synthesis_schemas.py`
- Modify: `tests/test_services/test_synthesis_llm_service.py`
- Modify: `tests/test_services/test_synthesis_service.py`
- Retain: `tests/test_services/test_claim_verification_policy.py`

**Interfaces:**
- Produces: `ClaimVerificationBatchItem(ClaimVerificationDecision)` with `claim_id` and `ClaimVerificationBatchOutput.decisions`.
- Produces: `verify_claim_set_batch(claims_with_evidence) -> ClaimVerificationBatchOutput`.
- Preserves: `verify_claim_set()` as the per-claim fallback.

- [ ] **Step 1: Write failing schema and prompt tests**

Assert decisive batch items require evidence IDs and the prompt isolates each claim's evidence subset, forbids cross-claim evidence use, and emits one structured call.

- [ ] **Step 2: Write failing reconciliation tests**

Cover full success, missing decision, duplicate decision, unknown claim ID, unknown evidence ID, total batch error, and fallback error. Assert topic-absence guarded claims never enter the batch. Assert fallback failure persists `insufficient` with a reason.

- [ ] **Step 3: Verify RED**

Run: `pytest tests/test_models/test_synthesis_schemas.py tests/test_services/test_synthesis_llm_service.py tests/test_services/test_synthesis_service.py tests/test_services/test_claim_verification_policy.py -q`

Expected: missing batch API/reconciliation.

- [ ] **Step 4: Implement schemas and adapter**

Subclass the existing decision model so its decisive-evidence validator is reused. Keep the existing single-call method unchanged.

- [ ] **Step 5: Implement prepare/reconcile/persist flow**

Prepare guarded claims and UUIDs before invoking the batch. Map exactly one known decision per claim; selectively call the single verifier for missing/duplicate entries; sanitize against per-claim allowed IDs; create links and statuses in the existing transaction.

- [ ] **Step 6: Verify GREEN**

Run the focused command from Step 3.

Expected: all pass.

---

### Task 8: Make drafting depth evidence-dependent (H)

**Files:**
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `tests/test_services/test_synthesis_llm_service.py`

**Interfaces:**
- Preserves: `draft_section(...) -> SectionDraftOutput` and sentence-level claim IDs.

- [ ] **Step 1: Write failing prompt regression**

Assert the draft prompt does not contain `3-5 coherent sentences`; contains 250–500-word conditional guidance, sparse-evidence restraint, cross-study comparison, and factual grounding requirements.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_services/test_synthesis_llm_service.py::test_draft_depth_scales_with_supported_evidence -q`

Expected: old hard limit is present.

- [ ] **Step 3: Update only the drafting prompt**

Keep the schema, claim IDs, and citation-marker prohibition unchanged.

- [ ] **Step 4: Verify GREEN**

Run: `pytest tests/test_services/test_synthesis_llm_service.py tests/test_services/test_synthesis_qa_policy.py tests/test_services/test_synthesis_response_builder.py -q`

Expected: all pass.

---

### Task 9: Complete synthesis regression coverage (I)

**Files:**
- Modify: `eval/test_known_regressions.py`
- Modify: relevant `tests/test_services/test_*.py` files only where a named invariant lacks coverage

**Interfaces:**
- Produces: an executable regression gate for provenance, grounding, scope, dedupe, coverage, batch verification, QA, and citations.

- [ ] **Step 1: Map the eight safety cases to existing tests**

Retain existing tests when they already prove an invariant. Add only missing cases: new session evidence IDs on cache hit, custom-RQ bypass, partial grounding preservation, and batch fallback linkage.

- [ ] **Step 2: Verify the regression gate**

Run: `pytest eval/test_known_regressions.py tests/test_services/test_claim_verification_policy.py tests/test_services/test_grounding_service.py tests/test_services/test_evidence_deduplication_policy.py tests/test_services/test_outline_coverage_policy.py tests/test_services/test_synthesis_qa_policy.py tests/test_services/test_synthesis_response_builder.py -q`

Expected: all pass.

---

### Task 10: Add aggregate performance instrumentation (J)

**Files:**
- Create: `alembic/versions/d42e5f607182_add_synthesis_metrics.py`
- Modify: `src/models/db_models.py`
- Create: `src/services/synthesis_metrics_service.py`
- Modify: `src/services/synthesis_llm_service.py`
- Modify: `src/services/synthesis_service.py`
- Modify: `src/tasks/synthesis_tasks.py`
- Modify: `tests/test_services/test_synthesis_observability.py`

**Interfaces:**
- Produces: one `SynthesisMetrics` record per session and deterministic aggregation helpers.

- [ ] **Step 1: Write failing model and aggregation tests**

Assert columns for calls, nullable provider tokens, cache hit/miss, grounding retries, verification count, duration, word count, and citation coverage. Assert aggregation counts retry attempts as LLM calls and leaves unavailable tokens null.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_services/test_synthesis_observability.py -q`

Expected: missing metrics model/service.

- [ ] **Step 3: Add migration and ORM model**

Create revision `d42e5f607182` descending from `b91c2d3e4f50`. Use a unique session FK and portable numeric types. Provide downgrade.

- [ ] **Step 4: Capture provider token metadata safely**

Read standard structured response metadata when present; never infer unavailable usage. Extend `LLMCallLog` only if exact provider usage cannot be aggregated without columns, with matching migration changes.

- [ ] **Step 5: Finalize session metrics**

At synthesis completion, aggregate logs and counters, measure elapsed task duration, calculate final words, and calculate citation coverage as cited factual sentences divided by eligible factual sentences using stored structured drafts/citations.

- [ ] **Step 6: Verify GREEN**

Run: `pytest tests/test_services/test_synthesis_observability.py tests/test_services/test_synthesis_response_builder.py -q`

Expected: all pass.

---

### Task 11: Add fail-open generic precomputation after ingest (K)

**Files:**
- Modify: `src/api/routes.py`
- Modify: `src/services/generic_evidence_cache_service.py`
- Modify: `tests/test_api/test_routes.py`
- Modify: `tests/test_api/test_direct_upload_route.py`
- Modify: `tests/test_services/test_generic_evidence_cache.py`

**Interfaces:**
- Produces: `precompute_generic_evidence(db, paper_id) -> cache status`.
- Invariant: parse/chunk/vector success determines ingestion usability; precompute failure cannot roll it back.

- [ ] **Step 1: Write failing ingest boundary tests**

For both upload routes, make precompute raise timeout, 429-like, and generic exceptions. Assert the route still reports successful ingestion, paper keeps its active ingestion, cache is marked failed, and later synthesis chooses fallback extraction.

- [ ] **Step 2: Verify RED**

Run: `pytest tests/test_api/test_routes.py tests/test_api/test_direct_upload_route.py tests/test_services/test_generic_evidence_cache.py -q`

Expected: precompute boundary absent.

- [ ] **Step 3: Implement synchronous fail-open precompute**

Call precompute only after provenance and vector indexing succeed. Catch errors at the precompute boundary, record failed status/logging in a transaction that does not roll back ingestion, and return the existing successful response.

- [ ] **Step 4: Verify GREEN**

Run the focused command from Step 2.

Expected: all pass.

---

### Task 12: Evaluate concurrency and run full verification (K)

**Files:**
- Modify: `src/config.py` and `.env.example` only if measurements justify a rate-limited increase
- Modify: provider/concurrency tests only if configuration changes

**Interfaces:**
- Preserves default concurrency of 1 unless measured evidence supports 2–3.

- [ ] **Step 1: Compare call flow from instrumentation**

Record expected requests for representative generic first-run, cache-hit, and custom-RQ scenarios. Confirm batching reduced request count before considering concurrency.

- [ ] **Step 2: Keep concurrency unchanged unless evidence supports change**

If no provider-backed rate-limit measurement is available, make no config change and document this deliberate decision. If measurement is available, add a failing concurrency/rate-limit test before changing the default.

- [ ] **Step 3: Run migration verification**

Run: `alembic heads`

Run against an isolated test database: `alembic upgrade head`, then `alembic downgrade e8f6b0d24c53`, then `alembic upgrade head`.

Expected: one head; upgrade/downgrade/upgrade succeeds.

- [ ] **Step 4: Run backend synthesis suite**

Run: `pytest tests/test_models/test_synthesis_models.py tests/test_models/test_synthesis_schemas.py tests/test_services/test_synthesis*.py tests/test_services/test_*evidence*.py tests/test_services/test_claim_verification_policy.py tests/test_services/test_grounding_service.py tests/test_services/test_outline_coverage_policy.py eval/test_known_regressions.py -q`

Expected: all pass with zero failures.

- [ ] **Step 5: Run complete backend suite**

Run: `pytest -q`

Expected: all pass with zero failures.

- [ ] **Step 6: Review diff scope**

Run: `git diff --check` and `git status --short`.

Confirm every changed production file maps to Tasks 1–12 and unrelated pre-existing changes were not overwritten.

---

## Expected request-count comparison

- Existing generic flow: up to 7 primary extraction calls per paper, grounding retries, one verification call per proposed claim, outline, section drafts, and QA.
- Optimized first generic flow: 1 primary extraction call per paper, retries only for failed dimensions, 1 batch verification call plus selective fallbacks, outline, section drafts, and QA.
- Optimized unchanged generic cache hit: 0 extraction calls per paper, 1 batch verification call plus selective fallbacks, outline, section drafts, and QA.
- Custom RQ: existing per-dimension extraction remains; batch verification still reduces claim-verification requests.

## Deliberate non-change

Do not change `synthesis_llm_max_concurrency` without provider-backed measurements. Request reduction is the primary optimization and avoids introducing a 429 regression.
