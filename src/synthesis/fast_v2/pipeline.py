"""Fast Synthesis v2 pipeline -- EXPERIMENTAL.

Dataflow::

    prepare_fast_v2
      -> build_dimension_queries
      -> retrieve_evidence_first
      -> apply_evidence_hygiene
      -> rerank_per_dimension
      -> apply_relevance_gate
      -> merge_evidence_bank
      -> generate_openscholar          (exactly ONE generation call)
      -> structured_provenance_guard   (semantic entailment unvalidated)
      -> semantic_verification         (one optional batch call)
      -> grounded_literature_writer    (one optional controlled call)
      -> deterministic_finalize        (P-165 owns citations)

Invariant: **ZERO query-time LLM evidence-extraction calls.** This pipeline
must never gain an ``extract_paper`` call, an evidence-extraction call, a
recovery-extraction loop, semantic LLM dedup, claim-graph generation, or an
iterative QA loop.

Legacy (``src/synthesis/graph.py``) is untouched and remains the default.
Every result from this pipeline is labelled ``fast_v2_experimental`` with
``claim_grounding_status="unvalidated"``.
"""
from __future__ import annotations

import asyncio

from dataclasses import dataclass, field
from typing import Any, Sequence

from src.synthesis.fast_v2.citations.finalizer import (
    FinalCitation,
    finalize_structured_draft,
)
from src.synthesis.fast_v2.dimensions.planner import (
    DeterministicDimensionQueryPlanner,
    DimensionQueryPlanner,
)
from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.evidence.retrieval import EvidenceRetriever
from src.synthesis.fast_v2.generator.base import SynthesisGenerator
from src.synthesis.fast_v2.grounding.interface import (
    ClaimGroundingService,
    StructuredClaimManifestGroundingService,
)
from src.synthesis.fast_v2.grounding.semantic import (
    SemanticVerifier,
    verify_and_filter_statements,
)
from src.synthesis.fast_v2.hygiene.classifier import filter_evidence_units
from src.synthesis.fast_v2.observability import PhaseTimings
from src.synthesis.fast_v2.planning.research_lead import LongformOutlinePlan
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
from src.synthesis.fast_v2.selection.rerank import (
    IdentityReranker,
    apply_reranker_many,
)
from src.synthesis.fast_v2.writer import (
    GroundedLiteratureWriter,
    apply_grounded_literature_writer,
)

SYNTHESIS_MODE = "fast_v2_experimental"


class FastV2CandidateExplosionError(RuntimeError):
    """Raised BEFORE calling the reranker when the total candidate pool would
    make the rerank call unbounded. Never let a user silently wait minutes
    for an unannounced-size rerank -- fail fast, tell the caller exactly
    which knob to turn (section_candidate_cap / candidates_per_dimension /
    fewer sections or queries)."""


def _dedupe_and_cap_pool(units: Sequence, *, cap: int) -> list:
    """Cheap union+fusion: dedupe by evidence_id keeping the best-scoring
    occurrence, then keep only the top ``cap`` by retrieval score.

    This is the per-section compute budget: a section's candidates -- unioned
    across ALL of that section's retrieval_queries -- are capped here BEFORE
    the single per-section rerank call, so rerank latency depends on the cap,
    not on how many queries a section happens to have.
    """
    best: dict[str, Any] = {}
    for unit in units:
        existing = best.get(unit.evidence_id)
        score = unit.retrieval_score if unit.retrieval_score is not None else float("-inf")
        if existing is None:
            best[unit.evidence_id] = unit
            continue
        existing_score = (
            existing.retrieval_score if existing.retrieval_score is not None else float("-inf")
        )
        if score > existing_score:
            best[unit.evidence_id] = unit

    ranked = sorted(
        best.values(),
        key=lambda unit: unit.retrieval_score if unit.retrieval_score is not None else float("-inf"),
        reverse=True,
    )
    return ranked[:cap]


