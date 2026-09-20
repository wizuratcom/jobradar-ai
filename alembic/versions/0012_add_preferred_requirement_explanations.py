"""Persist preferred requirement explanations for vacancy-oriented matching.

Revision ID: 0012_add_preferred_requirement_explanations
Revises: 0011_add_rich_candidate_profile
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_add_preferred_requirement_explanations"
down_revision: str | Sequence[str] | None = "0011_add_rich_candidate_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_matches",
        sa.Column(
            "preferred_requirement_explanations",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("job_matches", "preferred_requirement_explanations")
