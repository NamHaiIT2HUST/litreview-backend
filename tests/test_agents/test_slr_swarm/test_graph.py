from __future__ import annotations

import json
import time

import pytest

from src.agents.slr_swarm.contracts import KpiSnapshot, PaperRecord
from src.agents.slr_swarm.graph import build_slr_graph, run_data_analysis, run_slr
from src.agents.slr_swarm.kpi import compute_kpi, estimated_cost_saved
from src.agents.slr_swarm.state import merge_papers
from src.agents.slr_swarm.stubs import ScriptedLLM


@pytest.mark.asyncio
async def test_slr_pipeline_runs_end_to_end(make_deps, papers):
    deps = make_deps(search_papers=papers[:2], snowball_depth=0, min_papers=2)

    state = await run_slr("deep learning cho ECG", deps, inclusion_criteria=["nghiên cứu trên người"])

    assert state.get("error", "") == ""
    assert state["gate_passed"] is True
    assert state["awaiting_human"] is False
    assert state["included_ids"] == ["P1", "P2"]
    assert state["draft"].latex
    assert state["draft"].bibtex
    assert state["kpi"].grounding_precision >= 0.8


@pytest.mark.asyncio
async def test_pipeline_visits_agents_in_order(make_deps, papers):
    deps = make_deps(search_papers=papers[:2], snowball_depth=0, min_papers=2)

    state = await run_slr("ECG", deps)

    visited = [entry["agent"] for entry in state["trace"]]
    assert visited == [
        "gap_finder",
        "snowball",
        "peer_screener",
        "gate",
        "prisma_drafter",
        "finalize",
    ]


@pytest.mark.asyncio
async def test_gate_blocks_and_asks_for_human_when_grounding_low(make_deps):
    """Grounding thấp -> dừng ở HITL, KHÔNG được sinh bản thảo."""
    llm = ScriptedLLM(
        {
            "khung PICO": json.dumps({"population": "x", "intervention": "y", "outcome": "z"}),
            "reviewer": json.dumps(
                {
                    "decision": "keep",
                    "reason": "ok",
                    "confidence": 0.9,
                    "evidence_quotes": ["a randomized trial of 12000 diabetic children in Brazil"],
                }
            ),
        }
    )
    deps = make_deps(llm=llm, snowball_depth=0, min_papers=2)

    state = await run_slr("ECG", deps)

    assert state["gate_passed"] is False
    assert state["awaiting_human"] is True
    assert state.get("draft") is None
    assert any("Insufficient Data" in w for w in state["warnings"])
    assert "prisma_drafter" not in [entry["agent"] for entry in state["trace"]]


@pytest.mark.asyncio
async def test_human_override_resumes_drafting(make_deps):
    llm = ScriptedLLM(
        {
            "khung PICO": json.dumps({"population": "x", "intervention": "y", "outcome": "z"}),
            "reviewer": json.dumps(
                {"decision": "keep", "reason": "ok", "confidence": 0.9, "evidence_quotes": ["hoàn toàn bịa đặt"]}
            ),
            "Trích xuất thông tin PRISMA": json.dumps({"design": "", "sample_size": "500 patients", "method": "", "outcome": ""}),
        }
    )
    deps = make_deps(llm=llm, snowball_depth=0, min_papers=2)

    state = await run_slr("ECG", deps, human_action="override")

    assert state["gate_passed"] is False
    assert state["awaiting_human"] is False
    assert state["draft"] is not None
    # Đi tiếp không có nghĩa là hết cảnh báo — cảnh báo phải còn để truy trách nhiệm.
    assert any("Insufficient Data" in w for w in state["warnings"])


@pytest.mark.asyncio
async def test_one_ungrounded_paper_drags_precision_below_gate(make_deps, papers):
    """P3 lạc đề không có bằng chứng khớp -> kéo precision xuống dưới 80% và bị chặn."""
    deps = make_deps(search_papers=papers, snowball_depth=0, min_papers=2)

    state = await run_slr("ECG", deps)

    assert state["grounding_precision"] == pytest.approx(2 / 3, abs=1e-3)
    assert state["gate_passed"] is False
    assert state["awaiting_human"] is True


