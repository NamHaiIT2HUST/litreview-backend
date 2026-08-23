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
import os
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Enforce cache-only resolution for the already-downloaded local models.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

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
    paper_ids = [XU_2010_PAPER_ID, XU_2018_PAPER_ID]
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=paper_ids)
    selection_policy = EvidenceSelectionPolicy()

    facets = detect_facets(QUESTION)
    unscoped_queries = QuestionFacetDimensionQueryPlanner().plan(
        research_question=QUESTION, dimensions=facets
    )
    scoped_queries = QuestionFacetDimensionQueryPlanner(paper_ids=paper_ids).plan(
        research_question=QUESTION, dimensions=facets
    )

    async def measure(queries):
        timings = PhaseTimings()
        evidence_by_dimension: dict[str, list] = {}

        with timings.total():
            for query in queries:
                with timings.phase("retrieval_ms"):
                    if query.paper_id is None:
                        candidates = await retriever.retrieve(query.query_text, limit=40)
                    else:
                        candidates = await retriever.retrieve(
                            query.query_text, limit=40, paper_id=query.paper_id
                        )
                with timings.phase("hygiene_ms"):
                    kept, _dropped = filter_evidence_units(candidates)
                with timings.phase("rerank_ms"):
                    reranked = apply_reranker(
                        reranker, query=query.query_text, units=kept
                    )
                with timings.phase("evidence_bank_ms"):
                    evidence_by_dimension.setdefault(query.dimension, []).extend(
                        selection_policy.select(reranked, dimension=query.dimension)
                    )

            with timings.phase("evidence_bank_ms"):
                bank = GroundedEvidenceBank.build(
                    question=QUESTION,
                    dimensions=list(dict.fromkeys(query.dimension for query in queries)),
                    evidence_by_dimension=evidence_by_dimension,
                )

        evidence_pipeline_ms = sum(
            timings.timings[name]
            for name in ("retrieval_ms", "hygiene_ms", "rerank_ms", "evidence_bank_ms")
        )
        return timings, bank, evidence_pipeline_ms

    control_timings, control_bank, control_ms = await measure(unscoped_queries)
    scoped_timings, scoped_bank, scoped_ms = await measure(scoped_queries)

    def timing_result(timings, pipeline_ms):
        return {
            "retrieval_ms": round(timings.timings["retrieval_ms"], 3),
            "hygiene_ms": round(timings.timings["hygiene_ms"], 3),
            "rerank_ms": round(timings.timings["rerank_ms"], 3),
            "evidence_bank_ms": round(timings.timings["evidence_bank_ms"], 3),
            "evidence_pipeline_ms": round(pipeline_ms, 3),
        }

    result = {
        "warmup_ms": warmup_timings["warmup_ms"],
        "warmup_breakdown": warmup_timings,
        "same_process_warm_control": {
            "query_count": len(unscoped_queries),
            "timings_ms": timing_result(control_timings, control_ms),
            "evidence_count": len(control_bank.evidence),
            "paper_distribution": control_bank.paper_distribution,
        },
        "same_process_warm_scoped": {
            "query_count": len(scoped_queries),
            "timings_ms": timing_result(scoped_timings, scoped_ms),
            "evidence_count": len(scoped_bank.evidence),
            "paper_distribution": scoped_bank.paper_distribution,
        },
        "measured_extra_cost_ms": round(scoped_ms - control_ms, 3),
        "historical_unscoped_reference_ms": 6832,
    }
    print("\n=== WARM EVIDENCE PIPELINE RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    out_path = REPO_ROOT / "scratch" / "fast_v2_parity_results" / "warm_evidence_pipeline_timing.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
