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
from src.synthesis.fast_v2.hygiene.classifier import filter_evidence_units
from src.synthesis.fast_v2.observability import PhaseTimings
from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
from src.synthesis.fast_v2.selection.rerank import IdentityReranker, apply_reranker

SYNTHESIS_MODE = "fast_v2_experimental"


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
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def grounded(self) -> bool:
        """Always False: structural provenance is not semantic grounding."""
        return False

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
        candidates_per_dimension: int = 40,
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
        self.candidates_per_dimension = candidates_per_dimension

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

                # -- rerank_per_dimension ------------------------------------
                with timings.phase("rerank_ms"):
                    reranked = apply_reranker(
                        self.reranker, query=query.query_text, units=kept
                    )

                # -- apply_relevance_gate ------------------------------------
                with timings.phase("evidence_bank_ms"):
                    evidence_by_dimension.setdefault(query.dimension, []).extend(
                        self.selection_policy.select(
                            reranked, dimension=query.dimension
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
                )

            # -- generate_openscholar (exactly ONE call) ----------------------
            with timings.phase("generation_ms"):
                draft = self.generator.generate(question=question, evidence_bank=bank)
                timings.record_generation_call(draft.generation_calls)

            # -- structured_provenance_guard ----------------------------------
            with timings.phase("grounding_ms"):
                grounded = self.grounding_service.evaluate(
                    draft=draft, evidence_bank=bank
                )

            # -- deterministic_finalize ---------------------------------------
            with timings.phase("finalize_ms"):
                finalized = finalize_structured_draft(
                    grounded=grounded,
                    evidence_bank=bank,
                )

        return FastSynthesisV2Result(
            text=finalized.text,
            evidence_bank=bank,
            citations=finalized.citations,
            timings=timings.to_dict(),
            claim_grounding_status=grounded.claim_grounding_status.value,
            grounding_warning=grounded.warning,
            citation_authority=finalized.citation_authority,
            native_citation_indices=finalized.native_citation_indices,
            rejected_native_indices=finalized.rejected_native_indices,
            structured_provenance_validation=(
                grounded.structured_provenance_validation
            ),
            semantic_entailment=grounded.semantic_entailment,
            diagnostics={
                "hygiene_dropped": hygiene_dropped,
                "model_name": draft.model_name,
                "prompt_version": draft.prompt_version,
                "finish_reason": draft.finish_reason,
                "stop_reason": draft.stop_reason,
                "generation_calls": draft.generation_calls,
                "generation_network_ms": draft.generation_ms,
                "input_tokens": draft.input_tokens,
                "output_tokens": draft.output_tokens,
                **grounded.diagnostics,
                **finalized.diagnostics,
            },
        )
