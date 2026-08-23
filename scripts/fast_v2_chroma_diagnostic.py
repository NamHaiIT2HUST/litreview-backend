"""Fast v2 parity harness, step 8 -- Chroma diagnostic.

Runs the SAME explicit ORIGINAL DimensionQuery objects through
VectorStoreEvidenceRetriever (production Chroma path) and compares the
resulting candidate sets against InMemoryCosineEvidenceRetriever's (already
verified 100% parity with ORIGINAL v1). Does not modify Chroma or the index.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
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


async def main():
    from src.database import session_scope
    from src.services.vector_store import VectorStoreService
    from src.synthesis.fast_v2.evidence.reference_retriever import InMemoryCosineEvidenceRetriever
    from src.synthesis.fast_v2.evidence.retrieval import VectorStoreEvidenceRetriever

    lib = _load_original_lib()

    print("=== Chroma collection/embedding sanity ===")
    try:
        vs = VectorStoreService()
        print(f"embedding backend class: {type(vs.embeddings).__name__}")
    except Exception as e:
        print(f"VectorStoreService() construction FAILED: {type(e).__name__}: {e}")
        vs = None

    reference = InMemoryCosineEvidenceRetriever(session_scope, paper_ids=PAPER_IDS)

    results = {}
    for rq_label, dim_ids, v1_queries in [
        ("RQ1", ["D1", "D2", "D3", "D4", "D5"], lib.RQ1_V1_QUERIES),
        ("RQ2", ["D1", "D2", "D3", "D4"], lib.RQ2_V1_QUERIES),
    ]:
        print(f"\n=== {rq_label} ===")
        rq_result = {}
        for dim_id in dim_ids:
            query = v1_queries[dim_id]
            ref_candidates = await reference.retrieve(query, limit=40)
            ref_ids = {str(u.source_chunk_id) for u in ref_candidates}

            chroma_ids: set[str] = set()
            chroma_error = None
            if vs is not None:
                try:
                    chroma_retriever = VectorStoreEvidenceRetriever(vs, paper_ids=PAPER_IDS)
                    chroma_candidates = await chroma_retriever.retrieve(query, limit=40)
                    chroma_ids = {str(u.source_chunk_id) for u in chroma_candidates}
                except Exception as e:
                    chroma_error = f"{type(e).__name__}: {str(e)[:300]}"

            overlap = len(ref_ids & chroma_ids)
            rq_result[dim_id] = {
                "query": query,
                "reference_candidate_count": len(ref_ids),
                "chroma_candidate_count": len(chroma_ids),
                "overlap_at_40": overlap,
                "overlap_rate": round(overlap / len(ref_ids), 4) if ref_ids else None,
                "chroma_error": chroma_error,
            }
            print(f"  {dim_id}: reference={len(ref_ids)} chroma={len(chroma_ids)} "
                  f"overlap={overlap} error={chroma_error}")

        results[rq_label] = rq_result

    out_dir = REPO_ROOT / "scratch" / "fast_v2_parity_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "chroma_diagnostic.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
