"""Create papers.

Revision ID: 20260612003400
Revises: 20260612001100
Create Date: 2026-06-12 00:34:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612003400"
down_revision: str | None = "20260612001100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("latex_source", sa.Text(), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_papers_owner_id_updated_at",
        "papers",
        ["owner_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_papers_template_id",
        "papers",
        ["template_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_papers_template_id", table_name="papers")
    op.drop_index("ix_papers_owner_id_updated_at", table_name="papers")
    op.drop_table("papers")
