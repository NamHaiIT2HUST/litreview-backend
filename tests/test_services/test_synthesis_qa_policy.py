from src.services.synthesis_qa_policy import apply_sentence_qa


def _draft():
    return [{
        "section_id": "s1",
        "title": "Methods",
        "position": 0,
        "coverage": {},
        "sentences": [
            {"sentence": "Supported sentence.", "claim_ids": ["c1"], "sentence_type": "claim"},
            {"sentence": "Overstated sentence.", "claim_ids": ["c2"], "sentence_type": "claim"},
        ],
    }]


def test_blocked_sentence_is_removed_before_citation_resolution():
    drafts, warnings = apply_sentence_qa(
        _draft(),
        {"s1:0": "pass", "s1:1": "blocked"},
    )
    assert [item["sentence"] for item in drafts[0]["sentences"]] == ["Supported sentence."]
    assert warnings == []


def test_warning_sentence_is_retained_and_reported():
    drafts, warnings = apply_sentence_qa(_draft(), {"s1:1": "warning"})
    assert len(drafts[0]["sentences"]) == 2
    assert warnings == ["s1:1"]
