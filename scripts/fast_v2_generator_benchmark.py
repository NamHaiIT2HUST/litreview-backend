"""Fast v2 generator-only benchmark harness.

Loads a FROZEN, already-built Evidence Bank fixture (does NOT re-run
retrieval/hygiene/rerank) and times exactly one generation call through a
chosen generator. Use this to compare generator speed/cost without the
Evidence-First pipeline latency mixed in.

Fixture: tests/test_fast_v2/fixtures/rq2_evidence_bank_v1.json -- the
ORIGINAL validated Dimension-Aware v1 RQ2 Evidence Bank (7 EvidenceUnits),
recovered read-only reference, frozen for this benchmark's use as input.

Usage:

    # Hosted OpenAI-compatible API (no call happens without these three set):
    export FAST_V2_HOSTED_API_BASE_URL="https://api.openai.com/v1"
    export FAST_V2_HOSTED_API_KEY="sk-..."
    export FAST_V2_HOSTED_API_MODEL="gpt-4o-mini"
    python scripts/fast_v2_generator_benchmark.py --provider hosted_api

    # Remote warm OpenScholar GPU service:
    python scripts/fast_v2_generator_benchmark.py --provider remote_openscholar \\
        --base-url http://127.0.0.1:8500

No pricing is invented here -- estimated_cost is populated ONLY if the caller
supplies --price-per-1k-input/--price-per-1k-output explicitly.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

FIXTURE_PATH = REPO_ROOT / "tests" / "test_fast_v2" / "fixtures" / "rq2_evidence_bank_v1.json"


def load_fixture_bank():
    """Build a GroundedEvidenceBank from the frozen RQ2 v1 fixture -- no
    retrieval, no re-embedding, no re-ranking. Pure deserialization."""
    import uuid

    from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
    from src.synthesis.fast_v2.evidence.models import EvidenceUnit

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    evidence_by_dimension: dict[str, list] = {}
    for row in fixture["evidence"]:
        unit = EvidenceUnit.from_chunk(
            paper_id=uuid.UUID(row["paper_id"]),
            title=row["title"],
            page=row["page"],
            text=row["text"],
            source_chunk_id=None,  # fixture doesn't carry the raw chunk id; not needed for generation
            page_text_id=None,
            page_char_start=row.get("page_char_start"),
            page_char_end=row.get("page_char_end"),
        )
        for dimension, score in row["dimension_scores"].items():
            dim_unit = unit.with_dimension(dimension, score)
            evidence_by_dimension.setdefault(dimension, []).append(dim_unit)

    bank = GroundedEvidenceBank.build(
        question=fixture["question"],
        dimensions=list(evidence_by_dimension.keys()),
        evidence_by_dimension=evidence_by_dimension,
    )
    assert len(bank.evidence) == len(fixture["evidence"]), (
        f"fixture deserialization changed evidence count: "
        f"{len(fixture['evidence'])} in fixture, {len(bank.evidence)} in bank"
    )
    return fixture["question"], bank


def build_generator(args):
    if args.provider == "hosted_api":
        from src.synthesis.fast_v2.generator.hosted_api import HostedApiGenerator

        return HostedApiGenerator(
            base_url=args.hosted_api_base_url or _env("FAST_V2_HOSTED_API_BASE_URL"),
            api_key=args.hosted_api_key or _env("FAST_V2_HOSTED_API_KEY"),
            model=args.hosted_api_model or _env("FAST_V2_HOSTED_API_MODEL"),
        )
    if args.provider == "remote_openscholar":
        from src.synthesis.fast_v2.generator.remote_openscholar import RemoteOpenScholarGenerator

        if not args.base_url:
            raise SystemExit("--base-url is required for --provider remote_openscholar")
        return RemoteOpenScholarGenerator(base_url=args.base_url)

    raise SystemExit(f"unknown --provider {args.provider!r}")


def _env(name: str) -> str:
    import os

    return os.environ.get(name, "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["hosted_api", "remote_openscholar"], required=True)
    parser.add_argument("--base-url", default=None, help="for --provider remote_openscholar")
    parser.add_argument("--hosted-api-base-url", default=None)
    parser.add_argument("--hosted-api-key", default=None)
    parser.add_argument("--hosted-api-model", default=None)
    parser.add_argument("--price-per-1k-input", type=float, default=None)
    parser.add_argument("--price-per-1k-output", type=float, default=None)
    parser.add_argument("--out", default=None, help="output JSON path")
    args = parser.parse_args()

    question, bank = load_fixture_bank()
    print(f"Loaded frozen fixture bank: {len(bank.evidence)} EvidenceUnits, "
          f"paper_distribution={bank.paper_distribution}")

    generator = build_generator(args)

    started = time.perf_counter()
    draft = generator.generate(question=question, evidence_bank=bank)
    latency_seconds = time.perf_counter() - started

    estimated_cost = None
    if (
        args.price_per_1k_input is not None
        and args.price_per_1k_output is not None
        and draft.input_tokens is not None
        and draft.output_tokens is not None
    ):
        estimated_cost = round(
            (draft.input_tokens / 1000) * args.price_per_1k_input
            + (draft.output_tokens / 1000) * args.price_per_1k_output,
            6,
        )

    result = {
        "provider": args.provider,
        "model": draft.model_name,
        "latency_seconds": round(latency_seconds, 3),
        "input_tokens": draft.input_tokens,
        "output_tokens": draft.output_tokens,
        "estimated_cost": estimated_cost,
        "finish_reason": draft.finish_reason,
        "generation_calls": draft.generation_calls,
        "raw_answer": draft.text,
    }

    print("\n=== BENCHMARK RESULT ===")
    for key, value in result.items():
        if key == "raw_answer":
            print(f"  {key}: {value[:200]!r}...")
        else:
            print(f"  {key}: {value}")

    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "scratch" / "fast_v2_parity_results" / f"generator_benchmark_{args.provider}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
