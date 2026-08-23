# Fast Synthesis v2 — Architecture Freeze

Status: **EXPERIMENTAL**, behind `SYNTHESIS_MODE=fast_v2_experimental`.
Legacy remains the default and is unaffected.

This document is the source of truth for the validated P-165 fast-synthesis
research. It records experiment facts verbatim. Numbers here are **not** rounded
up or improved. Where something is unvalidated it is stated as unvalidated.

---

## A. Motivation

Legacy synthesis is accurate but slow, and its dominant cost is a query-time
LLM pass that re-reads every selected paper on every synthesis run. That work
is repeated for every question against the same corpus, and it scales linearly
with paper count.

Separately, two evidence-quality problems were observed in the OpenScholar
spike: bibliography/reference-list chunks occupied top evidence slots, and
per-dimension retrieval returned near-identical evidence.

Fast v2 freezes the validated answers to those problems into production-shaped,
feature-flagged, test-covered code so the work stops living in scratch scripts,
Colab notebooks, and the `phase123-merge` worktree.

## B. Legacy architecture

`prepare -> extract_paper (fan-out, LLM per paper) -> ensure_coverage ->
deduplicate_evidence -> cross_paper -> build_outline -> draft_section (fan-out)
-> qa_review -> finalize`

Implemented in `src/synthesis/graph.py` + `src/services/synthesis_service.py`.
Evidence is produced by an LLM extraction attempt per paper per dimension,
persisted as `EvidenceExtractionAttempt` and, when grounded, as
`EvidenceRecord`. Citations are rendered deterministically in
`SynthesisService.finalize_review`.

Legacy measured latency: **≈ 778.16s**.

## C. Fast v1.1 architecture

Fast v1.1 reduced total latency to **≈ 203.40s (~3.83x faster than Legacy)**.

Critically, Fast v1.1 **still used query-time per-paper evidence-extraction LLM
calls**; that critical extraction path alone was **≈ 141s**. So v1.1 sped up the
surrounding pipeline but did not remove the structural bottleneck.

## D. Evidence-First experiments

Evidence-First removed query-time evidence-extraction LLM calls entirely.

Core principle: reuse canonical scientific chunks as EvidenceUnits, plus
semantic retrieval and cross-encoder reranking, instead of having an LLM
re-read and extract from each paper on every synthesis query.

The experiments demonstrated **query-time extraction LLM calls = 0**. That is a
REQUIRED fast_v2 invariant, not a nice-to-have.

Caveat recorded deliberately: do **not** claim all historical Evidence-First
latency numbers are production-equivalent. Some earlier retrieval runs predated
the production embedding-provider correction (commit `5fbc555`, which stopped
the silent fallback to non-semantic hash embeddings).

## E. Evidence Hygiene experiment

Known problem: bibliography/reference-list chunks occupied top evidence slots.

Validated hygiene spike results:

- RQ1 contamination@10: **0.4 -> 0.0**
- RQ2 contamination@10: **0.3 -> 0.0**
- **No observed false positives** in manually inspected excluded chunks.

Known limitation: the threshold is calibrated only on the current small corpus
plus fixtures. It is an **experimental component, NOT a globally validated
scientific-paper classifier.**

Supporting detail from the spike report (all deterministic, no LLM):

| | RQ1 | RQ2 |
|---|---|---|
| candidate_pool | 40 | 40 |
| reference_like (before) | 8 | 9 |
| boilerplate (before) | 1 | 1 |
| scientific_content (before) | 31 | 30 |
| contamination@10 BEFORE | 0.4 | 0.3 |
| contamination@10 AFTER | 0.0 | 0.0 |
| promoted_evidence_count | 4 | 3 |
| candidate_loss_rate | 0.225 | 0.25 |

Two honest limitations carried over from the spike:

1. Hygiene **reduced** Xu2010 representation in top-10 (2 -> 1 in both RQs).
   Contamination went to 0, but paper coverage did not improve.
