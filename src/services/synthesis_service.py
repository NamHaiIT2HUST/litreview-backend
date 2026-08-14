"""Core literature-synthesis business logic.

This module deliberately keeps workflow orchestration out of the business
rules. LangGraph nodes call these methods; the methods own DB invariants,
evidence grounding, entailment, outline persistence and citation resolution.
"""
from __future__ import annotations

import uuid
import json
import time
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings

from src.models.db_models import (
    Citation,
    ClaimEvidenceLink,
    LLMCallLog,
    EntailmentStatus as DBEntailmentStatus,
    EvidenceExtractionAttempt,
    EvidenceRecord,
    RetrievalLog,
    EvidenceRelation as DBEvidenceRelation,
    GroundingStatus as DBGroundingStatus,
    PageText,
    Paper,
    SynthesisClaim,
    SynthesisClaimType as DBSynthesisClaimType,
    SynthesisSection,
    SynthesisSession,
    SynthesisStatus,
)
from src.models.synthesis_schemas import (
    ClaimVerificationBatchOutput,
    ClaimVerificationDecision,
    EvidenceDimension,
    EvidenceExtractionCandidate,
)
from src.services.claim_verification_policy import guard_topic_absence_claim, sanitize_claim_verification
from src.services.evidence_extraction_policy import (
    recovery_budget_allows,
    should_retry_evidence_batch,
)
from src.services.evidence_deduplication_policy import sanitize_evidence_deduplication
from src.services.grounding_service import build_anchor_contexts, grounding_service
from src.services.synthesis_llm_service import synthesis_llm_service, llm_trace
from src.services.synthesis_coverage_policy import (
    dimensions_needing_expansion,
    dimension_retrieval_hint,
    evaluate_section_coverage,
    missing_evidence_paper_ids,
    normalize_dimension,
    should_accept_dimension_scope,
)
from src.services.synthesis_session_utils import uuid_paper_ids
from src.services.research_question_policy import (
    GENERAL_LITERATURE_REVIEW_OBJECTIVE,
    resolve_research_objective,
)
from src.services.vector_store import vector_store_service
from src.services.synthesis_qa_policy import apply_sentence_qa
from src.services.outline_coverage_policy import ensure_paper_outline_coverage, flag_single_paper_multi_claim
from src.services.generic_evidence_cache_service import (
    extraction_fingerprint,
    lookup_ready_cache,
    materialize_cache,
    paper_content_hash,
    store_grounded_cache,
)
from src.services.synthesis_metrics_service import finalize_metrics, increment_metric


def _now_utc() -> datetime:
    return datetime.now(UTC)


def reconcile_claim_verification_batch(
    output: ClaimVerificationBatchOutput,
    expected_claim_ids: set[uuid.UUID],
) -> tuple[dict[uuid.UUID, object], set[uuid.UUID]]:
    """Accept exactly one decision per known claim; everything else falls back."""
    grouped: defaultdict[uuid.UUID, list[object]] = defaultdict(list)
    for decision in output.decisions:
        if decision.claim_id in expected_claim_ids:
            grouped[decision.claim_id].append(decision)
    accepted = {
        claim_id: decisions[0]
        for claim_id, decisions in grouped.items()
        if len(decisions) == 1
    }
    return accepted, expected_claim_ids - set(accepted)


def batch_verification_is_complete(output: ClaimVerificationBatchOutput, expected_count: int) -> bool:
    return len(output.decisions) == expected_count and len({item.claim_id for item in output.decisions}) == expected_count


