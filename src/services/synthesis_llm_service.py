"""Structured-output LLM adapter for literature synthesis.

Nodes and business services depend on this adapter instead of importing a
specific provider directly.  Every synthesis step uses a Pydantic schema.
"""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
from uuid import UUID

from src.config import get_settings
from src.models.synthesis_schemas import (
    ClaimVerificationDecision,
    EntailmentDecision,
    EvidenceExtractionBatch,
    SectionDraftOutput,
    SynthesisClaimProposalBatch,
    SynthesisOutlineOutput,
    SynthesisPlanOutput,
)


def create_synthesis_llm(settings, *, gemini_cls=None, groq_cls=None):
    """Create the configured synthesis chat model without making a network call."""
    provider = settings.synthesis_llm_provider.lower().strip()
    if provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("Groq synthesis requires GROQ_API_KEY in .env.")
        if groq_cls is None:
            from langchain_groq import ChatGroq

            groq_cls = ChatGroq
        return groq_cls(
            model=settings.synthesis_model,
            api_key=settings.groq_api_key,
            temperature=settings.synthesis_temperature,
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

    raise RuntimeError("SYNTHESIS_LLM_PROVIDER must be 'gemini' or 'groq'.")


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
        runner = self._get_llm().with_structured_output(schema)
        messages = [("system", system), ("human", human)]
        for attempt in range(len(self._retry_delays) + 1):
            try:
                async with self._get_semaphore():
                    return await runner.ainvoke(messages)
            except Exception as exc:
                if attempt >= len(self._retry_delays) or not _is_transient_provider_error(exc):
                    raise
                await asyncio.sleep(self._retry_delays[attempt])
        raise RuntimeError("unreachable")

    async def plan_dimensions(self, research_question: str) -> SynthesisPlanOutput:
        return await self._invoke_structured(
            SynthesisPlanOutput,
            system=(
                "You design evidence-comparison schemas for academic literature review. "
                "Return 3-6 concise, observable comparison dimensions. Prefer fields that "
                "can be supported by verbatim paper text (method, dataset/population, "
                "evaluation, finding, limitation, etc.). Do not create scores."
            ),
            human=f"Research question:\n{research_question}",
        )

    async def extract_evidence(
        self,
        *,
        research_question: str,
        dimension: str,
        indexed_chunks: Iterable[tuple[UUID, str]],
        exact_quote_only: bool,
    ) -> EvidenceExtractionBatch:
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
                "chunk boundary because each supplied context is a continuous raw page window. "
                "If the context does not contain evidence, return "
                "an empty items list. For a general literature review, treat paper-specific "
                "objectives, methods, findings, and limitations as useful evidence even when "
                "other papers use different terminology. When relevant text exists, return at "
                "least one item and copy the shortest complete supporting quote exactly. "
                "Never infer missing information. " + quote_rule
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Dimension:\n{dimension}\n\n"
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
                "more supplied evidence IDs. Ensure every paper represented in the evidence "
                "contributes at least one descriptive or comparative claim. Different topics "
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

    async def build_outline(self, *, research_question: str, claims_context: str) -> SynthesisOutlineOutput:
        return await self._invoke_structured(
            SynthesisOutlineOutput,
            system=(
                "Build a coherent academic literature-review outline from verified synthesis claims. "
                "Select ONLY claims directly relevant to the research question; omit unrelated claims "
                "even when they are supported by their source. Use only supplied claim IDs and assign "
                "each selected claim to at most one section. Organize the review as an introduction, "
                "thematic synthesis, limitations or research gaps, and a conclusion when the supplied "
                "claims support those roles. Do not invent themes or background facts."
            ),
            human=f"Research question:\n{research_question}\n\nVerified claims:\n{claims_context}",
        )

    async def draft_section(
        self,
        *,
        research_question: str,
        section_title: str,
        claims_context: str,
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
                " When the supplied claims permit it, write 3-5 coherent sentences for the "
                "section: introduce the theme, synthesize or contrast the claims, and close "
                "with a traceable transition. Never add factual background beyond the claims."
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Section title:\n{section_title}\n\n"
                f"Claims and evidence:\n{claims_context}"
            ),
        )


synthesis_llm_service = SynthesisLLMService()
