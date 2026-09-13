"""Add canonical job fields and source provenance.

Revision ID: 0005_add_canonical_job_schema
Revises: 0004_add_users_and_user_data
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_add_canonical_job_schema"
down_revision: str | Sequence[str] | None = "0004_add_users_and_user_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_postings", sa.Column("location_text", sa.String(length=200), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column("work_mode", sa.String(length=20), nullable=False, server_default="unknown"),
    )
    op.add_column("job_postings", sa.Column("salary_currency", sa.String(length=3), nullable=True))
    op.add_column("job_postings", sa.Column("salary_period", sa.String(length=20), nullable=True))
    op.add_column("job_postings", sa.Column("salary_gross", sa.Boolean(), nullable=True))
    op.add_column(
        "job_postings",
        sa.Column("preferred_skills", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "job_postings", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute(
        "UPDATE job_postings SET location_text = location, salary_currency = currency, work_mode = CASE WHEN remote THEN 'remote' ELSE 'unknown' END"
    )
def downgrade() -> None:
    for column in (
        "updated_at",
        "preferred_skills",
        "salary_gross",
        "salary_period",
        "salary_currency",
        "work_mode",
        "location_text",
    ):
        op.drop_column("job_postings", column)
