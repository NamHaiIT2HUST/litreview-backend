"""Structured claim-manifest prompt: ``p165_structured_claim_manifest_v1``.

Evidence is serialized with stable evidence/paper IDs and raw canonical text
so generated support quotes can be checked by exact substring. Output is one
strict JSON manifest; P-165 validates provenance and owns final citations.

The legacy citation-sanitizing helper remains for compatibility tests and old
artifacts. It is not used by the structured prompt.
"""
from __future__ import annotations

import json
import re
from typing import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit

PROMPT_VERSION = "p165_structured_claim_manifest_v1"

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
    """Render raw canonical evidence with stable provenance identifiers."""
    return json.dumps(
        [
            {
                "evidence_id": unit.evidence_id,
                "paper_id": str(unit.paper_id),
                "title": unit.title or "",
                "text": unit.text,
            }
            for unit in evidence
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_prompt(
    *,
    question: str,
    evidence: Sequence[EvidenceUnit],
    dimensions: Sequence[str] = (),
) -> str:
    """Build the strict structured-claim-manifest prompt.

    Deterministic: the same bank always yields the same prompt.
    """
    references = build_references_block(evidence)
    requested_facets = json.dumps(list(dimensions), ensure_ascii=False)

    return f"""You are an AI research assistant. Use only the provided EvidenceUnits.

EvidenceUnits (raw canonical text; copy support_quote exactly):
{references}

Question:
{question}

Requested facets:
{requested_facets}

Return exactly one JSON object with this shape and no extra fields:
{{"claims":[{{"facet":"<requested facet>","is_comparative":false,"statements":[{{"claim_text":"<one factual statement>","paper_id":"<selected paper UUID>","supports":[{{"evidence_id":"<exact EvidenceUnit ID>","support_quote":"<short exact substring copied from that EvidenceUnit text>"}}]}}]}}]}}

Rules:
- Every factual statement must have at least one support item.
- support_quote must be copied byte-for-byte from the referenced EvidenceUnit text.
- Do not emit bracket-number citations inside claim_text.
- Use only requested facets and IDs present above.
- A non-comparative claim has exactly one statement.
- A comparative claim has one explicit statement per compared paper, with distinct paper_id values and support from each paper.
- Do not use outside knowledge. Omit claims lacking exact support.
- Output JSON only; no Markdown fences, prose wrapper, bibliography, or extra keys.
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
