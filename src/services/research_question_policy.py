"""Research objective selection for evidence synthesis."""

GENERAL_LITERATURE_REVIEW_OBJECTIVE = (
    "What are the main themes, methods, findings, limitations, and future research "
    "directions across the selected papers?"
)


def resolve_research_objective(value: str | None) -> str:
    question = (value or "").strip()
    return question or GENERAL_LITERATURE_REVIEW_OBJECTIVE
