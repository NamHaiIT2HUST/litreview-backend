"""Structured-output LLM adapter for literature synthesis.

Nodes and business services depend on this adapter instead of importing a
specific provider directly.  Every synthesis step uses a Pydantic schema.
"""
from __future__ import annotations

from typing import Iterable
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


class SynthesisLLMService:
    def __init__(self, llm=None):
        self._llm = llm

    def _get_llm(self):
        if self._llm is not None:
            return self._llm

        # Lazy import keeps schema/grounding tests independent from LangChain runtime.
        from langchain_openai import ChatOpenAI

        settings = get_settings()
        kwargs = {
            "model": settings.model_name,
            "api_key": settings.openai_api_key,
            "temperature": getattr(settings, "synthesis_temperature", 0.0),
        }
        api_base = settings.get_api_base
        if api_base:
            kwargs["base_url"] = api_base
        self._llm = ChatOpenAI(**kwargs)
        return self._llm

    async def _invoke_structured(self, schema, *, system: str, human: str):
        runner = self._get_llm().with_structured_output(schema)
        return await runner.ainvoke([("system", system), ("human", human)])

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
                "an empty items list. Never infer missing information. " + quote_rule
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
                "more supplied evidence IDs. Do not introduce facts absent from evidence."
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
                "Build a literature-review outline from verified synthesis claims. Group "
                "claims by meaningful research themes. Use only supplied claim IDs and "
                "assign each selected claim to one section. Do not invent themes that have "
                "no supporting claims."
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
                "and evidence supplied. Return sentence-level structured output. Every "
                "sentence must reference at least one supplied claim_id so citations can be "
                "resolved by code. Do not write uncited factual sentences and do not create "
                "citation markers yourself."
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Section title:\n{section_title}\n\n"
                f"Claims and evidence:\n{claims_context}"
            ),
        )


synthesis_llm_service = SynthesisLLMService()
