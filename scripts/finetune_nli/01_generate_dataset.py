"""
MODULE 1 — Evidence Quantification Engine
Bước 1: Sinh dataset huấn luyện NLI 3 nhãn (supported / contradicted / insufficient)
từ chính kho PDF đã nạp vào vector store của dự án (đa lĩnh vực, giống cách
scripts/train_reranker.py từng train reranker trên 3 domain Y tế/Robotics/Toán).

Mỗi "premise" (1 đoạn chunk PDF thật) sinh ra 1 bộ 3 claim qua LLM (đi qua
router tập trung src/services/llm/ theo đúng PROJECT_STANDARDS.md mục 2.1,
KHÔNG tự dựng client riêng):
  - entailed_claim      -> label "supported"    (được premise xác nhận đúng)
  - contradicted_claim  -> label "contradicted"  (bị premise phủ định/trái ngược)
  - insufficient_claim  -> label "insufficient"  (cùng chủ đề nhưng premise này
                                                    không đủ để xác nhận hay bác bỏ)

Nhãn 3 lớp này khớp đúng enum EntailmentStatus đã có sẵn trong
src/models/synthesis_schemas.py (supported/contradicted/insufficient) để model
mới tích hợp thẳng vào pipeline hiện tại mà không cần lớp dịch nhãn.

Usage:
    python scripts/finetune_nli/01_generate_dataset.py --n-premises 200 --concurrency 5

Output:
    scripts/finetune_nli/data/train.jsonl
    scripts/finetune_nli/data/val.jsonl
    scripts/finetune_nli/data/test.jsonl
    scripts/finetune_nli/data/generation_report.json   (thống kê: bao nhiêu premise
        thành công/thất bại, nguồn paper nào, thời gian chạy -- số liệu thật cho báo cáo)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(override=False)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.services.llm import ainvoke_with_failover  # noqa: E402
from src.services.vector_store import vector_store_service  # noqa: E402

DATA_DIR = PROJECT_ROOT / "scripts" / "finetune_nli" / "data"
MIN_PREMISE_CHARS = 300
MAX_PREMISE_CHARS = 1800  # ~ giữ trong ngân sách token của model NLI nhỏ (max_length 384-512)


class NLITriplet(BaseModel):
    entailed_claim: str = Field(
        description=(
            "A single claim sentence that IS fully supported/entailed by the premise "
            "text -- a faithful paraphrase or direct restatement of something the "
            "premise explicitly states. Must not add any fact not present in the premise."
        )
    )
    contradicted_claim: str = Field(
        description=(
            "A single claim sentence that CONTRADICTS the premise -- states the "
            "logical opposite, or a factually altered version (a flipped inequality "
            "or bound, a wrong number, a wrong causal direction, an incorrect named "
            "result) of something the premise explicitly states. Must be clearly "
            "false given this premise, not merely unrelated."
        )
    )
    insufficient_claim: str = Field(
        description=(
            "A single plausible, academic-sounding claim in the SAME general topic "
            "area as the premise, but whose truth CANNOT be determined from this "
            "premise alone -- it is not stated, implied, or contradicted here. This "
            "must stay topically close (a reader skimming should not be able to "
            "tell at a glance it's unrelated) -- an obviously off-topic sentence "
            "makes this task trivial and useless for training."
        )
    )


PROMPT_TEMPLATE = """You are building training data for a 3-way Natural Language Inference \
(NLI) classifier used in an academic literature-review tool. Given ONE premise \
paragraph extracted from a real research paper, produce exactly 3 claim \
sentences as instructed by the schema: one entailed, one contradicted, one \
insufficient (topically related but not verifiable from this premise).

Rules:
- Each claim must be a single, self-contained sentence (10-30 words), written \
as if it is a sentence from a literature-review synthesis citing this paper.
- Do not mention "the premise" or "the paper" explicitly -- write it as a \
standalone factual claim, e.g. "The CQ algorithm converges weakly under a \
step-size bound of 2/||A||^2." not "The paper claims that...".
- The contradicted claim must be clearly, verifiably false given the premise \
-- not just a vague negation.
- The insufficient claim must stay in-domain and plausible, not a random \
unrelated sentence.

