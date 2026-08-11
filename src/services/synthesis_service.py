"""Core literature-synthesis business logic.

This module deliberately keeps workflow orchestration out of the business
rules. LangGraph nodes call these methods; the methods own DB invariants,
evidence grounding, entailment, outline persistence and citation resolution.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings

from src.models.db_models import (
    Citation,
    ClaimEvidenceLink,
    EntailmentStatus as DBEntailmentStatus,
    EvidenceExtractionAttempt,
    EvidenceRecord,
    EvidenceRelation as DBEvidenceRelation,
    GroundingStatus as DBGroundingStatus,
    PageText,
    Paper,
    Project,
    SynthesisClaim,
    SynthesisClaimType as DBSynthesisClaimType,
    SynthesisSection,
    SynthesisSession,
    SynthesisStatus,
)
from src.models.synthesis_schemas import EvidenceExtractionCandidate
from src.services.claim_verification_policy import sanitize_claim_verification
from src.services.evidence_extraction_policy import should_retry_evidence_batch
from src.services.grounding_service import build_anchor_contexts, grounding_service
from src.services.synthesis_llm_service import synthesis_llm_service
from src.services.vector_store import vector_store_service


def _now_utc() -> datetime:
    return datetime.now(UTC)


class SynthesisService:
    async def prepare_session(self, db: AsyncSession, session_id: uuid.UUID) -> dict:
        result = await db.execute(
            select(SynthesisSession, Project)
            .join(Project, SynthesisSession.project_id == Project.id)
            .where(SynthesisSession.id == session_id)
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError(f"Synthesis session {session_id} not found")
        session, project = row

        paper_ids = list(session.paper_ids or [])
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
            "research_question": project.research_question,
            "paper_ids": [str(paper_id) for paper_id in paper_ids],
        }

    async def plan_dimensions(self, research_question: str) -> list[str]:
        result = await synthesis_llm_service.plan_dimensions(research_question)
        return result.dimensions

    async def extract_paper_evidence(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        paper_id: uuid.UUID,
        research_question: str,
        dimensions: list[str],
    ) -> list[str]:
        paper_result = await db.execute(select(Paper).where(Paper.id == paper_id))
        paper = paper_result.scalar_one_or_none()
        if paper is None:
            raise ValueError(f"Paper {paper_id} not found")
        if paper.active_ingestion_id is None:
            raise ValueError(f"Paper {paper_id} has not been ingested")

        grounded_ids: list[str] = []
        model_name = get_settings().model_name
        filters = {
            "$and": [
                {"paper_id": str(paper.id)},
                {"ingestion_id": str(paper.active_ingestion_id)},
            ]
        }

        for dimension in dimensions:
            query = f"{research_question}\nEvidence dimension: {dimension}"
            docs = await vector_store_service.search_similar_documents(
                query,
                top_k=6,
                filters=filters,
            )
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
                batch = await synthesis_llm_service.extract_evidence(
                    research_question=research_question,
                    dimension=dimension,
                    indexed_chunks=indexed_chunks,
                    exact_quote_only=attempt_number == 2,
                )
                if not batch.items:
                    # Empty output is a legitimate "no evidence in this context" result.
                    break

                had_grounding_failure = False
                for item in batch.items:
                    item_chunk_id = item.source_chunk_id
                    attempt = EvidenceExtractionAttempt(
                        id=uuid.uuid4(),
                        synthesis_session_id=session_id,
                        paper_id=paper_id,
                        dimension=dimension,
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

                    if item_chunk_id not in allowed_chunk_ids:
                        attempt.grounding_status = DBGroundingStatus.rejected
                        attempt.failure_reason = "chunk_id_not_in_retrieved_context"
                        had_grounding_failure = True
                        continue

                    candidate = EvidenceExtractionCandidate(
                        paper_id=paper_id,
                        dimension=dimension,
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
                            EvidenceRecord.dimension == dimension,
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
                            dimension=dimension,
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

        proposals = await synthesis_llm_service.propose_claims(
            research_question=research_question,
            evidence_context="\n\n".join(context_parts),
        )

        await self._clear_downstream_outputs(db, session_id)
        supported_claim_ids: list[str] = []

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
            decision = await synthesis_llm_service.verify_claim_set(
                claim_statement=claim.statement,
                evidence_items=evidence_items,
            )
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
        for claim, _link, evidence in claim_rows:
            claim_map[claim.id] = claim
            evidence_by_claim[claim.id].append(evidence)

        context = []
        for claim_id, claim in claim_map.items():
            context.append(
                f"[claim_id={claim_id}] type={claim.claim_type.value}\n"
                f"{claim.statement}\n"
                f"Supported by evidence IDs: "
                + ", ".join(str(e.id) for e in evidence_by_claim[claim_id])
            )

        outline = await synthesis_llm_service.build_outline(
            research_question=research_question,
            claims_context="\n\n".join(context),
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

        unassigned = [claim_id for claim_id in claim_map if claim_id not in assigned]
        if unassigned:
            section = SynthesisSection(
                id=uuid.uuid4(),
                synthesis_session_id=session_id,
                title="Additional findings",
                position=len(section_ids),
            )
            db.add(section)
            for claim_id in unassigned:
                claim_map[claim_id].section_id = section.id
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
        context_parts: list[str] = []
        for claim, _link, evidence, paper in claim_rows:
            claim_ids.add(claim.id)
            context_parts.append(
                f"[claim_id={claim.id}] {claim.statement}\n"
                f"Evidence from {paper.title}: {evidence.value}\n"
                f"Quote: {evidence.quote}"
            )

        output = await synthesis_llm_service.draft_section(
            research_question=research_question,
            section_title=section.title,
            claims_context="\n\n".join(context_parts),
        )

        sentences: list[dict] = []
        for item in output.sentences:
            valid_claim_ids = [claim_id for claim_id in item.claim_ids if claim_id in claim_ids]
            if not valid_claim_ids:
                continue
            sentences.append(
                {
                    "sentence": item.sentence.strip(),
                    "claim_ids": [str(claim_id) for claim_id in valid_claim_ids],
                }
            )
        if not sentences:
            raise ValueError(f"Section {section_id} draft contained no traceable sentences")

        return {
            "section_id": str(section.id),
            "title": section.title,
            "position": section.position,
            "sentences": sentences,
        }

    async def finalize_review(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        drafted_sections: list[dict],
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

        paper_order = {
            paper_id: index + 1 for index, paper_id in enumerate(list(session.paper_ids or []))
        }
        await db.execute(delete(Citation).where(Citation.synthesis_session_id == session_id))

        ordered_sections = sorted(drafted_sections, key=lambda item: int(item["position"]))
        review_parts: list[str] = []
        cursor = 0

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

                append(sentence)
                section_sentence = sentence
                for paper_id in sorted(
                    evidence_by_paper,
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
                    db.add(
                        Citation(
                            id=uuid.uuid4(),
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

            append("\n\n")
            section.draft = " ".join(section_parts)

        review_markdown = "".join(review_parts).strip()
        if not review_markdown:
            raise ValueError("Final review contains no traceable sentences")

        session.review_markdown = review_markdown
        session.status = SynthesisStatus.done
        session.error_message = None
        await db.flush()
        return review_markdown

    async def mark_failed(self, db: AsyncSession, session_id: uuid.UUID, error: Exception | str) -> None:
        result = await db.execute(select(SynthesisSession).where(SynthesisSession.id == session_id))
        session = result.scalar_one_or_none()
        if session is not None:
            session.status = SynthesisStatus.failed
            session.error_message = str(error)[:4000]
            await db.flush()


synthesis_service = SynthesisService()
