"""add synthesis evidence foundation

Revision ID: 3f6c2d8a91b4
Revises: 7bbe5d089b1c
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "3f6c2d8a91b4"
down_revision: Union[str, Sequence[str], None] = "7bbe5d089b1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Explicitly create PostgreSQL enum types once, then disable per-table type
    # creation. Some enums are reused by multiple synthesis tables.
    grounding_status = postgresql.ENUM(
        "pending", "grounded", "rejected", name="groundingstatus", create_type=False
    )
    entailment_status = postgresql.ENUM(
        "supported", "contradicted", "insufficient",
        name="entailmentstatus",
        create_type=False,
    )
    evidence_relation = postgresql.ENUM(
        "supports", "contradicts", "context", name="evidencerelation", create_type=False
    )
    claim_type = postgresql.ENUM(
        "agreement",
        "disagreement",
        "comparison",
        "trend",
        "gap",
        "descriptive",
        name="synthesisclaimtype",
        create_type=False,
    )

    bind = op.get_bind()
    grounding_status.create(bind, checkfirst=True)
    entailment_status.create(bind, checkfirst=True)
    evidence_relation.create(bind, checkfirst=True)
    claim_type.create(bind, checkfirst=True)

    op.add_column("papers", sa.Column("active_ingestion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("synthesis_sessions", sa.Column("error_message", sa.Text(), nullable=True))

    op.create_table(
        "page_texts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=120), nullable=False),
        sa.Column("parser_version", sa.String(length=120), nullable=False),
        sa.Column("ingestion_version", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("paper_id", "ingestion_id", "page_number", name="uq_page_text_ingestion_page"),
    )
    op.create_index(op.f("ix_page_texts_ingestion_id"), "page_texts", ["ingestion_id"], unique=False)

    op.add_column("pdf_chunks", sa.Column("page_text_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pdf_chunks", sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("pdf_chunks", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column("pdf_chunks", sa.Column("page_char_start", sa.Integer(), nullable=True))
    op.add_column("pdf_chunks", sa.Column("page_char_end", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_pdf_chunks_page_text_id", "pdf_chunks", "page_texts", ["page_text_id"], ["id"])
    op.create_index(op.f("ix_pdf_chunks_ingestion_id"), "pdf_chunks", ["ingestion_id"], unique=False)
    op.create_unique_constraint(
        "uq_pdf_chunk_ingestion_index",
        "pdf_chunks",
        ["paper_id", "ingestion_id", "page", "chunk_index"],
    )
    op.create_check_constraint("ck_pdf_chunk_start_nonnegative", "pdf_chunks", "page_char_start >= 0")
    op.create_check_constraint("ck_pdf_chunk_offsets_ordered", "pdf_chunks", "page_char_end > page_char_start")

    op.create_table(
        "evidence_extraction_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synthesis_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(length=120), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("raw_quote", sa.Text(), nullable=True),
        sa.Column("suggested_chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_chunk_raw", sa.String(length=80), nullable=True),
        sa.Column("grounding_status", grounding_status, nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_number >= 1 AND attempt_number <= 2", name="ck_evidence_attempt_number"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["suggested_chunk_id"], ["pdf_chunks.id"]),
        sa.ForeignKeyConstraint(["synthesis_session_id"], ["synthesis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "evidence_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synthesis_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_text_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_from_attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("page_char_start", sa.Integer(), nullable=False),
        sa.Column("page_char_end", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("page_char_start >= 0", name="ck_evidence_start_nonnegative"),
        sa.CheckConstraint("page_char_end > page_char_start", name="ck_evidence_offsets_ordered"),
        sa.ForeignKeyConstraint(["created_from_attempt_id"], ["evidence_extraction_attempts.id"]),
        sa.ForeignKeyConstraint(["page_text_id"], ["page_texts.id"]),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["pdf_chunks.id"]),
        sa.ForeignKeyConstraint(["synthesis_session_id"], ["synthesis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("created_from_attempt_id"),
    )

    op.add_column("citations", sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_citations_evidence_id", "citations", "evidence_records", ["evidence_id"], ["id"]
    )

    op.create_table(
        "synthesis_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synthesis_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("draft", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["synthesis_session_id"], ["synthesis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("synthesis_session_id", "position", name="uq_synthesis_section_position"),
    )

    op.create_table(
        "synthesis_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synthesis_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("claim_type", claim_type, nullable=False),
        sa.Column("verification_status", entailment_status, nullable=False),
        sa.Column("verification_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["synthesis_sections.id"]),
        sa.ForeignKeyConstraint(["synthesis_session_id"], ["synthesis_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "claim_evidence_links",
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", evidence_relation, nullable=False),
        sa.Column("entailment_status", entailment_status, nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["synthesis_claims.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_records.id"]),
        sa.PrimaryKeyConstraint("claim_id", "evidence_id"),
    )


def downgrade() -> None:
    op.drop_table("claim_evidence_links")
    op.drop_table("synthesis_claims")
    op.drop_table("synthesis_sections")
    op.drop_constraint("fk_citations_evidence_id", "citations", type_="foreignkey")
    op.drop_column("citations", "evidence_id")
    op.drop_table("evidence_records")
    op.drop_table("evidence_extraction_attempts")

    op.drop_constraint("ck_pdf_chunk_offsets_ordered", "pdf_chunks", type_="check")
    op.drop_constraint("ck_pdf_chunk_start_nonnegative", "pdf_chunks", type_="check")
    op.drop_constraint("uq_pdf_chunk_ingestion_index", "pdf_chunks", type_="unique")
    op.drop_index(op.f("ix_pdf_chunks_ingestion_id"), table_name="pdf_chunks")
    op.drop_constraint("fk_pdf_chunks_page_text_id", "pdf_chunks", type_="foreignkey")
    op.drop_column("pdf_chunks", "page_char_end")
    op.drop_column("pdf_chunks", "page_char_start")
    op.drop_column("pdf_chunks", "chunk_index")
    op.drop_column("pdf_chunks", "ingestion_id")
    op.drop_column("pdf_chunks", "page_text_id")

    op.drop_index(op.f("ix_page_texts_ingestion_id"), table_name="page_texts")
    op.drop_table("page_texts")
    op.drop_column("synthesis_sessions", "error_message")
    op.drop_column("papers", "active_ingestion_id")

    postgresql.ENUM(name="synthesisclaimtype").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="evidencerelation").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="entailmentstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="groundingstatus").drop(op.get_bind(), checkfirst=True)
