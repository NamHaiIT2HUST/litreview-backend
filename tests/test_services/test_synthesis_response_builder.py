import json
from types import SimpleNamespace
from uuid import uuid4

from src.services.synthesis_response_builder import build_section_responses


def test_build_section_responses_preserves_sentence_provenance():
    citation_id = uuid4()
    section = SimpleNamespace(
        id=uuid4(),
        title="Main findings",
        position=0,
        draft=json.dumps({
            "tldr": "Short summary",
            "coverage": {
                "status": "sufficient",
                "evidence_count": 2,
                "paper_count": 2,
                "retrieval_attempts": 1,
                "reasons": [],
            },
            "sentences": [{
                "text": "Grounded finding.",
                "sentence_type": "claim",
                "claim_ids": [str(uuid4())],
                "citation_ids": [str(citation_id)],
            }],
        }),
    )

    [response] = build_section_responses([section], {citation_id})

    assert response.sentences[0].text == "Grounded finding."
    assert response.sentences[0].citation_ids == [citation_id]
    assert response.coverage.status == "sufficient"


def test_build_section_responses_handles_legacy_plain_text():
    section = SimpleNamespace(id=uuid4(), title="Legacy", position=1, draft="Old draft text")

    [response] = build_section_responses([section], set())

    assert response.sentences == []
    assert response.coverage.status == "limited"
