"""Make job posting timestamps required.

Revision ID: 0002_make_created_at_not_null
Revises: 0001_initial_job_postings
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_make_created_at_not_null"
down_revision: str | Sequence[str] | None = "0001_initial_job_postings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "job_postings",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_server_default=sa.text("now()"),
        nullable=True,
    )
