"""Fast v2 production repair -- step 10/11: Chroma-vs-reference parity + phase latency.

Uses the newly indexed fast_v2_evidence_minilm_v1 collection (Xu2010/Xu2018
only). Compares FastV2ChromaEvidenceRetriever against
InMemoryCosineEvidenceRetriever (the parity oracle) per dimension, and runs
the real GroundedEvidenceBank-only pipeline (FakeSynthesisGenerator, no
OpenScholar) with each retriever to compare the final banks.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

ORIGINAL_LIB_PATH = (
    REPO_ROOT / "scratch" / "original_dimension_v1_reference" / "dimension_aware_v1" / "dimension_aware_lib.py"
)
PAPER_IDS = [
    uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f"),  # Xu2010
    uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc"),  # Xu2018
]


def _load_original_lib():
    spec = importlib.util.spec_from_file_location("original_dimension_aware_lib", ORIGINAL_LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def run_bank(rq_label: str, dim_ids: list[str], v1_queries: dict, retriever) -> dict:
    from src.synthesis.fast_v2.dimensions.planner import DimensionQuery
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    explicit_queries = [DimensionQuery(dimension=d, query_text=v1_queries[d]) for d in dim_ids]

    class _ExplicitQueryPlanner:
        def plan(self, *, research_question, dimensions):
            return list(explicit_queries)

    pipeline = FastSynthesisV2Pipeline(
        retriever=retriever,
        generator=FakeSynthesisGenerator(),
        reranker=CrossEncoderReranker(),
        planner=_ExplicitQueryPlanner(),
        candidates_per_dimension=40,
    )
    result = await pipeline.run(question=f"{rq_label} (unused by explicit planner)", dimensions=dim_ids)
    return result.evidence_bank.to_dict(), result.timings


async def measure_retrieval_phase_latency(index, query: str, paper_ids) -> dict:
    """Split what the pipeline's single 'retrieval_ms' phase bundles together:
    query-embedding time vs Chroma search time."""
    model = await asyncio.to_thread(index._load_model)  # ensure warm, excluded from measured window
    t0 = time.perf_counter()
    query_embedding = await asyncio.to_thread(model.encode, [query], convert_to_numpy=True)
    embed_ms = (time.perf_counter() - t0) * 1000

    collection = await asyncio.to_thread(index._get_collection)
    index._validate_dimension(collection)
    where = {"paper_id": str(paper_ids[0])} if len(paper_ids) == 1 else {"paper_id": {"$in": [str(p) for p in paper_ids]}}
    t0 = time.perf_counter()
    await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding[0].tolist()],
        n_results=40,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    search_ms = (time.perf_counter() - t0) * 1000

    return {"query_embedding_ms": round(embed_ms, 2), "chroma_search_ms": round(search_ms, 2)}


async def main():
    from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
    from src.synthesis.fast_v2.evidence.reference_retriever import InMemoryCosineEvidenceRetriever
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
    from src.database import session_scope

    lib = _load_original_lib()
    index = FastV2SemanticIndex()
    chroma_retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=PAPER_IDS)
    reference_retriever = InMemoryCosineEvidenceRetriever(session_scope, paper_ids=PAPER_IDS)

    results = {}
    for rq_label, dim_ids, v1_queries in [
        ("RQ1", ["D1", "D2", "D3", "D4", "D5"], lib.RQ1_V1_QUERIES),
        ("RQ2", ["D1", "D2", "D3", "D4"], lib.RQ2_V1_QUERIES),
    ]:
        print(f"\n=== {rq_label}: candidate-set overlap@40 per dimension ===")
        dim_overlaps = {}
        for dim_id in dim_ids:
            query = v1_queries[dim_id]
            ref_candidates = await reference_retriever.retrieve(query, limit=40)
            chroma_candidates = await chroma_retriever.retrieve(query, limit=40)
            ref_ids = {str(u.source_chunk_id) for u in ref_candidates}
            chroma_ids = {str(u.source_chunk_id) for u in chroma_candidates}
            ref_top10 = {str(u.source_chunk_id) for u in ref_candidates[:10]}
            chroma_top10 = {str(u.source_chunk_id) for u in chroma_candidates[:10]}
            overlap40 = len(ref_ids & chroma_ids)
            overlap10 = len(ref_top10 & chroma_top10)
            dim_overlaps[dim_id] = {
                "overlap_at_40": overlap40, "overlap_at_40_rate": round(overlap40 / 40, 3),
                "top10_overlap": overlap10, "top10_overlap_rate": round(overlap10 / 10, 3),
            }
            print(f"  {dim_id}: overlap@40={overlap40}/40 top10_overlap={overlap10}/10")

        print(f"\n=== {rq_label}: final GroundedEvidenceBank comparison ===")
        ref_bank, ref_timings = await run_bank(rq_label, dim_ids, v1_queries, reference_retriever)
        chroma_bank, chroma_timings = await run_bank(rq_label, dim_ids, v1_queries, chroma_retriever)

        ref_ids = {u["evidence_id"] for u in ref_bank["evidence"]}
        chroma_ids_bank = {u["evidence_id"] for u in chroma_bank["evidence"]}
        # evidence_id is deterministic per source_chunk_id regardless of
        # retriever, so direct evidence_id overlap is meaningful here (unlike
        # the ORIGINAL-vs-fast_v2 comparison, both sides are fast_v2 now).
        bank_overlap = len(ref_ids & chroma_ids_bank)

        def _dist(bank):
            d = {}
            for u in bank["evidence"]:
                d[u["title"]] = d.get(u["title"], 0) + 1
            return d

        print(f"reference bank size={len(ref_bank['evidence'])} dist={_dist(ref_bank)}")
        print(f"chroma    bank size={len(chroma_bank['evidence'])} dist={_dist(chroma_bank)}")
        print(f"bank evidence_id overlap={bank_overlap}/{len(ref_ids)}")

        # Split-out latency for one representative (first) dimension query.
        latency_breakdown = await measure_retrieval_phase_latency(index, v1_queries[dim_ids[0]], PAPER_IDS)
        print(f"phase latency (dimension {dim_ids[0]}): {latency_breakdown}")
        print(f"pipeline timings (chroma retriever run): {chroma_timings}")

        results[rq_label] = {
            "candidate_overlap_per_dimension": dim_overlaps,
            "reference_bank": ref_bank,
            "chroma_bank": chroma_bank,
            "bank_evidence_id_overlap": bank_overlap,
            "reference_bank_size": len(ref_bank["evidence"]),
            "chroma_bank_size": len(chroma_bank["evidence"]),
            "reference_paper_distribution": _dist(ref_bank),
            "chroma_paper_distribution": _dist(chroma_bank),
            "phase_latency_sample": latency_breakdown,
            "pipeline_timings_reference": ref_timings,
            "pipeline_timings_chroma": chroma_timings,
        }

    out_dir = REPO_ROOT / "scratch" / "fast_v2_parity_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chroma_vs_reference_parity.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
