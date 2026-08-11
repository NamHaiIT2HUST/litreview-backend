import pytest
from src.services.grounding_service import locate_quote_in_raw_text, normalize_with_mapping


def test_normalization_collapses_whitespace_but_maps_back_to_raw_offsets():
    raw = "Alpha\n   beta gamma"
    normalized, mapping = normalize_with_mapping(raw)

    assert normalized == "Alpha beta gamma"
    start = normalized.index("beta")
    raw_start = mapping[start]
    raw_end = mapping[start + len("beta") - 1] + 1
    assert raw[raw_start:raw_end] == "beta"


def test_locate_quote_handles_pdf_linebreak_hyphenation_without_fuzzy_acceptance():
    raw = "The proposed trans-\nformer significantly improved accuracy."
    quote = "The proposed transformer significantly improved accuracy."

    located = locate_quote_in_raw_text(raw, quote)

    assert located is not None
    start, end = located
    assert raw[start:end] == raw


def test_locate_quote_returns_none_when_meaning_changed_even_if_words_overlap():
    raw = "The intervention did not significantly improve accuracy."
    changed = "The intervention significantly improved accuracy."

    assert locate_quote_in_raw_text(raw, changed) is None


def test_raw_window_uses_page_slice_not_overlapping_chunk_concatenation():
    from src.services.grounding_service import raw_window_from_ranges

    page_text = "0123456789ABCDEFGHIJ"
    start, end, window = raw_window_from_ranges(
        page_text,
        [(2, 10), (7, 15)],
    )

    assert (start, end) == (2, 15)
    assert window == page_text[2:15]
    assert window == "23456789ABCDE"

@pytest.mark.asyncio
async def test_build_anchor_contexts_uses_raw_grounding_windows_not_retrieved_chunk_text():
    import uuid
    from types import SimpleNamespace

    from src.services.grounding_service import GroundingWindow, build_anchor_contexts

    anchor_id = uuid.uuid4()
    paper_id = uuid.uuid4()
    page_text_id = uuid.uuid4()
    retrieved = [
        SimpleNamespace(
            page_content="TRUNCATED RETRIEVED CHUNK",
            metadata={"chunk_id": str(anchor_id)},
        )
    ]

    class FakeGroundingService:
        async def build_window(self, db, *, source_chunk_id, paper_id):
            assert source_chunk_id == anchor_id
            return (
                GroundingWindow(
                    anchor_chunk_id=anchor_id,
                    page_text_id=page_text_id,
                    page_number=2,
                    raw_start=100,
                    raw_end=180,
                    text="sentence begins before anchor and ends after anchor",
                ),
                None,
            )

    contexts, allowed_ids = await build_anchor_contexts(
        object(),
        paper_id=paper_id,
        retrieved_documents=retrieved,
        service=FakeGroundingService(),
    )

    assert contexts == [
        (anchor_id, "sentence begins before anchor and ends after anchor")
    ]
    assert allowed_ids == {anchor_id}


def test_normalize_for_matching_trims_text_and_mapping_together():
    from src.services.grounding_service import normalize_for_matching

    raw = "\u00a0  Alpha beta  \n"
    normalized, mapping = normalize_for_matching(raw)

    assert normalized == "Alpha beta"
    assert raw[mapping[0]] == "A"
    assert raw[mapping[-1]] == "a"


def test_locate_quote_with_surrounding_whitespace_returns_content_offsets():
    raw = "PREFIX  Alpha\n beta  SUFFIX"
    quote = "  Alpha beta \n"

    located = locate_quote_in_raw_text(raw, quote)

    assert located is not None
    start, end = located
    assert raw[start:end] == "Alpha\n beta"
