"""Structured claim-manifest prompt: ``p165_structured_claim_manifest_v2``.

Evidence is serialized with stable evidence/paper IDs and raw canonical text
so generated evidence IDs can be resolved deterministically. Output is one
strict JSON manifest; P-165 derives canonical quotes and owns final citations.

The legacy citation-sanitizing helper remains for compatibility tests and old
artifacts. It is not used by the structured prompt.
"""
from __future__ import annotations

import json
import re
from typing import Sequence

from src.synthesis.fast_v2.evidence.models import EvidenceUnit
from src.synthesis.fast_v2.grounding.manifest import (
    ClaimManifest,
    ClaimStatement,
    ClaimSupport,
    GeneratedClaim,
)

PROMPT_VERSION = "p165_structured_claim_manifest_v2"

RESPONSE_START = "[Response_Start]"
RESPONSE_END = "[Response_End]"

_INTERNAL_CITATION = re.compile(r"\[(\d{1,3}(?:[-,]\s?\d{1,3})*)\]")


class UnknownEvidenceHandleError(ValueError):
    """Generated manifest referenced a handle absent from this request."""


def build_evidence_handle_mapping(
    evidence: Sequence[EvidenceUnit],
) -> dict[str, str]:
    """Map compact per-request handles to canonical EvidenceUnit IDs."""
    return {
        f"E{index:03d}": unit.evidence_id
        for index, unit in enumerate(evidence, start=1)
    }


def bind_manifest_evidence_handles(
    manifest: ClaimManifest,
    handle_mapping: dict[str, str],
) -> ClaimManifest:
    """Resolve exact handles; reject every value outside the request map."""
    claims: list[GeneratedClaim] = []
    for claim in manifest.claims:
        statements: list[ClaimStatement] = []
        for statement in claim.statements:
            supports: list[ClaimSupport] = []
            for support in statement.supports:
                canonical_id = handle_mapping.get(support.evidence_id)
                if canonical_id is None:
                    raise UnknownEvidenceHandleError(
                        f"unknown evidence handle: {support.evidence_id}"
                    )
                supports.append(ClaimSupport(evidence_id=canonical_id))
            statements.append(
                ClaimStatement(
                    claim_text=statement.claim_text,
                    paper_id=statement.paper_id,
                    supports=tuple(supports),
                )
            )
        claims.append(
            GeneratedClaim(
                facet=claim.facet,
                is_comparative=claim.is_comparative,
                statements=tuple(statements),
            )
        )
    return ClaimManifest(claims=tuple(claims))


def sanitize_internal_citations(text: str) -> str:
    """Rewrite raw PDF bracket citations out of the reference-index namespace.

    ``[27]`` -> ``(source-ref 27)``, ``[9,16,18]`` -> ``(source-ref 9,16,18)``.
    """

    def _replace(match: re.Match[str]) -> str:
        return f"(source-ref {match.group(1)})"

    return _INTERNAL_CITATION.sub(_replace, text or "")


def build_references_block(evidence: Sequence[EvidenceUnit]) -> str:
    """Render evidence with deterministic prompt-local handles."""
    handle_mapping = build_evidence_handle_mapping(evidence)
    return json.dumps(
        [
            {
                "evidence_id": handle,
                "paper_id": str(unit.paper_id),
                "title": unit.title or "",
                "text": unit.text,
            }
            for handle, unit in zip(handle_mapping, evidence)
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

EvidenceUnits:
{references}

Question:
{question}

Requested facets:
{requested_facets}

Return exactly one JSON object with this shape and no extra fields:
{{"claims":[{{"facet":"<requested facet>","is_comparative":false,"statements":[{{"claim_text":"<one factual statement>","paper_id":"<selected paper UUID>","supports":[{{"evidence_id":"<exact E### handle>"}}]}}]}}]}}

SUPPORTS FORMAT — EXACT

Valid:
{{
  "supports": [
    {{
      "evidence_id": "E001"
    }}
  ]
}}

Invalid — string evidence IDs:
{{
  "supports": ["E001"]
}}

Invalid — extra fields or explanations inside support objects:
{{
  "supports": [
    {{
      "evidence_id": "E001",
      "reason": "..."
    }}
  ]
}}

- supports must always be an array of objects.
- Each support object must contain exactly one key: evidence_id.
- Never add reason, explanation, support_quote, quoted text, or any additional key.
- Never put explanations, quotes, or natural language inside supports.
- Never wrap JSON output in Markdown fences.
- Return no commentary outside the single JSON object.

Rules:
- Every factual statement must have at least one support item.
- Do not emit bracket-number citations inside claim_text.
- Copy only exact E### evidence handles and paper IDs present above.
- A non-comparative claim has exactly one statement.
- A comparative claim has one explicit statement per compared paper, with distinct paper_id values and support from each paper.
- Do not use outside knowledge. Omit claims lacking support from the listed EvidenceUnits.
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
