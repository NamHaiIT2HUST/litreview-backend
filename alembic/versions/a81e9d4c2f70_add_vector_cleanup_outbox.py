"""add durable vector cleanup outbox

Revision ID: a81e9d4c2f70
Revises: 3f6c2d8a91b4
Create Date: 2026-08-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a81e9d4c2f70"
down_revision: Union[str, Sequence[str], None] = "3f6c2d8a91b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vector_cleanup_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vector_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vector_cleanup_jobs_paper_id", "vector_cleanup_jobs", ["paper_id"])
    op.create_index("ix_vector_cleanup_jobs_ingestion_id", "vector_cleanup_jobs", ["ingestion_id"])
    op.create_index("ix_vector_cleanup_jobs_status", "vector_cleanup_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_vector_cleanup_jobs_status", table_name="vector_cleanup_jobs")
    op.drop_index("ix_vector_cleanup_jobs_ingestion_id", table_name="vector_cleanup_jobs")
    op.drop_index("ix_vector_cleanup_jobs_paper_id", table_name="vector_cleanup_jobs")
    op.drop_table("vector_cleanup_jobs")
