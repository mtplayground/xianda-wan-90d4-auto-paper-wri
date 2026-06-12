"""Enable pgvector extension.

Revision ID: 20260611235800
Revises:
Create Date: 2026-06-11 23:58:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260611235800"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION
            WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping vector extension creation';
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            DROP EXTENSION IF EXISTS vector;
        EXCEPTION
            WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping vector extension drop: insufficient privilege';
        END
        $$;
        """
    )
