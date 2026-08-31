"""Identity helpers and persistence boundary for generic evidence caching."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Iterable

from sqlalchemy import delete, select

from src.models.db_models import (
    EvidenceExtractionAttempt,
    EvidenceRecord,
    GenericEvidenceCache,
    GenericEvidenceCacheItem,
    GenericEvidenceCacheStatus,
    GroundingStatus,
    PageText,
    PDFChunk,
)
from src.models.synthesis_schemas import EvidenceDimension, PaperEvidenceExtractionOutput
from src.services.grounding_service import normalize_for_matching
from src.services.synthesis_coverage_policy import (
    dimension_extraction_rules,
    dimension_retrieval_hint,
)

logger = logging.getLogger(__name__)


GENERIC_EXTRACTION_PROMPT = (
    "Extract auditable evidence for every requested literature-review dimension. "
    "Quotes must be verbatim and each item must use a supplied source chunk ID. "
    "For each dimension, source_chunk_id must be selected only from that dimension's "
    "allowed source-chunk list."
)


def _dimension_context_failure(
    *, item, dimension: EvidenceDimension, allowed: dict, contexts: dict,
) -> str:
    """Return bounded diagnostics for a rejected cross-dimension chunk ID."""
    returned_id = str(item.source_chunk_id)
    allowed_ids = [str(value) for value in allowed.get(dimension, set())]
    other_dimensions = [
        key.value if isinstance(key, EvidenceDimension) else str(key)
        for key, values in allowed.items()
        if key != dimension and item.source_chunk_id in values
    ]
    prompt_dimensions = []
    for key, indexed in contexts.items():
        if any(str(chunk_id) == returned_id for chunk_id, _text in indexed):
            prompt_dimensions.append(key.value if isinstance(key, EvidenceDimension) else str(key))
    return json.dumps({
        "failure": "precompute returned a chunk outside its dimension context",
        "dimension": dimension.value,
        "returned_source_chunk_id": returned_id,
        "allowed_chunk_ids": allowed_ids,
        "exists_in_other_dimension_context": bool(other_dimensions),
        "other_dimensions": other_dimensions,
        "prompt_context_dimensions": prompt_dimensions,
        "quote": str(item.quote)[:1000],
    }, ensure_ascii=False)


def _validate_prompt_chunk(*, item, dimension: EvidenceDimension, allowed: dict, contexts: dict) -> None:
    """Require a returned chunk to have been supplied somewhere in this paper prompt."""
    supplied_ids = {
        chunk_id
        for dimension_ids in allowed.values()
        for chunk_id in dimension_ids
    }
    if item.source_chunk_id not in supplied_ids:
        raise ValueError(_dimension_context_failure(
            item=item, dimension=dimension, allowed=allowed, contexts=contexts,
        ))


def _quote_failure_diagnostic(*, item, chunk_text: str | None, window_text: str | None) -> str:
    quote_normalized, _ = normalize_for_matching(str(item.quote))
    chunk_normalized, _ = normalize_for_matching(chunk_text or "")
    window_normalized, _ = normalize_for_matching(window_text or "")
    return json.dumps({
        "failure": "quote_not_found",
        "returned_source_chunk_id": str(item.source_chunk_id),
        "returned_quote": str(item.quote)[:2000],
        "actual_chunk_text": (chunk_text or "")[:4000],
        "normalized_quote": quote_normalized[:2000],
        "normalized_chunk_text": chunk_normalized[:4000],
        "normalized_window_text": window_normalized[:4000],
        "exact_substring_in_chunk": bool(quote_normalized and quote_normalized in chunk_normalized),
        "exact_substring_in_grounding_window": bool(quote_normalized and quote_normalized in window_normalized),
    }, ensure_ascii=False)


def _quote_is_contiguous_in_chunk(*, quote: str, chunk_text: str | None) -> bool:
    normalized_quote, _ = normalize_for_matching(quote)
    normalized_chunk, _ = normalize_for_matching(chunk_text or "")
    return bool(normalized_quote and normalized_quote in normalized_chunk)


def paper_content_hash(page_text_rows: Iterable[object]) -> str:
    payload = [
        [int(page.page_number), str(page.content_hash)]
        for page in sorted(page_text_rows, key=lambda value: int(value.page_number))
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def extraction_fingerprint(settings) -> str:
    semantics = {
        "prompt": GENERIC_EXTRACTION_PROMPT,
        "rules": {
            dimension.value: dimension_extraction_rules(dimension)
            for dimension in EvidenceDimension
        },
        "retrieval_hints": {
            dimension.value: dimension_retrieval_hint(dimension)
            for dimension in EvidenceDimension
        },
        "schema": PaperEvidenceExtractionOutput.model_json_schema(),
        "provider": settings.synthesis_llm_provider,
        "model": settings.synthesis_model,
    }
    normalized = json.dumps(semantics, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def lookup_ready_cache(
    db,
    *,
    paper_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    content_hash: str,
    fingerprint: str,
) -> GenericEvidenceCache | None:
    result = await db.execute(
        select(GenericEvidenceCache).where(
            GenericEvidenceCache.paper_id == paper_id,
            GenericEvidenceCache.ingestion_id == ingestion_id,
            GenericEvidenceCache.content_hash == content_hash,
            GenericEvidenceCache.extraction_fingerprint == fingerprint,
            GenericEvidenceCache.status == GenericEvidenceCacheStatus.ready,
        )
    )
    return result.scalar_one_or_none()


async def _lookup_cache_identity(db, *, paper_id, content_hash, fingerprint):
    result = await db.execute(select(GenericEvidenceCache).where(
        GenericEvidenceCache.paper_id == paper_id,
        GenericEvidenceCache.content_hash == content_hash,
        GenericEvidenceCache.extraction_fingerprint == fingerprint,
    ))
    return result.scalar_one_or_none()


async def materialize_cache(
    db,
    *,
    cache: GenericEvidenceCache,
    session_id: uuid.UUID,
) -> list[str]:
    rows = await db.execute(
        select(GenericEvidenceCacheItem, PageText, PDFChunk)
        .join(PageText, PageText.id == GenericEvidenceCacheItem.page_text_id)
        .join(PDFChunk, PDFChunk.id == GenericEvidenceCacheItem.source_chunk_id)
        .where(GenericEvidenceCacheItem.cache_id == cache.id)
    )
    evidence_ids: list[str] = []
    for item, page, chunk in rows.all():
        if page.ingestion_id != cache.ingestion_id or chunk.ingestion_id != cache.ingestion_id:
            raise ValueError("Cached evidence provenance does not belong to the active ingestion")
        existing_result = await db.execute(
            select(EvidenceRecord).where(
                EvidenceRecord.synthesis_session_id == session_id,
                EvidenceRecord.paper_id == item.paper_id,
                EvidenceRecord.dimension == item.dimension,
                EvidenceRecord.page_text_id == item.page_text_id,
                EvidenceRecord.page_char_start == item.page_char_start,
                EvidenceRecord.page_char_end == item.page_char_end,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is not None:
            evidence_ids.append(str(existing.id))
            continue
        attempt = EvidenceExtractionAttempt(
            id=uuid.uuid4(),
            synthesis_session_id=session_id,
            paper_id=item.paper_id,
            dimension=item.dimension,
            attempt_number=1,
            raw_value=item.value,
            raw_quote=item.quote,
            suggested_chunk_raw=str(item.source_chunk_id),
            suggested_chunk_id=item.source_chunk_id,
            grounding_status=GroundingStatus.grounded,
            model_name="generic-cache",
            prompt_version=cache.extraction_fingerprint[:80],
        )
        evidence = EvidenceRecord(
            id=uuid.uuid4(),
            synthesis_session_id=session_id,
            paper_id=item.paper_id,
            page_text_id=item.page_text_id,
            source_chunk_id=item.source_chunk_id,
            created_from_attempt_id=attempt.id,
            dimension=item.dimension,
            applies_to=item.applies_to,
            value=item.value,
            quote=item.quote,
            page_char_start=item.page_char_start,
            page_char_end=item.page_char_end,
        )
        db.add(attempt)
        db.add(evidence)
        evidence_ids.append(str(evidence.id))
    await db.flush()
    return evidence_ids


async def store_grounded_cache(
    db,
    *,
    paper_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    content_hash: str,
    fingerprint: str,
    evidence_records: Iterable[EvidenceRecord],
) -> GenericEvidenceCache:
    cache = await _lookup_cache_identity(
        db, paper_id=paper_id, content_hash=content_hash, fingerprint=fingerprint,
    )
    if cache is None:
        cache = GenericEvidenceCache(
            id=uuid.uuid4(), paper_id=paper_id, ingestion_id=ingestion_id,
            content_hash=content_hash, extraction_fingerprint=fingerprint,
        )
        db.add(cache)
    else:
        await db.execute(delete(GenericEvidenceCacheItem).where(
            GenericEvidenceCacheItem.cache_id == cache.id
        ))
    cache.ingestion_id = ingestion_id
    cache.status = GenericEvidenceCacheStatus.ready
    cache.failure_reason = None
    for evidence in evidence_records:
        db.add(GenericEvidenceCacheItem(
            id=uuid.uuid4(), cache_id=cache.id, paper_id=paper_id,
            dimension=evidence.dimension, applies_to=evidence.applies_to, value=evidence.value,
            quote=evidence.quote, page_text_id=evidence.page_text_id,
            source_chunk_id=evidence.source_chunk_id,
            page_char_start=evidence.page_char_start,
            page_char_end=evidence.page_char_end,
        ))
    await db.flush()
    return cache


async def mark_cache_failed(
    db, *, paper_id, ingestion_id, content_hash, fingerprint, error: Exception | str
):
    cache = await _lookup_cache_identity(
        db, paper_id=paper_id, content_hash=content_hash, fingerprint=fingerprint,
    )
    if cache is None:
        cache = GenericEvidenceCache(
            id=uuid.uuid4(), paper_id=paper_id, content_hash=content_hash,
            extraction_fingerprint=fingerprint,
        )
        db.add(cache)
    cache.ingestion_id = ingestion_id
    cache.status = GenericEvidenceCacheStatus.failed
    cache.failure_reason = str(error)[:4000]
    await db.flush()
    return cache


async def precompute_generic_evidence(db, *, paper) -> GenericEvidenceCache | None:
    """Populate generic cache after ingest; never propagate failure to ingestion."""
    from src.config import get_settings
    from src.models.synthesis_schemas import EvidenceExtractionCandidate
    from src.services.grounding_service import build_anchor_contexts, grounding_service
    from src.services.synthesis_coverage_policy import should_accept_dimension_scope
    from src.services.synthesis_llm_service import synthesis_llm_service
    from src.services.vector_store import vector_store_service

    page_result = await db.execute(select(PageText).where(
        PageText.paper_id == paper.id,
        PageText.ingestion_id == paper.active_ingestion_id,
    ))
    pages = list(page_result.scalars().all())
    content = paper_content_hash(pages)
    fingerprint = extraction_fingerprint(get_settings())
    try:
        existing = await lookup_ready_cache(
            db, paper_id=paper.id, ingestion_id=paper.active_ingestion_id,
            content_hash=content, fingerprint=fingerprint,
        )
        if existing is not None:
            return existing
        filters = {"$and": [
            {"paper_id": str(paper.id)},
            {"ingestion_id": str(paper.active_ingestion_id)},
        ]}
        contexts = {}
        allowed = {}
        for dimension in EvidenceDimension:
            query = "\n".join([
                paper.title,
                f"Evidence dimension: {dimension.value}",
                f"Search terms: {dimension_retrieval_hint(dimension)}",
            ])
            scored = await vector_store_service.search_similar_documents_with_scores(
                query, top_k=12 if dimension in {EvidenceDimension.dataset, EvidenceDimension.evaluation} else 6,
                filters=filters,
            )
            indexed, allowed_ids = await build_anchor_contexts(
                db, paper_id=paper.id,
                retrieved_documents=[document for document, _score in scored],
            )
            if indexed:
                contexts[dimension] = indexed
                allowed[dimension] = allowed_ids
        try:
            output = await synthesis_llm_service.extract_paper_evidence_batch(
                research_question="General literature review across the selected papers.",
                contexts_by_dimension=contexts,
                strict_dimension_ids=True,
                enforce_dimension_membership=False,
            )
        except Exception as e:
            # One paper's extraction failing (provider hiccup, malformed
            # response) used to raise and abort the whole cache precompute
            # batch. Skip just this paper's contribution instead.
            logger.warning(f"Failed to extract evidence from generic cache for paper {paper.id}: {e}")
            output = PaperEvidenceExtractionOutput(items=[])
        grounded_items = []
        for item in output.items:
            dimension = EvidenceDimension(item.dimension)
            if not should_accept_dimension_scope(dimension, item.applies_to):
                raise ValueError("precompute returned evidence with invalid dimension scope")
            _validate_prompt_chunk(
                item=item, dimension=dimension, allowed=allowed, contexts=contexts,
            )
            chunk_row = (await db.execute(
                select(PDFChunk).where(PDFChunk.id == item.source_chunk_id)
            )).scalar_one_or_none()
            if not _quote_is_contiguous_in_chunk(
                quote=item.quote,
                chunk_text=chunk_row.chunk_text if chunk_row else None,
            ):
                # Retry only this item against the selected chunk, never the paper.
                try:
                    retry = await synthesis_llm_service.extract_evidence(
                        research_question="General literature review across the selected papers.",
                        dimension=dimension,
                        indexed_chunks=[(
                            item.source_chunk_id,
                            chunk_row.chunk_text if chunk_row else "",
                        )],
                        exact_quote_only=True,
                    )
                except Exception:
                    # The individual item remains failed; do not discard other grounded items.
                    continue
                retry_item = next((candidate for candidate in retry.items if (
                    candidate.source_chunk_id == item.source_chunk_id
                    and _quote_is_contiguous_in_chunk(
                        quote=candidate.quote,
                        chunk_text=chunk_row.chunk_text if chunk_row else None,
                    )
                )), None)
                if retry_item is None:
                    # Keep this item failed while preserving valid evidence from the batch.
                    continue
                item = retry_item
            outcome = await grounding_service.ground_candidate(db, EvidenceExtractionCandidate(
                paper_id=paper.id, dimension=dimension, value=item.value,
                quote=item.quote, source_chunk_id=item.source_chunk_id,
            ))
            if not outcome.grounded:
                if outcome.failure_reason == "quote_not_found":
                    chunk_row = (await db.execute(
                        select(PDFChunk).where(PDFChunk.id == item.source_chunk_id)
                    )).scalar_one_or_none()
                    window, _ = await grounding_service.build_window(
                        db, source_chunk_id=item.source_chunk_id, paper_id=paper.id,
                    )
                    # Quote grounding remains fail-closed for this item only.
                    continue
                raise ValueError(outcome.failure_reason or "precompute grounding failed")
            grounded_items.append((outcome.evidence, item.applies_to.value))
        if not grounded_items:
            raise ValueError("precompute returned no grounded evidence")
        cache = await _lookup_cache_identity(
            db, paper_id=paper.id, content_hash=content, fingerprint=fingerprint,
        )
        if cache is None:
            cache = GenericEvidenceCache(
                id=uuid.uuid4(), paper_id=paper.id, content_hash=content,
                extraction_fingerprint=fingerprint,
            )
            db.add(cache)
        else:
            await db.execute(delete(GenericEvidenceCacheItem).where(
                GenericEvidenceCacheItem.cache_id == cache.id
            ))
        cache.ingestion_id = paper.active_ingestion_id
        cache.status = GenericEvidenceCacheStatus.ready
        cache.failure_reason = None
        for grounded, applies_to in grounded_items:
            db.add(GenericEvidenceCacheItem(
                id=uuid.uuid4(), cache_id=cache.id, paper_id=paper.id,
                dimension=grounded.dimension.value, applies_to=applies_to,
                value=grounded.value, quote=grounded.quote,
                page_text_id=grounded.page_text_id, source_chunk_id=grounded.source_chunk_id,
                page_char_start=grounded.page_char_start, page_char_end=grounded.page_char_end,
            ))
        await db.flush()
        return cache
    except Exception as exc:
        failed_cache = await mark_cache_failed(
            db, paper_id=paper.id, ingestion_id=paper.active_ingestion_id,
            content_hash=content, fingerprint=fingerprint, error=exc,
        )
        return failed_cache
