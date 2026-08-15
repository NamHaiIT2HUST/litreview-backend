"""Structured-output LLM adapter for literature synthesis.

Nodes and business services depend on this adapter instead of importing a
specific provider directly.  Every synthesis step uses a Pydantic schema.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterable
from uuid import UUID

from src.config import get_settings
from src.models.db_models import LLMCallLog
from src.services.synthesis_coverage_policy import dimension_extraction_rules
from src.models.synthesis_schemas import (
    ClaimVerificationBatchOutput,
    ClaimVerificationDecision,
    EntailmentDecision,
    EvidenceExtractionBatch,
    PaperEvidenceExtractionOutput,
    EvidenceDeduplicationBatch,
    SectionDraftOutput,
    SynthesisClaimProposalBatch,
    SynthesisOutlineOutput,
    EvidenceDimension,
    ReviewQABatchOutput,
)

_TRACE_CONTEXT: ContextVar[tuple[object, UUID, str] | None] = ContextVar("synthesis_llm_trace", default=None)


@contextmanager
def llm_trace(db, session_id: UUID, step_name: str):
    token = _TRACE_CONTEXT.set((db, session_id, step_name))
    try:
        yield
    finally:
        _TRACE_CONTEXT.reset(token)


def create_synthesis_llm(settings, *, gemini_cls=None, groq_cls=None, openai_cls=None):
    """Create the configured synthesis chat model without making a network call."""
    provider = settings.synthesis_llm_provider.lower().strip()
    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("Groq synthesis requires GROQ_API_KEY in .env.")
        if groq_cls is None:
            from langchain_groq import ChatGroq  # type: ignore

            groq_cls = ChatGroq
        return groq_cls(
            model=settings.synthesis_model,
            api_key=settings.groq_api_key,
            temperature=settings.synthesis_temperature,
            max_tokens=8192,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI synthesis requires OPENAI_API_KEY in .env.")
        if openai_cls is None:
            from langchain_openai import ChatOpenAI

            openai_cls = ChatOpenAI
        return openai_cls(
            model=settings.synthesis_model,
            api_key=settings.openai_api_key,
            temperature=settings.synthesis_temperature,
            max_tokens=4096,
        )

    if provider == "gemini":
        gemini_key = settings.gemini_api_key or settings.google_api_key
        if not gemini_key:
            raise RuntimeError(
                "Gemini synthesis requires GEMINI_API_KEY or GOOGLE_API_KEY in .env."
            )
        if gemini_cls is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            gemini_cls = ChatGoogleGenerativeAI
        return gemini_cls(
            model=settings.synthesis_model,
            google_api_key=gemini_key,
            temperature=settings.synthesis_temperature,
        )

    raise RuntimeError("SYNTHESIS_LLM_PROVIDER must be 'gemini', 'groq', or 'openai'.")


def _is_transient_provider_error(exc: BaseException) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429 or (isinstance(status_code, int) and status_code >= 500):
        return True
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return (
        any(token in name for token in ("timeout", "connection", "ratelimit"))
        or "503 unavailable" in message
        or "high demand" in message
        or "resource_exhausted" in message
        or "429" in message
    )


class SynthesisLLMService:
    def __init__(self, llm=None, *, max_concurrency=None, retry_delays=(2.0, 5.0, 10.0, 20.0)):
        self._llm = llm
        settings = get_settings()
        self._max_concurrency = max_concurrency or settings.synthesis_llm_max_concurrency
        self._semaphore = None
        self._semaphore_loop = None
        self._retry_delays = tuple(retry_delays)
        self._active_invocations = 0
        self._max_active_invocations = 0

    def concurrency_snapshot(self) -> dict[str, int]:
        """Return provider invocation concurrency counters for instrumentation."""
        return {
            "active_invocations": self._active_invocations,
            "max_active_invocations": self._max_active_invocations,
            "configured_max_concurrency": self._max_concurrency,
        }

    def _get_semaphore(self):
        current_loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop is not current_loop:
            self._semaphore = asyncio.Semaphore(self._max_concurrency)
            self._semaphore_loop = current_loop
        return self._semaphore

    def _get_llm(self):
        if self._llm is not None:
            return self._llm

        self._llm = create_synthesis_llm(get_settings())
        return self._llm

    def validate_configuration(self) -> None:
        self._get_llm()

    async def _invoke_structured(self, schema, *, system: str, human: str):
        llm = self._get_llm()
        if getattr(llm, "_llm_type", None) == "openai-chat" or type(llm).__name__ == "ChatOpenAI":
            runner = llm.with_structured_output(schema, method="json_schema", strict=True)
        else:
            runner = llm.with_structured_output(schema)
        messages = [("system", system), ("human", human)]
        for attempt in range(len(self._retry_delays) + 1):
            started = time.perf_counter()
            try:
                async with self._get_semaphore():
                    self._active_invocations += 1
                    self._max_active_invocations = max(
                        self._max_active_invocations, self._active_invocations
                    )
                    try:
                        response = await runner.ainvoke(messages)
                    finally:
                        self._active_invocations -= 1
                trace = _TRACE_CONTEXT.get()
                if trace:
                    db, session_id, step_name = trace
                    db.add(LLMCallLog(
                        session_id=session_id, step_name=step_name,
                        model_name=get_settings().model_name, attempt=attempt + 1,
                        duration_ms=int((time.perf_counter() - started) * 1000), status="success",
                        prompt_json={"system": system, "human": human},
                        response_json=response.model_dump(mode="json") if hasattr(response, "model_dump") else {"value": str(response)},
                    ))
                return response
            except Exception as exc:
                trace = _TRACE_CONTEXT.get()
                if trace:
                    db, session_id, step_name = trace
                    db.add(LLMCallLog(
                        session_id=session_id, step_name=step_name,
                        model_name=get_settings().model_name, attempt=attempt + 1,
                        duration_ms=int((time.perf_counter() - started) * 1000), status="error",
                        prompt_json={"system": system, "human": human}, error=str(exc)[:4000],
                    ))
                if attempt >= len(self._retry_delays) or not _is_transient_provider_error(exc):
                    raise
                await asyncio.sleep(self._retry_delays[attempt])
        raise RuntimeError("unreachable")

    async def extract_evidence(
        self,
        *,
        research_question: str,
        dimension: EvidenceDimension,
        indexed_chunks: Iterable[tuple[UUID, str]],
        exact_quote_only: bool,
    ) -> EvidenceExtractionBatch:
        dimension = dimension if isinstance(dimension, EvidenceDimension) else EvidenceDimension(dimension)
        dimension_value = dimension.value
        dimension_rules = dimension_extraction_rules(dimension)
        context = "\n\n".join(
            f"[anchor_chunk_id={chunk_id}]\n{text}" for chunk_id, text in indexed_chunks
        )
        quote_rule = (
            "This is a retry after grounding failed. The quote MUST be copied verbatim "
            "from one supplied continuous raw page window; do not paraphrase, normalize, or repair wording."
            if exact_quote_only
            else "The quote MUST be copied verbatim from a supplied continuous raw page window."
        )
        return await self._invoke_structured(
            EvidenceExtractionBatch,
            system=(
                "You extract auditable evidence from academic papers. Return at most 3 "
                "evidence items for the requested dimension. Each item must cite exactly "
                "one provided anchor_chunk_id as source_chunk_id. A quote may cross the anchor "
                "chunk boundary. Set applies_to to proposed_method, study, baseline, or general "
                "to identify the subject of the evidence. "
                "Each supplied context is a continuous raw page window. "
                "If the context does not contain evidence, return "
                "an empty items list. For a general literature review, treat paper-specific "
                "objectives, methods, findings, and limitations as useful evidence even when "
                "other papers use different terminology. When relevant text exists, return at "
                "least one item and copy the shortest complete supporting quote exactly. "
                "Never infer missing information. " + quote_rule
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Dimension:\n{dimension_value}\n\n"
                f"Dimension-specific rules:\n{dimension_rules}\n\n"
                f"Context:\n{context}"
            ),
        )

    async def propose_claims(self, *, research_question: str, evidence_context: str) -> SynthesisClaimProposalBatch:
        return await self._invoke_structured(
            SynthesisClaimProposalBatch,
            system=(
                "You perform cross-paper literature synthesis from grounded evidence only. "
                "Create concise claims representing agreement, disagreement, comparison, "
                "trend, gap, or descriptive patterns. Every claim must reference one or "
                "more supplied evidence IDs. Each evidence item identifies its paper; retain "
                "explicit evidence links so comparative claims are auditable. When the supplied "
                "evidence defensibly supports it, prefer multi-paper claims for agreements, "
                "contrasts, methodological or evaluation differences, trade-offs, shared limitations, "
                "and research gaps. A comparative claim must use evidence from at least two papers. "
                "Do not fabricate relationships solely to increase multi-paper coverage. Single-paper "
                "claims remain valid when no defensible cross-paper relation exists. Different topics "
                "do not justify dropping a paper: describe its contribution independently. "
                "Do not introduce facts absent from evidence."
            ),
            human=f"Research question:\n{research_question}\n\nGrounded evidence:\n{evidence_context}",
        )

    async def verify_entailment(self, *, claim_statement: str, evidence_value: str, evidence_quote: str) -> EntailmentDecision:
        return await self._invoke_structured(
            EntailmentDecision,
            system=(
                "Judge whether the given evidence supports the exact synthesis claim. "
                "Use supported, contradicted, or insufficient. The label is relative to "
                "this claim statement, not an absolute truth judgment. Be conservative."
            ),
            human=(
                f"Claim:\n{claim_statement}\n\n"
                f"Interpreted evidence value:\n{evidence_value}\n\n"
                f"Verbatim evidence quote:\n{evidence_quote}"
            ),
        )

    async def verify_claim_set(
        self,
        *,
        claim_statement: str,
        evidence_items: Iterable[tuple[UUID, str, str]],
    ) -> ClaimVerificationDecision:
        evidence_context = "\n\n".join(
            f"[evidence_id={evidence_id}]\n"
            f"Interpretation: {value}\n"
            f"Verbatim quote: {quote}"
            for evidence_id, value, quote in evidence_items
        )
        return await self._invoke_structured(
            ClaimVerificationDecision,
            system=(
                "Verify the exact synthesis claim against the supplied grounded evidence "
                "AS A SET. Cross-paper claims may require multiple studies jointly (for "
                "example, two different findings can jointly support a disagreement claim). "
                "Return supported, contradicted, or insufficient and list only supplied "
                "evidence IDs that materially participate in the verdict. Never invent IDs."
            ),
            human=(
                f"Claim:\n{claim_statement}\n\n"
                f"Grounded evidence set:\n{evidence_context}"
            ),
        )

    async def verify_claim_set_batch(
        self,
        *,
        claims_with_evidence: Iterable[
            tuple[UUID, str, Iterable[tuple[UUID, str, str]]]
        ],
    ) -> ClaimVerificationBatchOutput:
        contexts = []
        for claim_id, statement, evidence_items in claims_with_evidence:
            evidence_context = "\n\n".join(
                f"[evidence_id={evidence_id}]\nInterpretation: {value}\n"
                f"Verbatim quote: {quote}"
                for evidence_id, value, quote in evidence_items
            )
            contexts.append(
                f"[claim_id={claim_id}]\nClaim: {statement}\n"
                f"Allowed grounded evidence for this claim:\n{evidence_context}"
            )
        return await self._invoke_structured(
            ClaimVerificationBatchOutput,
            system=(
                "Verify every exact synthesis claim against its own grounded evidence set. "
                "For every claim return its claim_id, supported, contradicted, or insufficient, "
                "a reason, and only evidence IDs listed inside that claim. Never borrow evidence "
                "from another claim and never invent IDs."
            ),
            human="\n\n--- NEXT CLAIM ---\n\n".join(contexts),
        )

    async def extract_paper_evidence_batch(
        self,
        *,
        research_question: str,
        contexts_by_dimension: dict[EvidenceDimension, Iterable[tuple[UUID, str]]],
        strict_dimension_ids: bool = False,
        enforce_dimension_membership: bool | None = None,
        exact_quote_only: bool = False,
    ) -> PaperEvidenceExtractionOutput:
        if enforce_dimension_membership is None:
            enforce_dimension_membership = strict_dimension_ids
        contexts = []
        rules = []
        for raw_dimension, indexed_chunks in contexts_by_dimension.items():
            indexed_chunks = list(indexed_chunks)
            dimension = raw_dimension if isinstance(raw_dimension, EvidenceDimension) else EvidenceDimension(raw_dimension)
            rules.append(f"{dimension.value}: {dimension_extraction_rules(dimension)}")
            body = "\n\n".join(
                f"<source_chunk_id={chunk_id}>\n{text}\n</source_chunk>"
                for chunk_id, text in indexed_chunks
            )
            allowed_ids = ", ".join(str(chunk_id) for chunk_id, _text in indexed_chunks)
            id_rule = (
                f"\nAllowed source_chunk_id values for this dimension: {allowed_ids}\n"
                if strict_dimension_ids else ""
            )
            contexts.append(f"<dimension name={dimension.value}>\n{id_rule}{body}\n</dimension>")
        return await self._invoke_structured(
            PaperEvidenceExtractionOutput,
            system=(
                "Extract auditable evidence for all supplied literature-review dimensions in one "
                "response. Every item must name its dimension, copy a verbatim quote, identify its "
                "subject scope with applies_to, and use only a source_chunk_id supplied inside that "
                "same dimension. Return up to five independent grounded candidates per dimension; "
                "Copy a short contiguous span directly from exactly one selected source chunk, "
                "preferably one or two sentences. Do not paraphrase, correct OCR or grammar, "
                "add or remove words, insert ellipses such as '...', or combine neighboring chunks. "
                "an empty list is valid when the supplied context contains no author-stated support. "
                "For objective, extract explicit aims/purposes/research questions, not inferred goals. "
                "For limitations and future_work, accept only author-stated content and never infer or "
                "convert a weakness into future work. Preserve exact quote and anchor provenance. "
                + (
                    "This is a retry after grounding failed. The quote MUST be copied verbatim "
                    "from one supplied continuous raw page window; do not paraphrase, normalize, or repair wording. "
                    if exact_quote_only
                    else "The quote MUST be copied verbatim from a supplied continuous raw page window. "
                )
                + (
                    "Never use a source_chunk_id outside its allowed ID list for this dimension. "
                    if enforce_dimension_membership else
                    "A source_chunk_id may come from any supplied dimension block; use only IDs supplied in the paper prompt. "
                )
                + "\n\n"
                "Dimension rules:\n"
                + "\n".join(rules)
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                + "\n\n--- NEXT DIMENSION ---\n\n".join(contexts)
            ),
        )

    async def build_outline(self, *, research_question: str, claims_context: str) -> SynthesisOutlineOutput:
        return await self._invoke_structured(
            SynthesisOutlineOutput,
            system=(
                "Build a coherent academic literature-review outline from verified synthesis claims. "
                "Select ONLY claims directly relevant to the research question; omit unrelated claims "
                "even when they are supported by their source. Use only supplied claim IDs and assign "
                "each selected claim to at most one section. Choose section titles and count dynamically "
                "from the actual themes in the verified claims; do not force a fixed four-part template. "
                "When studies are too heterogeneous for meaningful cross-paper themes, organize them into "
                "honest per-paper or small thematic clusters. Every paper with a supported relevant claim "
                "must appear in at least one section. Prefer grouping verified multi-paper claims into "
                "thematic comparative sections when their evidence supports a defensible comparison. "
                "Do not force unrelated claims together or invent themes or background facts."
                " Respect the supplied evidence dimensions when assigning sections: claims backed "
                "by limitations evidence belong in a limitations/gaps section, and claims backed by "
                "future_work evidence belong in a future-directions section. If a claim has both, "
                "assign it once to the role most explicit in its wording."
            ),
            human=f"Research question:\n{research_question}\n\nVerified claims:\n{claims_context}",
        )

    async def draft_section(
        self,
        *,
        research_question: str,
        section_title: str,
        claims_context: str,
        suggested_length: str = "250-500 words",
    ) -> SectionDraftOutput:
        return await self._invoke_structured(
            SectionDraftOutput,
            system=(
                "Write an academic literature-review section using only the verified claims "
                "and evidence supplied. Return sentence-level structured output. Classify "
                "each sentence as claim or discourse. Claim sentences state scientific facts "
                "and must be directly entailed by their claim_ids. Discourse sentences may "
                "connect, introduce, or summarize supplied claims, but must not add new facts; "
                "they still list the claim_ids they derive from. Do not create citation markers."
                " Expand each verified claim: state the synthesized claim, compare or contrast "
                "supporting papers where possible, explain what the evidence demonstrates, and "
                "connect the claims at section level. Aim for the suggested section length of "
                f"{suggested_length} when the supplied evidence supports it; sparse sections may "
                "remain shorter and must never be padded. Every factual statement must remain "
                "grounded in the verified claims."
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Section title:\n{section_title}\n\n"
                f"Claims and evidence:\n{claims_context}"
            ),
        )

    async def qa_review_batch(self, *, qa_context: str) -> ReviewQABatchOutput:
        return await self._invoke_structured(
            ReviewQABatchOutput,
            system=(
                "You are the final evidence QA gate for an academic literature review. "
                "Use only the supplied sentence, claims, interpreted evidence, dimensions, "
                "subject scope, and exact quotes; do not use outside knowledge. Return one "
                "check for every sentence_id. Use blocked when a factual sentence is not "
                "entailed, cites the wrong evidence, or depends on dimension/subject mismatch. "
                "Use warning only for weak or over-broad wording that remains substantially "
                "supported. Use pass when fully supported. Discourse sentences may summarize "
                "linked claims but may not add new factual content."
            ),
            human=f"Items to audit:\n{qa_context}",
        )

    async def deduplicate_evidence_batch(
        self, *, evidence_context: str
    ) -> EvidenceDeduplicationBatch:
        return await self._invoke_structured(
            EvidenceDeduplicationBatch,
            system=(
                "Identify only definite semantic duplicates in the supplied evidence. "
                "Items are partitioned into labeled groups; each group belongs to one paper "
                "and one dimension. Never compare or merge across group boundaries. Return a group only "
                "when multiple items express the same substantive fact; keep the most "
                "complete and precise item. Similar subject matter is not duplication. "
                "Items with different numeric results, datasets, populations, metrics, "
                "conditions, comparisons, or conclusions are materially distinct: do not merge them. "
                "For every returned group, provide a concise reason explaining why the duplicate "
                "items are substantively equivalent and why keep_id is the clearest record. "
                "When uncertain, return no duplicate group for those items. Use only supplied IDs."
            ),
            human=f"Evidence items to deduplicate:\n{evidence_context}",
        )


synthesis_llm_service = SynthesisLLMService()
