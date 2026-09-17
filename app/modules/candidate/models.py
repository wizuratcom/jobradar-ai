from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class CandidateProfileRecord(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    desired_titles: Mapped[list[str]] = mapped_column(json_type)
    core_skills: Mapped[list[str]] = mapped_column(json_type)
    secondary_skills: Mapped[list[str]] = mapped_column(json_type, default=list)
    preferred_remote: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_locations: Mapped[list[str]] = mapped_column(json_type, default=list)
    skills: Mapped[list[dict[str, object]]] = mapped_column(json_type, default=list)
    capabilities: Mapped[list[dict[str, object]]] = mapped_column(json_type, default=list)
    experience: Mapped[dict[str, object]] = mapped_column(json_type, default=dict)
    languages: Mapped[list[dict[str, object]]] = mapped_column(json_type, default=list)
    preferred_work_modes: Mapped[list[str]] = mapped_column(json_type, default=list)
    target_seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    employment_types: Mapped[list[str]] = mapped_column(json_type, default=list)
    relocation_willing: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CandidateProject(Base):
    __tablename__ = "candidate_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    technologies: Mapped[list[str]] = mapped_column(json_type, default=list)
    capabilities: Mapped[list[str]] = mapped_column(json_type, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(json_type, default=list)
    achievements: Mapped[list[str]] = mapped_column(json_type, default=list)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ended_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CandidateEvidence(Base):
    __tablename__ = "candidate_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate_projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(json_type, default=list)
    capabilities: Mapped[list[str]] = mapped_column(json_type, default=list)
    source_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    started_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ended_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
