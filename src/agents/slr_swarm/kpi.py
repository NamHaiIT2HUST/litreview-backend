"""Dashboard KPI Realtime — §7.3 Master Plan.

Hai chỉ số ràng buộc của BTC:
  - Grounding Precision >= 80%  (tỉ lệ claim có bằng chứng thật trong PDF)
  - Time Saved         >= 50%  (so với baseline làm tay)

Cả hai đều tính từ dữ liệu chạy thật trong state, không nhận số cứng từ cấu hình.
"""

from __future__ import annotations

import time

from src.agents.slr_swarm.contracts import KpiSnapshot
from src.agents.slr_swarm.ports import SwarmDeps

# Giá tham chiếu cho một lần gọi cloud bị né nhờ model local (USD).
CLOUD_CALL_UNIT_COST = 0.0015


def compute_kpi(state: dict, deps: SwarmDeps, *, now: float | None = None) -> KpiSnapshot:
    started = state.get("started_at")
    current = now if now is not None else time.monotonic()
    elapsed_minutes = max((current - started) / 60.0, 0.0) if started else 0.0

    draft = state.get("draft")
    if draft is not None and draft.claim_count:
        # Ưu tiên đo trên bản thảo cuối: đó mới là thứ nghiên cứu viên đọc.
        precision = round(draft.grounded_claim_count / draft.claim_count, 4)
    else:
        precision = float(state.get("grounding_precision", 0.0) or 0.0)

    baseline = deps.baseline_minutes
    time_saved = round(max(0.0, 1 - elapsed_minutes / baseline), 4) if baseline > 0 else 0.0

    return KpiSnapshot(
        grounding_precision=precision,
        time_saved_ratio=time_saved,
        papers_processed=len(state.get("corpus", [])),
        elapsed_minutes=round(elapsed_minutes, 3),
        baseline_minutes=baseline,
        llm_calls_saved=deps.router.local_calls,
    )


def estimated_cost_saved(snapshot: KpiSnapshot) -> float:
    """Số tiền API ước tính né được nhờ đẩy screening/extraction về model local."""
    return round(snapshot.llm_calls_saved * CLOUD_CALL_UNIT_COST, 2)
