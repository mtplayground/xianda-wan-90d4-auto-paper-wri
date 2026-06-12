"""create references

Revision ID: 20260612012600
Revises: 20260612011000
Create Date: 2026-06-12 01:26:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260612012600"
down_revision: str | None = "20260612011000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "references",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column(
            "authors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(length=512), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_identifier", sa.String(length=512), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_references_owner_id", "references", ["owner_id"])
    op.create_index("ix_references_paper_id", "references", ["paper_id"])
    op.create_index("ix_references_doi", "references", ["doi"])
    op.create_index(
        "ix_references_source_identifier",
        "references",
        ["source_identifier"],
    )

    op.create_table(
        "reference_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reference_id"],
            ["references.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reference_id",
            "chunk_index",
            name="uq_reference_chunks_reference_index",
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_reference_chunks_index"),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_reference_chunks_token_count",
        ),
    )
    op.create_index(
        "ix_reference_chunks_reference_id",
        "reference_chunks",
        ["reference_id"],
    )
    op.create_index("ix_reference_chunks_owner_id", "reference_chunks", ["owner_id"])
    op.create_index(
        "ix_reference_chunks_embedding",
        "reference_chunks",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"},
        postgresql_with={"lists": 100},
    )


def downgrade() -> None:
    op.drop_index("ix_reference_chunks_embedding", table_name="reference_chunks")
    op.drop_index("ix_reference_chunks_owner_id", table_name="reference_chunks")
    op.drop_index("ix_reference_chunks_reference_id", table_name="reference_chunks")
    op.drop_table("reference_chunks")
    op.drop_index("ix_references_source_identifier", table_name="references")
    op.drop_index("ix_references_doi", table_name="references")
    op.drop_index("ix_references_paper_id", table_name="references")
    op.drop_index("ix_references_owner_id", table_name="references")
    op.drop_table("references")
