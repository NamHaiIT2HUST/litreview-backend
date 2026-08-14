from types import SimpleNamespace

import pytest

from src.models.synthesis_schemas import EvidenceDimension


def test_paper_content_hash_is_ordered_and_changes_with_source_content():
    from src.services.generic_evidence_cache_service import paper_content_hash

    pages = [
        SimpleNamespace(page_number=1, content_hash="bbb"),
        SimpleNamespace(page_number=0, content_hash="aaa"),
    ]
    assert paper_content_hash(pages) == paper_content_hash(list(reversed(pages)))
    changed = [
        SimpleNamespace(page_number=0, content_hash="aaa"),
        SimpleNamespace(page_number=1, content_hash="changed"),
    ]
    assert paper_content_hash(pages) != paper_content_hash(changed)


def test_dimension_context_failure_reports_cross_dimension_prompt_mapping():
    from src.services.generic_evidence_cache_service import _dimension_context_failure

    chunk_a = "00000000-0000-0000-0000-000000000001"
    chunk_b = "00000000-0000-0000-0000-000000000002"
    item = SimpleNamespace(source_chunk_id=chunk_b, quote="verbatim quote")
    details = _dimension_context_failure(
        item=item,
        dimension=EvidenceDimension.objective,
        allowed={EvidenceDimension.objective: {chunk_a}, EvidenceDimension.method: {chunk_b}},
        contexts={
            EvidenceDimension.objective: [(chunk_a, "objective context")],
            EvidenceDimension.method: [(chunk_b, "method context")],
        },
    )

    assert '"exists_in_other_dimension_context": true' in details
    assert '"other_dimensions": ["method"]' in details
    assert '"prompt_context_dimensions": ["method"]' in details
    assert "verbatim quote" in details


def test_prompt_union_accepts_objective_evidence_from_evaluation_bucket():
    from src.services.generic_evidence_cache_service import _validate_prompt_chunk

    chunk = "00000000-0000-0000-0000-000000000010"
    item = SimpleNamespace(source_chunk_id=chunk, quote="The objective was to test SFP.")
    _validate_prompt_chunk(
        item=item,
        dimension=EvidenceDimension.objective,
        allowed={EvidenceDimension.evaluation: {chunk}},
        contexts={EvidenceDimension.evaluation: [(chunk, item.quote)]},
    )


def test_prompt_union_rejects_chunk_not_supplied_to_paper_prompt():
    from src.services.generic_evidence_cache_service import _validate_prompt_chunk

    supplied = "00000000-0000-0000-0000-000000000011"
    returned = "00000000-0000-0000-0000-000000000012"
    item = SimpleNamespace(source_chunk_id=returned, quote="unsupported")
    with pytest.raises(ValueError, match="outside its dimension context"):
        _validate_prompt_chunk(
            item=item,
            dimension=EvidenceDimension.objective,
            allowed={EvidenceDimension.evaluation: {supplied}},
            contexts={EvidenceDimension.evaluation: [(supplied, "supplied text")]},
        )


def test_valid_prompt_chunk_still_rejects_wrong_quote():
    from src.services.grounding_service import locate_quote_in_raw_text

    assert locate_quote_in_raw_text(
        "The objective was to test SFP.",
        "The objective was unrelated.",
    ) is None


def test_quote_failure_diagnostic_distinguishes_chunk_and_window_substrings():
    from src.services.generic_evidence_cache_service import _quote_failure_diagnostic

    item = SimpleNamespace(
        source_chunk_id="00000000-0000-0000-0000-000000000020",
        quote="A  method\nwas proposed.",
    )
    details = _quote_failure_diagnostic(
        item=item,
        chunk_text="A method was proposed.",
        window_text="Previous text. A method was proposed. Following text.",
    )
    assert '"exact_substring_in_chunk": true' in details
    assert '"exact_substring_in_grounding_window": true' in details


