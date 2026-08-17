from __future__ import annotations

import json

import pytest

from src.agents.slr_swarm.agents.code_copilot import profile_csv, run_code_copilot
from src.agents.slr_swarm.agents.gap_finder import build_boolean_query, run_gap_finder
from src.agents.slr_swarm.agents.peer_screener import run_peer_screener
from src.agents.slr_swarm.agents.prisma_drafter import cite_key, escape_latex, run_prisma_drafter
from src.agents.slr_swarm.agents.snowball import run_snowball
from src.agents.slr_swarm.contracts import GapSaturation, PICOFrame
from src.agents.slr_swarm.stubs import DefaultScriptedLLM, ScriptedLLM


# --------------------------------------------------------------------------- #
# Agent 1
# --------------------------------------------------------------------------- #
def test_build_boolean_query_skips_empty_clauses():
    query = build_boolean_query(
        PICOFrame(population="adults", intervention="", outcome="accuracy", mesh_terms=["Deep Learning"])
    )

    assert "AND ()" not in query
    assert '("adults")' in query
    assert '"Deep Learning"[MeSH]' in query


@pytest.mark.asyncio
async def test_gap_finder_builds_pico_and_heatmap(make_deps):
    deps = make_deps()

    result = await run_gap_finder({"idea": "dùng deep learning đọc ECG"}, deps)

    assert result["pico"].population == "bệnh nhân tim mạch"
    assert result["pico"].boolean_query
    assert result["gap_map"].axis_x == ["CNN", "Transformer"]
    assert len(result["gap_map"].cells) == 4


@pytest.mark.asyncio
async def test_gap_finder_marks_empty_cells_as_gaps(make_deps):
    """Ô không tìm được bài nào phải hiện là khoảng trống, không bị bỏ qua."""
    deps = make_deps(match_all=False)  # search khớp theo từ khoá thật

    result = await run_gap_finder({"idea": "ECG"}, deps)

    empties = result["gap_map"].empty_cells()
    assert empties, "phải phát hiện được ít nhất một khoảng trống"
    assert all(cell.saturation is GapSaturation.EMPTY for cell in empties)


@pytest.mark.asyncio
async def test_gap_finder_requires_idea(make_deps):
    result = await run_gap_finder({"idea": "  "}, make_deps())

    assert "error" in result


# --------------------------------------------------------------------------- #
# Agent 2
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_snowball_expands_both_directions(make_deps):
    deps = make_deps(match_all=False, snowball_depth=1)
    state = {"pico": PICOFrame(boolean_query='"Deep learning for ECG arrhythmia detection"')}

    result = await run_snowball(state, deps)

    ids = {p.paper_id for p in result["corpus"]}
    assert ids == {"P1", "P2", "P3"}, "phải kéo được cả forward (P2) và backward (P3)"
    assert result["seed_ids"] == ["P1"]

    sources = {p.paper_id: p.source for p in result["corpus"]}
    assert sources["P2"] == "forward_snowball"
    assert sources["P3"] == "backward_snowball"


@pytest.mark.asyncio
async def test_snowball_respects_max_papers(make_deps):
    deps = make_deps(match_all=False, snowball_depth=1, max_papers=2)
    state = {"pico": PICOFrame(boolean_query='"Deep learning for ECG arrhythmia detection"')}

    result = await run_snowball(state, deps)

    assert len(result["corpus"]) <= 2


@pytest.mark.asyncio
async def test_snowball_warns_when_corpus_too_small(make_deps):
    deps = make_deps(match_all=False, snowball_depth=0, min_papers=5)
    state = {"pico": PICOFrame(boolean_query='"Soil chemistry in agricultural plots"')}

    result = await run_snowball(state, deps)

    assert any("chưa đủ mạnh" in w for w in result["warnings"])


# --------------------------------------------------------------------------- #
# Agent 3
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_peer_screener_grounds_quotes_against_fulltext(make_deps, papers):
    deps = make_deps()

    result = await run_peer_screener({"corpus": papers[:1]}, deps)

    verdict = result["verdicts"][0]
    assert verdict.decision == "keep"
    assert verdict.grounding_score == 1.0
    assert verdict.spans[0].page == 1
    assert result["grounding_precision"] == 1.0


@pytest.mark.asyncio
async def test_peer_screener_scores_zero_for_fabricated_quote(make_deps, papers):
    """Reviewer trích dẫn không có trong bài -> grounding 0, không được làm ngơ."""
    llm = ScriptedLLM(
        {
            "reviewer": json.dumps(
                {
                    "decision": "keep",
                    "reason": "hợp chủ đề",
                    "confidence": 0.9,
                    "evidence_quotes": ["a randomized trial of 12000 diabetic children in Brazil"],
                }
            )
        }
    )
    deps = make_deps(llm=llm)

    result = await run_peer_screener({"corpus": papers[:1]}, deps)

    assert result["verdicts"][0].grounding_score == 0.0
    assert result["grounding_precision"] == 0.0


@pytest.mark.asyncio
async def test_peer_screener_calls_adjudicator_on_disagreement(make_deps, papers):
    keep = json.dumps({"decision": "keep", "reason": "liên quan", "confidence": 0.7, "evidence_quotes": []})
    reject = json.dumps({"decision": "reject", "reason": "lạc đề", "confidence": 0.9, "evidence_quotes": []})
    final = json.dumps({"decision": "reject", "reason": "trọng tài chốt loại", "confidence": 0.8, "evidence_quotes": []})

    llm = ScriptedLLM({"THỨ NHẤT": keep, "THỨ HAI": reject, "TRỌNG TÀI": final})
    deps = make_deps(llm=llm)

    result = await run_peer_screener({"corpus": papers[:1]}, deps)

    verdict = result["verdicts"][0]
    assert verdict.disagreed is True
    assert [o.reviewer for o in verdict.opinions] == ["inclusive", "strict", "adjudicator"]
    assert verdict.decision == "reject"
    assert result["included_ids"] == []