@dataclass(frozen=True)
class FastSynthesisV2Result:
    """Experimental synthesis output. Never presented as validated."""

    text: str
    evidence_bank: GroundedEvidenceBank
    citations: tuple[FinalCitation, ...]
    timings: dict[str, Any]

    synthesis_mode: str = SYNTHESIS_MODE
    claim_grounding_status: str = "unvalidated"
    grounding_warning: str = ""
    citation_authority: str = "p165_deterministic_finalizer"
    native_citation_indices: tuple[int, ...] = ()
    rejected_native_indices: tuple[int, ...] = ()
    structured_provenance_validation: str = "not_evaluated"
    semantic_entailment: str = "unvalidated"
    semantic_grounded: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def grounded(self) -> bool:
        return self.semantic_grounded

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "synthesis_mode": self.synthesis_mode,
            "claim_grounding_status": self.claim_grounding_status,
            "grounded": self.grounded,
            "grounding_warning": self.grounding_warning,
            "citation_authority": self.citation_authority,
            "citations": [citation.to_dict() for citation in self.citations],
            "native_citation_indices": list(self.native_citation_indices),
            "rejected_native_indices": list(self.rejected_native_indices),
            "structured_provenance_validation": self.structured_provenance_validation,
            "semantic_entailment": self.semantic_entailment,
            "evidence_bank": self.evidence_bank.to_dict(),
            "timings": dict(self.timings),
            "diagnostics": dict(self.diagnostics),
        }


