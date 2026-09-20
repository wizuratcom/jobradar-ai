"""Persist preferred requirement explanations for vacancy-oriented matching.

Revision ID: 0012_preferred_requirement_expl
Revises: 0011_add_rich_candidate_profile
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012_preferred_requirement_expl"
down_revision: str | Sequence[str] | None = "0011_add_rich_candidate_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS also recovers a local development database where the
    # predecessor revision ID overflowed alembic_version after the DDL landed.
    op.execute(
        "ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS "
        "preferred_requirement_explanations JSONB NOT NULL DEFAULT '[]'"
    )


def downgrade() -> None:
    op.drop_column("job_matches", "preferred_requirement_explanations")
