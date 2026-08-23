"""Fast v2 parity harness -- replays ORIGINAL Dimension-Aware v1 through Fast v2.

Deliberately lives OUTSIDE src/synthesis/fast_v2: the RQ1/RQ2 benchmark query
strings are read at runtime from the recovered ORIGINAL reference file
(scratch/original_dimension_v1_reference/), never copied into production
source. ``tests/test_fast_v2/test_dimension_and_selection.py::
test_no_benchmark_identifiers_are_hardcoded`` enforces this for the src tree;
this harness is exempt because it is not part of that tree.

Pipeline exercised, real fast_v2 components, stopped at GroundedEvidenceBank:

    explicit ORIGINAL DimensionQuery objects (D1..D5 / D1..D4)
      -> InMemoryCosineEvidenceRetriever   (reference-only, reproduces v1 retrieval)
      -> hygiene.classifier.filter_evidence_units   (literal port)
      -> CrossEncoderReranker              (production, unchanged)
      -> EvidenceSelectionPolicy           (production, unchanged: score>0, max 3)
      -> GroundedEvidenceBank.build        (first-seen merge order)

FastSynthesisV2Pipeline.run() is used end-to-end with FakeSynthesisGenerator
so the real pipeline wiring is exercised, but NO OpenScholar call happens --
FakeSynthesisGenerator loads nothing and calls nothing. Only
``result.evidence_bank`` is used; the generated text/citations are discarded.

Usage:
    python scripts/fast_v2_dimension_v1_parity_harness.py
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
ORIGINAL_RQ_JSON = {
    "RQ1": REPO_ROOT / "scratch" / "original_dimension_v1_reference" / "dimension_aware_v1" / "results" / "rq1_dimension_v1.json",
    "RQ2": REPO_ROOT / "scratch" / "original_dimension_v1_reference" / "dimension_aware_v1" / "results" / "rq2_dimension_v1.json",
}

PAPER_IDS = {
    "Xu2010 Study": uuid.UUID("52c06c26-1dd1-486a-8c4f-202779ed5c7f"),
    "Xu2018 Study": uuid.UUID("0373c7b5-3a9e-437d-a59a-a1baa9a708cc"),
}


def _load_original_lib():
    spec = importlib.util.spec_from_file_location("original_dimension_aware_lib", ORIGINAL_LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def run_rq(rq_label: str, dim_labels: dict, v1_queries: dict) -> dict:
    from src.database import session_scope
    from src.synthesis.fast_v2.dimensions.planner import DimensionQuery
    from src.synthesis.fast_v2.evidence.reference_retriever import InMemoryCosineEvidenceRetriever
    from src.synthesis.fast_v2.generator.fake import FakeSynthesisGenerator
    from src.synthesis.fast_v2.pipeline import FastSynthesisV2Pipeline
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker

    dim_ids = list(dim_labels.keys())
    explicit_queries = [
        DimensionQuery(dimension=dim_id, query_text=v1_queries[dim_id]) for dim_id in dim_ids
    ]

    class _ExplicitQueryPlanner:
        """Test/parity-only planner: returns the ORIGINAL v1 queries verbatim.

        Ignores the ``dimensions``/``research_question`` arguments the
        pipeline passes in -- this is NOT a general-purpose planner and is
        never wired into production; it exists only in this harness.
        """

        def plan(self, *, research_question, dimensions):
            return list(explicit_queries)

    retriever = InMemoryCosineEvidenceRetriever(
        session_scope,
        paper_ids=list(PAPER_IDS.values()),
    )
    reranker = CrossEncoderReranker()
    generator = FakeSynthesisGenerator()

    pipeline = FastSynthesisV2Pipeline(
        retriever=retriever,
        generator=generator,
        reranker=reranker,
        planner=_ExplicitQueryPlanner(),
        candidates_per_dimension=40,
    )

    result = await pipeline.run(
        question=f"{rq_label} (question text not used by the explicit planner)",
        dimensions=dim_ids,
    )

    assert generator.calls == 1, "FakeSynthesisGenerator must be called exactly once"
    return result.evidence_bank.to_dict()


def _paper_distribution(bank: dict) -> dict:
    dist: dict[str, int] = {}
    for unit in bank["evidence"]:
        dist[unit["title"]] = dist.get(unit["title"], 0) + 1
    return dist


def compare(rq_label: str, replay_bank: dict, original_artifact: dict) -> dict:
    original_evidence = original_artifact["merged_evidence"]

    def _key(unit_like):
        # Compare by (paper_id, page) -- evidence_id schemes differ between
        # ORIGINAL (EvidenceRecord.id / chunk-<PDFChunk.id>) and fast_v2
        # (ev-<uuid5 of source_chunk_id>) by design; the underlying chunk
        # identity (paper, page) is what must match.
        return (str(unit_like["paper_id"]), unit_like["page"])

    original_keys = [_key(u) for u in original_evidence]
    replay_keys = [_key(u) for u in replay_bank["evidence"]]

    original_set = set(original_keys)
    replay_set = set(replay_keys)

    rows = []
    for i, orig in enumerate(original_evidence):
        key = _key(orig)
        match_idx = replay_keys.index(key) if key in replay_keys else None
        replay_unit = replay_bank["evidence"][match_idx] if match_idx is not None else None
        rows.append({
            "index": i,
            "paper": orig["title"],
            "page": orig["page"],
            "original_score": orig["best_dimension_score"],
            "replay_score": replay_unit["best_dimension_score"] if replay_unit else None,
            "original_dimensions": orig["selected_for_dimensions"],
            "replay_dimensions": replay_unit["selected_for_dimensions"] if replay_unit else None,
            "replay_index": match_idx,
            "match": "MATCH" if match_idx is not None else "MISMATCH-missing-in-replay",
        })

    extra_in_replay = [
        {"paper": replay_bank["evidence"][i]["title"], "page": replay_bank["evidence"][i]["page"]}
        for i, key in enumerate(replay_keys)
        if key not in original_set
    ]

    return {
        "rq": rq_label,
        "original_bank_size": len(original_evidence),
        "replay_bank_size": len(replay_bank["evidence"]),
        "bank_size_match": len(original_evidence) == len(replay_bank["evidence"]),
        "original_paper_distribution": _paper_distribution({"evidence": original_evidence}),
        "replay_paper_distribution": _paper_distribution(replay_bank),
        "paper_distribution_match": _paper_distribution({"evidence": original_evidence})
        == _paper_distribution(replay_bank),
        "chunk_identity_match_rate": round(len(original_set & replay_set) / len(original_set), 4)
        if original_set
        else None,
        "order_match": original_keys == replay_keys,
        "rows": rows,
        "extra_in_replay_not_in_original": extra_in_replay,
        "negative_score_padded_count": sum(
            1 for u in replay_bank["evidence"] if (u.get("best_dimension_score") or 0) <= 0
        ),
    }


async def main():
    lib = _load_original_lib()

    results = {}
    for rq_label, dim_labels, v1_queries in [
        ("RQ1", lib.RQ1_DIM_LABELS if hasattr(lib, "RQ1_DIM_LABELS") else None, lib.RQ1_V1_QUERIES),
        ("RQ2", lib.RQ2_DIM_LABELS if hasattr(lib, "RQ2_DIM_LABELS") else None, lib.RQ2_V1_QUERIES),
    ]:
        # dimension_aware_lib.py itself doesn't carry RQ*_DIM_LABELS (that lived
        # in run_dimension_aware_v1.py); reconstruct the D1..Dn id list from the
        # query dict keys, which is all merge/selection actually keys on.
        dim_ids = {"RQ1": ["D1", "D2", "D3", "D4", "D5"], "RQ2": ["D1", "D2", "D3", "D4"]}[rq_label]
        labels = {d: d for d in dim_ids}

        print(f"\n=== Replaying {rq_label} through Fast v2 ===")
        replay_bank = await run_rq(rq_label, labels, v1_queries)

        original_artifact = json.loads(ORIGINAL_RQ_JSON[rq_label].read_text(encoding="utf-8"))
        comparison = compare(rq_label, replay_bank, original_artifact)
        results[rq_label] = {"replay_bank": replay_bank, "comparison": comparison}

        print(f"original_bank_size={comparison['original_bank_size']} "
              f"replay_bank_size={comparison['replay_bank_size']} "
              f"bank_size_match={comparison['bank_size_match']}")
        print(f"original_paper_distribution={comparison['original_paper_distribution']}")
        print(f"replay_paper_distribution={comparison['replay_paper_distribution']}")
        print(f"paper_distribution_match={comparison['paper_distribution_match']}")
        print(f"chunk_identity_match_rate={comparison['chunk_identity_match_rate']}")
        print(f"order_match={comparison['order_match']}")
        print(f"negative_score_padded_count={comparison['negative_score_padded_count']}")
        print("rows:")
        for row in comparison["rows"]:
            print(f"  #{row['index']} {row['paper']} p{row['page']} "
                  f"orig_score={row['original_score']} replay_score={row['replay_score']} "
                  f"orig_dims={row['original_dimensions']} replay_dims={row['replay_dimensions']} "
                  f"[{row['match']}]")
        if comparison["extra_in_replay_not_in_original"]:
            print(f"EXTRA in replay not in original: {comparison['extra_in_replay_not_in_original']}")

    out_dir = REPO_ROOT / "scratch" / "fast_v2_parity_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "parity_report.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
