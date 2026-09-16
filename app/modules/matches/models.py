from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"), index=True
    )
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id"), index=True
    )
    score: Mapped[int] = mapped_column(Integer)
    recommendation: Mapped[str] = mapped_column(String(20))
    breakdown: Mapped[dict[str, int]] = mapped_column(json_type)
    matched_core_skills: Mapped[list[str]] = mapped_column(json_type)
    matched_secondary_skills: Mapped[list[str]] = mapped_column(json_type)
    matched_stack_skills: Mapped[list[str]] = mapped_column(json_type, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(json_type)
    candidate_profile_snapshot: Mapped[dict[str, object]] = mapped_column(json_type)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
