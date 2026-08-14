from src.services.research_question_policy import resolve_research_objective


def test_blank_research_question_uses_a_general_literature_review_objective():
    assert resolve_research_objective("   ") == (
        "What are the main themes, methods, findings, limitations, and future research "
        "directions across the selected papers?"
    )


def test_research_question_is_trimmed():
    assert resolve_research_objective("  How does RAG support review?  ") == "How does RAG support review?"
