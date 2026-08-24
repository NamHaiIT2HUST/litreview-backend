"""OFFLINE facet-planner coverage check against the real persistent Fast v2 index.

Runs the new question-facet planner (src/synthesis/fast_v2/dimensions/facets.py)
plus the existing, UNMODIFIED retrieval/hygiene/reranker/selection stack
against the real Xu2010 (28 chunks) / Xu2018 (59 chunks) persistent Chroma
collection. NO generator call -- this only proves the Evidence Bank the new
dimension planning would hand to a generator, before spending another paid
API call.

Usage:
    python scripts/fast_v2_facet_coverage_check.py
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

FIXTURE_PATH = REPO_ROOT / "tests" / "test_fast_v2" / "fixtures" / "rq2_evidence_bank_v1.json"


async def main() -> None:
    from src.synthesis.fast_v2.dimensions.facets import (
        QuestionFacetDimensionQueryPlanner,
        detect_facets,
    )
    from src.synthesis.fast_v2.evidence.chroma_retriever import FastV2ChromaEvidenceRetriever
    from src.synthesis.fast_v2.evidence.semantic_index import FastV2SemanticIndex
    from src.synthesis.fast_v2.hygiene.classifier import filter_evidence_units
    from src.synthesis.fast_v2.selection.cross_encoder import CrossEncoderReranker
    from src.synthesis.fast_v2.selection.policy import EvidenceSelectionPolicy
    from src.synthesis.fast_v2.selection.rerank import apply_reranker
    from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank

    facets = detect_facets(QUESTION)
    print(f"Detected facets: {facets}")
    assert facets == ["formulation", "algorithms", "assumptions", "convergence"], facets

    paper_ids = [XU_2010_PAPER_ID, XU_2018_PAPER_ID]
    paper_labels = {
        XU_2010_PAPER_ID: "Xu2010",
        XU_2018_PAPER_ID: "Xu2018",
    }
    planner = QuestionFacetDimensionQueryPlanner(paper_ids=paper_ids)
    queries = planner.plan(research_question=QUESTION, dimensions=facets)
    for q in queries:
        print(
            f"  [{q.dimension} x {paper_labels[q.paper_id]}] "
            f"paper_id={q.paper_id} query_text={q.query_text!r}"
        )

    index = FastV2SemanticIndex()
    retriever = FastV2ChromaEvidenceRetriever(index, paper_ids=paper_ids)
    reranker = CrossEncoderReranker()
    selection_policy = EvidenceSelectionPolicy()  # frozen defaults: max 3/dim, threshold 0.0

    report: dict = {
        "question": QUESTION,
        "facets": facets,
        "paper_ids": {label: str(paper_id) for paper_id, label in paper_labels.items()},
        "per_cell": {facet: {} for facet in facets},
    }
    evidence_by_dimension: dict[str, list] = {}
    hygiene_dropped_total = 0
    selected_occurrences = 0

    for query in queries:
        t0 = time.perf_counter()
        candidates = await retriever.retrieve(
            query.query_text, limit=40, paper_id=query.paper_id
        )
        retrieval_ms = (time.perf_counter() - t0) * 1000.0

        kept, dropped = filter_evidence_units(candidates)
        hygiene_dropped_total += len(dropped)

        t0 = time.perf_counter()
        reranked = apply_reranker(reranker, query=query.query_text, units=kept)
        rerank_ms = (time.perf_counter() - t0) * 1000.0

        selected = selection_policy.select(reranked, dimension=query.dimension)
        evidence_by_dimension.setdefault(query.dimension, []).extend(selected)
        selected_occurrences += len(selected)

        label = paper_labels[query.paper_id]
        report["per_cell"][query.dimension][label] = {
            "paper_id": str(query.paper_id),
            "query_text": query.query_text,
            "candidates_retrieved": len(candidates),
            "candidates_after_hygiene": len(kept),
            "hygiene_dropped": len(dropped),
            "hygiene_dropped_evidence_ids": [unit.evidence_id for unit in dropped],
            "retrieval_ms": round(retrieval_ms, 2),
            "rerank_ms": round(rerank_ms, 2),
            "reranked": [
                {
                    "evidence_id": unit.evidence_id,
                    "source_chunk_id": str(unit.source_chunk_id),
                    "page": unit.page,
                    "score": round(unit.rerank_score, 6),
                }
                for unit in reranked
            ],
            "best_reranker_score": (
                None if not reranked else round(reranked[0].rerank_score, 6)
            ),
            "selected_count": len(selected),
            "selected": [
                {
                    "evidence_id": u.evidence_id,
                    "source_chunk_id": str(u.source_chunk_id),
                    "paper_title": u.title,
                    "page": u.page,
                    "rerank_score": u.rerank_score,
                }
                for u in selected
            ],
        }

    bank = GroundedEvidenceBank.build(
        question=QUESTION, dimensions=facets, evidence_by_dimension=evidence_by_dimension
    )

    paper_distribution = bank.paper_distribution
    xu2010_count = paper_distribution.get("Xu 2010 Study", 0)
    xu2018_count = paper_distribution.get("Xu 2018 Study", 0)

    # The frozen fixture (tests/test_fast_v2/fixtures/rq2_evidence_bank_v1.json)
    # does NOT carry source_chunk_id -- it was deliberately dropped when the
    # fixture was built from the recovered ORIGINAL v1 result (see
    # scripts/fast_v2_generator_benchmark.py::load_fixture_bank, "fixture
    # doesn't carry the raw chunk id; not needed for generation"). Its own
    # "evidence_id" field is the ORIGINAL experiment's identifier scheme, not
    # this codebase's EvidenceUnit.evidence_id (which is a deterministic
    # ev-<uuid5> derived from source_chunk_id) -- the two are not directly
    # comparable strings. The only identity signal both sides actually carry
    # is (paper title, page, exact character span), which pins the same
    # source text regardless of id scheme -- used here instead.
    original = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    original_spans = {
        (row["title"], row["page"], row["page_char_start"], row["page_char_end"])
        for row in original["evidence"]
    }
    new_spans = {
        (u.title, u.page, u.page_char_start, u.page_char_end) for u in bank.evidence
    }
    overlap = original_spans & new_spans

    report["merged_bank"] = {
        "total_evidence": len(bank.evidence),
        "selected_occurrences_before_merge": selected_occurrences,
        "duplicate_count": selected_occurrences - len(bank.evidence),
        "xu2010_count": xu2010_count,
        "xu2018_count": xu2018_count,
        "paper_distribution": paper_distribution,
        "pages_represented": bank.pages_represented,
        "dimensions_requested": bank.coverage["dimensions_requested"],
        "dimensions_with_evidence": bank.coverage["dimensions_with_evidence"],
        "dimensions_without_evidence": bank.coverage["dimensions_without_evidence"],
        "is_thin": bank.coverage["is_thin"],
        "hygiene_dropped_total": hygiene_dropped_total,
        "page_diversity": sum(len(pages) for pages in bank.pages_represented.values()),
    }
    empty_cells = [
        f"{facet} x {label}"
        for facet in facets
        for label in paper_labels.values()
        if report["per_cell"][facet][label]["selected_count"] == 0
    ]
    report["comparative_coverage"] = {
        "cells_requested": len(facets) * len(paper_ids),
        "cells_with_positive_evidence": len(facets) * len(paper_ids) - len(empty_cells),
        "empty_cells": empty_cells,
        "previous_unscoped_cells_with_evidence": 4,
    }
    report["overlap_with_original_v1_bank"] = {
        "method": "(paper_title, page, page_char_start, page_char_end) span match "
                  "-- fixture carries no source_chunk_id, see comment above",
        "original_span_count": len(original_spans),
        "new_bank_span_count": len(new_spans),
        "overlap_count": len(overlap),
        "overlap_spans": sorted(str(s) for s in overlap),
    }

    print("\n=== MERGED BANK ===")
    print(json.dumps(report["merged_bank"], indent=2, ensure_ascii=False))
    print("\n=== OVERLAP WITH ORIGINAL v1 BANK ===")
    print(json.dumps(report["overlap_with_original_v1_bank"], indent=2, ensure_ascii=False))
    print("\n=== FACET x PAPER MATRIX ===")
    print(json.dumps(report["per_cell"], indent=2, ensure_ascii=False))
    print("\n=== COMPARATIVE COVERAGE ===")
    print(json.dumps(report["comparative_coverage"], indent=2, ensure_ascii=False))

    out_path = REPO_ROOT / "scratch" / "fast_v2_parity_results" / "facet_planner_offline_coverage.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    acceptance = {
        "A_both_papers_present": xu2010_count > 0 and xu2018_count > 0,
        "B_all_facets_represented": not bank.coverage["dimensions_without_evidence"],
        "C_comparative_coverage_improved": (
            report["comparative_coverage"]["cells_with_positive_evidence"] > 4
        ),
        "D_no_negative_padding": all(
            unit.best_dimension_score is not None and unit.best_dimension_score > 0
            for unit in bank.evidence
        ),
    }
    acceptance["overall_pass"] = all(acceptance.values())
    report["acceptance"] = acceptance
    report["structural_constraints"] = {
        "paper_quota_or_balancing_added": False,
        "generator_constructed_or_called": False,
        "selection_order_verified_by_repeat_run": "verified by caller comparison",
    }
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print("\n=== ACCEPTANCE ===")
    print(json.dumps(acceptance, indent=2, ensure_ascii=False))
    if not acceptance["overall_pass"]:
        raise SystemExit("Offline comparison-aware acceptance checks failed")


if __name__ == "__main__":
    asyncio.run(main())