2. Promoted replacement chunks have markedly lower/negative rerank scores
   (RQ1 top-10 min 0.11 -> -0.49; RQ2 -0.04 -> -1.47). Hygiene trades
   contamination for weaker semantic-relevance scores at the tail.

Hygiene guarantees "not bibliography/boilerplate". It does **not** guarantee
"high content value".

## F. Dimension-Aware v0 failure

v0 query construction was: full research question + `"Focus specifically on:
{dimension}"`.

- RQ1: 15 selections -> **3 unique evidence, 80% duplicate rate**
- RQ2: 12 selections -> **3 unique evidence, 75% duplicate rate**

Reason: the full research question already contained the dimension terms, so
the dimension queries had embedding cosine similarity **>0.98** and were
effectively identical.

## G. Dimension Query v1 success

The fix was standalone deterministic dimension queries — a dimension query is
built from the dimension itself, not by appending the dimension to the full
research question.

Query similarity (off-diagonal mean/max/min):

| | v0 | v1 |
|---|---|---|
| RQ1 | 0.987 / 0.991 / 0.983 | 0.656 / 0.778 / 0.514 |
| RQ2 | 0.988 / 0.990 / 0.985 | 0.595 / 0.767 / 0.509 |

Duplicate selection rate: RQ1 **80% -> 40%**, RQ2 **75% -> 41.7%**.

Final v1 banks:

- RQ1: **9 EvidenceUnits** (Xu2018=7, Xu2010=2)
- RQ2: **7 EvidenceUnits** (Xu2018=4, Xu2010=3)

RQ1 surfaced computational evidence (Xu2018 runtime/table evidence). RQ2
surfaced Xu2010 formulation evidence, Xu2010 bounded-linear/Hilbert-space
evidence, and Xu2018 convergence/stationary-point evidence.

**No negative-score padding, no forced per-paper balance.**

## H. OpenScholar validation

Model validated in Colab T4: `NeuML/Llama-3.1_OpenScholar-8B-AWQ`.

Native OpenScholar citation IDs are **NOT trusted as provenance authority** —
known citation-namespace failures occurred in previous spikes. P-165 must own
citation/provenance mapping.

Final corrected controlled RQ2 generation:

- input tokens **3974**
- output tokens **493**
- warm generation **27.18s**
- `finish_reason=stop`
- `stop_reason=[Response_End]`

An earlier **162.99s / 3000-token run was INVALID as latency evidence** — the
model had already emitted `[Response_End]` and then repeated numeric output
until `max_tokens`. That invalid artifact is preserved at
`openscholar_rq2_dimension_v1_raw.json` (`finish_reason=length`,
`stop_reason=null`, `min_tokens=450`) and must not be cited as a latency result.

Correct generation termination config (frozen):

```
min_tokens=0
stop=["[Response_End]"]
stop_token_ids=[128009]
```

**Do NOT reintroduce `min_tokens=450` in fast_v2.**

## I. Known failures / limitations

Quality status, stated honestly:

- OpenScholar **speed**: PASS / promising.
- Final RQ2 answer: all major facets present or partial, real cross-paper
  synthesis exists, the old second-derivative error disappeared.
- **Factual control is NOT solved.** Observed generator issues include:
  - an unsupported claim about Xu2010 proximity-function convexity,
  - overclaiming future-work language as something Xu2018 already investigated,
  - incomplete/weak comparison of some convergence assumptions,
  - native citation misattribution.

Therefore: **generation latency is validated; final factual grounding is NOT
validated.** Never state fast_v2 quality is "solved".

Additional limitations:

- Hygiene threshold (8.0) is a reasonable first cut, not a calibrated
  production threshold.
- The relevance gate `score > 0` is likewise **not** calibrated.
- The core benchmark corpus is only Xu2010/Xu2018. No held-out generalization.
- A concrete cross-encoder adapter now ships (section J), but it is **not the
  default**, and it has **not** been re-validated against the RQ1/RQ2 v1
  evidence banks — see "Reranker wiring status" in section J for exactly what
  could and could not be verified.

