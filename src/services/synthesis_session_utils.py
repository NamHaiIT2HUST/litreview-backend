"""Small persistence conversions for synthesis sessions."""

from uuid import UUID


def json_paper_ids(paper_ids) -> list[str]:
    return [str(paper_id) for paper_id in paper_ids]


def uuid_paper_ids(paper_ids) -> list[UUID]:
    return [UUID(str(paper_id)) for paper_id in paper_ids]
