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
from collections.abc import Sequence

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

    return f"""You are an elite scientific research synthesis assistant. Use only the provided EvidenceUnits.

EvidenceUnits:
{references}

Question:
{question}

Requested facets:
{requested_facets}

Synthesis Guidance:
- Analyze the user question and the collection of EvidenceUnits.
- Capture dialectical relationships (how later models resolve earlier bottlenecks, relax assumptions, generalize formulations, or trade off efficiency) whenever supported by the evidence.
- Prioritize comparative and multi-perspective claims across papers where evidence allows.

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


NATURAL_WRITER_SYSTEM_PROMPT = """You are a rigorous academic scholar writing a comparative literature review section.
Your task is to write a comprehensive, well-structured literature review answering the research question based strictly on the provided evidence passages.

Writing & Grounding Invariants:
1. Strict Attribution & Separation of Contributions:
   - Attribute every paper-specific claim (formulation, theorem, algorithmic step, operator property, optimization framing, or interpretation) strictly to the paper whose supplied evidence directly supports it.
   - Do NOT transfer or back-project a formulation, theorem, property, or theoretical interpretation from one paper to another (e.g., Xu (2010) identified CQ as a special case of gradient-projection, not Byrne (2002)).
   - Keep the mathematical formulation of each paper faithful to its own evidence passage.
   - Use exact source terminology (e.g., "largest eigenvalue of A^T A", not "spectral radius").
2. No Extrapolations or Unstated Mechanisms:
   - Do NOT invent explanations, mechanisms, or consequences not explicitly present in the evidence passages.
   - Do NOT claim that "gamma ensures nonexpansiveness" (state only that gamma is chosen in (0, 2/L) where L is the largest eigenvalue of A^T A, and the algorithm converges).
   - Do NOT claim that "regularization provides stronger convergence" or "addresses multiple solutions" (state only that regularization and iterative algorithms are introduced to find the minimum-norm solution of the SFP, exactly as written).
   - Do NOT claim that "strong convergence requires additional assumptions" (state only that CQ has weak convergence in general in infinite-dimensional settings).
   - Do NOT invent trade-offs such as "flexibility at the cost of computational complexity".
   - SYNTHESIS may only combine, compare, contrast, or organize facts already supported by the supplied evidence. It must NOT introduce unevidenced implications or domain assumptions.
   - If a statement requires outside mathematical/domain knowledge to justify it, OMIT it.
3. STRICTLY CITATION-FREE PROSE: Write the literature review in fluent academic prose. Do NOT include evidence IDs, citation handles, [E###] markers, provenance IDs, bracketed numbers, or internal source identifiers in the text. Citation attribution will be performed by a separate post-hoc stage. Refer to papers naturally by author names and publication years (e.g. "Censor and Elfving (1994) introduced...", "Byrne (2002) proposed...", "Xu (2010) extended...").
4. Format: Write continuous academic Markdown with clear paragraph structure and headers where appropriate."""


def format_evidence_context(evidence: Sequence[EvidenceUnit]) -> tuple[str, dict[str, str]]:
    """Format top evidence units into handled context and return handle mapping."""
    handle_mapping = build_evidence_handle_mapping(evidence)

    parts: list[str] = []
    for handle, unit in zip(handle_mapping.keys(), evidence):
        parts.append(
            f"--- [{handle}] (Source: {unit.title}, Page {unit.page}) ---\n"
            f"{unit.text.strip()}"
        )
    return "\n\n".join(parts), handle_mapping


def format_evidence_context_for_writer(evidence: Sequence[EvidenceUnit]) -> str:
    """Format evidence context for the Writer without [E###] handles to enforce citation-free prose."""
    parts: list[str] = []
    for idx, unit in enumerate(evidence, start=1):
        parts.append(
            f"--- Document Source {idx}: {unit.title} (Page {unit.page}) ---\n"
            f"{unit.text.strip()}"
        )
    return "\n\n".join(parts)


def build_natural_cited_writer_prompt(question: str, evidence: Sequence[EvidenceUnit]) -> tuple[str, str, dict[str, str]]:
    """Build system and human prompts for natural citation-free literature review writing."""
    writer_context = format_evidence_context_for_writer(evidence)
    handle_mapping = build_evidence_handle_mapping(evidence)
    human_prompt = f"""Research Question:
{question}

Supplied Evidence Pack:
{writer_context}

Write a thorough comparative literature review answering the research question. Adhere strictly to the academic writing, grounding, and citation-free rules."""
    return NATURAL_WRITER_SYSTEM_PROMPT, human_prompt, handle_mapping
