"""Deterministic application of structured post-draft QA verdicts."""
from __future__ import annotations

from copy import deepcopy


def apply_sentence_qa(
    drafted_sections: list[dict], verdicts: dict[str, str]
) -> tuple[list[dict], list[str]]:
    filtered = deepcopy(drafted_sections)
    warning_ids: list[str] = []
    for section in filtered:
        section_id = str(section.get("section_id"))
        kept = []
        for index, sentence in enumerate(section.get("sentences", [])):
            sentence_id = f"{section_id}:{index}"
            verdict = verdicts.get(sentence_id, "pass")
            if verdict == "blocked":
                continue
            if verdict == "warning":
                warning_ids.append(sentence_id)
            kept.append(sentence)
        section["sentences"] = kept
    return filtered, warning_ids
