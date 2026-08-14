"""align Scopus source table with the current Elsevier importer

Revision ID: e8f6b0d24c53
Revises: d7e5a9c13b42
Create Date: 2026-08-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f6b0d24c53"
down_revision: Union[str, Sequence[str], None] = "d7e5a9c13b42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The legacy PostgreSQL migration keyed this table by ISSN. The official
    # Elsevier source list has a stable Sourcerecord ID and may omit print ISSN.
    op.drop_constraint("scopus_sources_pkey", "scopus_sources", type_="primary")
    op.add_column("scopus_sources", sa.Column("sourcerecord_id", sa.String(), nullable=True))
    op.add_column("scopus_sources", sa.Column("eissn", sa.String(), nullable=True))
    op.add_column("scopus_sources", sa.Column("active_status", sa.String(), nullable=True))
    op.add_column("scopus_sources", sa.Column("coverage_ranges", sa.Text(), nullable=True))
    op.alter_column("scopus_sources", "issn", existing_type=sa.String(), nullable=True)
    op.execute("UPDATE scopus_sources SET sourcerecord_id = COALESCE(issn, md5(title))")
    op.alter_column("scopus_sources", "sourcerecord_id", existing_type=sa.String(), nullable=False)
    op.create_primary_key("scopus_sources_pkey", "scopus_sources", ["sourcerecord_id"])
    op.drop_column("scopus_sources", "coverage_year_end")
    op.drop_column("scopus_sources", "coverage_year_start")


def downgrade() -> None:
    op.add_column("scopus_sources", sa.Column("coverage_year_start", sa.Integer(), nullable=True))
    op.add_column("scopus_sources", sa.Column("coverage_year_end", sa.Integer(), nullable=True))
    op.drop_constraint("scopus_sources_pkey", "scopus_sources", type_="primary")
    op.execute("DELETE FROM scopus_sources WHERE issn IS NULL")
    op.alter_column("scopus_sources", "issn", existing_type=sa.String(), nullable=False)
    op.create_primary_key("scopus_sources_pkey", "scopus_sources", ["issn"])
    op.drop_column("scopus_sources", "coverage_ranges")
    op.drop_column("scopus_sources", "active_status")
    op.drop_column("scopus_sources", "eissn")
    op.drop_column("scopus_sources", "sourcerecord_id")
