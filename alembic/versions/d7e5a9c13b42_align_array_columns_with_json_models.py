"""align legacy PostgreSQL arrays with cross-database JSON models

Revision ID: d7e5a9c13b42
Revises: c2a4f7e91d03
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d7e5a9c13b42"
down_revision: Union[str, Sequence[str], None] = "c2a4f7e91d03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Earlier PostgreSQL-only migrations used text[]/uuid[]. Runtime models now
    # deliberately use JSON on SQLite and JSONB on PostgreSQL.
    op.execute(
        "ALTER TABLE projects ALTER COLUMN criteria_include TYPE jsonb "
        "USING to_jsonb(criteria_include)"
    )
    op.execute(
        "ALTER TABLE projects ALTER COLUMN criteria_exclude TYPE jsonb "
        "USING to_jsonb(criteria_exclude)"
    )
    op.execute(
        "ALTER TABLE papers ALTER COLUMN authors TYPE jsonb USING to_jsonb(authors)"
    )
    op.execute(
        "ALTER TABLE synthesis_sessions ALTER COLUMN paper_ids TYPE jsonb "
        "USING to_jsonb(paper_ids)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE synthesis_sessions ALTER COLUMN paper_ids TYPE uuid[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(paper_ids)::uuid)"
    )
    op.execute(
        "ALTER TABLE papers ALTER COLUMN authors TYPE text[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(authors))"
    )
    op.execute(
        "ALTER TABLE projects ALTER COLUMN criteria_exclude TYPE text[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(criteria_exclude))"
    )
    op.execute(
        "ALTER TABLE projects ALTER COLUMN criteria_include TYPE text[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(criteria_include))"
    )
