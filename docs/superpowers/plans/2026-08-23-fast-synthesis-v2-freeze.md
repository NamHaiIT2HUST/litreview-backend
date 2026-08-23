# Plan — Fast Synthesis v2 architecture freeze (2026-08-23)

Goal: freeze validated fast-synthesis research (Evidence-First retrieval,
Evidence Hygiene, Dimension-Aware evidence selection, OpenScholar generation)
into production-shaped, test-driven, feature-flagged code.

This is **not** a benchmark iteration and **not** a production migration.
Legacy stays default. See `docs/architecture/FAST_SYNTHESIS_V2.md`.

Method for every task: write the test first, run it and confirm it fails for
the right reason, write the minimal implementation, run the focused test, run
relevant regression tests, commit separately.

Baseline before any change: `128 passed, 5 failed` — all 5 pre-existing
(2 OpenAI auth/network in `tests/test_agents/test_graph.py`, 3 `SimpleNamespace`
fixture breakage in `tests/test_services/test_vector_store_async.py`).

---

## Task 1 — Architecture ADR + config flag
- Test: legacy is default; fast_v2 activates only on exact opt-in; a typo raises.
- Impl: `synthesis_mode` Literal + `fast_v2_enabled` property + experimental
  knobs in `src/config.py`.
- Docs: `docs/architecture/FAST_SYNTHESIS_V2.md`, this plan.

## Task 2 — Evidence-First reusable evidence/domain types
- Test 2: `EvidenceUnit` preserves paper/page/source provenance.
- Test: `evidence_id` is not the same field as `source_chunk_id`.
- Impl: `fast_v2/evidence/models.py` — `EvidenceUnit`, frozen + serializable.

## Task 3 — Port tested Evidence Hygiene
- Tests 3/4/5: bibliography removed; inline citations in prose retained;
  boilerplate removed. Plus numeric regression fixtures from the spike JSON.
- Impl: `fast_v2/hygiene/classifier.py`. Runtime filtering only — never mutate
  or delete canonical chunks.

## Task 4 — Dimension query + selection policy
- Tests 6/9/10/11: distinct dimensions -> distinct queries; below-threshold
  rejected; no padding to max_per_dimension; no forced paper balance.
- Impl: `fast_v2/dimensions/planner.py` (`DimensionQueryPlanner` interface +
  deterministic implementation), `fast_v2/selection/policy.py`
  (`EvidenceSelectionPolicy`), `fast_v2/selection/rerank.py` (protocol only).

## Task 5 — Evidence Bank merge/dedupe
- Tests 7/8: same evidence selected by multiple dimensions dedupes once;
  dimension metadata preserved.
- Impl: `fast_v2/evidence/bank.py` — `GroundedEvidenceBank`, deterministic
  dedupe keyed on `evidence_id`, `selected_for_dimensions`, `dimension_scores`,
  `best_dimension_score`. No LLM semantic dedup.

## Task 6 — OpenScholar generator adapter + frozen prompt/config
- Tests 12/13/14/15/16: generator receives the bank only; `stop=["[Response_End]"]`;
  `min_tokens == 0`; no model load at import; fake generator works on CPU.
- Impl: `fast_v2/generator/base.py` (`SynthesisGenerator`, `GeneratedDraft`),
  `prompt.py` (`p165_controlled_sanitized_v1`), `openscholar.py` (lazy load),
  `fake.py`.

## Task 7 — Fast v2 pipeline wiring
- Test: full pipeline runs on fakes; Test 1: zero query-time extraction LLM calls.
- Impl: `fast_v2/pipeline.py`.

## Task 8 — Deterministic citation/finalizer integration
- Tests 17/18: native OpenScholar citation IDs are not authoritative; final
  provenance resolves via P-165 evidence IDs.
- Impl: `fast_v2/citations/finalizer.py`.

## Task 9 — Claim-grounding interface placeholder
- Test: status is `unvalidated`, never `grounded=true`.
- Impl: `fast_v2/grounding/interface.py` +
  `UnvalidatedClaimGroundingPassthrough`.

## Task 10 — Observability / timings
- Test: all required phase timings and `generation_calls == 1` are exposed.
- Impl: `fast_v2/observability.py`.

## Task 11 — Regression + full tests
- Run the whole suite; confirm no new failures against the recorded baseline.

## Task 12 — Documentation / handoff
- Final doc pass, `git status` clean.

---

## Outcome (all tasks complete)

Tasks were implemented in dependency order rather than strict numeric order:
1, 2, 3, 4, 5, 6, then 9 (grounding) and 8 (finalizer) as leaf components,
then 7 + 10 together (the pipeline needs the timings), then 11 and 12.

Commits (one per task boundary):

| Commit | Task |
|---|---|
| `ca04592` | 1 — ADR + `SYNTHESIS_MODE` flag |
| `90cc3b1` | 2 — `EvidenceUnit` |
| `7e8ce1d` | 3 — Evidence Hygiene |
| `6ba6cf2` | 4 — dimension planner, selection policy, reranker contract |
| `fc11545` | 5 — `GroundedEvidenceBank` |
| `6627e04` | 6 — OpenScholar adapter + frozen prompt |
| `d8c98dc` | 9 — claim-grounding interface |
| `efdbb87` | 8 — deterministic citation finalizer |
| `8385639` | 7 + 10 — pipeline wiring + observability |

Test results: **277 passed, 5 failed**, versus the recorded baseline of
**128 passed, 5 failed**. The same 5 pre-existing failures, unchanged:

- `tests/test_agents/test_graph.py::test_agent_basic_flow` — OpenAI auth
- `tests/test_agents/test_graph.py::test_agent_state_structure` — OpenAI auth
- 3 × `tests/test_services/test_vector_store_async.py` — `SimpleNamespace`
  fixtures lack `local_embedding_model`, pre-existing since commit `5fbc555`

**149 new tests, zero regressions.** The diff against `5fbc555` is 4132
insertions and **0 deletions**; the only file changed outside
`src/synthesis/fast_v2/` is `src/config.py` (22 additive lines). Legacy
synthesis is byte-for-byte untouched.

### Deliberately NOT ported from the scratch experiments

- `run_dimension_aware_v1.py`, `run_controlled_legacy.py`,
  `run_final_controlled_ab.py`, `run_multi_set_stress_benchmarks.py`,
  `spike_evidence_first_v*.py`, `spike_global_extraction*.py`,
  `microbench_*.py`, `measure_round1_variance.py` — benchmark runners and
  report printers, not runtime services.
- `colab_rq2_dimension_v1_generation.py` and the Colab notebooks — notebook
  cells, `google.colab` download helpers, and a `min_tokens=450` sampling
  config that is a known-invalid setting. Only the prompt structure and the
  sanitization regex were taken from CELL 4.
- Benchmark identifiers (RQ1/RQ2/Xu2010/Xu2018) and the hardcoded dimension
  strings — enforced absent from executable code by a tokenizer-based test.
- `evidence_hygiene_report.md` metrics tables — recorded in the ADR as
  evidence, not embedded in runtime code.
- The invalid 162.99s generation artifact — recorded in the ADR only, as a
  counter-example.

---

## Explicitly out of scope

- Any LLM planner for dimension decomposition.
- Any real claim verification.
- Any new reranker model or scoring convention.
- Any change to Legacy synthesis behaviour.
- Any GPU/Colab run — the OpenScholar numbers are recorded, not re-verified.
