"""Agent 5 — Methodology & Code Copilot (§5.5 / §4.2 Master Plan).

Luồng 2 chạy độc lập với luồng SLR: nghiên cứu viên upload CSV/Excel, agent profile
dữ liệu bằng code tất định (không hỏi LLM những gì đếm được), rồi mới nhờ LLM đề
xuất phương pháp thống kê và sinh code Pandas/scikit-learn.

Code sinh ra KHÔNG được thực thi ở đây — trả về cho người dùng tự chạy (HITL).
"""

from __future__ import annotations

import csv
import io

from src.agents.slr_swarm.contracts import AnalysisPlan, DatasetProfile
from src.agents.slr_swarm.json_utils import as_str_list, parse_object
from src.agents.slr_swarm.ports import SwarmDeps

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "methods": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "code": {"type": "string"},
        "interpretation": {"type": "string"},
    },
    "required": ["methods", "code"],
}

_PROMPT = """Bạn là chuyên gia thống kê hỗ trợ nghiên cứu viên phân tích dữ liệu ban đầu.

Mục tiêu nghiên cứu: {goal}

Hồ sơ dữ liệu (đã đo tự động, hãy tin số này):
- Số dòng: {rows}
- Cột số: {numeric}
- Cột phân loại: {categorical}
- Tỉ lệ thiếu: {missing}

Trả về DUY NHẤT JSON: methods (list phương pháp phù hợp, vd ANOVA, Random Forest),
rationale (vì sao chọn), code (Python dùng pandas/scikit-learn/matplotlib, đọc từ 'data.csv'),
interpretation (hướng dẫn đọc kết quả).
"""


def _is_number(value: str) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def profile_csv(csv_text: str, *, sample_rows: int = 500) -> DatasetProfile:
    """Đo hồ sơ dữ liệu bằng stdlib — không phụ thuộc pandas, chạy được ở mọi môi trường."""
    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        return DatasetProfile()

    columns = [name.strip() for name in header]
    filled = {name: 0 for name in columns}
    numeric_hits = {name: 0 for name in columns}
    rows = 0

    for row in reader:
        rows += 1
        if rows > sample_rows:
            continue
        for index, name in enumerate(columns):
            value = row[index].strip() if index < len(row) else ""
            if not value:
                continue
            filled[name] += 1
            if _is_number(value):
                numeric_hits[name] += 1

    sampled = min(rows, sample_rows) or 1
    numeric: list[str] = []
    categorical: list[str] = []
    missing: dict[str, float] = {}

    for name in columns:
        missing[name] = round(1 - filled[name] / sampled, 4)
        # Cột được coi là số nếu >=90% giá trị có mặt là số.
        if filled[name] and numeric_hits[name] / filled[name] >= 0.9:
            numeric.append(name)
        else:
            categorical.append(name)

    return DatasetProfile(
        rows=rows,
        columns=columns,
        numeric_columns=numeric,
        categorical_columns=categorical,
        missing_ratio=missing,
    )


async def run_code_copilot(state: dict, deps: SwarmDeps) -> dict:
    csv_text = state.get("csv_text") or ""
    if not csv_text.strip():
        return {"error": "Agent 5: chưa có dữ liệu CSV để phân tích."}

    profile = profile_csv(csv_text)
    if not profile.columns:
        return {"error": "Agent 5: file dữ liệu không đọc được header."}

    warnings = list(state.get("warnings", []))
    if profile.rows < 30:
        warnings.append(
            f"Cảnh báo: chỉ {profile.rows} dòng dữ liệu — kiểm định thống kê có thể không đủ lực."
        )
    for column, ratio in profile.missing_ratio.items():
        if ratio >= 0.3:
            warnings.append(f"Cảnh báo: cột '{column}' thiếu {ratio:.0%} giá trị.")

    llm = deps.router.pick("planning")
    raw = await llm.complete(
        _PROMPT.format(
            goal=state.get("goal", "(chưa nêu)"),
            rows=profile.rows,
            numeric=", ".join(profile.numeric_columns) or "(không có)",
            categorical=", ".join(profile.categorical_columns) or "(không có)",
            missing=", ".join(f"{k}={v:.0%}" for k, v in profile.missing_ratio.items()),
        ),
        schema=PLAN_SCHEMA,
    )
    data = parse_object(raw)

    plan = AnalysisPlan(
        methods=as_str_list(data.get("methods")),
        rationale=str(data.get("rationale", "") or ""),
        code=str(data.get("code", "") or ""),
        interpretation=str(data.get("interpretation", "") or ""),
    )
    if not plan.code.strip():
        warnings.append("Agent 5: model không sinh được code, cần chạy lại hoặc đổi model.")

    return {
        "profile": profile,
        "plan": plan,
        "warnings": warnings,
        "trace": [{"agent": "code_copilot", "rows": profile.rows, "methods": len(plan.methods)}],
    }
