"""Small normalization helpers for persisting search-provider paper metadata."""
from __future__ import annotations


def normalize_authors_for_db(authors) -> list[str]:
    """Normalize provider/front-end author values to PostgreSQL ``TEXT[]``."""
    if not authors:
        return []
    if isinstance(authors, str):
        return [part.strip() for part in authors.split(",") if part.strip()]
    return [str(item).strip() for item in authors if str(item).strip()]
