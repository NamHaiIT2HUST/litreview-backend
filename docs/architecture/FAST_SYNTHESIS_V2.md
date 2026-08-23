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
- The reranker is an injected interface in this worktree; no cross-encoder
  implementation ships here (see section J).

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

`src/synthesis/fast_v2/selection/rerank.py` defines an `EvidenceReranker`
protocol only. **No reranker model, service, or scoring convention is
introduced by this freeze** — the target worktree contains none, and the
validated experiments used an externally supplied cross-encoder. The protocol
documents the call signature and the return-order contract (returns
`(index, score)` pairs, caller re-associates; ordering is the reranker's
output order, not the input order). Wiring a concrete reranker is a follow-up.

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
4. **Reranker wiring.** Protocol only; no concrete implementation in this
   worktree.
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