## J. Final fast_v2 architecture

```
canonical PDF chunks / PageText
    -> Evidence-First reusable EvidenceUnits
    -> deterministic dimension queries
    -> retrieve EvidenceUnits
    -> Evidence Hygiene
    -> rerank
    -> relevance gate
    -> merge/dedupe Evidence Bank
    -> ONE OpenScholar generation call
    -> future claim-grounding layer (interface only, unvalidated passthrough)
    -> deterministic P-165 provenance/citation finalizer
```

Pipeline stages as implemented in `src/synthesis/fast_v2/pipeline.py`:

`prepare_fast_v2 -> build_dimension_queries -> retrieve_evidence_first ->
apply_evidence_hygiene -> rerank_per_dimension -> apply_relevance_gate ->
merge_evidence_bank -> generate_openscholar -> claim_grounding_placeholder ->
deterministic_finalize`

**The single most important invariant: ZERO query-time LLM evidence-extraction
calls.** Do not reintroduce, even accidentally: `extract_paper` LLM calls,
evidence-extraction LLM calls, a "recovery extraction loop", semantic LLM
dedup, claim-graph generation, or iterative QA loops into fast_v2.

### Reranker

`src/synthesis/fast_v2/selection/rerank.py` defines the `EvidenceReranker`
protocol. Its contract is unchanged: `rerank(query, texts)` returns
`(index, score)` pairs, the caller re-associates by `index`, ordering is the
reranker's output order (not input order), and scores are raw cross-encoder
logits which are unbounded and legitimately negative.

#### The model

`src/synthesis/fast_v2/selection/cross_encoder.py` implements
`CrossEncoderReranker` over **`cross-encoder/ms-marco-MiniLM-L-6-v2`**.

That is the reranker the validated Evidence-First / Hygiene / Dimension-Aware
work actually ran against. It is not a new choice — it is the repository's
pre-existing reranker, declared at `src/services/reranker.py:13` on the
`feat/phase123-eval-hybrid-agentic` worktree and imported by every
Evidence-First spike there (`spike_evidence_first_v0.py:61`,
`spike_evidence_first_v1_context_budget.py:61`,
`spike_evidence_first_v2_section_routing.py:61`, `spike_global_extraction.py:45`,
`spike_global_extraction_v2.py:31`) as "the existing cross-encoder reranker".

`Qwen/Qwen3-Reranker-0.6B` (`feat/scientific-reranker-mvp`,
`src/services/qwen_reranker.py:12`) is documented in that worktree as a
"Candidate replacement for the MiniLM reranker slot" whose real inference was
deferred to Colab. It did **not** produce the v1 numbers and is deliberately
NOT implemented here. Nor is the locally fine-tuned QASPER checkpoint under
`scientific-reranker/final_model` (`run_manifest.json`, base
`ms-marco-MiniLM-L6-v2`), which belongs to a separate evaluation.

#### Call contract, preserved exactly

Upstream built `(query, doc.page_content)` pairs — query first, input order —
scored them with `CrossEncoder.predict`, and sorted **score-descending**. The
adapter reproduces all of that; the only shape change is returning `(index,
score)` instead of `(Document, score)`, so nothing can positionally mis-pair
evidence with scores.

Verified live against the real checkpoint (offline, cached): adapter output is
byte-identical to the upstream call in both index order and score values.
Observed logit range on a 5-passage probe: **-11.42 .. +5.91**.

Note what that range implies for the *uncalibrated* `score > 0` gate: on that
probe only 1 of 5 passages cleared it. The gate and this model's score scale
are coupled; re-calibrating one without the other is not meaningful.

#### Selection

`fast_v2_reranker` (`src/config.py`) is `Literal["identity", "cross_encoder"]`
and defaults to **`"identity"`** — `IdentityReranker`, which performs no
reranking. `src/synthesis/fast_v2/selection/factory.py::build_reranker`
resolves it. The default keeps imports, CI, and CPU-only machines free of a
checkpoint download and keeps tests deterministic; an unknown value fails
loudly. The model loads lazily on the first `rerank` call, never at import or
construction (asserted by AST and subprocess tests, matching the OpenScholar
discipline).

