from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Recommendation = Literal["strong_apply", "apply", "maybe", "skip"]


class JobAnalysisResult(BaseModel):
    recommendation: Recommendation
    summary: str = Field(min_length=1, max_length=2000)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    cv_emphasis: list[str] = Field(default_factory=list)
    recruiter_message: str = Field(min_length=1, max_length=3000)
    interview_topics: list[str] = Field(default_factory=list)
    questions_to_prepare: list[str] = Field(default_factory=list)


class JobAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    job_match_id: int | None
    provider: str
    model: str | None
    recommendation: Recommendation
    analysis: JobAnalysisResult
    created_at: datetime


class JobAnalysisPage(BaseModel):
    items: list[JobAnalysisRead]
    total: int
    limit: int
    offset: int
