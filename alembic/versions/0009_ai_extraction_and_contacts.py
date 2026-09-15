"""Add AI extraction history and source contact data.

Revision ID: 0009_ai_extraction_and_contacts
Revises: 0008_smart_assessments
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_ai_extraction_and_contacts"
down_revision: str | Sequence[str] | None = "0008_smart_assessments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_source_records", sa.Column("contact_data", sa.JSON(), nullable=True))
    op.add_column("job_analyses", sa.Column("cached_input_tokens", sa.Integer(), nullable=True))
    op.create_table(
        "ai_extractions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("job_postings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_record_id", sa.Integer(), sa.ForeignKey("job_source_records.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False, server_default="extraction"),
        sa.Column("extraction_payload", sa.JSON(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_extractions_job_id", "ai_extractions", ["job_id"])
    op.create_index("ix_ai_extractions_user_id", "ai_extractions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_extractions_user_id", table_name="ai_extractions")
    op.drop_index("ix_ai_extractions_job_id", table_name="ai_extractions")
    op.drop_table("ai_extractions")
    op.drop_column("job_analyses", "cached_input_tokens")
    op.drop_column("job_source_records", "contact_data")