#### Reranker wiring status — what is NOT validated

The RQ1/RQ2 Dimension-Aware v1 evidence banks (RQ1 9 units, Xu2018=7,
Xu2010=2; RQ2 7 units, Xu2018=4, Xu2010=3) have **not** been reproduced with
this adapter, and could not be. Absent from disk anywhere searched:

- `dimension_aware_lib.py`, `run_dimension_aware_v1.py`, `test_dimension_aware.py`;
- `rq1_dimension_v1.json`, `rq2_dimension_v1.json`, `dimension_aware_summary.json`,
  `evidence_hygiene_report.md`, `rq1/rq2_before_after.json`;
- the RQ1/RQ2 research-question texts and the explicit dimension lists they used;
- the ingested corpus instance itself — the spikes reference Xu2010
  `52c06c26-1dd1-486a-8c4f-202779ed5c7f` and Xu2018
  `0373c7b5-3a9e-437d-a59a-a1baa9a708cc`, and neither the target worktree's
  Chroma store (0 embeddings), `phase123-merge`'s (0 embeddings), nor the root
  store (779 embeddings, different paper ids) contains them.

`data/setB_benchmark.db` in the repo root does hold `5.-xu2010` / `6.-xu2018`
chunk text, but under different paper ids from a different ingestion, with no
matching embedding index and no recorded dimension queries. Running against it
would produce a *new* number, not a comparison, so no such comparison was
fabricated.

Promotion criterion 6 is therefore **partially** met: the reranker is wired and
its scoring convention is pinned by tests, but its effect on the evidence bank
is unmeasured. Re-validating it requires re-ingesting Xu2010/Xu2018 and
recovering the v1 dimension lists.

### EvidenceUnit vs EvidenceRecord — mapping

`EvidenceUnit` is a **new runtime type**, deliberately NOT reusing the
`EvidenceRecord` ORM model. Reason, verified against `src/models/db_models.py`:

`EvidenceRecord.created_from_attempt_id` is `nullable=False` and unique — an
`EvidenceRecord` cannot exist without an `EvidenceExtractionAttempt`, i.e.
without an LLM extraction. Evidence-First produces evidence with **no**
extraction attempt by construction, so reusing `EvidenceRecord` would either
violate the schema or force a fake extraction attempt row.

Mapping of semantics:

| EvidenceUnit field | Legacy analogue | Note |
|---|---|---|
| `evidence_id` | `EvidenceRecord.id` | canonical dedupe/provenance key |
| `source_chunk_id` | `EvidenceRecord.source_chunk_id` | the `PDFChunk.id` |
| `page_text_id` | `EvidenceRecord.page_text_id` | canonical `PageText.id` |
| `text` | `EvidenceRecord.quote` | verbatim canonical chunk text |
| `page_char_start/end` | same | offsets into `PageText.full_text` |
| `paper_id`, `page` | same | |

**Do not confuse `EvidenceRecord.id` with `PDFChunk.id`.** This exact confusion
bit the team during the hygiene spike. In fast_v2, `EvidenceUnit.evidence_id`
is derived from the source chunk identity and is explicitly a *different*
field from `source_chunk_id`, and both are carried.

## K. What is frozen

| Component | Status | Evidence |
|---|---|---|
| Evidence-First retrieval | FROZEN candidate | zero query-time extraction LLM |
| Production semantic embeddings | FROZEN | corrected MiniLM 384 local backend |
| Evidence Hygiene | FROZEN experimental | contamination 30-40% -> 0 on current benchmark |
| Dimension Query v1 concept | FROZEN experimental | query separation + lower duplicate rate |
| No negative padding | FROZEN | prevents weak tail evidence |
| OpenScholar generator | FROZEN experimental | 27.18s controlled warm generation |
| Native OpenScholar citations | REJECTED | provenance failures |
| P-165 deterministic finalizer | KEEP | authoritative citations |
| Claim grounding | OPEN | quality failures remain |
| General-purpose dimension decomposition | OPEN | current experiment used deterministic explicit dimensions |
| Held-out generalization | OPEN | current core benchmark only Xu2010/Xu2018 |
| Reranker model choice | FROZEN | `cross-encoder/ms-marco-MiniLM-L-6-v2`, the reranker the v1 spikes imported |
| Reranker effect on the bank | OPEN | v1 banks not reproducible; corpus + dimension lists absent |

