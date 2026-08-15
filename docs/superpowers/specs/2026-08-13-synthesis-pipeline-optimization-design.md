# P-165 Synthesis Pipeline Optimization Design

**Date:** 2026-08-13

**Status:** Approved

## Goal

Reduce synthesis latency and LLM request count while producing evidence-dependent, more substantive literature-review sections without weakening evidence provenance, grounding, claim verification, coverage, semantic deduplication, QA, or citation mapping.

## Non-negotiable invariants

- Keep the existing LangGraph topology and improve its services incrementally.
- Keep `EvidenceRecord`, `EvidenceExtractionAttempt`, `ClaimEvidenceLink`, per-link `entailment_status`, quote grounding, raw page offsets, and citation-to-evidence mapping.
- Keep dimension/scope validation, baseline-versus-self protection, topic-absence guarding, coverage expansion, semantic LLM deduplication, QA, and final citation checks functionally active.
- Generic extraction caching applies only to `GENERAL_LITERATURE_REVIEW_OBJECTIVE`. Custom research questions always bypass the generic cache.
- Cache hits create new session-owned `EvidenceExtractionAttempt` and `EvidenceRecord` rows with new IDs while retaining the cached quote, value, dimension, scope, page, offsets, and source chunk provenance.
- A generic precompute failure must not fail otherwise-successful PDF ingestion. It marks the cache failed; synthesis falls back to normal extraction.
- Do not increase LLM concurrency until request-count reductions and instrumentation show that doing so will not cause a 429 regression.

## Existing architecture

The current graph performs prepare, per-paper extraction, thin-dimension expansion, semantic evidence deduplication, cross-paper claim proposal and verification, outline generation, parallel section drafting, QA, and deterministic citation finalization. Extraction currently loops over seven dimensions and may make two LLM calls per dimension. Evidence is session-owned, and every accepted record points to canonical `PageText` and `PDFChunk` rows.

The current implementation has an outline-coverage call in `draft_section()` that references variables only available in `build_outline()`. Claim verification is sequential, drafting is limited to three to five sentences, and observability is call-level rather than session aggregate.

## Architecture

### 1. Outline coverage correction

Remove `ensure_paper_outline_coverage()` from `draft_section()`. Invoke it in `build_outline()` immediately after the LLM returns `SynthesisOutlineOutput` and before downstream reset and section persistence, using the already-built `paper_ids_by_claim` map. Retain `evaluate_section_coverage()` in drafting.

### 2. Session-independent generic evidence cache

Add two Alembic-managed tables following the repository's SQLAlchemy conventions.

`GenericEvidenceCache` is the cache header and contains:

- UUID primary key;
- `paper_id` foreign key;
- active ingestion identifier;
- deterministic paper content hash;
- deterministic extraction fingerprint;
- status: `processing`, `ready`, or `failed`;
- failure text and timestamps;
- a unique cache identity over paper, content hash, and fingerprint.

`GenericEvidenceCacheItem` contains one grounded evidence item and retains:

- cache and paper identifiers;
- dimension and `applies_to`;
- interpreted value and verbatim quote;
- `page_text_id` and `source_chunk_id` foreign keys;
- raw page character start/end offsets;
- creation timestamp.

Cache rows are independent of `SynthesisSession`. They never replace session evidence and are never referenced directly by claims or citations.

### 3. Cache identity and invalidation

The paper content hash is computed deterministically from ordered `PageText` content hashes for the paper's active ingestion. The extraction fingerprint is a SHA-256 digest of normalized semantic inputs:

- primary extraction prompt templates;
- every dimension extraction rule;
- dimension retrieval hints that influence context selection;
- structured output JSON schema;
- configured synthesis provider and model.

Changing source content, extraction prompts, rules, relevant retrieval hints, schema, provider, or model creates a cache miss automatically. Old cache rows remain auditable but are not reused.

### 4. Structured paper extraction

Add a `StructuredPaperEvidence` Pydantic container and a structured LLM output that explicitly groups candidate items by all seven `EvidenceDimension` values. The container is an orchestration boundary only; accepted outputs continue to become ordinary grounded records.

For generic extraction, retrieve dimension-specific anchor contexts first, label every context with its dimension and allowed chunk ID, and make one primary structured LLM call per paper. Each returned item carries a dimension, scope, quote, value, and source chunk ID. Business logic validates that the dimension exists, the source chunk belongs to that dimension's allowed context, and the existing scope policy accepts `applies_to`.

### 5. Item-level grounding and targeted recovery

Ground each candidate independently with the existing grounding service. Preserve every accepted candidate even when a sibling fails. Track failed dimensions, then perform the existing dimension-specific retrieval and single-dimension exact-quote retry only for those dimensions. Legitimately empty dimensions do not retry. Successful retry results merge into the structured paper result without replacing primary-call successes.

The custom-RQ path retains the current per-dimension extraction behavior. Coverage expansion also remains dimension-targeted and is not replaced by generic cache reuse.

### 6. Cache materialization

