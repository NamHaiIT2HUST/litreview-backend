from src.models.db_models import LLMCallLog, RetrievalLog


def test_observability_models_capture_required_trace_fields():
    retrieval_columns = set(RetrievalLog.__table__.columns.keys())
    llm_columns = set(LLMCallLog.__table__.columns.keys())

    assert {"session_id", "paper_id", "dimension", "query", "results_json", "duration_ms"} <= retrieval_columns
    assert {"session_id", "step_name", "model_name", "attempt", "duration_ms", "status", "prompt_json", "response_json", "error"} <= llm_columns


def test_synthesis_metrics_capture_performance_and_quality_totals():
    from src.models.db_models import SynthesisMetrics

    columns = set(SynthesisMetrics.__table__.columns.keys())
    assert {
        "session_id", "total_llm_calls", "total_input_tokens", "total_output_tokens",
        "cache_hits", "cache_misses", "grounding_retry_count",
        "claim_verification_count", "synthesis_duration_ms", "final_word_count",
        "citation_coverage",
        "section_metrics",
    } <= columns