@pytest.mark.asyncio
async def test_gate_blocks_when_too_few_papers_kept(make_deps):
    deps = make_deps(match_all=True, snowball_depth=0, min_papers=10)

    state = await run_slr("ECG", deps)

    assert state["gate_passed"] is False
    assert state["awaiting_human"] is True


@pytest.mark.asyncio
async def test_agent_failure_stops_pipeline_without_crashing(make_deps):
    class BoomLLM:
        async def complete(self, prompt: str, *, schema=None) -> str:
            raise RuntimeError("model local chết")

    deps = make_deps(llm=BoomLLM())

    state = await run_slr("ECG", deps)

    assert "gap_finder lỗi" in state["error"]
    assert state.get("draft") is None
    assert state["kpi"] is not None  # finalize vẫn chạy để KPI ghi nhận lần hỏng


@pytest.mark.asyncio
async def test_empty_idea_short_circuits(make_deps):
    state = await run_slr("   ", make_deps())

    assert state["error"]
    assert "snowball" not in [entry["agent"] for entry in state["trace"]]


@pytest.mark.asyncio
async def test_data_analysis_graph_runs(make_deps):
    csv_text = "age,group\n" + "\n".join(f"{20 + i},A" for i in range(35))

    state = await run_data_analysis(csv_text, "so sánh 2 nhóm", make_deps())

    assert state["profile"].rows == 35
    assert state["plan"].code
    assert [entry["agent"] for entry in state["trace"]] == ["code_copilot"]


def test_build_slr_graph_compiles(make_deps):
    app = build_slr_graph(make_deps())

    nodes = set(app.get_graph().nodes)
    assert {"gap_finder", "snowball", "screener", "gate", "human_review", "draft", "finalize"} <= nodes


def test_merge_papers_keeps_record_closest_to_seed():
    left = [PaperRecord(paper_id="A", seed_distance=2), PaperRecord(paper_id="B", seed_distance=0)]
    right = [PaperRecord(paper_id="A", seed_distance=1)]

    merged = {p.paper_id: p for p in merge_papers(left, right)}

    assert merged["A"].seed_distance == 1
    assert merged["B"].seed_distance == 0


# --------------------------------------------------------------------------- #
# KPI
# --------------------------------------------------------------------------- #
def test_kpi_prefers_draft_ratio_over_screening_precision(make_deps):
    from src.agents.slr_swarm.contracts import ReviewDraft

    deps = make_deps()
    started = time.monotonic()
    state = {
        "started_at": started,
        "grounding_precision": 0.2,
        "draft": ReviewDraft(claim_count=10, grounded_claim_count=9),
        "corpus": [PaperRecord(paper_id="A")],
    }

    snapshot = compute_kpi(state, deps, now=started + 60)

    assert snapshot.grounding_precision == 0.9
    assert snapshot.papers_processed == 1
    assert snapshot.elapsed_minutes == pytest.approx(1.0)


def test_kpi_time_saved_never_negative(make_deps):
    deps = make_deps(baseline_minutes=10)
    started = time.monotonic()

    snapshot = compute_kpi({"started_at": started}, deps, now=started + 6000)

    assert snapshot.time_saved_ratio == 0.0


def test_kpi_meets_btc_thresholds():
    assert KpiSnapshot(grounding_precision=0.86, time_saved_ratio=0.62).meets_btc is True
    assert KpiSnapshot(grounding_precision=0.79, time_saved_ratio=0.62).meets_btc is False
    assert KpiSnapshot(grounding_precision=0.86, time_saved_ratio=0.49).meets_btc is False


def test_estimated_cost_saved_counts_local_calls():
    assert estimated_cost_saved(KpiSnapshot(llm_calls_saved=1000)) == 1.5
