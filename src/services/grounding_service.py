"""Deterministic evidence grounding against raw page text.

Grounding answers only one question: does the proposed verbatim quote exist in
our stored source representation, and if so where?  Semantic entailment is a
separate later step.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from sqlalchemy import select

from src.models.synthesis_schemas import EvidenceExtractionCandidate, GroundedEvidence


def _is_word_char(value: str) -> bool:
    return bool(value) and (value.isalnum() or value == "_")


def normalize_with_mapping(raw_text: str) -> tuple[str, list[int]]:
    """Normalize PDF extraction artifacts while retaining raw-index mapping.

    Rules are intentionally conservative:
    - Unicode NFKC per raw character;
    - collapse whitespace runs to one ASCII space;
    - remove line-break hyphenation only for word-char `x-\n y` patterns.

    The returned mapping contains, for every normalized character, the raw
    character index it came from.  We never store normalized offsets as source
    provenance.
    """
    normalized_chars: list[str] = []
    raw_indexes: list[int] = []
    i = 0
    length = len(raw_text)

    while i < length:
        char = raw_text[i]

        # PDF discretionary hyphenation. Parsers/LLMs may preserve the line
        # break ("sta-\ntistical") or collapse it to a space
        # ("sta- statistical"). Normalize both forms identically while only
        # joining alphabetic word fragments.
        if char == "-" and i > 0 and _is_word_char(raw_text[i - 1]):
            j = i + 1
            while j < length and raw_text[j].isspace():
                j += 1
            if (
                j > i + 1
                and j < length
                and raw_text[i - 1].isalpha()
                and raw_text[j].isalpha()
                and raw_text[j].islower()
            ):
                fragment_start = i - 1
                while fragment_start > 0 and raw_text[fragment_start - 1].isalpha():
                    fragment_start -= 1
                fragment = raw_text[fragment_start:i]
                # LLMs sometimes turn "sta-\ntistical" into
                # "sta- statistical", repeating the prefix. Skip only that
                # exact repeated fragment; all remaining characters must still
                # match exactly after normalization.
                if fragment and raw_text[j:j + len(fragment)].casefold() == fragment.casefold():
                    j += len(fragment)
                i = j
                continue

        if char.isspace():
            first_ws_index = i
            while i < length and raw_text[i].isspace():
                i += 1
            if normalized_chars and normalized_chars[-1] != " ":
                normalized_chars.append(" ")
                raw_indexes.append(first_ws_index)
            continue

        canonical = unicodedata.normalize("NFKC", char)
        for canonical_char in canonical:
            normalized_chars.append(canonical_char)
            raw_indexes.append(i)
        i += 1

    return "".join(normalized_chars), raw_indexes


def normalize_for_matching(raw_text: str) -> tuple[str, list[int]]:
    """Normalize text for matching and trim mapping in lockstep.

    ``normalize_with_mapping`` intentionally preserves a trailing collapsed
    whitespace character. Matching does not need leading/trailing whitespace,
    so this helper removes it from both the normalized text and its raw-index
    mapping. Keeping the two arrays aligned prevents offset drift.
    """
    normalized, mapping = normalize_with_mapping(raw_text)
    if not normalized or not mapping:
        return "", []

    left = 0
    right = len(normalized)
    while left < right and normalized[left].isspace():
        left += 1
    while right > left and normalized[right - 1].isspace():
        right -= 1
    return normalized[left:right], mapping[left:right]


def raw_window_from_ranges(
    raw_text: str,
    ranges: list[tuple[int, int]],
) -> tuple[int, int, str]:
    """Return one continuous raw page slice covering overlapping chunk ranges."""
    valid = [
        (max(0, int(start)), min(len(raw_text), int(end)))
        for start, end in ranges
        if start is not None and end is not None and int(end) > int(start)
    ]
    if not valid:
        raise ValueError("At least one valid raw-text range is required")
    window_start = min(start for start, _ in valid)
    window_end = max(end for _, end in valid)
    if window_end <= window_start:
        raise ValueError("Invalid raw-text window")
    return window_start, window_end, raw_text[window_start:window_end]

def locate_quote_in_raw_text(
    raw_text: str,
    quote: str,
    *,
    window_start: int = 0,
    window_end: int | None = None,
) -> tuple[int, int] | None:
    """Locate quote using normalization-exact matching, never fuzzy acceptance.

    Returned offsets are raw page-text offsets.  `None` means the quote could
    not be grounded and must be retried/rejected by the caller.
    """
    if not quote or not raw_text:
        return None

    end = len(raw_text) if window_end is None else min(window_end, len(raw_text))
    start = max(0, window_start)
    if end <= start:
        return None

    raw_window = raw_text[start:end]
    normalized_window, mapping = normalize_for_matching(raw_window)
    normalized_quote, _ = normalize_for_matching(quote)
    if not normalized_quote or not mapping:
        return None

    match_start = normalized_window.find(normalized_quote)
    if match_start < 0:
        return None

    match_end_inclusive = match_start + len(normalized_quote) - 1
    if match_end_inclusive >= len(mapping):
        return None

    raw_start = start + mapping[match_start]
    raw_end = start + mapping[match_end_inclusive] + 1
    return raw_start, raw_end


@dataclass(slots=True)
class GroundingWindow:
    anchor_chunk_id: object
    page_text_id: object
    page_number: int
    raw_start: int
    raw_end: int
    text: str


@dataclass(slots=True)
class GroundingOutcome:
    evidence: GroundedEvidence | None
    failure_reason: str | None = None

    @property
    def grounded(self) -> bool:
        return self.evidence is not None


class GroundingService:
    """Build canonical raw windows and ground extraction candidates in them."""

    async def build_window(self, db, *, source_chunk_id, paper_id) -> tuple[GroundingWindow | None, str | None]:
        # Import lazily so pure normalization tests do not initialize DB config.
        from src.models.db_models import PDFChunk, PageText

        chunk_result = await db.execute(
            select(PDFChunk).where(PDFChunk.id == source_chunk_id)
        )
        anchor = chunk_result.scalar_one_or_none()
        if anchor is None:
            return None, "unknown_chunk_id"
        if anchor.paper_id != paper_id:
            return None, "chunk_paper_mismatch"
        if anchor.page_text_id is None:
            return None, "chunk_missing_page_text"
        if anchor.chunk_index is None:
            return None, "chunk_missing_index"

        page_result = await db.execute(select(PageText).where(PageText.id == anchor.page_text_id))
        page_text = page_result.scalar_one_or_none()
        if page_text is None:
            return None, "page_text_not_found"

        neighbour_result = await db.execute(
            select(PDFChunk)
            .where(
                PDFChunk.page_text_id == anchor.page_text_id,
                PDFChunk.chunk_index >= max(0, anchor.chunk_index - 1),
                PDFChunk.chunk_index <= anchor.chunk_index + 1,
            )
            .order_by(PDFChunk.chunk_index)
        )
        neighbours = list(neighbour_result.scalars().all())
        ranges = [
            (chunk.page_char_start, chunk.page_char_end)
            for chunk in neighbours
            if chunk.page_char_start is not None and chunk.page_char_end is not None
        ]
        if not ranges:
            return None, "chunk_missing_offsets"

        try:
            window_start, window_end, window_text = raw_window_from_ranges(
                page_text.full_text, ranges
            )
        except ValueError:
            return None, "chunk_missing_offsets"

        return (
            GroundingWindow(
                anchor_chunk_id=anchor.id,
                page_text_id=page_text.id,
                page_number=page_text.page_number,
                raw_start=window_start,
                raw_end=window_end,
                text=window_text,
            ),
            None,
        )

    async def ground_candidate(self, db, candidate: EvidenceExtractionCandidate) -> GroundingOutcome:
        window, failure_reason = await self.build_window(
            db,
            source_chunk_id=candidate.source_chunk_id,
            paper_id=candidate.paper_id,
        )
        if window is None:
            return GroundingOutcome(None, failure_reason)

        located = locate_quote_in_raw_text(
            window.text,
            candidate.quote,
        )
        if located is None:
            return GroundingOutcome(None, "quote_not_found")

        relative_start, relative_end = located
        raw_start = window.raw_start + relative_start
        raw_end = window.raw_start + relative_end
        return GroundingOutcome(
            GroundedEvidence(
                **candidate.model_dump(),
                page_text_id=window.page_text_id,
                page_number=window.page_number,
                page_char_start=raw_start,
                page_char_end=raw_end,
            )
        )



async def build_anchor_contexts(
    db,
    *,
    paper_id,
    retrieved_documents,
    service=None,
) -> tuple[list[tuple[object, str]], set[object]]:
    """Turn vector-search hits into canonical continuous raw-page windows.

    Vector search is only an anchor selector. The LLM receives source text rebuilt
    from persisted PageText/PDFChunk offsets so evidence may cross the anchor
    chunk boundary without duplicating overlapped chunk text.
    """
    import uuid

    grounding = service or grounding_service
    contexts: list[tuple[object, str]] = []
    allowed_ids: set[object] = set()
    seen: set[object] = set()

    for document in retrieved_documents:
        raw_id = getattr(document, "metadata", {}).get("chunk_id")
        try:
            anchor_id = uuid.UUID(str(raw_id))
        except (TypeError, ValueError, AttributeError):
            continue
        if anchor_id in seen:
            continue
        seen.add(anchor_id)

        window, _failure_reason = await grounding.build_window(
            db,
            source_chunk_id=anchor_id,
            paper_id=paper_id,
        )
        if window is None:
            continue
        allowed_ids.add(anchor_id)
        contexts.append((anchor_id, window.text))

    return contexts, allowed_ids

grounding_service = GroundingService()
