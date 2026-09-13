"""Enforce source identity and use decimal salary columns.

Revision ID: 0006_source_identity_salary
Revises: 0005_add_canonical_job_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_source_identity_salary"
down_revision: str | Sequence[str] | None = "0005_add_canonical_job_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_source_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255)),
        sa.Column("source_url", sa.String(length=2048)),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("normalization_warnings", sa.JSON(), nullable=False),
        sa.Column("normalization_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_job_source_records_job_id", "job_source_records", ["job_id"])
    op.alter_column(
        "job_postings",
        "salary_min",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        postgresql_using="salary_min::numeric(12,2)",
        existing_nullable=True,
    )
    op.alter_column(
        "job_postings",
        "salary_max",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        postgresql_using="salary_max::numeric(12,2)",
        existing_nullable=True,
    )
    op.create_unique_constraint(
        "uq_job_source_records_source_external_id",
        "job_source_records",
        ["source_name", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_job_source_records_source_external_id", "job_source_records", type_="unique"
    )
    op.drop_index("ix_job_source_records_job_id", table_name="job_source_records")
    op.drop_table("job_source_records")
    op.alter_column(
        "job_postings",
        "salary_max",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        postgresql_using="salary_max::double precision",
        existing_nullable=True,
    )
    op.alter_column(
        "job_postings",
        "salary_min",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        postgresql_using="salary_min::double precision",
        existing_nullable=True,
    )