On a ready cache hit, validate that cached page/chunk rows still belong to the paper's active ingestion, then create a session-owned grounded `EvidenceExtractionAttempt` and `EvidenceRecord` for each cache item. Every clone receives new IDs. Idempotency checks use session, paper, dimension, page text, and offsets so graph retries do not duplicate evidence.

On a generic cache miss, run the one-call extraction plus targeted recovery, persist only grounded items into the cache, mark the cache ready, and materialize them into the current session. A failed or unusable cache falls back to extraction rather than leaving the paper without evidence.

### 7. Batch claim verification

Normalize claim proposals before the LLM call: whitelist and deduplicate evidence IDs, enforce topic-absence and existing scope/dimension protections, create claim UUIDs, and build a separate evidence set for each claim. Batch output contains `claim_id`, verdict status, evidence IDs, and reason.

Reconcile output fail-closed:

- accept exactly one decision for a known claim;
- ignore unknown claim IDs;
- selectively fall back to the existing single-claim verifier for missing or duplicate decisions;
- apply `sanitize_claim_verification()` against that claim's evidence whitelist;
- downgrade decisive verdicts containing unknown evidence IDs as the current policy requires;
- if fallback also fails, persist the claim as `insufficient` with an auditable reason rather than losing it.

Persist claims and `ClaimEvidenceLink` rows in the existing transaction. The batch changes request shape, not provenance semantics.

### 8. Evidence-dependent drafting

Replace the hard three-to-five-sentence instruction with guidance targeting roughly 250–500 words when supported evidence is sufficient, scaling depth down for sparse evidence. Require explicit comparison across studies and prohibit padding or unsupported factual statements. Keep structured sentence-level claim IDs, QA filtering, and deterministic citations unchanged.

### 9. Ingest-time generic precomputation

After parsing, provenance persistence, and vector indexing succeed, synchronously attempt generic cache population using the same cache service. Do not introduce another worker architecture. Precompute exceptions, including 429 and timeouts, are caught at this boundary, recorded as a failed cache state, and logged. They do not roll back the successful ingest or make the paper unusable.

Synthesis uses ready cache entries. Missing, stale, processing, failed, or invalid entries trigger the safe extraction fallback.

### 10. Instrumentation

Extend existing observability with session-level synthesis metrics rather than a new monitoring stack. Capture:

- total LLM calls;
- provider-reported input and output tokens when available, otherwise null;
- cache hits and misses;
- grounding retry count;
- number of claims sent for verification;
- synthesis duration;
- final word count;
- citation coverage.

Call and retrieval logs remain the detailed audit trail. Aggregate metrics enable before/after comparisons without estimating unavailable token counts as facts.

## Migration convention

The repository uses Alembic. The new revision must descend from the current head `e8f6b0d24c53`, use SQLAlchemy portable types consistent with `db_models.py`, create explicit indexes and uniqueness constraints, and provide a complete downgrade. Runtime `create_all()` compatibility remains, but Alembic is the authoritative migration path.

## Error handling

- Cache lookup or materialization errors fail open to normal extraction and are logged.
- Generic precompute errors mark cache failed but never fail a completed parse/chunk/vector ingest.
- Batch claim verification errors fall back per claim and never silently accept an unverified verdict.
- Grounding failures preserve successful sibling items and retry only affected dimensions.
- Semantic deduplication remains fail-open as currently implemented.
- QA failure behavior remains unchanged.

## Testing strategy

Each production change follows red-green-refactor and runs focused tests before broader synthesis tests. Coverage includes:

- outline repair location and multi-paper representation;
- cache identity, hit, miss, invalidation, and custom-RQ bypass;
- cache clone provenance and new session IDs;
- structured seven-dimension extraction formatting;
- item-level grounding with targeted dimension retry;
- preservation of dimension/scope rules;
- semantic dedupe cross-dimension and numeric protections;
- batch verification happy path, unknown IDs, duplicates, partial output, total failure, and fallback failure;
- evidence-dependent drafting prompt;
- ingest precompute fail-open behavior;
- QA and citation provenance regressions;
- metric aggregation and missing provider token usage.

## Expected call-flow change

For `P` papers, seven dimensions, `C` proposed claims, and `S` drafted sections:

- Before: approximately `7P + grounding retries + C + S + fixed pipeline calls`.
- First generic run after optimization: approximately `P + failed-dimension retries + 1 batch verification + S + fixed pipeline calls`.
- Unchanged generic cache hit: extraction calls approach zero, leaving batch verification, drafting, QA, and fixed synthesis calls.
- Custom RQ: extraction remains approximately `7P` plus retries, while claim verification still benefits from batching.

These are request-count estimates. Actual latency and token usage are reported from instrumentation.

## Delivery order

Implement strictly in this sequence: outline bug, regression tests, generic cache, structured container, one-call paper extraction, targeted grounding recovery, batch claim verification, longer drafting, regression suite, instrumentation, ingest precompute, and rate-limited concurrency only if measurements justify it.
