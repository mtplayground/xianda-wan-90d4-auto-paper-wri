"""Create templates.

Revision ID: 20260612004800
Revises: 20260612003400
Create Date: 2026-06-12 00:48:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612004800"
down_revision: str | None = "20260612003400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_built_in", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
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
        sa.CheckConstraint(
            "(is_built_in = true AND owner_id IS NULL) OR "
            "(is_built_in = false AND owner_id IS NOT NULL)",
            name="ck_templates_owner_scope",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_owner_id", "templates", ["owner_id"], unique=False)
    op.create_index(
        "ix_templates_storage_key",
        "templates",
        ["storage_key"],
        unique=False,
    )
    op.create_index(
        "uq_templates_builtin_name",
        "templates",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_built_in = true"),
    )
    op.create_index(
        "uq_templates_owner_name",
        "templates",
        ["owner_id", "name"],
        unique=True,
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )
    op.create_foreign_key(
        "fk_papers_template_id_templates",
        "papers",
        "templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_papers_template_id_templates", "papers", type_="foreignkey")
    op.drop_index("uq_templates_owner_name", table_name="templates")
    op.drop_index("uq_templates_builtin_name", table_name="templates")
    op.drop_index("ix_templates_storage_key", table_name="templates")
    op.drop_index("ix_templates_owner_id", table_name="templates")
    op.drop_table("templates")
