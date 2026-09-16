"""Add stack and remote availability vacancy semantics.

Revision ID: 0010_add_vacancy_semantics
Revises: 0009_ai_extraction_and_contacts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_add_vacancy_semantics"
down_revision: str | Sequence[str] | None = "0009_ai_extraction_and_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_postings", sa.Column("remote_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("job_postings", sa.Column("onsite_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("job_postings", sa.Column("hybrid_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("job_postings", sa.Column("stack_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.execute("UPDATE job_postings SET remote_allowed = true WHERE work_mode IN ('remote', 'hybrid')")
    op.execute("UPDATE job_postings SET onsite_allowed = true WHERE work_mode IN ('onsite', 'hybrid')")
    op.add_column("job_matches", sa.Column("matched_stack_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade() -> None:
    op.drop_column("job_matches", "matched_stack_skills")
    op.drop_column("job_postings", "stack_skills")
    op.drop_column("job_postings", "hybrid_allowed")
    op.drop_column("job_postings", "onsite_allowed")
    op.drop_column("job_postings", "remote_allowed")
