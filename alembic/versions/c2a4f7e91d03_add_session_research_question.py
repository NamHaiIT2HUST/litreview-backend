"""add per-session synthesis research question

Revision ID: c2a4f7e91d03
Revises: a81e9d4c2f70
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c2a4f7e91d03"
down_revision: Union[str, Sequence[str], None] = "a81e9d4c2f70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("synthesis_sessions") as batch_op:
        batch_op.add_column(sa.Column("research_question", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("qa_warning", sa.Text(), nullable=True))
    with op.batch_alter_table("evidence_records") as batch_op:
        batch_op.add_column(sa.Column("merged_into_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("merge_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_evidence_records_merged_into_id",
            "evidence_records",
            ["merged_into_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("synthesis_sessions.id"), nullable=False),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("dimension", sa.String(length=120), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retrieval_logs_session_id", "retrieval_logs", ["session_id"])
    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("synthesis_sessions.id"), nullable=False),
        sa.Column("step_name", sa.String(length=120), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prompt_json", sa.JSON(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_llm_call_logs_session_id", "llm_call_logs", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_logs_session_id", table_name="llm_call_logs")
    op.drop_table("llm_call_logs")
    op.drop_index("ix_retrieval_logs_session_id", table_name="retrieval_logs")
    op.drop_table("retrieval_logs")
    with op.batch_alter_table("evidence_records") as batch_op:
        batch_op.drop_constraint("fk_evidence_records_merged_into_id", type_="foreignkey")
        batch_op.drop_column("merge_reason")
        batch_op.drop_column("merged_into_id")
    with op.batch_alter_table("synthesis_sessions") as batch_op:
        batch_op.drop_column("qa_warning")
        batch_op.drop_column("research_question")
