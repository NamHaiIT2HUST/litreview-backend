"""OFFLINE warm-evidence-pipeline timing check.

Proves warmup (src/synthesis/fast_v2/runtime.py::warm_fast_v2) actually moves
cold-model-load cost out of the interactive request path, using the real
process-wide singletons the backend would use (get_fast_v2_index /
get_fast_v2_reranker), the real persistent Chroma index, and NO generator
call.

Usage:
    python scripts/fast_v2_warm_evidence_pipeline_check.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

XU_2010_PAPER_ID = uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f")
XU_2018_PAPER_ID = uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc")

QUESTION = (
    "How do Xu2010 and Xu2018 differ in their formulations of the split "
    "feasibility problem, algorithmic strategies, assumptions, and "
    "convergence guarantees?"
)


async def main() -> None:
    from src.synthesis.fast_v2.dimensions.facets import (
        QuestionFacetDimensionQueryPlanner,
        detect_facets,
    )
    from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
    from src.synthesis.fast_v2.hygiene.classifier import filter_evidence_units
    from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
    from src.synthesis.fast_v2.selection.rerank import apply_reranker
    from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
    from src.synthesis.fast_v2.observability import PhaseTimings
    from src.synthesis.fast_v2 import runtime as runtime_module

    # -- warmup (this is the cost section 5 must remove from a real request) --
    warmup_timings = await runtime_module.warm_fast_v2()
    print(f"warmup_timings: {json.dumps(warmup_timings, indent=2)}")

    index = runtime_module.get_fast_v2_index()
    reranker = runtime_module.get_fast_v2_reranker()
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=[XU_2010_PAPER_ID, XU_2018_PAPER_ID])
    selection_policy = EvidenceSelectionPolicy()
    planner = QuestionFacetDimensionQueryPlanner()

    facets = detect_facets(QUESTION)
    queries = planner.plan(research_question=QUESTION, dimensions=facets)

    timings = PhaseTimings()
    evidence_by_dimension: dict[str, list] = {}

    with timings.total():
        for query in queries:
            with timings.phase("retrieval_ms"):
                candidates = await retriever.retrieve(query.query_text, limit=40)
            with timings.phase("hygiene_ms"):
                kept, _dropped = filter_evidence_units(candidates)
            with timings.phase("rerank_ms"):
                reranked = apply_reranker(reranker, query=query.query_text, units=kept)
            with timings.phase("evidence_bank_ms"):
                evidence_by_dimension[query.dimension] = selection_policy.select(
                    reranked, dimension=query.dimension
                )

        with timings.phase("evidence_bank_ms"):
            bank = GroundedEvidenceBank.build(
                question=QUESTION, dimensions=facets, evidence_by_dimension=evidence_by_dimension
            )

    evidence_pipeline_ms = (
        timings.timings["retrieval_ms"]
        + timings.timings["hygiene_ms"]
        + timings.timings["rerank_ms"]
        + timings.timings["evidence_bank_ms"]
    )

    result = {
        "warmup_ms": warmup_timings["warmup_ms"],
        "warmup_breakdown": warmup_timings,
        "warm_evidence_timings_ms": {
            "retrieval_ms": round(timings.timings["retrieval_ms"], 3),
            "hygiene_ms": round(timings.timings["hygiene_ms"], 3),
            "rerank_ms": round(timings.timings["rerank_ms"], 3),
            "evidence_bank_ms": round(timings.timings["evidence_bank_ms"], 3),
            "evidence_pipeline_ms": round(evidence_pipeline_ms, 3),
        },
        "previously_observed_warm_reference_ms": 11600,
        "evidence_count": len(bank.evidence),
        "paper_distribution": bank.paper_distribution,
    }
    print("\n=== WARM EVIDENCE PIPELINE RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    out_path = REPO_ROOT / "scratch" / "fast_v2_parity_results" / "warm_evidence_pipeline_timing.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
