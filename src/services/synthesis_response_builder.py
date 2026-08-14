"""Build API-safe synthesis sections from persisted structured drafts."""

import json
from collections.abc import Iterable
from uuid import UUID

from src.models.synthesis_schemas import (
    SectionCoverage,
    SynthesisSectionResponse,
    SynthesisSentenceResponse,
)


def build_section_responses(sections: Iterable, valid_citation_ids: set[UUID]):
    responses = []
    for section in sections:
        try:
            payload = json.loads(section.draft or "{}")
            if not isinstance(payload, dict):
                raise ValueError("draft is not an object")
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}

        raw_coverage = payload.get("coverage") or {
            "status": "limited",
            "evidence_count": 0,
            "paper_count": 0,
            "retrieval_attempts": 1,
            "reasons": ["Legacy draft has no sentence-level provenance."],
        }
        sentences = []
        for raw in payload.get("sentences", []):
            citation_ids = [
                UUID(str(value)) for value in raw.get("citation_ids", [])
                if UUID(str(value)) in valid_citation_ids
            ]
            sentences.append(SynthesisSentenceResponse(
                text=raw.get("text", ""),
                sentence_type=raw.get("sentence_type", "claim"),
                claim_ids=[UUID(str(value)) for value in raw.get("claim_ids", [])],
                citation_ids=citation_ids,
            ))

        responses.append(SynthesisSectionResponse(
            id=section.id,
            title=section.title,
            position=section.position,
            tldr=payload.get("tldr"),
            coverage=SectionCoverage.model_validate(raw_coverage),
            sentences=sentences,
        ))
    return responses
