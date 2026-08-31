"""Unit Tests for Citation Guardrails & Map-Reduce Cost Optimizer."""
from langchain_core.documents import Document

from src.services.map_reduce_optimizer import MapReduceOptimizer, MapSummaryCache
from src.services.rag_guardrail_service import rag_guardrail_service


def test_sanitize_citations_strips_phantom_keys():
    text = "Thuật toán CQ hội tụ yếu trong không gian Hilbert [1][99], với điều kiện gamma [2]."
    valid_keys = {"1", "2"}
    sanitized, stripped = rag_guardrail_service.sanitize_citations(text, valid_keys=valid_keys)
    assert "99" in stripped
    assert "[99]" not in sanitized
    assert "[1, 2]" in sanitized or ("[1]" in sanitized and "[2]" in sanitized)


def test_prune_redundant_citations():
    text = "Kết quả phân vùng đạt 95% độ chính xác [1][1][2] trên tập dữ liệu kiểm thử [2][2]."
    pruned = rag_guardrail_service.prune_redundant_citations(text)
    assert "[1, 2]" in pruned
    assert "[1][1]" not in pruned
    assert "[2][2]" not in pruned


def test_detect_and_strip_ghost_authors():
    text = "Theo nghiên cứu của (Xu, 2010), thuật toán hội tụ. Ngược lại (FakeAuthor, 2025) cho rằng không đúng."
    valid_authors = {"Xu", "Byrne"}
    valid_years = {"2002", "2010", "2018"}
    sanitized, ghosts = rag_guardrail_service.detect_and_strip_ghost_authors(
        text, valid_authors=valid_authors, valid_years=valid_years
    )
    assert any("FakeAuthor" in g for g in ghosts)
    assert "FakeAuthor" not in sanitized
    assert "(Xu, 2010)" in sanitized


def test_map_reduce_prefiltering():
    optimizer = MapReduceOptimizer()
    query = "thuật toán CQ gradient projection Byrne"
    doc_relevant = Document(page_content="Thuật toán CQ của Byrne là trường hợp đặc biệt của gradient projection.")
    doc_irrelevant = Document(page_content="Công thức nấu ăn và các loại gia vị truyền thống Đông Nam Á.")

    kept, pruned_tokens = optimizer.prefilter_chunks(query, [doc_relevant, doc_irrelevant])
    assert len(kept) == 1
    assert kept[0][1].page_content == doc_relevant.page_content
    assert pruned_tokens > 0


def test_map_summary_cache():
    cache = MapSummaryCache(max_size=10)
    query = "Convergence rate of CQ algorithm"
    chunk = "Theorem 3.1 states that the CQ algorithm converges weakly."
    summary = {"summary": "CQ converges weakly under condition.", "relevance_score": 9}

    assert cache.get(chunk, query) is None
    cache.set(chunk, query, summary)
    retrieved = cache.get(chunk, query)
    assert retrieved == summary


def test_cost_report_calculation():
    optimizer = MapReduceOptimizer()
    report = optimizer.compute_cost_report(
        prompt_tokens=1000,
        completion_tokens=200,
        tokens_saved_cache=1500,
        tokens_saved_prefilter=1500,
        cache_hits=2,
        total_chunks=6,
        chunks_sent=2,
    )
    assert report.total_tokens == 1200
    assert report.cost_savings_pct > 50.0
    assert report.estimated_cost_usd > 0.0
