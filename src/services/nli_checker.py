"""Module 1 — Evidence Quantification Engine, Tier 2: custom NLI cross-encoder.

Classifies a single (premise, claim) pair into the SAME 3-way label space
already used elsewhere in this codebase (``EntailmentStatus`` in
src/models/synthesis_schemas.py: supported / contradicted / insufficient),
so this tier's output can be consumed anywhere that enum already is without a
translation layer.

No checkpoint ships in this repo. Train one via scripts/finetune_nli/ (see
MODULE_1_PLAN.md) and place it at ``settings.nli_evidence_model_path``
(default ``./models/nli_evidence_v1``) before enabling
``NLI_EVIDENCE_ENABLED=true``. Mirrors src/services/reranker_service.py's
lazy-singleton-load shape for consistency with the one other locally-hosted
cross-encoder already in this project.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Sequence

from src.models.synthesis_schemas import ClaimVerificationDecision, EntailmentStatus

_ID2STATUS = {
    0: EntailmentStatus.contradicted,
    1: EntailmentStatus.insufficient,
    2: EntailmentStatus.supported,
}


@dataclass(frozen=True, slots=True)
class NLIVerdict:
    status: EntailmentStatus
    confidence: float  # softmax probability of the winning class, 0..1
    scores: dict[str, float]  # all 3 class probabilities, for Tier 3 escalation logic


class NLIModelUnavailableError(RuntimeError):
    """Raised when NLI_EVIDENCE_ENABLED=true but no usable checkpoint is found.

    Refuses to silently no-op (e.g. return "insufficient" for everything) --
    a claim-verification tier that always answers "can't tell" without ever
    having loaded a model is worse than an explicit startup failure, per this
    project's established fail-loud convention (see reranker_service.py /
    fast_v2/selection/rerank.py for the same shape of guard)."""


class NLIChecker:
    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._model_path: str | None = None
        self.last_load_ms: float | None = None

    def _get_model(self):
        if self._model is not None:
            return self._model, self._tokenizer

        from src.config import get_settings
        settings = get_settings()
        model_path = settings.nli_evidence_model_path

        import os
        if not os.path.isdir(model_path):
            raise NLIModelUnavailableError(
                f"NLI_EVIDENCE_ENABLED=true but no checkpoint directory at "
                f"{model_path!r}. Train one first: see scripts/finetune_nli/ "
                f"and MODULE_1_PLAN.md. Refusing to silently skip claim "
                f"verification for this tier."
            )

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        t0 = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        model.to("cpu").eval()
        self.last_load_ms = (time.perf_counter() - t0) * 1000.0

        id2label = {int(k): v for k, v in model.config.id2label.items()}
        expected = {0: "contradicted", 1: "insufficient", 2: "supported"}
        if id2label != expected:
            raise NLIModelUnavailableError(
                f"Checkpoint at {model_path!r} has id2label={id2label}, expected "
                f"{expected} (the label order scripts/finetune_nli/ trains with). "
                f"A mismatched label order silently flips supported<->contradicted "
                f"-- refusing to load it as-is."
            )

        self._model, self._tokenizer, self._model_path = model, tokenizer, model_path
        return self._model, self._tokenizer

    def load(self):
        """Materialise the model now (for startup warmup), not on first request."""
        return self._get_model()

    def _classify_sync(self, pairs: Sequence[tuple[str, str]]) -> list[NLIVerdict]:
        import torch

        model, tokenizer = self._get_model()
        verdicts: list[NLIVerdict] = []
        with torch.no_grad():
            for premise, hypothesis in pairs:
                enc = tokenizer(
                    premise, hypothesis, truncation=True, max_length=384, return_tensors="pt"
                )
                logits = model(**enc).logits[0]
                probs = torch.softmax(logits, dim=-1)
                pred_id = int(torch.argmax(probs))
                scores = {_ID2STATUS[i].value: float(probs[i]) for i in range(3)}
                verdicts.append(
                    NLIVerdict(status=_ID2STATUS[pred_id], confidence=float(probs[pred_id]), scores=scores)
                )
        return verdicts

    async def check(self, premise: str, claim: str) -> NLIVerdict:
        """Single (premise, claim) check. See check_many for batches."""
        results = await self.check_many([(premise, claim)])
        return results[0]

    async def check_many(self, pairs: Sequence[tuple[str, str]]) -> list[NLIVerdict]:
        """Batch of (premise, claim) checks, offloaded to a worker thread.

        PROJECT_STANDARDS.md mandates asyncio.to_thread for any CPU-bound
        model call on this deployment: EC2 runs bare uvicorn with
        BackgroundTasks, not a Celery worker, so a blocking call here would
        freeze the whole process's event loop for every other in-flight
        request, not just this one.
        """
        import asyncio
        if not pairs:
            return []
        return await asyncio.to_thread(self._classify_sync, pairs)


nli_checker = NLIChecker()


# Confidence a per-evidence NLI verdict must clear before Tier 2 is allowed to
# decide a claim on its own (below this, the claim escalates to Tier 3 --
# LLM-as-Judge -- exactly like the "0.4-0.8 confidence -> escalate" rule in
# MODULE_1_PLAN.md). Not tuned against production data yet -- 0.75 is a
# deliberately conservative starting point (favours escalating over a wrong
# auto-decision); revisit once NLI_EVIDENCE_ENABLED has real traffic to look at.
TIER2_CONFIDENCE_THRESHOLD = 0.75


async def resolve_claims_via_nli(
    claims_with_evidence: Sequence[tuple[uuid.UUID, str, Sequence[tuple[uuid.UUID, str, str]]]],
    *,
    checker: NLIChecker | None = None,
    confidence_threshold: float = TIER2_CONFIDENCE_THRESHOLD,
) -> dict[uuid.UUID, ClaimVerificationDecision]:
    """Tier 2 of the tri-layer engine: try to resolve each claim from its own
    evidence set using the local NLI cross-encoder, before any claim reaches
    the LLM (Tier 3).

    ``claims_with_evidence`` matches the exact shape
    ``SynthesisService.cross_paper_analysis()`` already builds for
    ``synthesis_llm_service.verify_claim_set_batch()``: one entry per claim,
    each evidence item as ``(evidence_id, value, quote)`` -- reused as-is so
    this function is a drop-in pre-filter, not a parallel code path with its
    own evidence-formatting rules.

    Per claim, every evidence item is scored independently against the claim
    (the NLI model's contract is one premise, one hypothesis -- it never sees
    multiple evidence records at once). The per-evidence verdicts are then
    merged with a fixed, evidence-grounded rule instead of a majority vote:

    - Any evidence item NLI calls "contradicted" at >= ``confidence_threshold``
      settles the claim as contradicted immediately -- a single well-attested
      contradiction should not be out-voted by several weaker "supported"
      reads, since a hallucinated claim only needs one real contradiction.
    - Otherwise, if at least one evidence item is "supported" at
      >= ``confidence_threshold`` AND none is "contradicted" at ANY
      confidence (even low), the claim is settled as supported. Requiring a
      clean sweep on contradiction (not just above-threshold) is deliberately
      stricter than the support side -- a faint contradiction signal is still
      a reason for a human/LLM to look, not something Tier 2 should paper over.
    - Otherwise Tier 2 does not decide: the claim is left out of the returned
      dict entirely, so the caller's existing Tier-3 LLM path runs for it
      completely unchanged.

    Returns a dict only for claims Tier 2 actually settled -- never a partial
    or low-confidence decision. Never returns "insufficient": that verdict is
    already the caller's default for whatever it doesn't override, so a
    manufactured "insufficient" from Tier 2 would just hide claims that
    should have reached Tier 3.
    """
    active_checker = checker or nli_checker
    resolved: dict[uuid.UUID, ClaimVerificationDecision] = {}

    for claim_id, claim_statement, evidence_items in claims_with_evidence:
        evidence_items = list(evidence_items)
        if not evidence_items:
            continue

        pairs = [
            (f"{value} {quote}", claim_statement)
            for _evidence_id, value, quote in evidence_items
        ]
        verdicts = await active_checker.check_many(pairs)

        contradicted_hits = [
            evidence_items[i][0]
            for i, v in enumerate(verdicts)
            if v.status == EntailmentStatus.contradicted and v.confidence >= confidence_threshold
        ]
        any_contradiction_signal = any(
            v.status == EntailmentStatus.contradicted for v in verdicts
        )
        supported_hits = [
            evidence_items[i][0]
            for i, v in enumerate(verdicts)
            if v.status == EntailmentStatus.supported and v.confidence >= confidence_threshold
        ]

        if contradicted_hits:
            resolved[claim_id] = ClaimVerificationDecision(
                status=EntailmentStatus.contradicted,
                evidence_ids=contradicted_hits,
                reason=(
                    f"Tier 2 (local NLI cross-encoder) found high-confidence "
                    f"contradiction against {len(contradicted_hits)} evidence "
                    f"record(s); resolved without an LLM call."
                ),
            )
        elif supported_hits and not any_contradiction_signal:
            resolved[claim_id] = ClaimVerificationDecision(
                status=EntailmentStatus.supported,
                evidence_ids=supported_hits,
                reason=(
                    f"Tier 2 (local NLI cross-encoder) found high-confidence "
                    f"support from {len(supported_hits)} evidence record(s), "
                    f"no contradiction signal from any evidence; resolved "
                    f"without an LLM call."
                ),
            )
        # else: leave unresolved -- caller's Tier 3 (LLM) path handles it.

    return resolved