def test_quote_failure_diagnostic_identifies_paraphrase_or_truncation():
    from src.services.generic_evidence_cache_service import _quote_failure_diagnostic

    item = SimpleNamespace(
        source_chunk_id="00000000-0000-0000-0000-000000000021",
        quote="The method always converges.",
    )
    details = _quote_failure_diagnostic(
        item=item,
        chunk_text="The method converges under the stated assumptions.",
        window_text="The method converges under the stated assumptions.",
    )
    assert '"exact_substring_in_chunk": false' in details
    assert '"exact_substring_in_grounding_window": false' in details


def test_single_chunk_quote_policy_rejects_ellipsis_and_cross_chunk_text():
    from src.services.generic_evidence_cache_service import _quote_is_contiguous_in_chunk

    chunk = "The laptop computer was tested. The method converged."
    assert _quote_is_contiguous_in_chunk(
        quote="The laptop computer was tested.", chunk_text=chunk
    )
    assert not _quote_is_contiguous_in_chunk(
        quote="The laptops computer was tested.", chunk_text=chunk
    )
    assert not _quote_is_contiguous_in_chunk(
        quote="The laptop computer ... converged.", chunk_text=chunk
    )
    assert not _quote_is_contiguous_in_chunk(
        quote="The laptop computer was tested. Adjacent chunk text.", chunk_text=chunk
    )


def test_extraction_fingerprint_tracks_prompt_rules_schema_and_model(monkeypatch):
    from src.services.generic_evidence_cache_service import (
        GENERIC_EXTRACTION_PROMPT,
        extraction_fingerprint,
    )

    settings = SimpleNamespace(synthesis_llm_provider="gemini", synthesis_model="model-a")
    first = extraction_fingerprint(settings)
    assert first == extraction_fingerprint(settings)
    assert first != extraction_fingerprint(
        SimpleNamespace(synthesis_llm_provider="groq", synthesis_model="model-a")
    )
    assert first != extraction_fingerprint(
        SimpleNamespace(synthesis_llm_provider="gemini", synthesis_model="model-b")
    )
    assert "allowed source-chunk list" in GENERIC_EXTRACTION_PROMPT
    monkeypatch.setattr(
        "src.services.generic_evidence_cache_service.dimension_extraction_rules",
        lambda dimension: f"changed-{EvidenceDimension(dimension).value}",
    )
    assert first != extraction_fingerprint(settings)


@pytest.mark.asyncio
async def test_precompute_failure_returns_failed_cache(monkeypatch):
    from src.models.db_models import GenericEvidenceCache, GenericEvidenceCacheStatus
    from src.services import generic_evidence_cache_service as service

    paper = SimpleNamespace(
        id="paper-id",
        active_ingestion_id="ingestion-id",
        title="Paper",
    )
    failed_cache = GenericEvidenceCache(
        id="cache-id", paper_id=paper.id, content_hash="content",
        extraction_fingerprint="fingerprint", status=GenericEvidenceCacheStatus.failed,
        failure_reason="provider failure",
    )

    class Result:
        def scalars(self):
            return self

        def all(self):
            return []

    class DB:
        async def execute(self, _query):
            return Result()

    async def fail_cache(_db, **_kwargs):
        return failed_cache

    async def no_ready(_db, **_kwargs):
        return None

    async def fail_extract(**_kwargs):
        raise RuntimeError("provider failure")

    async def no_search(*_args, **_kwargs):
        return []

    monkeypatch.setattr(service, "paper_content_hash", lambda _pages: "content")
    monkeypatch.setattr(service, "extraction_fingerprint", lambda _settings: "fingerprint")
    monkeypatch.setattr(service, "lookup_ready_cache", no_ready)
    monkeypatch.setattr(service, "mark_cache_failed", fail_cache)
    monkeypatch.setattr(
        "src.services.synthesis_llm_service.synthesis_llm_service.extract_paper_evidence_batch",
        fail_extract,
    )
    monkeypatch.setattr(
        "src.services.vector_store.vector_store_service.search_similar_documents_with_scores",
        no_search,
    )
    monkeypatch.setattr("src.config.get_settings", lambda: SimpleNamespace())

    result = await service.precompute_generic_evidence(DB(), paper=paper)

    assert result is failed_cache
    assert result.status is GenericEvidenceCacheStatus.failed
