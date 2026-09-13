"""Add persisted LLM job analyses.

Revision ID: 0003_add_job_analyses
Revises: 0002_make_created_at_not_null
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_add_job_analyses"
down_revision: str | Sequence[str] | None = "0002_make_created_at_not_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("analysis_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_analyses_job_id", "job_analyses", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_analyses_job_id", table_name="job_analyses")
    op.drop_table("job_analyses")
