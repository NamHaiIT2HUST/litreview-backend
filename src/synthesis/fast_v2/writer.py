"""Grounded literature writer over semantic-supported Fast v2 claims only.

Writer receives no EvidenceUnits, chunks, PDFs, retrieval context, or rejected
claims. Its claim-ID output is validated fail-closed, then projected onto the
already provenance-validated supports consumed by existing P-165 finalizer.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Protocol, Sequence, runtime_checkable
from uuid import UUID

from src.synthesis.fast_v2.evidence.bank import GroundedEvidenceBank
from src.synthesis.fast_v2.grounding.interface import GroundedDraft
from src.synthesis.fast_v2.grounding.manifest import (
    ValidatedClaim,
    ValidatedStatement,
    ValidatedSupport,
)
from src.synthesis.fast_v2.grounding.semantic import (
    SemanticVerificationOutcome,
    SemanticVerdict,
    build_finalizer_draft,
)


WRITER_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "grounded_literature_writer.txt"
)
# 6000 truncated a real 4,000-6,000 word review mid-sentence (~3,192 words /
# ~6,844 completion tokens observed in one production run). Raised so the
# writer's single call has enough budget for the full structured JSON output.
# Overridable per-instance; see src/config.py::fast_v2_writer_max_tokens.
WRITER_MAX_TOKENS = 12000
NEUTRAL_SECTION_TITLES = {
    "literature synthesis",
    "thematic synthesis",
    "cross-study synthesis",
    "overview",
}
NEUTRAL_SECTION_CATEGORY_TERMS = {
    "analysis",
    "application",
    "applications",
    "approach",
    "approaches",
    "assumption",
    "assumptions",
    "characteristic",
    "characteristics",
    "dataset",
    "datasets",
    "evaluation",
    "evaluations",
    "experiment",
    "experiments",
    "finding",
    "findings",
    "formulation",
    "formulations",
    "limitation",
    "limitations",
    "method",
    "methodology",
    "methods",
    "model",
    "models",
    "outcome",
    "outcomes",
    "result",
    "results",
    "setting",
    "settings",
    "synthesis",
}
UNSUPPORTED_SECTION_TITLE_TERMS = {
    "advance",
    "advances",
    "advancement",
    "advancements",
    "best",
    "better",
    "breakthrough",
    "breakthroughs",
    "evolution",
    "evolutionary",
    "future",
    "historical",
    "history",
    "improvement",
    "improvements",
    "progress",
    "roadmap",
    "roadmaps",
    "superior",
    "superiority",
}


class LiteratureWriterError(RuntimeError):
    """Writer request or output contract failed without breaking synthesis."""


class WriterValidationError(LiteratureWriterError):
    def __init__(self, reason: str, *, coverage: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.coverage = coverage


@dataclass(frozen=True)
class WriterClaim:
    claim_id: str
    facet: str
    claim_text: str
    paper_id: UUID
    paper_title: str
    evidence_snippets: tuple[dict[str, Any], ...] = ()

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "facet": self.facet,
            "claim_text": self.claim_text,
            "paper_id": str(self.paper_id),
            "paper_title": self.paper_title,
            "evidence_snippets": [dict(item) for item in self.evidence_snippets],
        }


@dataclass(frozen=True)
class WriterGeneration:
    content: str
    calls: int = 1
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class GroundedLiteratureWriter(Protocol):
    def write(
        self,
        claims: tuple[WriterClaim, ...],
        *,
        outline: Any | None = None,
    ) -> WriterGeneration:
        ...


@dataclass(frozen=True)
class WriterParagraph:
    text: str
    supporting_claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class WriterSection:
    title: str
    paragraphs: tuple[WriterParagraph, ...]


@dataclass(frozen=True)
class WriterDocument:
    sections: tuple[WriterSection, ...]


@dataclass(frozen=True)
class LiteratureWriterOutcome:
    finalizer_draft: GroundedDraft
    writer_calls: int
    writer_latency_ms: float | None
    writer_input_tokens: int | None
    writer_output_tokens: int | None
    writer_fallback_reason: str | None
    claim_coverage: dict[str, Any]
    document: WriterDocument | None = None


class DeterministicFakeLiteratureWriter:
    """CPU-only writer double. Never opens a network connection."""

    def __init__(
        self,
        *,
        content: str = "",
        error: Exception | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        self.content = content
        self.error = error
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = 0
        self.last_claims: tuple[WriterClaim, ...] = ()

    def write(
        self, claims: tuple[WriterClaim, ...], *, outline: Any | None = None
    ) -> WriterGeneration:
        self.calls += 1
        self.last_claims = claims
        if self.error is not None:
            raise self.error
        return WriterGeneration(
            content=self.content,
            calls=1,
            latency_ms=0.0,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


class HostedGroundedLiteratureWriter:
    """One-call OpenAI-compatible writer. No retry and no evidence payload."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = WRITER_MAX_TOKENS,
        connect_timeout_s: float = 10.0,
        generation_timeout_s: float = 120.0,
        http_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        missing = [
            name
            for name, value in (
                ("base_url", base_url),
                ("api_key", api_key),
                ("model", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "HostedGroundedLiteratureWriter requires " + ", ".join(missing)
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.connect_timeout_s = connect_timeout_s
        self.generation_timeout_s = generation_timeout_s
        self.http_client_factory = http_client_factory
        self.calls = 0

    def _client(self) -> Any:
        if self.http_client_factory is not None:
            return self.http_client_factory()
        import httpx

        return httpx.Client(
            timeout=httpx.Timeout(
                connect=self.connect_timeout_s,
                read=self.generation_timeout_s,
                write=self.generation_timeout_s,
                pool=self.connect_timeout_s,
            )
        )

    def write(
        self, claims: tuple[WriterClaim, ...], *, outline: Any | None = None
    ) -> WriterGeneration:
        self.calls += 1
        system_prompt = WRITER_PROMPT_PATH.read_text(encoding="utf-8")
        min_sections = 3 if len(claims) >= 4 else 1

        outline_context = ""
        if outline is not None and getattr(outline, "sections", None):
            outline_lines = "\n".join(
                f"- \"{section.title}\": {section.purpose} (target ~{section.target_words} words)"
                for section in outline.sections
            )
            outline_context = (
                "RESEARCH LEAD OUTLINE -- follow this section structure and use "
                "these exact section titles (one per section, in this order where "
                "the supplied claims allow it):\n" + outline_lines + "\n\n"
            )

        user_prompt = (
            "NON-NEGOTIABLE OUTPUT LANGUAGE: Vietnamese. Every section title and "
            "every prose sentence must be Vietnamese. Do not answer in English. "
            "Retain only necessary technical terms or formulae in their original notation. "
            "Use every supplied claim_id exactly once. Create at least "
            f"{min_sections} thematic sections. A paragraph may cite at most two "
            "claim_ids, and must not become a list of every claim. Section titles "
            "must describe their supplied facets. Return only required JSON.\n\n"
            + outline_context
            + "VERIFIED CLAIMS:\n"
            + json.dumps(
                [claim.to_prompt_dict() for claim in claims],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        started = time.perf_counter()
        try:
            response = self._client().post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except Exception as exc:
            raise LiteratureWriterError(
                f"writer request failed: {type(exc).__name__}"
            ) from exc
        latency_ms = (time.perf_counter() - started) * 1000.0
        if response.status_code != 200:
            detail = response.text.strip().replace("\n", " ")[:240]
            raise LiteratureWriterError(
                f"writer returned HTTP {response.status_code}: {detail}"
            )
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LiteratureWriterError("writer returned malformed response") from exc
        if not isinstance(content, str) or not content.strip():
            raise LiteratureWriterError("writer returned empty content")
        usage = data.get("usage") or {}
        return WriterGeneration(
            content=content,
            calls=1,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )


def _writer_claim_sources(
    semantic: SemanticVerificationOutcome,
    evidence_bank: GroundedEvidenceBank,
) -> tuple[tuple[WriterClaim, ...], dict[str, ValidatedStatement]]:
    titles_by_paper = {
        unit.paper_id: unit.title for unit in evidence_bank.evidence
    }
    units_by_evidence_id = {
        unit.evidence_id: unit for unit in evidence_bank.evidence
    }
    results = {
        (item.claim_index, item.statement_index): item
        for item in semantic.verification_results
    }
    claims: list[WriterClaim] = []
    sources: dict[str, ValidatedStatement] = {}
    for claim_index, claim in enumerate(semantic.original_draft.validated_claims):
        for statement_index, statement in enumerate(claim.statements):
            result = results.get((claim_index, statement_index))
            if result is None or result.verdict is not SemanticVerdict.supported:
                continue
            claim_id = f"claim_{claim_index}_{statement_index}"
            snippets: list[dict[str, Any]] = []
            for support in statement.supports:
                unit = units_by_evidence_id.get(support.evidence_id)
                if unit is not None:
                    snippets.append({
                        "evidence_id": unit.evidence_id,
                        "page": unit.page,
                        "text": unit.text,
                    })
            claims.append(
                WriterClaim(
                    claim_id=claim_id,
                    facet=claim.facet,
                    claim_text=statement.claim_text,
                    paper_id=statement.paper_id,
                    paper_title=titles_by_paper.get(statement.paper_id, "Selected paper"),
                    evidence_snippets=tuple(snippets),
                )
            )
            sources[claim_id] = statement
    return tuple(claims), sources


def _coverage(expected_ids: Sequence[str], referenced_ids: Sequence[str]) -> dict[str, Any]:
    counts = Counter(referenced_ids)
    expected = list(expected_ids)
    missing = [claim_id for claim_id in expected if claim_id not in counts]
    duplicates = sorted(
        claim_id for claim_id, count in counts.items() if count > 1
    )
    return {
        "expected": len(expected),
        "used_unique": len(set(referenced_ids) & set(expected)),
        "references_total": len(referenced_ids),
        "missing": missing,
        "duplicates": duplicates,
        "coverage_percent": (
            round(100.0 * (len(expected) - len(missing)) / len(expected), 3)
            if expected
            else 100.0
        ),
    }


def _is_neutral_academic_section_title(normalized_title: str) -> bool:
    if normalized_title in NEUTRAL_SECTION_TITLES:
        return True
    words = re.findall(r"[\w\d]+", normalized_title, re.UNICODE)
    if not words or len(words) > 20:
        return False
    # Any word from the historical/evaluative/hype blocklist is a hard
    # reject, regardless of what else is in the title -- these are exactly
    # the claim types this pipeline has no evidence to ground (see
    # UNSUPPORTED_SECTION_TITLE_TERMS' own comment).
    if any(word in UNSUPPORTED_SECTION_TITLE_TERMS for word in words):
        return False
    # Otherwise require at least one word from the neutral academic-category
    # allowlist, so an arbitrary/creative title (no evidence it's a genuine
    # structural section like "Methods" or "Limitations") doesn't pass just
    # by avoiding the blocklist.
    return any(word in NEUTRAL_SECTION_CATEGORY_TERMS for word in words)


def _canonical_facet_label(value: str) -> str:
    return re.sub(r"\s+", "_", value.strip().casefold())


def _parse_and_validate(
    content: str,
    claims: tuple[WriterClaim, ...],
) -> tuple[WriterDocument, dict[str, Any]]:
    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise WriterValidationError("invalid_json") from exc
    if isinstance(payload, dict) and isinstance(payload.get("sections"), list):
        normalized_sections = []
        for section in payload["sections"]:
            if (
                isinstance(section, dict)
                and "section_title" in section
                and "title" not in section
            ):
                section = dict(section)
                section["title"] = section.pop("section_title")
            normalized_sections.append(section)
        payload = {**payload, "sections": normalized_sections}
    if not isinstance(payload, dict) or set(payload) != {"sections"}:
        raise WriterValidationError("invalid_schema")
    raw_sections = payload["sections"]
    if not isinstance(raw_sections, list) or not raw_sections:
        raise WriterValidationError("invalid_schema")

    claims_by_id = {claim.claim_id: claim for claim in claims}
    allowed_facet_titles = {_canonical_facet_label(claim.facet) for claim in claims}
    referenced: list[str] = []
    sections: list[WriterSection] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict) or set(raw_section) != {
            "title",
            "paragraphs",
        }:
            raise WriterValidationError("invalid_schema")
        title = raw_section["title"]
        raw_paragraphs = raw_section["paragraphs"]
        if not isinstance(title, str) or not title.strip():
            raise WriterValidationError("invalid_schema")
        normalized_title = title.replace("_", " ").strip().casefold()
        canonical_title = _canonical_facet_label(title)
        is_facet_title = canonical_title in allowed_facet_titles
        is_neutral_title = _is_neutral_academic_section_title(normalized_title)
        if not is_facet_title and not is_neutral_title:
            raise WriterValidationError("unsupported_section_title")
        if not isinstance(raw_paragraphs, list) or not raw_paragraphs:
            raise WriterValidationError("invalid_schema")

        paragraphs: list[WriterParagraph] = []
        section_facets: set[str] = set()
        for raw_paragraph in raw_paragraphs:
            if not isinstance(raw_paragraph, dict) or set(raw_paragraph) != {
                "text",
                "supporting_claim_ids",
            }:
                raise WriterValidationError("invalid_schema")
            text = raw_paragraph["text"]
            claim_ids = raw_paragraph["supporting_claim_ids"]
            if not isinstance(text, str) or not text.strip():
                raise WriterValidationError("invalid_schema")
            if (
                not isinstance(claim_ids, list)
                or not claim_ids
                or not all(isinstance(claim_id, str) for claim_id in claim_ids)
            ):
                raise WriterValidationError("invalid_schema")
            if len(claim_ids) > 2:
                raise WriterValidationError("paragraph_claims_too_many")
            unknown = [claim_id for claim_id in claim_ids if claim_id not in claims_by_id]
            if unknown:
                coverage = _coverage(tuple(claims_by_id), (*referenced, *claim_ids))
                raise WriterValidationError("unknown_claim_id", coverage=coverage)
            paragraph_facets = {claims_by_id[claim_id].facet for claim_id in claim_ids}
            if len(paragraph_facets) > 1:
                raise WriterValidationError("mixed_facet_paragraph")
            section_facets.update(paragraph_facets)
            referenced.extend(claim_ids)
            paragraphs.append(
                WriterParagraph(
                    text=text.strip(),
                    supporting_claim_ids=tuple(claim_ids),
                )
            )
        sections.append(WriterSection(title=title.strip(), paragraphs=tuple(paragraphs)))

    coverage = _coverage(tuple(claims_by_id), referenced)
    if coverage["duplicates"]:
        raise WriterValidationError("duplicate_claim_id", coverage=coverage)
    if coverage["missing"]:
        raise WriterValidationError("missing_claim_coverage", coverage=coverage)
    min_sections = 3 if len(claims) >= 4 else 1
    if len(sections) < min_sections:
        raise WriterValidationError("insufficient_thematic_sections", coverage=coverage)
    return WriterDocument(sections=tuple(sections)), coverage


def _project_document(
    *,
    document: WriterDocument,
    claims: tuple[WriterClaim, ...],
    sources: dict[str, ValidatedStatement],
    fallback_draft: GroundedDraft,
) -> GroundedDraft:
    claims_by_id = {claim.claim_id: claim for claim in claims}
    projected: list[ValidatedClaim] = []
    for section in document.sections:
        for paragraph in section.paragraphs:
            source_statements = [sources[claim_id] for claim_id in paragraph.supporting_claim_ids]
            supports: list[ValidatedSupport] = []
            seen_evidence_ids: set[str] = set()
            for statement in source_statements:
                for support in statement.supports:
                    if support.evidence_id in seen_evidence_ids:
                        continue
                    seen_evidence_ids.add(support.evidence_id)
                    supports.append(support)
            paper_ids = {statement.paper_id for statement in source_statements}
            projected.append(
                ValidatedClaim(
                    # Finalizer uses facet as display grouping. Preserve writer's
                    # approved thematic title instead of collapsing every section
                    # back into its retrieval facet.
                    facet=section.title,
                    is_comparative=len(paper_ids) > 1,
                    statements=(
                        ValidatedStatement(
                            claim_text=paragraph.text,
                            paper_id=source_statements[0].paper_id,
                            supports=tuple(supports),
                        ),
                    ),
                )
            )
    return replace(fallback_draft, validated_claims=tuple(projected))


def apply_grounded_literature_writer(
    *,
    semantic: SemanticVerificationOutcome,
    evidence_bank: GroundedEvidenceBank,
    writer: GroundedLiteratureWriter | None,
    outline: Any | None = None,
) -> LiteratureWriterOutcome:
    """Run at most one writer call; every failure preserves current output."""
    fallback_draft = build_finalizer_draft(semantic)
    claims, sources = _writer_claim_sources(semantic, evidence_bank)
    empty_coverage = _coverage([claim.claim_id for claim in claims], ())
    if writer is None:
        return LiteratureWriterOutcome(
            finalizer_draft=fallback_draft,
            writer_calls=0,
            writer_latency_ms=None,
            writer_input_tokens=None,
            writer_output_tokens=None,
            writer_fallback_reason="writer_unavailable",
            claim_coverage=empty_coverage,
        )
    if not claims:
        return LiteratureWriterOutcome(
            finalizer_draft=fallback_draft,
            writer_calls=0,
            writer_latency_ms=None,
            writer_input_tokens=None,
            writer_output_tokens=None,
            writer_fallback_reason="no_supported_claims",
            claim_coverage=empty_coverage,
        )

    generation: WriterGeneration | None = None
    try:
        generation = writer.write(claims, outline=outline)
        if generation.calls != 1:
            raise LiteratureWriterError(
                f"writer_call_count_mismatch:{generation.calls}"
            )
        document, coverage = _parse_and_validate(generation.content, claims)
        finalizer_draft = _project_document(
            document=document,
            claims=claims,
            sources=sources,
            fallback_draft=fallback_draft,
        )
        return LiteratureWriterOutcome(
            finalizer_draft=finalizer_draft,
            writer_calls=1,
            writer_latency_ms=generation.latency_ms,
            writer_input_tokens=generation.input_tokens,
            writer_output_tokens=generation.output_tokens,
            writer_fallback_reason=None,
            claim_coverage=coverage,
            document=document,
        )
    except Exception as exc:
        coverage = (
            exc.coverage
            if isinstance(exc, WriterValidationError) and exc.coverage is not None
            else empty_coverage
        )
        return LiteratureWriterOutcome(
            finalizer_draft=fallback_draft,
            writer_calls=int(getattr(writer, "calls", 1) or 1),
            writer_latency_ms=(
                None if generation is None else generation.latency_ms
            ),
            writer_input_tokens=(
                None if generation is None else generation.input_tokens
            ),
            writer_output_tokens=(
                None if generation is None else generation.output_tokens
            ),
            writer_fallback_reason=f"{type(exc).__name__}: {exc}",
            claim_coverage=coverage,
        )
