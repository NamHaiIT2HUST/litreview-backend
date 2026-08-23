"""Warm-latency measurement: run the Chroma-backed Fast v2 bank pipeline twice
with the SAME reranker/index instances so the second run's timings exclude
one-time model load (sentence-transformers, CrossEncoder)."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

ORIGINAL_LIB_PATH = (
    REPO_ROOT / "scratch" / "original_dimension_v1_reference" / "dimension_aware_v1" / "dimension_aware_lib.py"
)
PAPER_IDS = [
    uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f"),
    uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc"),
]


def _load_original_lib():
    spec = importlib.util.spec_from_file_location("original_dimension_aware_lib", ORIGINAL_LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def main():
    from src.synthesis.fast_v2.dimensions.planner import DimensionQuery
    from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    lib = _load_original_lib()
    dim_ids = ["D1", "D2", "D3", "D4", "D5"]
    v1_queries = lib.RQ1_V1_QUERIES
    explicit_queries = [DimensionQuery(dimension=d, query_text=v1_queries[d]) for d in dim_ids]

    class _ExplicitQueryPlanner:
        def plan(self, *, research_question, dimensions):
            return list(explicit_queries)

    index = FastV2SemanticIndex()
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=PAPER_IDS)
    reranker = CrossEncoderReranker()  # shared across both runs -- loads once

    pipeline = FastSynthesisV2Pipeline(
        retriever=retriever,
        generator=FakeSynthesisGenerator(),
        reranker=reranker,
        planner=_ExplicitQueryPlanner(),
        candidates_per_dimension=40,
    )

    print("=== RUN 1 (cold: model load included) ===")
    result1 = await pipeline.run(question="RQ1", dimensions=dim_ids)
    print(result1.timings)

    print("\n=== RUN 2 (warm: models already loaded) ===")
    result2 = await pipeline.run(question="RQ1", dimensions=dim_ids)
    print(result2.timings)

    print(f"\nreranker.is_loaded (after both runs): {reranker.is_loaded}")
    print(f"index.is_model_loaded (after both runs): {index.is_model_loaded if hasattr(index, 'is_model_loaded') else 'n/a'}")


if __name__ == "__main__":
    asyncio.run(main())
