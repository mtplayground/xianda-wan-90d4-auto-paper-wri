"""create compilation jobs

Revision ID: 20260612011000
Revises: 20260612004800
Create Date: 2026-06-12 01:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612011000"
down_revision: str | None = "20260612004800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compilation_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pdf_storage_key", sa.Text(), nullable=True),
        sa.Column("log_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_compilation_jobs_status",
        ),
    )
    op.create_index(
        "ix_compilation_jobs_owner_id_created_at",
        "compilation_jobs",
        ["owner_id", "created_at"],
    )
    op.create_index(
        "ix_compilation_jobs_paper_id_created_at",
        "compilation_jobs",
        ["paper_id", "created_at"],
    )
    op.create_index(
        "ix_compilation_jobs_status_created_at",
        "compilation_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_compilation_jobs_status_created_at", table_name="compilation_jobs"
    )
    op.drop_index(
        "ix_compilation_jobs_paper_id_created_at", table_name="compilation_jobs"
    )
    op.drop_index(
        "ix_compilation_jobs_owner_id_created_at", table_name="compilation_jobs"
    )
    op.drop_table("compilation_jobs")