class SynthesisService:
    async def _record_coverage_decision(
        self, db: AsyncSession, *, session_id: uuid.UUID, paper_id: uuid.UUID,
        dimension: EvidenceDimension, cached_evidence_count: int,
        threshold_reason: str, expansion_triggered: bool,
        new_grounded_evidence_count: int,
    ) -> None:
        db.add(RetrievalLog(
            session_id=session_id,
            paper_id=paper_id,
            dimension=dimension.value,
            query="Coverage expansion decision",
            results_json={
                "diagnostic": "coverage_expansion",
                "cached_evidence_count_before": cached_evidence_count,
                "coverage_threshold_reason": threshold_reason,
                "expansion_triggered": expansion_triggered,
                "new_grounded_evidence_count": new_grounded_evidence_count,
            },
            duration_ms=0,
        ))

    async def _annotate_latest_llm_log(
        self, db: AsyncSession, *, session_id: uuid.UUID, step_name: str,
        diagnostic: dict,
    ) -> None:
        result = await db.execute(
            select(LLMCallLog)
            .where(LLMCallLog.session_id == session_id, LLMCallLog.step_name == step_name)
            .order_by(LLMCallLog.created_at.desc())
        )
        log = result.scalars().first()
        if log is not None:
            payload = dict(log.response_json or {})
            payload.setdefault("_diagnostics", {}).update(diagnostic)
            log.response_json = payload

    async def prepare_session(self, db: AsyncSession, session_id: uuid.UUID) -> dict:
        result = await db.execute(
            select(SynthesisSession).where(SynthesisSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Synthesis session {session_id} not found")
        research_question = resolve_research_objective(session.research_question)

        paper_ids = uuid_paper_ids(session.paper_ids or [])
        if not paper_ids:
            raise ValueError("Synthesis session contains no papers")

        paper_result = await db.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        papers = list(paper_result.scalars().all())
        by_id = {paper.id: paper for paper in papers}
        missing = [paper_id for paper_id in paper_ids if paper_id not in by_id]
        if missing:
            raise ValueError(f"Papers not found: {', '.join(str(x) for x in missing)}")

        not_ingested = [
            paper.id for paper in papers if paper.active_ingestion_id is None
        ]
        if not_ingested:
            raise ValueError(
                "These papers have no provenance-aware PDF ingestion: "
                + ", ".join(str(x) for x in not_ingested)
            )

        session.status = SynthesisStatus.processing
        session.error_message = None
        await db.flush()
        return {
            "research_question": research_question,
            "paper_ids": [str(paper_id) for paper_id in paper_ids],
        }

    async def extract_paper_evidence(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper_id: uuid.UUID,
        research_question: str,
        dimensions: list[EvidenceDimension],
        expanded: bool = False,
    ) -> list[str]:
        paper_result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = paper_result.scalar_one_or_none()
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        if paper.active_ingestion_id is None:
            raise ValueError(f"Paper {paper_id} has not been ingested")

        if expanded:
            retry_rows = await db.execute(
                select(RetrievalLog.dimension).where(
                    RetrievalLog.session_id == session_id,
                    RetrievalLog.paper_id == paper_id,
                    RetrievalLog.query.like("%Broaden retrieval:%"),
                )
            )
            prior_retries = [row[0] for row in retry_rows.all()]
            allowed_dimensions = []
            projected_retries = len(prior_retries)
            for raw_dimension in dimensions:
                dimension = normalize_dimension(raw_dimension)
                if recovery_budget_allows(
                    existing_dimension_retries=prior_retries.count(dimension.value),
                    existing_paper_retries=projected_retries,
                ):
                    allowed_dimensions.append(dimension)
                    projected_retries += 1
            dimensions = allowed_dimensions
            if not dimensions:
                return []
            await increment_metric(
                db, session_id, "grounding_retry_count", len(dimensions)
            )

        if research_question == GENERAL_LITERATURE_REVIEW_OBJECTIVE and not expanded:
            return await self._extract_generic_paper_evidence(
                db,
                session_id=session_id,
                paper=paper,
                dimensions=dimensions,
                research_question=research_question,
            )
        if not expanded:
            return await self._extract_custom_paper_evidence_batch(
                db,
                session_id=session_id,
                paper=paper,
                dimensions=dimensions,
                research_question=research_question,
            )

        grounded_ids: list[str] = []
        model_name = get_settings().model_name
        filters = {
            "$and": [
                {"paper_id": str(paper.id)},
                {"ingestion_id": str(paper.active_ingestion_id)},
            ]
        }

        for dimension in dimensions:
            dimension = normalize_dimension(dimension)
            dimension_value = dimension.value
            query_parts = [
                paper.title,
                f"Evidence dimension: {dimension_value}",
                f"Search terms: {dimension_retrieval_hint(dimension)}",
            ]
            if research_question != GENERAL_LITERATURE_REVIEW_OBJECTIVE:
                query_parts.append(f"Research question: {research_question}")
            query = "\n".join(query_parts)
            if expanded:
                query += "\nBroaden retrieval: include related terminology, methods, outcomes, limitations, and contrary findings."
            retrieval_started = time.perf_counter()
            scored_docs = await vector_store_service.search_similar_documents_with_scores(
                query,
                top_k=12 if expanded or dimension in {
                    EvidenceDimension.dataset,
                    EvidenceDimension.evaluation,
                } else 6,
                filters=filters,
            )
            docs = [document for document, _score in scored_docs]
            db.add(RetrievalLog(
                session_id=session_id,
                paper_id=paper_id,
                dimension=dimension_value,
                query=query,
                results_json=[
                    {
                        "chunk_id": str(document.metadata.get("chunk_id") or document.metadata.get("id") or ""),
                        "score": float(score),
                        "metadata": {key: str(value) for key, value in document.metadata.items()},
                    }
                    for document, score in scored_docs
                ],
                duration_ms=int((time.perf_counter() - retrieval_started) * 1000),
            ))
            # Chroma chooses anchor chunks only.  The LLM must read canonical raw
            # PageText windows rebuilt from persisted offsets so a verbatim quote can
            # cross a chunk boundary without duplicated overlap text.
            indexed_chunks, allowed_chunk_ids = await build_anchor_contexts(
                db,
                paper_id=paper.id,
                retrieved_documents=docs,
            )

            if not indexed_chunks:
                continue

            for attempt_number in (1, 2):
                with llm_trace(db, session_id, "extract_evidence"):
                    batch = await synthesis_llm_service.extract_evidence(
                        research_question=research_question,
                        dimension=dimension_value,
                        indexed_chunks=indexed_chunks,
                        exact_quote_only=attempt_number == 2,
                    )
                if not batch.items:
                    # Empty output is a legitimate "no evidence in this context" result.
                    db.add(EvidenceExtractionAttempt(
                        id=uuid.uuid4(),
                        synthesis_session_id=session_id,
                        paper_id=paper_id,
                        dimension=dimension_value,
                        attempt_number=attempt_number,
                        grounding_status=DBGroundingStatus.rejected,
                        failure_reason="no_candidates_in_retrieved_context",
                        model_name=model_name,
                        prompt_version="evidence-v2-raw-window",
                    ))
                    await db.flush()
                    break

                had_grounding_failure = False
                for item in batch.items:
                    item_chunk_id = item.source_chunk_id
                    attempt = EvidenceExtractionAttempt(
                        id=uuid.uuid4(),
                        synthesis_session_id=session_id,
                        paper_id=paper_id,
                        dimension=dimension_value,
                        attempt_number=attempt_number,
                        raw_value=item.value,
                        raw_quote=item.quote,
                        suggested_chunk_raw=str(item_chunk_id),
                        suggested_chunk_id=(
                            item_chunk_id if item_chunk_id in allowed_chunk_ids else None
                        ),
                        grounding_status=DBGroundingStatus.pending,
                        model_name=model_name,
                        prompt_version="evidence-v2-raw-window",
                    )
                    db.add(attempt)

                    if not should_accept_dimension_scope(dimension, item.applies_to):
                        attempt.grounding_status = DBGroundingStatus.rejected
                        attempt.failure_reason = "dimension_subject_scope_mismatch"
                        had_grounding_failure = True
                        continue

                    if item_chunk_id not in allowed_chunk_ids:
                        attempt.grounding_status = DBGroundingStatus.rejected
                        attempt.failure_reason = "chunk_id_not_in_retrieved_context"
                        had_grounding_failure = True
                        continue

                    candidate = EvidenceExtractionCandidate(
                        paper_id=paper_id,
                        dimension=dimension_value,
                        value=item.value,
                        quote=item.quote,
                        source_chunk_id=item_chunk_id,
                    )
                    outcome = await grounding_service.ground_candidate(db, candidate)
                    if not outcome.grounded:
                        attempt.grounding_status = DBGroundingStatus.rejected
                        attempt.failure_reason = outcome.failure_reason
                        had_grounding_failure = True
                        continue

                    attempt.grounding_status = DBGroundingStatus.grounded
                    grounded = outcome.evidence
                    assert grounded is not None

                    # Idempotent evidence insertion for graph/task retries.
                    existing_result = await db.execute(
                        select(EvidenceRecord).where(
                            EvidenceRecord.synthesis_session_id == session_id,
                            EvidenceRecord.paper_id == paper_id,
                            EvidenceRecord.dimension == dimension_value,
                            EvidenceRecord.page_text_id == grounded.page_text_id,
                            EvidenceRecord.page_char_start == grounded.page_char_start,
                            EvidenceRecord.page_char_end == grounded.page_char_end,
                        )
                    )
                    existing = existing_result.scalar_one_or_none()
                    if existing is None:
                        evidence = EvidenceRecord(
                            id=uuid.uuid4(),
                            synthesis_session_id=session_id,
                            paper_id=paper_id,
                            page_text_id=grounded.page_text_id,
                            source_chunk_id=grounded.source_chunk_id,
                            created_from_attempt_id=attempt.id,
                            dimension=dimension_value,
                            applies_to=item.applies_to.value,
                            value=grounded.value,
                            quote=grounded.quote,
                            page_char_start=grounded.page_char_start,
                            page_char_end=grounded.page_char_end,
                        )
                        db.add(evidence)
                        grounded_ids.append(str(evidence.id))
                    else:
                        grounded_ids.append(str(existing.id))

                await db.flush()
                if not should_retry_evidence_batch(
                    attempt_number=attempt_number,
                    had_candidates=bool(batch.items),
                    had_grounding_failure=had_grounding_failure,
                ):
                    break
                # Retry once if *any* first-pass candidate failed grounding, even
                # when another candidate succeeded. This avoids silently dropping
                # potentially valid evidence from a mixed-success LLM batch.

        return list(dict.fromkeys(grounded_ids))

    async def _extract_custom_paper_evidence_batch(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper: Paper,
        dimensions: list[EvidenceDimension],
        research_question: str,
    ) -> list[str]:
        """Extract all custom-RQ dimensions in one call, then ground item by item."""
        filters = {"$and": [
            {"paper_id": str(paper.id)},
            {"ingestion_id": str(paper.active_ingestion_id)},
        ]}
        contexts_by_dimension = {}
        allowed_by_dimension: dict[EvidenceDimension, set[uuid.UUID]] = {}
        for raw_dimension in dimensions:
            dimension = normalize_dimension(raw_dimension)
            query = "\n".join([
                paper.title,
                f"Evidence dimension: {dimension.value}",
                f"Search terms: {dimension_retrieval_hint(dimension)}",
                f"Research question: {research_question}",
            ])
            started = time.perf_counter()
            scored_docs = await vector_store_service.search_similar_documents_with_scores(
                query,
                top_k=12 if dimension in {EvidenceDimension.dataset, EvidenceDimension.evaluation} else 6,
                filters=filters,
            )
            db.add(RetrievalLog(
                session_id=session_id, paper_id=paper.id, dimension=dimension.value,
                query=query,
                results_json=[{
                    "chunk_id": str(doc.metadata.get("chunk_id") or doc.metadata.get("id") or ""),
                    "score": float(score),
                    "metadata": {key: str(value) for key, value in doc.metadata.items()},
                } for doc, score in scored_docs],
                duration_ms=int((time.perf_counter() - started) * 1000),
            ))
            indexed, allowed = await build_anchor_contexts(
                db, paper_id=paper.id,
                retrieved_documents=[doc for doc, _score in scored_docs],
            )
            if indexed:
                contexts_by_dimension[dimension] = indexed
                allowed_by_dimension[dimension] = allowed

        with llm_trace(db, session_id, "extract_paper_evidence_batch_custom"):
            output = await synthesis_llm_service.extract_paper_evidence_batch(
                research_question=research_question,
                contexts_by_dimension=contexts_by_dimension,
                strict_dimension_ids=True,
            )

        grounded_ids: list[str] = []
        failed_dimensions: set[EvidenceDimension] = set()
        primary_stats: defaultdict[EvidenceDimension, dict] = defaultdict(
            lambda: {"candidate_count": 0, "grounded_count": 0, "failure_reasons": []}
        )
        model_name = get_settings().synthesis_model
        for item in output.items:
            dimension = normalize_dimension(item.dimension)
            allowed_ids = allowed_by_dimension.get(dimension, set())
            attempt = EvidenceExtractionAttempt(
                id=uuid.uuid4(), synthesis_session_id=session_id, paper_id=paper.id,
                dimension=dimension.value, attempt_number=1, raw_value=item.value,
                raw_quote=item.quote, suggested_chunk_raw=str(item.source_chunk_id),
                suggested_chunk_id=item.source_chunk_id if item.source_chunk_id in allowed_ids else None,
                grounding_status=DBGroundingStatus.pending, model_name=model_name,
                prompt_version="custom-evidence-v3-batch",
            )
            db.add(attempt)
            primary_stats[dimension]["candidate_count"] += 1
            if not should_accept_dimension_scope(dimension, item.applies_to):
                attempt.grounding_status = DBGroundingStatus.rejected
                attempt.failure_reason = "dimension_subject_scope_mismatch"
                primary_stats[dimension]["failure_reasons"].append("other")
                failed_dimensions.add(dimension)
                continue
            if item.source_chunk_id not in allowed_ids:
                attempt.grounding_status = DBGroundingStatus.rejected
                attempt.failure_reason = "chunk_id_not_in_retrieved_context"
                primary_stats[dimension]["failure_reasons"].append("wrong_source_chunk_id")
                failed_dimensions.add(dimension)
                continue
            outcome = await grounding_service.ground_candidate(db, EvidenceExtractionCandidate(
                paper_id=paper.id, dimension=dimension, value=item.value,
                quote=item.quote, source_chunk_id=item.source_chunk_id,
            ))
            if not outcome.grounded:
                attempt.grounding_status = DBGroundingStatus.rejected
                attempt.failure_reason = outcome.failure_reason
                primary_stats[dimension]["failure_reasons"].append(
                    "quote_mismatch" if outcome.failure_reason == "quote_not_found" else "other"
                )
                failed_dimensions.add(dimension)
                continue
            attempt.grounding_status = DBGroundingStatus.grounded
            grounded = outcome.evidence
            assert grounded is not None
            evidence = EvidenceRecord(
                id=uuid.uuid4(), synthesis_session_id=session_id, paper_id=paper.id,
                page_text_id=grounded.page_text_id, source_chunk_id=grounded.source_chunk_id,
                created_from_attempt_id=attempt.id, dimension=dimension.value,
                applies_to=item.applies_to.value, value=grounded.value, quote=grounded.quote,
                page_char_start=grounded.page_char_start, page_char_end=grounded.page_char_end,
            )
            db.add(evidence)
            grounded_ids.append(str(evidence.id))
            primary_stats[dimension]["grounded_count"] += 1
        await db.flush()

        if failed_dimensions:
            for dimension in sorted(failed_dimensions, key=lambda value: value.value):
                before_result = await db.execute(select(EvidenceExtractionAttempt).where(
                    EvidenceExtractionAttempt.synthesis_session_id == session_id,
                    EvidenceExtractionAttempt.paper_id == paper.id,
                    EvidenceExtractionAttempt.dimension == dimension.value,
                ))
                before_count = len(list(before_result.scalars().all()))
                retry_ids = await self.extract_paper_evidence(
                    db, session_id=session_id, paper_id=paper.id,
                    research_question=research_question,
                    dimensions=[dimension], expanded=True,
                )
                after_result = await db.execute(select(EvidenceExtractionAttempt).where(
                    EvidenceExtractionAttempt.synthesis_session_id == session_id,
                    EvidenceExtractionAttempt.paper_id == paper.id,
                    EvidenceExtractionAttempt.dimension == dimension.value,
                ))
                after_rows = list(after_result.scalars().all())
                targeted_rows = after_rows[before_count:]
                targeted_grounded = sum(
                    row.grounding_status == DBGroundingStatus.grounded for row in targeted_rows
                )
                db.add(RetrievalLog(
                    session_id=session_id, paper_id=paper.id, dimension=dimension.value,
                    query="Targeted recovery diagnostic", duration_ms=0,
                    results_json={
                        "diagnostic": "targeted_recovery",
                        "primary_candidate_count": primary_stats[dimension]["candidate_count"],
                        "grounded_candidate_count": primary_stats[dimension]["grounded_count"],
                        "failure_reasons": sorted(set(primary_stats[dimension]["failure_reasons"])),
                        "targeted_calls": len(targeted_rows),
                        "retry_success": bool(targeted_grounded),
                        "targeted_grounded_candidate_count": targeted_grounded,
                    },
                ))
                grounded_ids.extend(retry_ids)
        return list(dict.fromkeys(grounded_ids))

    async def _extract_generic_paper_evidence(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper: Paper,
        dimensions: list[EvidenceDimension],
        research_question: str,
    ) -> list[str]:
        page_result = await db.execute(
            select(PageText).where(
                PageText.paper_id == paper.id,
                PageText.ingestion_id == paper.active_ingestion_id,
            )
        )
        pages = list(page_result.scalars().all())
        content_hash = paper_content_hash(pages)
        fingerprint = extraction_fingerprint(get_settings())
        cache = await lookup_ready_cache(
            db,
            paper_id=paper.id,
            ingestion_id=paper.active_ingestion_id,
            content_hash=content_hash,
            fingerprint=fingerprint,
        )
        if cache is not None:
            await increment_metric(db, session_id, "cache_hits")
            return await materialize_cache(db, cache=cache, session_id=session_id)
        await increment_metric(db, session_id, "cache_misses")

        contexts_by_dimension = {}
        allowed_by_dimension: dict[EvidenceDimension, set[uuid.UUID]] = {}
        filters = {"$and": [
            {"paper_id": str(paper.id)},
            {"ingestion_id": str(paper.active_ingestion_id)},
        ]}
        normalized_dimensions = [normalize_dimension(value) for value in dimensions]
        for dimension in normalized_dimensions:
            query = "\n".join([
                paper.title,
                f"Evidence dimension: {dimension.value}",
                f"Search terms: {dimension_retrieval_hint(dimension)}",
            ])
            started = time.perf_counter()
            scored_docs = await vector_store_service.search_similar_documents_with_scores(
                query,
                top_k=12 if dimension in {EvidenceDimension.dataset, EvidenceDimension.evaluation} else 6,
                filters=filters,
            )
            db.add(RetrievalLog(
                session_id=session_id, paper_id=paper.id, dimension=dimension.value,
                query=query,
                results_json=[{
                    "chunk_id": str(doc.metadata.get("chunk_id") or doc.metadata.get("id") or ""),
                    "score": float(score),
                    "metadata": {key: str(value) for key, value in doc.metadata.items()},
                } for doc, score in scored_docs],
                duration_ms=int((time.perf_counter() - started) * 1000),
            ))
            indexed, allowed = await build_anchor_contexts(
                db,
                paper_id=paper.id,
                retrieved_documents=[doc for doc, _score in scored_docs],
            )
            if indexed:
                contexts_by_dimension[dimension] = indexed
                allowed_by_dimension[dimension] = allowed

        with llm_trace(db, session_id, "extract_paper_evidence_batch"):
            output = await synthesis_llm_service.extract_paper_evidence_batch(
                research_question=research_question,
                contexts_by_dimension=contexts_by_dimension,
            )

        grounded_ids: list[str] = []
        failed_dimensions: set[EvidenceDimension] = set()
        model_name = get_settings().synthesis_model
        for item in output.items:
            dimension = normalize_dimension(item.dimension)
            allowed_ids = allowed_by_dimension.get(dimension, set())
            attempt = EvidenceExtractionAttempt(
                id=uuid.uuid4(), synthesis_session_id=session_id, paper_id=paper.id,
                dimension=dimension.value, attempt_number=1, raw_value=item.value,
                raw_quote=item.quote, suggested_chunk_raw=str(item.source_chunk_id),
                suggested_chunk_id=item.source_chunk_id if item.source_chunk_id in allowed_ids else None,
                grounding_status=DBGroundingStatus.pending, model_name=model_name,
                prompt_version=fingerprint[:80],
            )
            db.add(attempt)
            if (
                not should_accept_dimension_scope(dimension, item.applies_to)
                or item.source_chunk_id not in allowed_ids
            ):
                attempt.grounding_status = DBGroundingStatus.rejected
                attempt.failure_reason = (
                    "dimension_subject_scope_mismatch"
                    if not should_accept_dimension_scope(dimension, item.applies_to)
                    else "chunk_id_not_in_retrieved_context"
                )
                failed_dimensions.add(dimension)
                continue
            outcome = await grounding_service.ground_candidate(db, EvidenceExtractionCandidate(
                paper_id=paper.id, dimension=dimension, value=item.value,
                quote=item.quote, source_chunk_id=item.source_chunk_id,
            ))
            if not outcome.grounded:
                attempt.grounding_status = DBGroundingStatus.rejected
                attempt.failure_reason = outcome.failure_reason
                failed_dimensions.add(dimension)
                continue
            attempt.grounding_status = DBGroundingStatus.grounded
            grounded = outcome.evidence
            evidence = EvidenceRecord(
                id=uuid.uuid4(), synthesis_session_id=session_id, paper_id=paper.id,
                page_text_id=grounded.page_text_id, source_chunk_id=grounded.source_chunk_id,
                created_from_attempt_id=attempt.id, dimension=dimension.value,
                applies_to=item.applies_to.value,
                value=grounded.value, quote=grounded.quote,
                page_char_start=grounded.page_char_start, page_char_end=grounded.page_char_end,
            )
            db.add(evidence)
            grounded_ids.append(str(evidence.id))
        await db.flush()

        if failed_dimensions:
            grounded_ids.extend(await self.extract_paper_evidence(
                db, session_id=session_id, paper_id=paper.id,
                research_question=research_question,
                dimensions=sorted(failed_dimensions, key=lambda value: value.value),
                expanded=True,
            ))

        records_result = await db.execute(select(EvidenceRecord).where(
            EvidenceRecord.synthesis_session_id == session_id,
            EvidenceRecord.paper_id == paper.id,
        ))
        records = list(records_result.scalars().all())
        if records:
            await store_grounded_cache(
                db, paper_id=paper.id, ingestion_id=paper.active_ingestion_id,
                content_hash=content_hash, fingerprint=fingerprint,
                evidence_records=records,
            )
        return list(dict.fromkeys(grounded_ids))

    async def recover_and_validate_paper_coverage(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper_ids: list[uuid.UUID],
        research_question: str,
    ) -> list[str]:
        evidence_rows = await db.execute(
            select(EvidenceRecord.paper_id).where(
                EvidenceRecord.synthesis_session_id == session_id
            )
        )
        covered = [str(paper_id) for paper_id in evidence_rows.scalars().all()]
        missing = missing_evidence_paper_ids(
            selected_paper_ids=[str(paper_id) for paper_id in paper_ids],
            evidence_paper_ids=covered,
        )

        recovery_dimensions = [
            EvidenceDimension.objective,
            EvidenceDimension.method,
            EvidenceDimension.findings,
        ]
        for raw_paper_id in missing:
            paper_uuid = uuid.UUID(raw_paper_id)
            before_rows = await db.execute(
                select(EvidenceRecord.dimension).where(
                    EvidenceRecord.synthesis_session_id == session_id,
                    EvidenceRecord.paper_id == paper_uuid,
                )
            )
            before_by_dimension = defaultdict(int)
            for dimension in before_rows.scalars().all():
                before_by_dimension[dimension] += 1
            await self.extract_paper_evidence(
                db,
                session_id=session_id,
                paper_id=paper_uuid,
                research_question=research_question,
                dimensions=recovery_dimensions,
                expanded=True,
            )
            after_rows = await db.execute(
                select(EvidenceRecord.dimension).where(
                    EvidenceRecord.synthesis_session_id == session_id,
                    EvidenceRecord.paper_id == paper_uuid,
                )
            )
            after_by_dimension = defaultdict(int)
            for dimension in after_rows.scalars().all():
                after_by_dimension[dimension] += 1
            for dimension in recovery_dimensions:
                await self._record_coverage_decision(
                    db, session_id=session_id, paper_id=paper_uuid,
                    dimension=dimension, cached_evidence_count=before_by_dimension[dimension.value],
                    threshold_reason="paper_missing_any_grounded_evidence",
                    expansion_triggered=True,
                    new_grounded_evidence_count=max(
                        0, after_by_dimension[dimension.value] - before_by_dimension[dimension.value]
                    ),
                )

        evidence_rows = await db.execute(
            select(EvidenceRecord.paper_id).where(
                EvidenceRecord.synthesis_session_id == session_id
            )
        )
        covered = [str(paper_id) for paper_id in evidence_rows.scalars().all()]
        still_missing = missing_evidence_paper_ids(
            selected_paper_ids=[str(paper_id) for paper_id in paper_ids],
            evidence_paper_ids=covered,
        )
        if still_missing:
            paper_rows = await db.execute(
                select(Paper.id, Paper.title).where(
                    Paper.id.in_([uuid.UUID(value) for value in still_missing])
                )
            )
            missing_titles = [title for _paper_id, title in paper_rows.all()]
            raise ValueError(
                "Không đủ bằng chứng để tạo tổng quan cho: "
                + "; ".join(missing_titles or still_missing)
                + ". Hãy kiểm tra PDF hoặc thử tài liệu khác."
            )
        return missing

    async def expand_thin_dimensions_once(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper_ids: list[uuid.UUID],
        research_question: str,
        dimensions: list[EvidenceDimension],
    ) -> list[str]:
        rows = await db.execute(
            select(EvidenceRecord.dimension, EvidenceRecord.paper_id).where(
                EvidenceRecord.synthesis_session_id == session_id
            )
        )
        paper_ids_by_dimension: defaultdict[str, list[str]] = defaultdict(list)
        for dimension, paper_id in rows.all():
            paper_ids_by_dimension[dimension].append(str(paper_id))
        thin_dimensions = dimensions_needing_expansion(
            dimensions=dimensions,
            paper_ids_by_dimension=paper_ids_by_dimension,
        )
        prior_sparse = await db.execute(
            select(RetrievalLog.dimension, RetrievalLog.results_json).where(
                RetrievalLog.session_id == session_id,
                RetrievalLog.query == "Coverage expansion decision",
            )
        )
        sparse_dimensions = {
            dimension for dimension, payload in prior_sparse.all()
            if isinstance(payload, dict)
            and payload.get("diagnostic") == "coverage_expansion"
            and payload.get("coverage_threshold_reason") == "dimension_marked_sparse"
        }
        thin_dimensions = [
            normalize_dimension(dimension) for dimension in thin_dimensions
            if normalize_dimension(dimension).value not in sparse_dimensions
        ]
        if not thin_dimensions:
            return []
        if not thin_dimensions:
            for paper_id in paper_ids:
                for raw_dimension in dimensions:
                    dimension = normalize_dimension(raw_dimension)
                    count = len(paper_ids_by_dimension.get(dimension.value, []))
                    await self._record_coverage_decision(
                        db, session_id=session_id, paper_id=paper_id,
                        dimension=dimension, cached_evidence_count=count,
                        threshold_reason="dimension_meets_two_paper_coverage_threshold",
                        expansion_triggered=False, new_grounded_evidence_count=0,
                    )
            return []

        for paper_id in paper_ids:
            paper_dimensions = {
                normalize_dimension(dimension).value
                for dimension, values in paper_ids_by_dimension.items()
                if str(paper_id) in {str(value) for value in values}
            }
            paper_thin_dimensions = [
                dimension for dimension in thin_dimensions
                if dimension.value not in paper_dimensions
            ]
            if not paper_thin_dimensions:
                continue
            before_rows = await db.execute(
                select(EvidenceRecord.dimension).where(
                    EvidenceRecord.synthesis_session_id == session_id,
                    EvidenceRecord.paper_id == paper_id,
                )
            )
            before_by_dimension = defaultdict(int)
            for dimension in before_rows.scalars().all():
                before_by_dimension[dimension] += 1
            await self.extract_paper_evidence(
                db,
                session_id=session_id,
                paper_id=paper_id,
                research_question=research_question,
                dimensions=paper_thin_dimensions,
                expanded=True,
            )
            after_rows = await db.execute(
                select(EvidenceRecord.dimension).where(
                    EvidenceRecord.synthesis_session_id == session_id,
                    EvidenceRecord.paper_id == paper_id,
                )
            )
            after_by_dimension = defaultdict(int)
            for dimension in after_rows.scalars().all():
                after_by_dimension[dimension] += 1
            for raw_dimension in paper_thin_dimensions:
                dimension = normalize_dimension(raw_dimension)
                triggered = dimension in [normalize_dimension(item) for item in thin_dimensions]
                await self._record_coverage_decision(
                    db, session_id=session_id, paper_id=paper_id,
                    dimension=dimension, cached_evidence_count=before_by_dimension[dimension.value],
                    threshold_reason=(
                        "fewer_than_two_papers_have_evidence"
                        if triggered else "dimension_meets_two_paper_coverage_threshold"
                    ),
                    expansion_triggered=triggered,
                    new_grounded_evidence_count=(
                        max(0, after_by_dimension[dimension.value] - before_by_dimension[dimension.value])
                        if triggered else 0
                    ),
                )
                if triggered and not max(0, after_by_dimension[dimension.value] - before_by_dimension[dimension.value]):
                    await self._record_coverage_decision(
                        db, session_id=session_id, paper_id=paper_id,
                        dimension=dimension, cached_evidence_count=before_by_dimension[dimension.value],
                        threshold_reason="dimension_marked_sparse",
                        expansion_triggered=False, new_grounded_evidence_count=0,
                    )
        return thin_dimensions

    async def _clear_downstream_outputs(self, db: AsyncSession, session_id: uuid.UUID) -> None:
        claim_ids_subquery = select(SynthesisClaim.id).where(
            SynthesisClaim.synthesis_session_id == session_id
        )
        await db.execute(
            delete(ClaimEvidenceLink).where(
                ClaimEvidenceLink.claim_id.in_(claim_ids_subquery)
            )
        )
        await db.execute(delete(Citation).where(Citation.synthesis_session_id == session_id))
        await db.execute(delete(SynthesisClaim).where(SynthesisClaim.synthesis_session_id == session_id))
        await db.execute(delete(SynthesisSection).where(SynthesisSection.synthesis_session_id == session_id))
        await db.flush()

    async def cross_paper_analysis(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        research_question: str,
    ) -> list[str]:
        evidence_result = await db.execute(
            select(EvidenceRecord, Paper, PageText)
            .join(Paper, EvidenceRecord.paper_id == Paper.id)
            .join(PageText, EvidenceRecord.page_text_id == PageText.id)
            .where(EvidenceRecord.synthesis_session_id == session_id)
            .where(EvidenceRecord.merged_into_id.is_(None))
            .order_by(Paper.year, Paper.title, EvidenceRecord.dimension)
        )
        evidence_rows = list(evidence_result.all())
        if not evidence_rows:
            raise ValueError("No grounded evidence is available for synthesis")

        evidence_by_id: dict[uuid.UUID, EvidenceRecord] = {}
        context_parts: list[str] = []
        for evidence, paper, page_text in evidence_rows:
            evidence_by_id[evidence.id] = evidence
            context_parts.append(
                "\n".join(
                    [
                        f"[evidence_id={evidence.id}]",
                        f"Paper: {paper.title} ({paper.year or 'n.d.'})",
                        f"Dimension: {evidence.dimension}",
                        f"Interpretation: {evidence.value}",
                        f"Verbatim quote: {evidence.quote}",
                        f"Page index: {page_text.page_number}",
                    ]
                )
            )

        with llm_trace(db, session_id, "propose_claims"):
            proposals = await synthesis_llm_service.propose_claims(
                research_question=research_question,
                evidence_context="\n\n".join(context_parts),
            )
        proposal_paper_counts = []
        for proposal in proposals.claims:
            proposal_paper_counts.append(len({
                evidence_by_id[item.evidence_id].paper_id
                for item in proposal.evidence
                if item.evidence_id in evidence_by_id
            }))
        await self._annotate_latest_llm_log(
            db, session_id=session_id, step_name="propose_claims",
            diagnostic={
                "proposal_diagnostics": {
                    "total_proposed_claims": len(proposals.claims),
                    "multi_paper_claims": sum(count >= 2 for count in proposal_paper_counts),
                    "single_paper_claims": sum(count == 1 for count in proposal_paper_counts),
                    "papers_per_claim": proposal_paper_counts,
                }
            },
        )

        await self._clear_downstream_outputs(db, session_id)
        supported_claim_ids: list[str] = []
        prepared = []
        for proposal in proposals.claims:
            # Deduplicate proposal links by evidence ID before creating a composite-PK
            # ClaimEvidenceLink row. Only canonical grounded evidence IDs are allowed.
            valid_link_by_evidence = {}
            for proposed_link in proposal.evidence:
                if proposed_link.evidence_id in evidence_by_id:
                    valid_link_by_evidence.setdefault(
                        proposed_link.evidence_id, proposed_link
                    )
            if not valid_link_by_evidence:
                continue

            evidence_texts = [
                f"{evidence_by_id[evidence_id].value} {evidence_by_id[evidence_id].quote}"
                for evidence_id in valid_link_by_evidence
            ]
            if guard_topic_absence_claim(proposal.statement, evidence_texts):
                continue

            claim = SynthesisClaim(
                id=uuid.uuid4(),
                synthesis_session_id=session_id,
                statement=proposal.statement,
                claim_type=DBSynthesisClaimType(proposal.claim_type.value),
                verification_status=DBEntailmentStatus.insufficient,
            )
            db.add(claim)
            evidence_items = [
                (
                    evidence_id,
                    evidence_by_id[evidence_id].value,
                    evidence_by_id[evidence_id].quote,
                )
                for evidence_id in valid_link_by_evidence
            ]
            prepared.append((claim, valid_link_by_evidence, evidence_items))

        if not prepared:
            raise ValueError("Cross-paper analysis produced no usable synthesis claims")

        try:
            with llm_trace(db, session_id, "verify_claim_set_batch"):
                batch_output = await synthesis_llm_service.verify_claim_set_batch(
                    claims_with_evidence=[
                        (claim.id, claim.statement, evidence_items)
                        for claim, _links, evidence_items in prepared
                    ]
                )
            batch_error = None
            if not batch_verification_is_complete(batch_output, len(prepared)):
                with llm_trace(db, session_id, "verify_claim_set_batch_retry"):
                    retry_output = await synthesis_llm_service.verify_claim_set_batch(
                        claims_with_evidence=[
                            (claim.id, claim.statement, evidence_items)
                            for claim, _links, evidence_items in prepared
                        ]
                    )
                batch_output = retry_output
        except Exception as exc:
            batch_error = f"schema/parse failure: {type(exc).__name__}: {str(exc)[:300]}"
            batch_output = ClaimVerificationBatchOutput(decisions=[])
        expected_ids = {claim.id for claim, _links, _items in prepared}
        returned_ids = [item.claim_id for item in batch_output.decisions]
        duplicate_ids = {item for item in returned_ids if returned_ids.count(item) > 1}
        unknown_claim_ids = {item for item in returned_ids if item not in expected_ids}
        decisions, fallback_ids = reconcile_claim_verification_batch(
            batch_output,
            expected_ids,
        )
        await increment_metric(db, session_id, "claim_verification_count", len(prepared))

        for claim, valid_link_by_evidence, evidence_items in prepared:
            decision = decisions.get(claim.id)
            if claim.id in fallback_ids:
                fallback_reason = (
                    batch_error
                    or ("duplicate decision" if claim.id in duplicate_ids else None)
                    or ("unknown claim ID" if unknown_claim_ids else None)
                    or "missing batch decision"
                )
                try:
                    with llm_trace(db, session_id, "verify_claim_set_fallback"):
                        decision = await synthesis_llm_service.verify_claim_set(
                            claim_statement=claim.statement,
                            evidence_items=evidence_items,
                        )
                except Exception as exc:
                    decision = ClaimVerificationDecision(
                        status="insufficient",
                        evidence_ids=[],
                        reason=f"Verification fallback failed: {str(exc)[:1000]}",
                    )
                await self._annotate_latest_llm_log(
                    db, session_id=session_id, step_name="verify_claim_set_fallback",
                    diagnostic={"fallback_reason": fallback_reason, "claim_id": str(claim.id)},
                )
            assert decision is not None
            sanitized = sanitize_claim_verification(
                decision,
                set(valid_link_by_evidence),
            )
            decision_status = DBEntailmentStatus(sanitized.status.value)
            verdict_evidence_ids = set(sanitized.evidence_ids)

            claim.verification_status = decision_status
            if sanitized.had_unknown_ids:
                claim.verification_reason = (
                    "Decisive verification verdict rejected because the LLM "
                    "referenced evidence IDs outside the grounded evidence set. "
                    f"LLM reason: {decision.reason}"
                )
            else:
                claim.verification_reason = decision.reason
            if sanitized.had_unknown_ids and claim.id in fallback_ids:
                await self._annotate_latest_llm_log(
                    db, session_id=session_id, step_name="verify_claim_set_fallback",
                    diagnostic={
                        "fallback_reason": "sanitation rejection: invalid/unknown evidence ID",
                        "claim_id": str(claim.id),
                    },
                )

            for evidence_id, proposed_link in valid_link_by_evidence.items():
                link_status = (
                    decision_status
                    if evidence_id in verdict_evidence_ids
                    else DBEntailmentStatus.insufficient
                )
                db.add(
                    ClaimEvidenceLink(
                        claim_id=claim.id,
                        evidence_id=evidence_id,
                        relation=DBEvidenceRelation(proposed_link.relation.value),
                        entailment_status=link_status,
                        verified_at=_now_utc(),
                    )
                )

            if decision_status == DBEntailmentStatus.supported:
                supported_claim_ids.append(str(claim.id))

        await db.flush()
        if not supported_claim_ids:
            raise ValueError("Cross-paper analysis produced no supported synthesis claims")
        return supported_claim_ids

    async def deduplicate_evidence(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
    ) -> int:
        """Mark definite same-paper/dimension semantic duplicates for audit.

        The LLM receives only persisted interpretations and verbatim quotes. Any
        provider failure or invalid/cross-group response leaves every record active.
        """
        result = await db.execute(
            select(EvidenceRecord, Paper)
            .join(Paper, Paper.id == EvidenceRecord.paper_id)
            .where(
                EvidenceRecord.synthesis_session_id == session_id,
                EvidenceRecord.merged_into_id.is_(None),
            )
            .order_by(EvidenceRecord.paper_id, EvidenceRecord.dimension, EvidenceRecord.created_at)
        )
        grouped: defaultdict[tuple[uuid.UUID, str], list[tuple[EvidenceRecord, Paper]]] = defaultdict(list)
        for evidence, paper in result.all():
            grouped[(evidence.paper_id, evidence.dimension)].append((evidence, paper))

        candidate_groups = {key: rows for key, rows in grouped.items() if len(rows) > 1}
        if not candidate_groups:
            return 0

        group_by_id: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
        context_groups: list[str] = []
        for group_index, (group_key, rows) in enumerate(candidate_groups.items(), start=1):
            paper_id, dimension = group_key
            context_items = [
                f"[group={group_index}] Paper: {rows[0][1].title}\nDimension: {dimension}"
            ]
            for evidence, _paper in rows:
                group_by_id[evidence.id] = group_key
                context_items.append(
                    f"[evidence_id={evidence.id}]\nInterpretation: {evidence.value}\n"
                    f"Verbatim quote: {evidence.quote}"
                )
            context_groups.append("\n".join(context_items))

        with llm_trace(db, session_id, "deduplicate_evidence"):
            output = await synthesis_llm_service.deduplicate_evidence_batch(
                evidence_context="\n\n--- NEXT GROUP ---\n\n".join(context_groups)
            )
        merges = sanitize_evidence_deduplication(
            decisions=output.groups,
            group_by_id=group_by_id,
        )
        if not merges:
            return 0

        evidence_by_id = {
            evidence.id: evidence
            for rows in candidate_groups.values()
            for evidence, _paper in rows
        }
        for duplicate_id, (keep_id, reason) in merges.items():
            evidence_by_id[duplicate_id].merged_into_id = keep_id
            evidence_by_id[duplicate_id].merge_reason = reason
        await db.flush()
        return len(merges)

    async def build_outline(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        research_question: str,
    ) -> list[str]:
        rows = await db.execute(
            select(SynthesisClaim, ClaimEvidenceLink, EvidenceRecord)
            .join(ClaimEvidenceLink, ClaimEvidenceLink.claim_id == SynthesisClaim.id)
            .join(EvidenceRecord, EvidenceRecord.id == ClaimEvidenceLink.evidence_id)
            .where(
                SynthesisClaim.synthesis_session_id == session_id,
                SynthesisClaim.verification_status == DBEntailmentStatus.supported,
                ClaimEvidenceLink.entailment_status == DBEntailmentStatus.supported,
            )
            .order_by(SynthesisClaim.created_at)
        )
        claim_rows = list(rows.all())
        if not claim_rows:
            raise ValueError("No verified claims available for outline generation")

        claim_map: dict[uuid.UUID, SynthesisClaim] = {}
        evidence_by_claim: defaultdict[uuid.UUID, list[EvidenceRecord]] = defaultdict(list)
        paper_ids_by_claim: defaultdict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for claim, _link, evidence in claim_rows:
            claim_map[claim.id] = claim
            evidence_by_claim[claim.id].append(evidence)
            paper_ids_by_claim[claim.id].add(evidence.paper_id)

        context = []
        for claim_id, claim in claim_map.items():
            claim_dimensions = sorted({e.dimension for e in evidence_by_claim[claim_id]})
            context.append(
                f"[claim_id={claim_id}] type={claim.claim_type.value}\n"
                f"{claim.statement}\n"
                f"Evidence dimensions: {', '.join(claim_dimensions)}\n"
                f"Supported by evidence IDs: "
                + ", ".join(str(e.id) for e in evidence_by_claim[claim_id])
            )

        with llm_trace(db, session_id, "build_outline"):
            outline = await synthesis_llm_service.build_outline(
                research_question=research_question,
                claims_context="\n\n".join(context),
            )
        outline = ensure_paper_outline_coverage(
            outline=outline,
            paper_ids_by_claim=dict(paper_ids_by_claim),
        )

        # Idempotent downstream reset without deleting the verified claims.
        await db.execute(
            update(SynthesisClaim)
            .where(SynthesisClaim.synthesis_session_id == session_id)
            .values(section_id=None)
        )
        await db.execute(delete(Citation).where(Citation.synthesis_session_id == session_id))
        await db.execute(delete(SynthesisSection).where(SynthesisSection.synthesis_session_id == session_id))
        await db.flush()

        assigned: set[uuid.UUID] = set()
        section_ids: list[str] = []
        ordered_proposals = sorted(outline.sections, key=lambda item: item.position)
        for position, proposal in enumerate(ordered_proposals):
            valid_claim_ids = [
                claim_id
                for claim_id in proposal.claim_ids
                if claim_id in claim_map and claim_id not in assigned
            ]
            if not valid_claim_ids:
                continue

            section = SynthesisSection(
                id=uuid.uuid4(),
                synthesis_session_id=session_id,
                title=proposal.title,
                position=position,
            )
            db.add(section)
            for claim_id in valid_claim_ids:
                claim_map[claim_id].section_id = section.id
                assigned.add(claim_id)
            section_ids.append(str(section.id))

        await db.flush()
        if not section_ids:
            raise ValueError("Outline generation produced no usable sections")
        return section_ids

    async def draft_section(
        self,
        db: AsyncSession,
        *,
        section_id: uuid.UUID,
        research_question: str,
    ) -> dict:
        section_result = await db.execute(
            select(SynthesisSection).where(SynthesisSection.id == section_id)
        )
        section = section_result.scalar_one_or_none()
        if section is None:
            raise ValueError(f"Section {section_id} not found")

        rows = await db.execute(
            select(SynthesisClaim, ClaimEvidenceLink, EvidenceRecord, Paper)
            .join(ClaimEvidenceLink, ClaimEvidenceLink.claim_id == SynthesisClaim.id)
            .join(EvidenceRecord, EvidenceRecord.id == ClaimEvidenceLink.evidence_id)
            .join(Paper, Paper.id == EvidenceRecord.paper_id)
            .where(
                SynthesisClaim.section_id == section_id,
                SynthesisClaim.verification_status == DBEntailmentStatus.supported,
                ClaimEvidenceLink.entailment_status == DBEntailmentStatus.supported,
            )
            .order_by(SynthesisClaim.created_at)
        )
        claim_rows = list(rows.all())
        if not claim_rows:
            raise ValueError(f"Section {section_id} has no supported claims")

        claim_ids: set[uuid.UUID] = set()
        evidence_paper_ids: list[str] = []
        represented_dimensions: set[str] = set()
        claim_types = []
        context_parts: list[str] = []
        for claim, _link, evidence, paper in claim_rows:
            claim_ids.add(claim.id)
            evidence_paper_ids.append(str(evidence.paper_id))
            represented_dimensions.add(getattr(evidence, "dimension", "unknown"))
            claim_types.append(claim.claim_type)
            context_parts.append(
                f"[claim_id={claim.id}] {claim.statement}\n"
                f"Evidence from {paper.title}: {evidence.value}\n"
                f"Quote: {evidence.quote}"
            )

        coverage = evaluate_section_coverage(
            evidence_paper_ids=evidence_paper_ids,
            claim_types=claim_types,
        )
        suggested_length = (
            "80-150 words" if len(claim_ids) <= 1
            else "150-250 words" if len(claim_ids) == 2
            else "220-400 words"
        )
        sentences: list[dict] = []
        for _draft_attempt in range(2):
            with llm_trace(db, section.synthesis_session_id, "draft_section"):
                output = await synthesis_llm_service.draft_section(
                    research_question=research_question,
                    section_title=section.title,
                    claims_context="\n\n".join(context_parts),
                    suggested_length=suggested_length,
                )
            sentences = []
            for item in output.sentences:
                valid_claim_ids = [claim_id for claim_id in item.claim_ids if claim_id in claim_ids]
                if not valid_claim_ids:
                    continue
                sentences.append(
                    {
                        "sentence": item.sentence.strip(),
                        "sentence_type": item.sentence_type.value,
                        "claim_ids": [str(claim_id) for claim_id in valid_claim_ids],
                    }
                )
            if sentences:
                break
        if not sentences:
            raise ValueError(f"Section {section_id} draft contained no traceable sentences")

        return {
            "section_id": str(section.id),
            "title": section.title,
            "position": section.position,
            "coverage": coverage.model_dump(),
            "verified_claim_count": len(claim_ids),
            "assigned_claim_count": len(claim_ids),
            "distinct_paper_count": len(set(evidence_paper_ids)),
            "single_paper_multi_claim_flag": len(claim_ids) > 1 and len(set(evidence_paper_ids)) == 1,
            "evidence_count": len(claim_rows),
            "dimensions_represented": sorted(represented_dimensions),
            "raw_draft_word_count": sum(
                len(item["sentence"].split()) for item in sentences
            ),
            "sentences": sentences,
        }

    async def qa_drafted_review(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        drafted_sections: list[dict],
    ) -> tuple[list[dict], str | None]:
        claim_rows = await db.execute(
            select(SynthesisClaim, ClaimEvidenceLink, EvidenceRecord, Paper)
            .join(ClaimEvidenceLink, ClaimEvidenceLink.claim_id == SynthesisClaim.id)
            .join(EvidenceRecord, EvidenceRecord.id == ClaimEvidenceLink.evidence_id)
            .join(Paper, Paper.id == EvidenceRecord.paper_id)
            .where(
                SynthesisClaim.synthesis_session_id == session_id,
                SynthesisClaim.verification_status == DBEntailmentStatus.supported,
                ClaimEvidenceLink.entailment_status == DBEntailmentStatus.supported,
            )
        )
        context_by_claim: defaultdict[str, list[str]] = defaultdict(list)
        statement_by_claim: dict[str, str] = {}
        for claim, _link, evidence, paper in claim_rows.all():
            claim_id = str(claim.id)
            statement_by_claim[claim_id] = claim.statement
            context_by_claim[claim_id].append(
                f"Paper: {paper.title}\nDimension: {evidence.dimension}\n"
                f"Interpreted value: {evidence.value}\nExact quote: {evidence.quote}"
            )

        qa_items: list[str] = []
        for section in drafted_sections:
            section_id = str(section.get("section_id"))
            for index, sentence in enumerate(section.get("sentences", [])):
                sentence_id = f"{section_id}:{index}"
                claim_ids = [str(value) for value in sentence.get("claim_ids", [])]
                claim_context = []
                for claim_id in claim_ids:
                    claim_context.append(
                        f"Claim {claim_id}: {statement_by_claim.get(claim_id, '[missing]')}\n"
                        + "\n".join(context_by_claim.get(claim_id, ["[no supported evidence]"]))
                    )
                qa_items.append(
                    f"[sentence_id={sentence_id}]\nType: {sentence.get('sentence_type', 'claim')}\n"
                    f"Sentence: {sentence.get('sentence', '')}\n" + "\n".join(claim_context)
                )

        with llm_trace(db, session_id, "qa_review"):
            output = await synthesis_llm_service.qa_review_batch(
                qa_context="\n\n---\n\n".join(qa_items)
            )
        verdicts = {item.sentence_id: item.verdict.value for item in output.sentence_checks}
        filtered, warning_ids = apply_sentence_qa(drafted_sections, verdicts)
        qa_warning = (
            f"QA flagged {len(warning_ids)} sentence(s) for human review."
            if warning_ids else None
        )
        return filtered, qa_warning

    async def finalize_review(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        drafted_sections: list[dict],
        qa_warning: str | None = None,
    ) -> str:
        session_result = await db.execute(
            select(SynthesisSession).where(SynthesisSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Synthesis session {session_id} not found")

        rows = await db.execute(
            select(SynthesisClaim, ClaimEvidenceLink, EvidenceRecord, PageText)
            .join(ClaimEvidenceLink, ClaimEvidenceLink.claim_id == SynthesisClaim.id)
            .join(EvidenceRecord, EvidenceRecord.id == ClaimEvidenceLink.evidence_id)
            .join(PageText, PageText.id == EvidenceRecord.page_text_id)
            .where(
                SynthesisClaim.synthesis_session_id == session_id,
                SynthesisClaim.verification_status == DBEntailmentStatus.supported,
                ClaimEvidenceLink.entailment_status == DBEntailmentStatus.supported,
            )
        )
        claim_to_evidence: defaultdict[uuid.UUID, list[tuple[EvidenceRecord, PageText]]] = defaultdict(list)
        for claim, _link, evidence, page_text in rows.all():
            claim_to_evidence[claim.id].append((evidence, page_text))

        selected_paper_ids = uuid_paper_ids(session.paper_ids or [])
        supported_paper_ids = {
            evidence.paper_id
            for evidence_items in claim_to_evidence.values()
            for evidence, _page_text in evidence_items
        }
        missing_supported_papers = [
            paper_id for paper_id in selected_paper_ids if paper_id not in supported_paper_ids
        ]
        if missing_supported_papers:
            paper_rows = await db.execute(
                select(Paper.title).where(Paper.id.in_(missing_supported_papers))
            )
            raise ValueError(
                "Tổng quan chưa có claim được kiểm chứng cho: "
                + "; ".join(paper_rows.scalars().all())
            )

        paper_order = {
            paper_id: index + 1
            for index, paper_id in enumerate(selected_paper_ids)
        }
        await db.execute(delete(Citation).where(Citation.synthesis_session_id == session_id))

        ordered_sections = sorted(drafted_sections, key=lambda item: int(item["position"]))
        review_parts: list[str] = []
        cursor = 0
        factual_sentence_count = 0
        section_metrics: list[dict] = []

        def append(text: str) -> None:
            nonlocal cursor
            review_parts.append(text)
            cursor += len(text)

        for section_payload in ordered_sections:
            section_id = uuid.UUID(str(section_payload["section_id"]))
            section_result = await db.execute(
                select(SynthesisSection).where(SynthesisSection.id == section_id)
            )
            section = section_result.scalar_one_or_none()
            if section is None:
                continue

            heading = f"## {section.title}\n\n"
            append(heading)
            section_parts: list[str] = []
            stored_sentences: list[dict] = []

            for sentence_payload in section_payload.get("sentences", []):
                sentence = str(sentence_payload.get("sentence", "")).strip()
                if not sentence:
                    continue

                evidence_candidates: list[tuple[EvidenceRecord, PageText]] = []
                for raw_claim_id in sentence_payload.get("claim_ids", []):
                    try:
                        claim_id = uuid.UUID(str(raw_claim_id))
                    except ValueError:
                        continue
                    evidence_candidates.extend(claim_to_evidence.get(claim_id, []))

                # One exact evidence span per paper is sufficient for a sentence-level
                # marker; repeated evidence from the same paper would render [1][1].
                evidence_by_paper: dict[uuid.UUID, tuple[EvidenceRecord, PageText]] = {}
                for evidence, page_text in evidence_candidates:
                    evidence_by_paper.setdefault(evidence.paper_id, (evidence, page_text))
                if not evidence_by_paper:
                    continue  # deterministic final guard: no unsupported prose

                sentence_type = sentence_payload.get("sentence_type", "claim")
                if sentence_type == "claim":
                    factual_sentence_count += 1
                append(sentence)
                section_sentence = sentence
                citation_ids: list[str] = []
                # Discourse prose remains traceable through claim_ids but does not
                # repeat inline citation markers unless it carries a factual claim.
                cited_papers = evidence_by_paper if sentence_type == "claim" else {}
                for paper_id in sorted(
                    cited_papers,
                    key=lambda pid: paper_order.get(pid, 10**9),
                ):
                    evidence, page_text = evidence_by_paper[paper_id]
                    display_number = paper_order.get(paper_id)
                    if display_number is None:
                        continue
                    marker = f"[{display_number}]"
                    marker_start = cursor
                    append(marker)
                    marker_end = cursor
                    section_sentence += marker
                    citation_id = uuid.uuid4()
                    citation_ids.append(str(citation_id))
                    db.add(
                        Citation(
                            id=citation_id,
                            synthesis_session_id=session_id,
                            paper_id=paper_id,
                            evidence_id=evidence.id,
                            citation_marker=marker,
                            review_char_start=marker_start,
                            review_char_end=marker_end,
                            source_page=page_text.page_number,
                            source_char_start=evidence.page_char_start,
                            source_char_end=evidence.page_char_end,
                            quoted_snippet=evidence.quote,
                        )
                    )

                append(" ")
                section_parts.append(section_sentence)
                stored_sentences.append({
                    "text": sentence,
                    "sentence_type": sentence_type,
                    "claim_ids": sentence_payload.get("claim_ids", []),
                    "citation_ids": citation_ids,
                })

            append("\n\n")
            section.draft = json.dumps({
                "tldr": " ".join(item["text"] for item in stored_sentences[:2]),
                "coverage": section_payload.get("coverage", {}),
                "sentences": stored_sentences,
            })
            section_metrics.append({
                "section_id": str(section.id),
                "title": section.title,
                "verified_claim_count": int(section_payload.get("verified_claim_count", 0)),
                "assigned_claim_count": int(section_payload.get("assigned_claim_count", 0)),
                "distinct_paper_count": int(section_payload.get("distinct_paper_count", 0)),
                "single_paper_multi_claim_flag": bool(section_payload.get("single_paper_multi_claim_flag", False)),
                "evidence_count": int(section_payload.get("evidence_count", 0)),
                "dimensions_represented": list(section_payload.get("dimensions_represented", [])),
                "raw_draft_word_count": int(section_payload.get("raw_draft_word_count", 0)),
                "post_qa_final_word_count": sum(
                    len(str(item.get("text", "")).split())
                    for item in stored_sentences
                ),
            })

        review_markdown = "".join(review_parts).strip()
        if not review_markdown:
            raise ValueError("Final review contains no traceable sentences")

        session.review_markdown = review_markdown
        session.status = SynthesisStatus.done
        session.qa_warning = qa_warning
        session.error_message = None
        await db.flush()
        await finalize_metrics(
            db,
            session_id=session_id,
            duration_ms=None,
            review_markdown=review_markdown,
            factual_sentence_count=factual_sentence_count,
            section_metrics=section_metrics,
        )
        return review_markdown

    async def mark_failed(self, db: AsyncSession, session_id: uuid.UUID, error: Exception | str) -> None:
        result = await db.execute(select(SynthesisSession).where(SynthesisSession.id == session_id))
        session = result.scalar_one_or_none()
        if session is not None:
            session.status = SynthesisStatus.failed
            session.error_message = str(error)[:4000]
            await db.flush()


synthesis_service = SynthesisService()
