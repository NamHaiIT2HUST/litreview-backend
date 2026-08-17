"""Agent 1 — Research Gap & PICO Finder (§5.1 Master Plan).

Input : ý tưởng thô / câu hỏi nghiên cứu.
Output: PICOFrame + Boolean MeSH query + Research Gap Heatmap.

Heatmap được dựng bằng cách *đo thật*: với mỗi ô (trục X × trục Y) ta bắn một truy vấn
đếm số bài. Ô nào đếm ra 0 là khoảng trống, ô nào dày đặc là đã bão hoà.
"""

from __future__ import annotations

import asyncio

from src.agents.slr_swarm.contracts import GapCell, GapMap, PICOFrame
from src.agents.slr_swarm.json_utils import as_str_list, parse_object
from src.agents.slr_swarm.ports import SwarmDeps

PICO_SCHEMA = {
    "type": "object",
    "properties": {
        "population": {"type": "string"},
        "intervention": {"type": "string"},
        "comparison": {"type": "string"},
        "outcome": {"type": "string"},
        "mesh_terms": {"type": "array", "items": {"type": "string"}},
        "axis_x": {"type": "array", "items": {"type": "string"}},
        "axis_y": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["population", "intervention", "outcome"],
}

_PROMPT = """Bạn là chuyên gia phương pháp nghiên cứu hệ thống (systematic review).
Chuyển ý tưởng sau thành khung PICO và đề xuất 2 trục để dựng bản đồ khoảng trống.

Ý tưởng: {idea}

Trả về DUY NHẤT JSON với các khoá:
population, intervention, comparison, outcome, mesh_terms (list),
axis_x (list 2-5 hướng tiếp cận/phương pháp), axis_y (list 2-5 nhóm đối tượng/bối cảnh).
"""


def build_boolean_query(pico: PICOFrame) -> str:
    """Ghép chuỗi Boolean từ PICO + MeSH. Bỏ qua vế rỗng để tránh sinh `AND ()`."""
    clauses: list[str] = []
    for value in (pico.population, pico.intervention, pico.comparison, pico.outcome):
        cleaned = value.strip()
        if cleaned:
            clauses.append(f'("{cleaned}")')
    if pico.mesh_terms:
        mesh = " OR ".join(f'"{term.strip()}"[MeSH]' for term in pico.mesh_terms if term.strip())
        if mesh:
            clauses.append(f"({mesh})")
    return " AND ".join(clauses)


async def _probe_cell(deps: SwarmDeps, x: str, y: str) -> GapCell:
    try:
        hits = await deps.search.search(f'"{x}" AND "{y}"', limit=12)
    except Exception:  # noqa: BLE001 - một ô lỗi không được làm sập cả heatmap
        hits = []
    count = len(hits)
    return GapCell(dimension_x=x, dimension_y=y, paper_count=count, saturation=GapCell.classify(count))


async def run_gap_finder(state: dict, deps: SwarmDeps) -> dict:
    idea = (state.get("idea") or "").strip()
    if not idea:
        return {"error": "Thiếu ý tưởng nghiên cứu (idea), Agent 1 không thể bắt đầu."}

    llm = deps.router.pick("planning")
    raw = await llm.complete(_PROMPT.format(idea=idea), schema=PICO_SCHEMA)
    data = parse_object(raw)

    pico = PICOFrame(
        population=str(data.get("population", "") or ""),
        intervention=str(data.get("intervention", "") or ""),
        comparison=str(data.get("comparison", "") or ""),
        outcome=str(data.get("outcome", "") or ""),
        mesh_terms=as_str_list(data.get("mesh_terms")),
    )
    pico.boolean_query = build_boolean_query(pico) or idea

    axis_x = as_str_list(data.get("axis_x"))[:5]
    axis_y = as_str_list(data.get("axis_y"))[:5]

    cells: list[GapCell] = []
    if axis_x and axis_y:
        pairs = [(x, y) for x in axis_x for y in axis_y]
        cells = list(await asyncio.gather(*(_probe_cell(deps, x, y) for x, y in pairs)))

    gap_map = GapMap(axis_x=axis_x, axis_y=axis_y, cells=cells)

    warnings = list(state.get("warnings", []))
    if not cells:
        warnings.append("Agent 1: không dựng được Gap Heatmap (thiếu trục phân tích).")

    return {
        "pico": pico,
        "gap_map": gap_map,
        "warnings": warnings,
        "trace": [{"agent": "gap_finder", "query": pico.boolean_query, "cells": len(cells)}],
    }
