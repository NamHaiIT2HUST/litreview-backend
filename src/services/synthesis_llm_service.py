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


def create_synthesis_llm(
    settings,
    *,
    model_override: str | None = None,
    key_override: str | None = None,
    provider_override: str | None = None,
    gemini_cls=None,
    groq_cls=None,
    openai_cls=None,
):
    """Create the configured synthesis chat model universally across any provider."""
    provider = (provider_override or getattr(settings, "synthesis_llm_provider", "") or getattr(settings, "llm_provider", "") or "openai").lower().strip()
    model_name = model_override or getattr(settings, "synthesis_model", "") or getattr(settings, "effective_model_name", "gpt-4o-mini")
    openai_key = key_override or getattr(settings, "effective_openai_api_key", "") or getattr(settings, "openai_api_key", "")
    gemini_key = key_override or getattr(settings, "effective_gemini_api_key", "") or getattr(settings, "gemini_api_key", "")
    groq_key = key_override or getattr(settings, "groq_api_key", "")

    # 1. Groq
    if provider == "groq":
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is required when synthesis_llm_provider='groq'")
        if groq_cls is None:
            from langchain_groq import ChatGroq  # type: ignore
            groq_cls = ChatGroq
        g_model = model_name if model_name and not model_name.startswith("gpt-") else "llama-3.3-70b-versatile"
        return groq_cls(
            model=g_model,
            api_key=groq_key,
            temperature=settings.synthesis_temperature,
            max_tokens=8192,
        )

    # 2. Gemini
    if provider == "gemini":
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is required when synthesis_llm_provider='gemini'")
        if gemini_cls is None:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_cls = ChatGoogleGenerativeAI
        g_model = model_name if model_name.startswith("gemini-") else "gemini-2.0-flash"
        return gemini_cls(
            model=g_model,
            google_api_key=gemini_key,
            temperature=settings.synthesis_temperature,
            max_output_tokens=8192,
        )

    # 3. OpenAI / OpenAI-compatible (DeepSeek, OpenRouter, GoRouter, vLLM, OpenAI, Ollama, etc.)
    if openai_cls is None:
        from langchain_openai import ChatOpenAI
        openai_cls = ChatOpenAI

    kwargs = {
        "model": model_name or "claude-opus-5-thinking",
        "api_key": openai_key or "sk-placeholder",
        "temperature": settings.synthesis_temperature,
        "max_tokens": 8192,
        "default_headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    }
    api_base = settings.get_api_base() if callable(getattr(settings, "get_api_base", None)) else (getattr(settings, "get_api_base", None) or getattr(settings, "openai_api_base", None) or getattr(settings, "llm_base_url", None) or "")
    if api_base:
        kwargs["base_url"] = api_base

    return openai_cls(**kwargs)


def _is_transient_provider_error(exc: BaseException) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in (400, 401, 403, 404, 409, 422, 429) or (isinstance(status_code, int) and status_code >= 500):
        return True
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    return (
        "429" in message
        or "resource_exhausted" in message
        or "quota" in message
        or "rate limit" in message
        or "overloaded" in message
        or "high demand" in message
        or "timeout" in message
        or "503" in message
        or "500" in message
        or "502" in message
        or "504" in message
        or "connection" in message
        or "unavailable" in message
        or "unauthorized" in message
        or "user not found" in message
        or "forbidden" in message
        or "bad gateway" in message
        or "gateway timeout" in message
        or "ratelimit" in name
    )


class SynthesisLLMService:
    def __init__(
        self,
        llm: Any | None = None,
        *,
        max_concurrency: int | None = None,
        retry_delays: tuple[float, ...] = (1.0, 2.0, 4.0),
    ):
        self._llm = llm
        self._max_concurrency = max(1, max_concurrency if max_concurrency is not None else get_settings().synthesis_llm_max_concurrency)
        self._semaphore = None
        self._semaphore_loop = None
        self._retry_delays = retry_delays
        self._active_invocations = 0
        self._max_active_invocations = 0

    def _get_semaphore(self):
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if self._semaphore is None or (current_loop and self._semaphore_loop is not current_loop):
            self._semaphore = asyncio.Semaphore(self._max_concurrency)
            self._semaphore_loop = current_loop
        return self._semaphore

    def get_runtime_metrics(self) -> dict[str, int]:
        return {
            "active_invocations": self._active_invocations,
            "max_active_invocations": self._max_active_invocations,
            "configured_max_concurrency": self._max_concurrency,
        }

    def concurrency_snapshot(self) -> dict[str, int]:
        return self.get_runtime_metrics()

    def validate_configuration(self) -> None:
        """Validate that the synthesis LLM can be created with current settings.

        Raises RuntimeError when the configuration is missing required keys
        (e.g. no API key for the chosen provider).  Called by the HTTP layer
        *before* creating a session so the user gets a clear 503 instead of
        a confusing background-task failure.
        """
        try:
            self._get_llm()
        except Exception as exc:
            raise RuntimeError(
                f"Synthesis LLM configuration error: {exc}"
            ) from exc

    def _get_llm(self) -> Any:
        if self._llm is None:
            self._llm = create_synthesis_llm(get_settings())
        return self._llm

    def _get_runner_candidates(self, schema):
        settings = get_settings()
        candidates = []
        
        # 1. Primary configured LLM
        primary = self._get_llm()
        m_name = getattr(primary, "model", getattr(primary, "model_name", "primary"))
        
        # Try standard structured output
        try:
            candidates.append((m_name, primary.with_structured_output(schema)))
        except Exception:
            pass

        # Try json_mode (most compatible with proxies like GoRouter/OpenRouter)
        try:
            candidates.append((f"{m_name}:json_mode", primary.with_structured_output(schema, method="json_mode")))
        except Exception:
            pass

        try:
            candidates.append((f"{m_name}:function", primary.with_structured_output(schema, method="function_calling")))
        except Exception:
            pass

        # 2. Universal Prompt-based JSON runner fallback (100% compatible with all proxies)
        if hasattr(primary, "ainvoke") or hasattr(primary, "invoke"):
            class UniversalJsonRunner:
                def __init__(self, raw_llm, target_schema):
                    self._raw_llm = raw_llm
                    self._schema = target_schema

                async def ainvoke(self, messages, **kwargs):
                    import json
                    if hasattr(self._schema, "model_json_schema"):
                        schema_json = json.dumps(self._schema.model_json_schema(), indent=2)
                    elif isinstance(self._schema, dict):
                        schema_json = json.dumps(self._schema, indent=2)
                    else:
                        schema_json = "{}"
                    sys_addition = f"\n\nCRITICAL: Output ONLY a valid JSON object matching this schema:\n{schema_json}"
                    augmented_messages = []
                    for role, content in messages:
                        if role == "system":
                            augmented_messages.append((role, content + sys_addition))
                        else:
                            augmented_messages.append((role, content))
                    
                    if hasattr(self._raw_llm, "ainvoke"):
                        resp = await self._raw_llm.ainvoke(augmented_messages, **kwargs)
                    else:
                        resp = self._raw_llm.invoke(augmented_messages, **kwargs)
                    raw_text = resp.content if hasattr(resp, "content") else str(resp)
                    if isinstance(raw_text, list):
                        raw_text = "".join(part.get("text", "") for part in raw_text if isinstance(part, dict))
                    raw_text = str(raw_text).strip()
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    if hasattr(self._schema, "model_validate_json"):
                        return self._schema.model_validate_json(raw_text)
                    elif hasattr(self._schema, "parse_raw"):
                        return self._schema.parse_raw(raw_text)
                    else:
                        return json.loads(raw_text)

            candidates.append((f"{m_name}:universal_json", UniversalJsonRunner(primary, schema)))

        # 3. Fallback candidate for OpenAI / GPT-4o-mini (nếu primary khác gpt-4o-mini)
        oai_key = settings.effective_openai_api_key
        if oai_key and m_name != "gpt-4o-mini":
            try:
                from langchain_openai import ChatOpenAI
                llm_oai = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=oai_key,
                    base_url=settings.get_api_base or None,
                    temperature=settings.synthesis_temperature,
                    default_headers={"User-Agent": "Mozilla/5.0"}
                )
                candidates.append(("gpt-4o-mini", llm_oai.with_structured_output(schema, method="json_mode")))
            except Exception:
                pass

        # 4. Fallback candidate for Gemini (CHỈ KHI có key AIzaSy thực sự)
        gemini_key = settings.effective_gemini_api_key
        if gemini_key and gemini_key.startswith("AIzaSy") and m_name != "gemini-2.0-flash":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm_gem = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=gemini_key,
                    temperature=settings.synthesis_temperature
                )
                candidates.append(("gemini-2.0-flash", llm_gem.with_structured_output(schema)))
            except Exception:
                pass

        return candidates

    async def _invoke_structured(self, schema, *, system: str, human: str | list):
        import random
        candidates = self._get_runner_candidates(schema)
        messages = [("system", system), ("human", human)]
        
        last_exception = None
        for attempt in range(len(self._retry_delays) + 1):
            started = time.perf_counter()
            for model_tag, runner in candidates:
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
                            model_name=model_tag, attempt=attempt + 1,
                            duration_ms=int((time.perf_counter() - started) * 1000), status="success",
                            prompt_json={"system": system, "human": human},
                            response_json=response.model_dump(mode="json") if hasattr(response, "model_dump") else {"value": str(response)},
                        ))
                    return response
                except Exception as exc:
                    last_exception = exc
                    trace = _TRACE_CONTEXT.get()
                    if trace:
                        db, session_id, step_name = trace
                        db.add(LLMCallLog(
                            session_id=session_id, step_name=step_name,
                            model_name=model_tag, attempt=attempt + 1,
                            duration_ms=int((time.perf_counter() - started) * 1000), status="error",
                            prompt_json={"system": system, "human": human}, error=str(exc)[:4000],
                        ))
                    if _is_transient_provider_error(exc):
                        # Switch to the next candidate model/key immediately
                        continue
                    else:
                        raise exc

            if attempt < len(self._retry_delays):
                delay = self._retry_delays[attempt]
                jitter = random.uniform(0.1, 0.5) if delay > 0 else 0
                await asyncio.sleep(delay + jitter)

        if last_exception:
            raise last_exception
        raise RuntimeError("Synthesis LLM call failed after all retries and fallback models.")

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
        page_images: dict[int, str] | None = None,
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
            
        system_prompt = (
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
        )
        
        human_text = (
            f"Research question:\n{research_question}\n\n"
            + "\n\n--- NEXT DIMENSION ---\n\n".join(contexts)
        )
        
        if page_images:
            human_message = [{"type": "text", "text": human_text}]
            for page_num, b64_img in sorted(page_images.items()):
                human_message.append({"type": "text", "text": f"\n[IMAGE OF PAGE {page_num}]\n"})
                human_message.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}})
        else:
            human_message = human_text

        return await self._invoke_structured(
            PaperEvidenceExtractionOutput,
            system=system_prompt,
            human=human_message,
        )

    async def build_outline(self, *, research_question: str, claims_context: str) -> SynthesisOutlineOutput:
        return await self._invoke_structured(
            SynthesisOutlineOutput,
            system=(
                "You are an expert scientific literature review synthesizer. "
                "Build a comprehensive, multi-perspective academic literature-review outline from verified synthesis claims. "
                "Organize sections across the 4 core academic perspectives whenever supported by claims:\n"
                "1. Theoretical Foundations & Problem Formulation (Bối cảnh lý thuyết, mục tiêu và định nghĩa bài toán)\n"
                "2. Methodological Approaches & Technical Innovations (Phân tích đối chiếu phương pháp, giải thuật, kỹ thuật tiếp cận)\n"
                "3. Empirical Validation & Comparative Findings (Đánh giá thực nghiệm, tập dữ liệu, kết quả và phát hiện cốt lõi)\n"
                "4. Critical Analysis, Research Gaps & Future Directions (Phân tích phê phán, giới hạn chưa giải quyết và hướng mở)\n\n"
                "Rules:\n"
                "- Select ONLY claims directly relevant to the research question.\n"
                "- Use only supplied claim IDs and assign each selected claim to at most one section.\n"
                "- Assign descriptive, highly academic Vietnamese section titles (e.g., '1. Cơ sở Lý thuyết & Tổng quan Bài toán', '2. Phân tích Đối chiếu Phương pháp luận & Đột phá Kỹ thuật', '3. Đánh giá Thực nghiệm & Phát hiện Cốt lõi', '4. Phân tích Phê phán & Khoảng trống Nghiên cứu').\n"
                "- Every paper with a supported relevant claim must appear in at least one section.\n"
                "- Group multi-paper claims into thematic comparative sections when their evidence supports a cross-paper comparison.\n"
                "- Claims backed by limitations/gaps belong in the Critical Gaps section, and future_work in Future Directions."
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
                "Write an academic literature-review section in professional Vietnamese using only the verified claims "
                f"and evidence supplied. Target length: {suggested_length}. Return sentence-level structured output.\n"
                "- Classify each sentence as claim or discourse.\n"
                "- Claim sentences state scientific facts and must be directly entailed by their claim_ids.\n"
                "- Discourse sentences may connect, introduce, or summarize supplied claims, but must not add new facts.\n"
                "- Do not create citation markers (they will be injected automatically).\n"
                "- Compare and contrast findings across papers even if evidence is sparse; explain nuances and significance.\n"
                "- Every factual statement must remain strictly grounded in the verified claims."
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Section title:\n{section_title}\n\n"
                f"Claims and evidence:\n{claims_context}"
            ),
        )

    async def refine_section(
        self,
        *,
        research_question: str,
        section_title: str,
        claims_context: str,
        original_draft: str,
        qa_feedback: str,
    ) -> SectionDraftOutput:
        return await self._invoke_structured(
            SectionDraftOutput,
            system=(
                "You are an expert academic editor refining a literature-review section based on automated QA feedback. "
                "Rewrite the provided draft to fix all sentences flagged by the QA review. "
                "Return the entire section as sentence-level structured output, maintaining the flow and structure "
                "where possible, but replacing or modifying problematic sentences to ensure strict adherence to the "
                "verified claims and evidence. Classify each sentence as claim or discourse. "
                "Claim sentences state scientific facts and must be directly entailed by their claim_ids. "
                "Discourse sentences may connect, introduce, or summarize supplied claims, but must not add new facts. "
                "Do not create citation markers. Every factual statement must remain grounded in the verified claims."
            ),
            human=(
                f"Research question:\n{research_question}\n\n"
                f"Section title:\n{section_title}\n\n"
                f"Claims and evidence:\n{claims_context}\n\n"
                f"Original Draft:\n{original_draft}\n\n"
                f"QA Feedback to Address:\n{qa_feedback}"
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
