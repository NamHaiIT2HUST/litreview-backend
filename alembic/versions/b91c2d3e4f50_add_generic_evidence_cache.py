"""add session-independent generic evidence cache

Revision ID: b91c2d3e4f50
Revises: e8f6b0d24c53
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b91c2d3e4f50"
down_revision: Union[str, Sequence[str], None] = "e8f6b0d24c53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("evidence_records") as batch_op:
        batch_op.add_column(
            sa.Column("applies_to", sa.String(length=80), nullable=False, server_default="study")
        )
    op.create_table(
        "generic_evidence_caches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("ingestion_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extraction_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum("processing", "ready", "failed", name="genericevidencecachestatus"),
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "paper_id", "content_hash", "extraction_fingerprint",
            name="uq_generic_evidence_cache_identity",
        ),
    )
    op.create_index("ix_generic_evidence_caches_paper_id", "generic_evidence_caches", ["paper_id"])
    op.create_index("ix_generic_evidence_caches_ingestion_id", "generic_evidence_caches", ["ingestion_id"])
    op.create_table(
        "generic_evidence_cache_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "cache_id", sa.Uuid(),
            sa.ForeignKey("generic_evidence_caches.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("dimension", sa.String(length=120), nullable=False),
        sa.Column("applies_to", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("page_text_id", sa.Uuid(), sa.ForeignKey("page_texts.id"), nullable=False),
        sa.Column("source_chunk_id", sa.Uuid(), sa.ForeignKey("pdf_chunks.id"), nullable=False),
        sa.Column("page_char_start", sa.Integer(), nullable=False),
        sa.Column("page_char_end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("page_char_start >= 0", name="ck_generic_cache_item_start_nonnegative"),
        sa.CheckConstraint("page_char_end > page_char_start", name="ck_generic_cache_item_offsets_ordered"),
    )
    op.create_index("ix_generic_evidence_cache_items_cache_id", "generic_evidence_cache_items", ["cache_id"])


def downgrade() -> None:
    op.drop_index("ix_generic_evidence_cache_items_cache_id", table_name="generic_evidence_cache_items")
    op.drop_table("generic_evidence_cache_items")
    op.drop_index("ix_generic_evidence_caches_ingestion_id", table_name="generic_evidence_caches")
    op.drop_index("ix_generic_evidence_caches_paper_id", table_name="generic_evidence_caches")
    op.drop_table("generic_evidence_caches")
    with op.batch_alter_table("evidence_records") as batch_op:
        batch_op.drop_column("applies_to")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS genericevidencecachestatus")
