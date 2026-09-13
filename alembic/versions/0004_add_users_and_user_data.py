"""Add users, profiles, user jobs, matches, and analysis ownership.

Revision ID: 0004_add_users_and_user_data
Revises: 0003_add_job_analyses
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_add_users_and_user_data"
down_revision: str | Sequence[str] | None = "0003_add_job_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("desired_titles", postgresql.JSONB(), nullable=False),
        sa.Column("core_skills", postgresql.JSONB(), nullable=False),
        sa.Column("secondary_skills", postgresql.JSONB(), nullable=False),
        sa.Column("preferred_remote", sa.Boolean(), nullable=False),
        sa.Column("preferred_locations", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "user_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_user_jobs_user_job"),
    )
    op.create_index("ix_user_jobs_user_id", "user_jobs", ["user_id"])
    op.create_index("ix_user_jobs_job_id", "user_jobs", ["job_id"])
    op.create_table(
        "job_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(), nullable=False),
        sa.Column("matched_core_skills", postgresql.JSONB(), nullable=False),
        sa.Column("matched_secondary_skills", postgresql.JSONB(), nullable=False),
        sa.Column("missing_skills", postgresql.JSONB(), nullable=False),
        sa.Column("candidate_profile_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job_postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"]),
    )
    for column in ("user_id", "job_id", "candidate_profile_id"):
        op.create_index(f"ix_job_matches_{column}", "job_matches", [column])
    op.add_column("job_analyses", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("job_analyses", sa.Column("job_match_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_job_analyses_user_id", "job_analyses", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_job_analyses_job_match_id",
        "job_analyses",
        "job_matches",
        ["job_match_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_job_analyses_user_id", "job_analyses", ["user_id"])
    op.create_index("ix_job_analyses_job_match_id", "job_analyses", ["job_match_id"])


def downgrade() -> None:
    op.drop_index("ix_job_analyses_job_match_id", table_name="job_analyses")
    op.drop_index("ix_job_analyses_user_id", table_name="job_analyses")
    op.drop_constraint("fk_job_analyses_job_match_id", "job_analyses", type_="foreignkey")
    op.drop_constraint("fk_job_analyses_user_id", "job_analyses", type_="foreignkey")
    op.drop_column("job_analyses", "job_match_id")
    op.drop_column("job_analyses", "user_id")
    op.drop_table("job_matches")
    op.drop_table("user_jobs")
    op.drop_table("candidate_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
