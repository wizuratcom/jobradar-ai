from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.analysis.schemas import Recommendation


class AssessmentResult(BaseModel):
    grade: int = Field(ge=1, le=3)
    fit_score: int = Field(ge=0, le=100)
    verdict: Recommendation
    concise_summary: str = Field(min_length=1, max_length=3000)
    required_matched: list[str] = Field(default_factory=list)
    required_missing: list[str] = Field(default_factory=list)
    preferred_matched: list[str] = Field(default_factory=list)
    preferred_missing: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    candidate_strengths: list[str] = Field(default_factory=list)
    cv_emphasis: list[str] = Field(default_factory=list)
    cv_improvements: list[str] = Field(default_factory=list)
    do_not_claim: list[str] = Field(default_factory=list)
    detailed_fit_explanation: str | None = None
    hard_requirements: list[str] = Field(default_factory=list)
    soft_requirements: list[str] = Field(default_factory=list)
    likely_rejection_risks: list[str] = Field(default_factory=list)
    cv_sections_to_emphasize: list[str] = Field(default_factory=list)
    cv_bullets_to_rewrite: list[str] = Field(default_factory=list)
    keywords_to_include_if_truthful: list[str] = Field(default_factory=list)
    recruiter_message: str | None = None
    application_strategy: str | None = None
    likely_screening_questions: list[str] = Field(default_factory=list)
    likely_technical_topics: list[str] = Field(default_factory=list)
    questions_to_prepare: list[str] = Field(default_factory=list)
    behavioral_questions: list[str] = Field(default_factory=list)
    system_design_topics: list[str] = Field(default_factory=list)
    study_gaps: list[str] = Field(default_factory=list)
    interviewer_questions: list[str] = Field(default_factory=list)


class AssessmentRead(AssessmentResult):
    id: int
    job_id: int
    job_match_id: int | None
    provider: str
    model: str | None
    prompt_version: str
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    purpose: str
    created_at: datetime


class AssessmentFailure(BaseModel):
    grade: int
    status: Literal["failed"] = "failed"
    detail: str


class AssessmentPage(BaseModel):
    items: list[AssessmentRead]
    total: int
    limit: int
    offset: int