class FastSynthesisV2Pipeline:
    """Wires the frozen fast_v2 components together."""

    def __init__(
        self,
        *,
        retriever: EvidenceRetriever,
        generator: SynthesisGenerator,
        reranker: Any | None = None,
        planner: DimensionQueryPlanner | None = None,
        selection_policy: EvidenceSelectionPolicy | None = None,
        grounding_service: ClaimGroundingService | None = None,
        semantic_verifier: SemanticVerifier | None = None,
        literature_writer: GroundedLiteratureWriter | None = None,
        candidates_per_dimension: int = 40,
        evidence_budget: int = 36,
        section_candidate_cap: int = 32,
        max_total_rerank_pairs: int = 320,
        outline: LongformOutlinePlan | None = None,
        extraction_llm: Any | None = None,
    ) -> None:
        self.retriever = retriever
        self.generator = generator
        self.reranker = reranker or IdentityReranker()
        self.planner = planner or DeterministicDimensionQueryPlanner()
        self.selection_policy = selection_policy or EvidenceSelectionPolicy()
        self.grounding_service = (
            grounding_service or StructuredClaimManifestGroundingService()
        )
        self.semantic_verifier = semantic_verifier
        self.literature_writer = literature_writer
        self.candidates_per_dimension = candidates_per_dimension
        self.evidence_budget = evidence_budget
        self.section_candidate_cap = section_candidate_cap
        self.max_total_rerank_pairs = max_total_rerank_pairs
        self.outline = outline

        # Held only so tests can prove it is never used. fast_v2 performs no
        # query-time evidence extraction; this must stay unused.
        self._extraction_llm = extraction_llm

    async def run(
        self, *, question: str, dimensions: Sequence[str]
    ) -> FastSynthesisV2Result:
        timings = PhaseTimings()

        with timings.total():
            # -- build_dimension_queries -------------------------------------
            with timings.phase("dimension_query_ms"):
                queries = self.planner.plan(
                    research_question=question, dimensions=dimensions
                )

            evidence_by_dimension: dict[str, list] = {}
            hygiene_dropped = 0
            hygiene_rescued = 0
            # Fusion group key is (dimension, paper_id), NOT dimension alone.
            # Outline sections never set paper_id, so all of a section's
            # retrieval_queries share one group and get fused/capped/reranked
            # together (the union+fusion this restructuring exists for).
            # Comparative facet-paper-scoped queries (paper_id set, one query
            # per selected paper under the same facet) instead get one group
            # PER PAPER -- merging them would let one paper's stronger scores
            # silently squeeze a weaker-but-genuine paper out of the bank,
            # which is exactly the "no negative padding, keep each paper's
            # own positive evidence" guarantee this pipeline already made.
            pool_raw: dict[tuple[str, Any], list] = {}
            pool_rerank_query: dict[tuple[str, Any], str] = {}

            for query in queries:
                # -- retrieve_evidence_first (no LLM) ------------------------
                with timings.phase("retrieval_ms"):
                    retrieve_kwargs: dict[str, Any] = {
                        "limit": self.candidates_per_dimension
                    }
                    if query.paper_id is not None:
                        retrieve_kwargs["paper_id"] = query.paper_id
                    candidates = list(
                        await self.retriever.retrieve(
                            query.query_text, **retrieve_kwargs
                        )
                    )

                # -- apply_evidence_hygiene ----------------------------------
                with timings.phase("hygiene_ms"):
                    kept, dropped = filter_evidence_units(candidates)
                    hygiene_dropped += len(dropped)
                    # Hygiene was calibrated on one old math corpus. Never let
                    # it starve a whole user request: when it rejects every
                    # candidate for a query, retain the least risky rejected
                    # chunks as retrieval context. They still must pass claim
                    # provenance and semantic verification before output.
                    if not kept and dropped:
                        non_boilerplate = [
                            unit for unit in dropped
                            if unit.hygiene_class != "boilerplate"
                        ]
                        kept = non_boilerplate or list(dropped[:3])
                        hygiene_rescued += len(kept)

                group_key = (query.dimension, query.paper_id)
                pool_raw.setdefault(group_key, []).extend(kept)
                # First query text seen for a group is what that group's
                # single rerank call scores candidates against.
                pool_rerank_query.setdefault(group_key, query.query_text)

            # -- cheap union + fusion + per-group compute-budget cap ---------
            # NOT an evidence quota -- purely a rerank compute ceiling. Raw
            # union of every query's raw candidates is exactly the failure
            # mode that made an earlier run's rerank stage take 918s: unbind
            # the cap and pairs explode with every extra retrieval_query.
            with timings.phase("evidence_bank_ms"):
                pool_capped: dict[tuple[str, Any], list] = {
                    group_key: _dedupe_and_cap_pool(units, cap=self.section_candidate_cap)
                    for group_key, units in pool_raw.items()
                }

            total_pairs = sum(len(pool) for pool in pool_capped.values())
            if total_pairs > self.max_total_rerank_pairs:
                raise FastV2CandidateExplosionError(
                    f"total rerank pairs {total_pairs} across "
                    f"{len(pool_capped)} group(s) exceed "
                    f"max_total_rerank_pairs={self.max_total_rerank_pairs}. "
                    "Lower fast_v2_section_candidate_cap/"
                    "fast_v2_candidates_per_dimension or reduce the number of "
                    "sections/retrieval_queries -- refusing to run an "
                    "unbounded rerank call before it starts."
                )

            # -- rerank_per_dimension: exactly ONE call per (dimension,paper) group --
            with timings.phase("rerank_ms"):
                group_order = list(pool_capped.keys())
                reranked_groups = await asyncio.to_thread(
                    apply_reranker_many,
                    self.reranker,
                    requests=[
                        (pool_rerank_query[group_key], pool_capped[group_key])
                        for group_key in group_order
                    ],
                )

            for (dimension, _paper_id), reranked in zip(group_order, reranked_groups):
                # -- prepare Evidence Bank candidate pool --------------------
                # Groups sharing a dimension (different paper_id -- the
                # comparative case) merge back into the same dimension bucket
                # here, each having already been selected independently above.
                with timings.phase("evidence_bank_ms"):
                    dimension_candidates = evidence_by_dimension.setdefault(
                        dimension, []
                    )
                    dimension_candidates.extend(
                        self.selection_policy.select(
                            reranked, dimension=dimension
                        )
                    )

            # -- merge_evidence_bank ------------------------------------------
            with timings.phase("evidence_bank_ms"):
                planned_dimensions = list(
                    dict.fromkeys(query.dimension for query in queries)
                )
                bank = GroundedEvidenceBank.build(
                    question=question,
                    dimensions=planned_dimensions,
                    evidence_by_dimension=evidence_by_dimension,
                    query_ms=timings.timings["dimension_query_ms"],
                    retrieval_ms=timings.timings["retrieval_ms"],
                    rerank_ms=timings.timings["rerank_ms"],
                    evidence_budget=self.evidence_budget,
                    relevance_threshold=(
                        self.selection_policy.relevance_threshold
                    ),
                )

            # -- generate_openscholar (exactly ONE call) ----------------------
            with timings.phase("generation_ms"):
                draft = await asyncio.to_thread(
                    self.generator.generate,
                    question=question,
                    evidence_bank=bank,
                )
                timings.record_generation_call(draft.generation_calls)

            # -- structured_provenance_guard ----------------------------------
            with timings.phase("grounding_ms"):
                grounded = self.grounding_service.evaluate(
                    draft=draft, evidence_bank=bank
                )

            semantic = await asyncio.to_thread(
                verify_and_filter_statements,
                original_draft=grounded,
                evidence_bank=bank,
                verifier=self.semantic_verifier,
            )
            writer = await asyncio.to_thread(
                apply_grounded_literature_writer,
                semantic=semantic,
                evidence_bank=bank,
                writer=self.literature_writer,
                outline=self.outline,
            )

            # -- deterministic_finalize ---------------------------------------
            with timings.phase("finalize_ms"):
                finalized = finalize_structured_draft(
                    grounded=writer.finalizer_draft,
                    evidence_bank=bank,
                )

        return FastSynthesisV2Result(
            text=finalized.text,
            evidence_bank=bank,
            citations=finalized.citations,
            timings=timings.to_dict(),
            claim_grounding_status=grounded.claim_grounding_status.value,
            grounding_warning=semantic.warning,
            citation_authority=finalized.citation_authority,
            native_citation_indices=finalized.native_citation_indices,
            rejected_native_indices=finalized.rejected_native_indices,
            structured_provenance_validation=(
                grounded.structured_provenance_validation
            ),
            semantic_entailment=semantic.semantic_entailment,
            semantic_grounded=semantic.grounded,
            diagnostics={
            "hygiene_dropped": hygiene_dropped,
            "hygiene_rescued": hygiene_rescued,
                "candidates_before_fusion_per_group": {
                    f"{dimension}|{paper_id}": len(units)
                    for (dimension, paper_id), units in pool_raw.items()
                },
                "candidates_after_fusion_per_group": {
                    f"{dimension}|{paper_id}": len(units)
                    for (dimension, paper_id), units in pool_capped.items()
                },
                "total_rerank_pairs": total_pairs,
                "model_name": draft.model_name,
                "prompt_version": draft.prompt_version,
                "finish_reason": draft.finish_reason,
                "stop_reason": draft.stop_reason,
                "generation_calls": draft.generation_calls,
                "generation_network_ms": draft.generation_ms,
                "input_tokens": draft.input_tokens,
                "output_tokens": draft.output_tokens,
                "evidence_handle_mapping": dict(draft.evidence_handle_mapping),
                **grounded.diagnostics,
                "semantic_verification_ms": semantic.verification_ms,
                "semantic_verified_statements": len(semantic.verified_statements),
                "semantic_rejected_statements": len(semantic.rejected_statements),
                **semantic.diagnostics,
                "writer_calls": writer.writer_calls,
                "writer_latency_ms": writer.writer_latency_ms,
                "writer_input_tokens": writer.writer_input_tokens,
                "writer_output_tokens": writer.writer_output_tokens,
                "writer_fallback_reason": writer.writer_fallback_reason,
                "writer_claim_coverage": writer.claim_coverage,
                **finalized.diagnostics,
            },
        )
