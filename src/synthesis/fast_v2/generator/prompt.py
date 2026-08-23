"""Frozen prompt: ``p165_controlled_sanitized_v1``.

Taken verbatim in structure from CELL 4 of
``P165_OpenScholar_RQ2_Clean_Validation.ipynb``, the notebook that produced
the validated controlled RQ2 generation.

Design points that are load-bearing
-----------------------------------
* Answer using **only** the provided References; no outside knowledge; no
  unsupported claims.
* References are presented with **local temporary indices** ``[0]..[N-1]``.
  Those indices are a prompt-local namespace for the generator's convenience.
  They are **not** authoritative provenance -- P-165 owns citations.
* Raw in-text bibliography-style bracket citations inside the source PDF text
  (``...prior work [27]...``) are mechanically rewritten to
  ``(source-ref 27)`` so they cannot collide with the temporary reference
  namespace. This is a regex rewrite of the *evidence text*, not a change to
  the model's instructions.
* The answer is delimited by ``[Response_Start]`` / ``[Response_End]``.
"""
from __future__ import annotations

import re
from typing import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit

PROMPT_VERSION = "p165_controlled_sanitized_v1"

RESPONSE_START = "[Response_Start]"
RESPONSE_END = "[Response_End]"

_INTERNAL_CITATION = re.compile(r"\[(\d{1,3}(?:[-,]\s?\d{1,3})*)\]")


def sanitize_internal_citations(text: str) -> str:
    """Rewrite raw PDF bracket citations out of the reference-index namespace.

    ``[27]`` -> ``(source-ref 27)``, ``[9,16,18]`` -> ``(source-ref 9,16,18)``.
    """

    def _replace(match: re.Match[str]) -> str:
        return f"(source-ref {match.group(1)})"

    return _INTERNAL_CITATION.sub(_replace, text or "")


def build_references_block(evidence: Sequence[EvidenceUnit]) -> str:
    """Render evidence as ``[i] Title: ... Text: ...`` with sanitized text."""
    lines = []
    for index, unit in enumerate(evidence):
        title = unit.title or ""
        lines.append(f"[{index}] Title: {title} Text: {sanitize_internal_citations(unit.text)}")
    return "\n".join(lines)


def build_prompt(*, question: str, evidence: Sequence[EvidenceUnit]) -> str:
    """Build the frozen controlled sanitized prompt.

    Deterministic: the same bank always yields the same prompt.
    """
    count = len(evidence)
    last_index = max(count - 1, 0)
    references = build_references_block(evidence)

    return f"""You are an AI research assistant. Answer the Question using only the provided References.

References:
{references}

Question:
{question}

Instructions:
- Use only information from the References to answer the Question.
- Do not use outside knowledge or make unsupported claims.
- Cite statements by placing citation numbers in square brackets, e.g. [1], [2], immediately after the relevant claim.
- Citation numbers must correspond to the numeric labels of the References.
- Use only citation numbers [0] through [{last_index}]; do not invent or renumber citations.
- If multiple references support a claim, include all relevant citation numbers, e.g. [1][3].
- If the References do not contain enough information to answer the Question, state that the information is insufficient.
- Do not include a separate bibliography or reference list in the answer.
- Start the answer with {RESPONSE_START} and end the answer with {RESPONSE_END}.
- Do not write any text outside the {RESPONSE_START} and {RESPONSE_END} markers.

Response:
{RESPONSE_START}
"""


def extract_native_citation_indices(text: str) -> tuple[int, ...]:
    """Collect the generator's own temporary indices -- **diagnostics only**.

    These are retained so citation misattribution can be measured. They are
    never published as final citations.
    """
    found: list[int] = []
    for match in _INTERNAL_CITATION.finditer(text or ""):
        for part in re.split(r"[-,]", match.group(1)):
            part = part.strip()
            if part.isdigit() and int(part) not in found:
                found.append(int(part))
    return tuple(found)