PREMISE:
{premise}
"""


def _load_source_chunks(n_needed: int, seed: int) -> list[dict]:
    """Pull a diverse, length-filtered sample of real chunks already embedded
    in the shared vector store (spans every paper ingested so far across
    domains, not just the 3 optimization-theory benchmark PDFs -- mirrors
    scripts/train_reranker.py's own multi-domain design)."""
    coll = vector_store_service.vector_store._collection  # noqa: SLF001
    total = coll.count()
    if total == 0:
        raise RuntimeError("Vector store is empty -- ingest at least one paper first.")

    raw = vector_store_service.vector_store.get(
        limit=min(total, max(n_needed * 6, 600)),
        include=["documents", "metadatas"],
    )
    candidates = []
    for doc, meta in zip(raw["documents"], raw["metadatas"]):
        text = (doc or "").strip()
        if MIN_PREMISE_CHARS <= len(text) <= MAX_PREMISE_CHARS:
            candidates.append({"text": text, "source": (meta or {}).get("source", "unknown")})

    if not candidates:
        raise RuntimeError(
            f"No chunk in the vector store falls inside the "
            f"[{MIN_PREMISE_CHARS}, {MAX_PREMISE_CHARS}] char window used as NLI premises."
        )

    rng = random.Random(seed)
    rng.shuffle(candidates)

    # Cap how many premises can come from the same source file so no single
    # paper dominates the dataset (diversity across domains matters more than
    # raw count for a model meant to generalize to any uploaded paper).
    per_source_cap = max(3, n_needed // 15)
    selected: list[dict] = []
    per_source_count: Counter = Counter()
    for c in candidates:
        if len(selected) >= n_needed:
            break
        if per_source_count[c["source"]] >= per_source_cap:
            continue
        selected.append(c)
        per_source_count[c["source"]] += 1

    return selected


async def _generate_one(premise: dict, sem: asyncio.Semaphore, idx: int) -> dict | None:
    async with sem:
        prompt = PROMPT_TEMPLATE.format(premise=premise["text"])
        try:
            result, outcome = await ainvoke_with_failover(
                "generate_nli_training_triplet",
                lambda client: client.with_structured_output(NLITriplet),
                [("human", prompt)],
                temperature=0.8,
            )
        except Exception as e:
            print(f"  [{idx}] FAILED: {e}", flush=True)
            return None

        return {
            "premise_id": idx,
            "source": premise["source"],
            "premise": premise["text"],
            "entailed_claim": result.entailed_claim.strip(),
            "contradicted_claim": result.contradicted_claim.strip(),
            "insufficient_claim": result.insufficient_claim.strip(),
        }


def _triplet_to_rows(triplet: dict) -> list[dict]:
    base = {"premise_id": triplet["premise_id"], "source": triplet["source"], "premise": triplet["premise"]}
    return [
        {**base, "hypothesis": triplet["entailed_claim"], "label": "supported"},
        {**base, "hypothesis": triplet["contradicted_claim"], "label": "contradicted"},
        {**base, "hypothesis": triplet["insufficient_claim"], "label": "insufficient"},
    ]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


async def main():
    parser = argparse.ArgumentParser(description="Generate the Module 1 NLI training dataset.")
    parser.add_argument("--n-premises", type=int, default=200, help="Number of source premises to sample.")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent LLM calls.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for premise sampling and split.")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f" MODULE 1 — Sinh dataset NLI 3 nhãn ({args.n_premises} premises, concurrency={args.concurrency})")
    print("=" * 80)

    premises = _load_source_chunks(args.n_premises, args.seed)
    print(f"Đã lấy {len(premises)} premise thật từ vector store "
          f"({len(set(p['source'] for p in premises))} nguồn paper khác nhau).")

    sem = asyncio.Semaphore(args.concurrency)
    t0 = time.time()
    tasks = [_generate_one(p, sem, i) for i, p in enumerate(premises)]

    results = []
    completed = 0
    for coro in asyncio.as_completed(tasks):
        r = await coro
        completed += 1
        if r is not None:
            results.append(r)
        if completed % 10 == 0 or completed == len(tasks):
            print(f"  ... {completed}/{len(tasks)} premises xử lý xong "
                  f"({len(results)} thành công) — {time.time()-t0:.1f}s", flush=True)

    elapsed = time.time() - t0
    n_ok, n_fail = len(results), len(premises) - len(results)
    print(f"\nHoàn tất sinh dữ liệu: {n_ok} thành công, {n_fail} lỗi, {elapsed:.1f}s tổng.")

    if not results:
        raise RuntimeError("Không sinh được triplet nào -- kiểm tra lại LLM router / API key.")

    rng = random.Random(args.seed)
    rng.shuffle(results)

    n = len(results)
    n_test = max(1, int(n * 0.15))
    n_val = max(1, int(n * 0.15))
    test_triplets = results[:n_test]
    val_triplets = results[n_test:n_test + n_val]
    train_triplets = results[n_test + n_val:]

    train_rows = [row for t in train_triplets for row in _triplet_to_rows(t)]
    val_rows = [row for t in val_triplets for row in _triplet_to_rows(t)]
    test_rows = [row for t in test_triplets for row in _triplet_to_rows(t)]

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    rng.shuffle(test_rows)

    _write_jsonl(DATA_DIR / "train.jsonl", train_rows)
    _write_jsonl(DATA_DIR / "val.jsonl", val_rows)
    _write_jsonl(DATA_DIR / "test.jsonl", test_rows)

    report = {
        "n_premises_requested": args.n_premises,
        "n_premises_sampled": len(premises),
        "n_premises_succeeded": n_ok,
        "n_premises_failed": n_fail,
        "n_distinct_sources": len(set(p["source"] for p in premises)),
        "generation_seconds": round(elapsed, 1),
        "split": {
            "train_premises": len(train_triplets), "train_rows": len(train_rows),
            "val_premises": len(val_triplets), "val_rows": len(val_rows),
            "test_premises": len(test_triplets), "test_rows": len(test_rows),
        },
        "label_balance_train": dict(Counter(r["label"] for r in train_rows)),
        "seed": args.seed,
    }
    with open(DATA_DIR / "generation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(" TÓM TẮT (số liệu thật cho báo cáo)")
    print("=" * 80)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nĐã ghi: {DATA_DIR / 'train.jsonl'} ({len(train_rows)} dòng)")
    print(f"Đã ghi: {DATA_DIR / 'val.jsonl'} ({len(val_rows)} dòng)")
    print(f"Đã ghi: {DATA_DIR / 'test.jsonl'} ({len(test_rows)} dòng)")


if __name__ == "__main__":
    asyncio.run(main())