## L. What is explicitly NOT solved yet

1. **Claim-level factual grounding.** `ClaimGroundingService` is an interface.
   The only implementation is `UnvalidatedClaimGroundingPassthrough`, which
   reports `claim_grounding_status="unvalidated"` and never `grounded=true`.
2. **General question decomposition.** fast_v2 requires explicit dimensions.
   There is deliberately **no** production heuristic that turns an arbitrary
   research question into dimensions. This is the NEXT design decision. The
   validated experiments used manually specified dimensions.
3. **Calibrated thresholds.** Hygiene 8.0 and relevance `> 0` are experimental
   defaults exposed as configuration, not calibrated values.
4. **Reranker effect on the evidence bank.** `CrossEncoderReranker`
   (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is wired and its call/score
   contract is pinned by tests, but the RQ1/RQ2 v1 banks were **not**
   reproduced with it — the v1 scripts, artifacts, dimension lists and corpus
   instance are gone. Default stays `identity`. See section J, "Reranker
   wiring status".
5. **Held-out corpus validation.** Only Xu2010/Xu2018.
6. **Answer quality.** See section I. Latency is validated; factuality is not.

## M. Promotion criteria before becoming default

fast_v2 may only become the default when ALL of the following hold:

1. A real claim-grounding implementation exists and its precision/recall is
   measured against a labelled claim-support set — not a passthrough.
2. The four named generator failure modes in section I are shown to be
   detected or prevented, with evidence.
3. Hygiene threshold is re-calibrated against a held-out multi-paper corpus
   with a reported false-positive rate.
4. The relevance gate is calibrated rather than `> 0`.
5. A general dimension-decomposition strategy is designed and validated, or
   the API contractually requires caller-supplied dimensions.
6. A concrete reranker is wired and its scoring convention is pinned by tests.
   **PARTIAL.** `CrossEncoderReranker` is wired and its convention is pinned,
   but it is still not the default and its effect on the RQ1/RQ2 evidence
   banks is unmeasured. This criterion is met only once the v1 banks are
   reproduced (or deliberately superseded) on a re-ingested corpus.
7. End-to-end latency is re-measured on the production embedding backend, so
   the numbers are production-equivalent (see section D caveat).
8. Legacy regression suite still passes and a quality A/B on a held-out set
   shows fast_v2 is not worse.

Until then, fast_v2 stays behind `SYNTHESIS_MODE=fast_v2_experimental` and
every result it emits carries `synthesis_mode="fast_v2_experimental"` and
`claim_grounding_status="unvalidated"`.

---

## Appendix: provenance of the ported code

- The Evidence Hygiene classifier source file (`hygiene_classifier.py`) was
  **not present on disk** in the `phase123-merge` worktree or anywhere else
  searched. It was reconstructed from the spike's own written specification in
  `evidence_hygiene_report.md` (signals, weights, caps, threshold, structural
  gate, boilerplate rules) and then **verified numerically**: the scoring
  formula reproduces the recorded `hygiene_score` exactly for all 16
  `reference_like` chunks in `rq1_before_after.json` / `rq2_before_after.json`.
  Those recorded signal vectors are checked into the test suite as regression
  fixtures.
- The frozen prompt `p165_controlled_sanitized_v1` is taken from CELL 4 of
  `P165_OpenScholar_RQ2_Clean_Validation.ipynb`.
- The citation-sanitization regex is taken from the same notebook cell.
