"""Add rich candidate profile, projects, evidence, and match explanations.

Revision ID: 0011_add_rich_candidate_profile
Revises: 0010_add_vacancy_semantics
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_add_rich_candidate_profile"
down_revision: str | Sequence[str] | None = "0010_add_vacancy_semantics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column("skills", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("experience", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column("languages", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "preferred_work_modes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "candidate_profiles", sa.Column("target_seniority", sa.String(length=50), nullable=True)
    )
    op.add_column("candidate_profiles", sa.Column("salary_min", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "candidate_profiles", sa.Column("salary_currency", sa.String(length=3), nullable=True)
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "employment_types", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
    )
    op.add_column(
        "candidate_profiles", sa.Column("relocation_willing", sa.Boolean(), nullable=True)
    )
    op.create_table(
        "candidate_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=True),
        sa.Column(
            "technologies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "responsibilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "achievements", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("started_at", sa.String(length=32), nullable=True),
        sa.Column("ended_at", sa.String(length=32), nullable=True),
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
    )
    op.create_index("ix_candidate_projects_user_id", "candidate_projects", ["user_id"])
    op.create_table(
        "candidate_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "technologies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "capabilities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("source_label", sa.String(length=200), nullable=True),
        sa.Column("started_at", sa.String(length=32), nullable=True),
        sa.Column("ended_at", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["candidate_projects.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_candidate_evidence_user_id", "candidate_evidence", ["user_id"])
    op.create_index("ix_candidate_evidence_project_id", "candidate_evidence", ["project_id"])
    op.add_column(
        "job_postings", sa.Column("required_experience_min_years", sa.Integer(), nullable=True)
    )
    op.add_column(
        "job_postings", sa.Column("required_experience_area", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "job_matches",
        sa.Column(
            "requirement_explanations",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "job_matches",
        sa.Column(
            "experience_requirements",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("job_matches", "experience_requirements")
    op.drop_column("job_matches", "requirement_explanations")
    op.drop_column("job_postings", "required_experience_area")
    op.drop_column("job_postings", "required_experience_min_years")
    op.drop_index("ix_candidate_evidence_project_id", table_name="candidate_evidence")
    op.drop_index("ix_candidate_evidence_user_id", table_name="candidate_evidence")
    op.drop_table("candidate_evidence")
    op.drop_index("ix_candidate_projects_user_id", table_name="candidate_projects")
    op.drop_table("candidate_projects")
    for column in (
        "relocation_willing",
        "employment_types",
        "salary_currency",
        "salary_min",
        "target_seniority",
        "preferred_work_modes",
        "languages",
        "experience",
        "capabilities",
        "skills",
    ):
        op.drop_column("candidate_profiles", column)