@pytest.mark.asyncio
async def test_peer_screener_skips_adjudicator_when_reviewers_agree(make_deps, papers):
    deps = make_deps()

    result = await run_peer_screener({"corpus": papers[:1]}, deps)

    assert result["verdicts"][0].disagreed is False
    assert len(result["verdicts"][0].opinions) == 2


@pytest.mark.asyncio
async def test_peer_screener_routes_screening_to_local_model(make_deps, papers):
    """§6: screening không được đi cloud, phải nằm ở model local."""
    deps = make_deps()

    await run_peer_screener({"corpus": papers[:2]}, deps)

    assert deps.router.cloud_calls == 0
    assert deps.router.local_calls == 4  # 2 bài × 2 reviewer, không có bất đồng


# --------------------------------------------------------------------------- #
# Agent 4
# --------------------------------------------------------------------------- #
def test_escape_latex_and_cite_key():
    assert escape_latex("cost 50% & rising") == r"cost 50\% \& rising"
    from src.agents.slr_swarm.contracts import PaperRecord

    assert cite_key(PaperRecord(paper_id="P-1", year=2023)) == "P12023"
    assert cite_key(PaperRecord(paper_id="P-1")) == "P1nd"


@pytest.mark.asyncio
async def test_prisma_drafter_emits_grounded_table_and_bibtex(make_deps, papers):
    deps = make_deps()
    state = {"corpus": papers[:1], "included_ids": ["P1"]}

    result = await run_prisma_drafter(state, deps)

    row = result["prisma_rows"][0]
    assert row.sample_size == "500 patients"
    assert row.evidence, "mỗi ô có giá trị phải kèm toạ độ chứng minh"

    draft = result["draft"]
    assert "\\begin{tabular}" in draft.latex
    assert "anchor: page" in draft.latex
    assert "@article{P12023" in draft.bibtex
    assert draft.grounded_claim_count == draft.claim_count


@pytest.mark.asyncio
async def test_prisma_drafter_blanks_ungrounded_fields(make_deps, papers):
    """Giá trị model bịa ra phải thành ô trống (n/a), không được lên bảng."""
    llm = ScriptedLLM(
        {
            "Trích xuất thông tin PRISMA": json.dumps(
                {
                    "design": "randomized controlled trial in Brazil",  # không có trong full-text
                    "sample_size": "500 patients",                      # có thật
                    "method": "",
                    "outcome": "",
                }
            )
        }
    )
    deps = make_deps(llm=llm)

    result = await run_prisma_drafter({"corpus": papers[:1], "included_ids": ["P1"]}, deps)

    row = result["prisma_rows"][0]
    assert row.design == ""
    assert row.sample_size == "500 patients"
    assert "n/a" in result["draft"].latex
    assert result["draft"].grounded_claim_count < result["draft"].claim_count


@pytest.mark.asyncio
async def test_prisma_drafter_errors_without_included_papers(make_deps, papers):
    result = await run_prisma_drafter({"corpus": papers, "included_ids": []}, make_deps())

    assert "error" in result


# --------------------------------------------------------------------------- #
# Agent 5
# --------------------------------------------------------------------------- #
def test_profile_csv_detects_column_types_and_missing():
    csv_text = "age,group,score\n30,A,1.5\n40,B,\n50,A,2.5\n"

    profile = profile_csv(csv_text)

    assert profile.rows == 3
    assert profile.numeric_columns == ["age", "score"]
    assert profile.categorical_columns == ["group"]
    assert profile.missing_ratio["score"] == pytest.approx(1 / 3, abs=1e-3)


def test_profile_csv_handles_empty_input():
    assert profile_csv("").columns == []


@pytest.mark.asyncio
async def test_code_copilot_returns_methods_and_code(make_deps):
    deps = make_deps()
    csv_text = "age,group\n" + "\n".join(f"{20 + i},A" for i in range(40))

    result = await run_code_copilot({"csv_text": csv_text, "goal": "so sánh nhóm"}, deps)

    assert result["plan"].methods == ["Descriptive statistics", "ANOVA"]
    assert "pandas" in result["plan"].code
    assert result["profile"].rows == 40


@pytest.mark.asyncio
async def test_code_copilot_warns_on_small_sample(make_deps):
    result = await run_code_copilot({"csv_text": "age,group\n30,A\n", "goal": "x"}, make_deps())

    assert any("lực" in w or "dòng dữ liệu" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_code_copilot_requires_data(make_deps):
    result = await run_code_copilot({"csv_text": "   "}, make_deps())

    assert "error" in result


@pytest.mark.asyncio
async def test_scripted_llm_default_covers_all_agents():
    """Bảo vệ stub: nếu prompt đổi mà quên cập nhật marker, test này gãy sớm."""
    llm = DefaultScriptedLLM()

    assert json.loads(await llm.complete("... khung PICO ..."))["population"]
    assert json.loads(await llm.complete("Bạn là reviewer THỨ NHẤT"))["decision"]
    assert json.loads(await llm.complete("Trích xuất thông tin PRISMA"))["sample_size"]
    assert json.loads(await llm.complete("Bạn là chuyên gia thống kê"))["code"]
