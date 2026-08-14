"""add aggregate synthesis performance metrics

Revision ID: d42e5f607182
Revises: b91c2d3e4f50
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d42e5f607182"
down_revision: Union[str, Sequence[str], None] = "b91c2d3e4f50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "synthesis_metrics",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("synthesis_sessions.id"), nullable=False),
        sa.Column("total_llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_input_tokens", sa.Integer(), nullable=True),
        sa.Column("total_output_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_misses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("grounding_retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_verification_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synthesis_duration_ms", sa.Integer(), nullable=True),
        sa.Column("final_word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citation_coverage", sa.Float(), nullable=True),
        sa.Column("section_metrics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", name="uq_synthesis_metrics_session_id"),
    )
    op.create_index("ix_synthesis_metrics_session_id", "synthesis_metrics", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_synthesis_metrics_session_id", table_name="synthesis_metrics")
    op.drop_table("synthesis_metrics")
