from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

SkillList = Annotated[list[str], Field(default_factory=list)]


class JobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    url: HttpUrl | None = None
    application_url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=200)
    location_text: str | None = Field(default=None, max_length=200)
    remote: bool = False
    work_mode: str | None = None
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_text: str | None = None
    required_skills: SkillList
    preferred_skills: SkillList
    stack_skills: SkillList


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    description: str
    url: str | None
    application_url: str | None
    location: str | None
    remote: bool
    location_text: str | None
    work_mode: str
    remote_allowed: bool
    onsite_allowed: bool
    hybrid_allowed: bool
    employment_type: str | None
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    salary_currency: str | None
    salary_period: str | None
    salary_gross: bool | None
    required_skills: list[str]
    preferred_skills: list[str]
    stack_skills: list[str]
    created_at: datetime


class JobPage(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int


class JobReviewListItem(BaseModel):
    job_id: int
    title: str
    company: str
    location_text: str | None
    work_mode: str
    salary_summary: str | None
    deterministic_score: int | None
    deterministic_recommendation: str | None
    latest_assessment_grade: int | None
    ai_fit_score: int | None
    ai_verdict: str | None
    matched_required_count: int
    missing_required_count: int
    preferred_gap_count: int
    blocker_count: int
    imported_at: datetime


class JobReviewListPage(BaseModel):
    items: list[JobReviewListItem]
    total: int
    limit: int
    offset: int
