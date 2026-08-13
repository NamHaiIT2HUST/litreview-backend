from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class SynthesisState(TypedDict, total=False):
    session_id: str
    research_question: str
    paper_ids: list[str]
    dimensions: list[str]
    completed_papers: Annotated[list[str], operator.add]
    expanded_dimensions: list[str]
    claim_ids: list[str]
    section_ids: list[str]
    drafted_sections: Annotated[list[dict], operator.add]
    review_markdown: str
