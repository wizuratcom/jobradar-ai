"""Add graded assessment and AI usage metadata.

Revision ID: 0008_smart_assessments
Revises: 0007_remove_legacy_columns
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_smart_assessments"
down_revision: str | Sequence[str] | None = "0007_remove_legacy_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_analyses", sa.Column("grade", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("job_analyses", sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default="assessment-v1"))
    op.add_column("job_analyses", sa.Column("fit_score", sa.Integer(), nullable=True))
    op.add_column("job_analyses", sa.Column("purpose", sa.String(length=50), nullable=False, server_default="grade1_screening"))
    op.add_column("job_analyses", sa.Column("input_tokens", sa.Integer(), nullable=True))
    op.add_column("job_analyses", sa.Column("output_tokens", sa.Integer(), nullable=True))
    op.add_column("job_analyses", sa.Column("reasoning_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    for column in ("reasoning_tokens", "output_tokens", "input_tokens", "purpose", "fit_score", "prompt_version", "grade"):
        op.drop_column("job_analyses", column)
