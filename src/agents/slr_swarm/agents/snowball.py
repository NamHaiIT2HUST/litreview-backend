"""Agent 2 — Autonomous Citation Snowball Swarm (§5.2 Master Plan).

Chống sót nguồn: sau khi search từ khoá, mở rộng 2 chiều trên đồ thị trích dẫn
(backward = tài liệu tham khảo, forward = bài trích dẫn lại) theo từng vòng.
Mỗi vòng chạy song song cho toàn bộ frontier — đây là phần "swarm".
"""

from __future__ import annotations

import asyncio

from src.agents.slr_swarm.contracts import PaperRecord
from src.agents.slr_swarm.ports import SwarmDeps


async def _expand(deps: SwarmDeps, paper_id: str, distance: int) -> list[PaperRecord]:
    """Lấy cả 2 chiều cho một bài. Lỗi ở một chiều không huỷ chiều còn lại."""
    backward, forward = await asyncio.gather(
        deps.citations.references(paper_id),
        deps.citations.citations(paper_id),
        return_exceptions=True,
    )

    found: list[PaperRecord] = []
    for records, source in ((backward, "backward_snowball"), (forward, "forward_snowball")):
        if isinstance(records, BaseException):
            continue
        for record in records:
            found.append(record.model_copy(update={"source": source, "seed_distance": distance}))
    return found


async def run_snowball(state: dict, deps: SwarmDeps) -> dict:
    pico = state.get("pico")
    query = getattr(pico, "boolean_query", "") or state.get("idea", "")
    if not query:
        return {"error": "Agent 2: không có truy vấn để tìm kiếm."}

    seeds = await deps.search.search(query, limit=min(50, deps.max_papers))
    corpus: dict[str, PaperRecord] = {}
    for seed in seeds:
        corpus[seed.paper_id] = seed.model_copy(update={"source": "query", "seed_distance": 0})

    frontier = list(corpus.keys())
    for depth in range(1, deps.snowball_depth + 1):
        if not frontier or len(corpus) >= deps.max_papers:
            break

        batches = await asyncio.gather(*(_expand(deps, pid, depth) for pid in frontier))

        next_frontier: list[str] = []
        for batch in batches:
            for record in batch:
                if record.paper_id in corpus:
                    continue
                if len(corpus) >= deps.max_papers:
                    break
                corpus[record.paper_id] = record
                next_frontier.append(record.paper_id)
        frontier = next_frontier

    papers = list(corpus.values())
    warnings = list(state.get("warnings", []))
    if len(papers) < deps.min_papers:
        warnings.append(
            f"Cảnh báo: chỉ tìm được {len(papers)} bài (< {deps.min_papers}). "
            "Dữ liệu chưa đủ mạnh để đưa ra kết luận chắc chắn."
        )

    snowballed = sum(1 for p in papers if p.seed_distance > 0)
    return {
        "corpus": papers,
        "seed_ids": [p.paper_id for p in papers if p.seed_distance == 0],
        "warnings": warnings,
        "trace": [
            {
                "agent": "snowball",
                "seeds": len(seeds),
                "snowballed": snowballed,
                "total": len(papers),
            }
        ],
    }
