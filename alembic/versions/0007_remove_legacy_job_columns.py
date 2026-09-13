"""Remove duplicate legacy job storage.

Revision ID: 0007_remove_legacy_columns
Revises: 0006_source_identity_salary
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_remove_legacy_columns"
down_revision: str | Sequence[str] | None = "0006_source_identity_salary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "job_postings",
        "url",
        new_column_name="application_url",
        existing_type=sa.String(length=2048),
        existing_nullable=True,
    )
    op.drop_column("job_postings", "currency")
    op.drop_column("job_postings", "remote")
    op.drop_column("job_postings", "location")


def downgrade() -> None:
    op.add_column("job_postings", sa.Column("location", sa.String(length=200), nullable=True))
    op.add_column(
        "job_postings", sa.Column("remote", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("job_postings", sa.Column("currency", sa.String(length=3), nullable=True))
    op.execute(
        "UPDATE job_postings SET location = location_text, currency = salary_currency, "
        "remote = (work_mode = 'remote')"
    )
    op.alter_column(
        "job_postings",
        "application_url",
        new_column_name="url",
        existing_type=sa.String(length=2048),
        existing_nullable=True,
    )
