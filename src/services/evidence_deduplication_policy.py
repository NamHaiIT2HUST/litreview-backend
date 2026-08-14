"""Fail-safe validation for LLM-proposed semantic evidence merges."""
from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence

from src.models.synthesis_schemas import EvidenceDuplicateGroup


def sanitize_evidence_deduplication(
    *,
    decisions: Sequence[EvidenceDuplicateGroup],
    group_by_id: Mapping[uuid.UUID, tuple[uuid.UUID, str]],
) -> dict[uuid.UUID, tuple[uuid.UUID, str]]:
    """Return duplicate->canonical mappings only when the whole batch is unambiguous.

    Unknown IDs, cross-paper/dimension decisions, duplicate ownership conflicts, and
    chained/cyclic merges invalidate the batch. Fail-safe means retaining everything.
    """
    merges: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
    keep_ids: set[uuid.UUID] = set()

    for decision in decisions:
        keep_group = group_by_id.get(decision.keep_id)
        if keep_group is None or decision.keep_id in decision.duplicate_ids:
            return {}
        keep_ids.add(decision.keep_id)
        for duplicate_id in decision.duplicate_ids:
            if group_by_id.get(duplicate_id) != keep_group:
                return {}
            existing = merges.get(duplicate_id)
            if existing is not None and existing[0] != decision.keep_id:
                return {}
            merges[duplicate_id] = (decision.keep_id, decision.reason.strip())

    if keep_ids.intersection(merges):
        return {}
    return merges
