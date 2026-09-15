from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIExtractionResult(BaseModel):
    """Facts explicitly supported by one supplied vacancy source."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    company: str | None = None
    description: str | None = None
    location: str | None = None
    work_mode: Literal["remote", "hybrid", "onsite", "unknown"] | None = None
    raw_salary: str | None = None
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: str | None = None
    salary_period: Literal["month", "year"] | None = None
    salary_gross: bool | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    hard_requirements: list[str] = Field(default_factory=list)
    preferred_requirements: list[str] = Field(default_factory=list)
    required_experience: str | None = None
    preferred_experience: str | None = None
    application_url: str | None = None
    company_website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    application_instructions: str | None = None
    published_at: str | None = None


class AIExtractionRead(AIExtractionResult):
    id: int
    job_id: int | None
    user_id: int
    provider: str
    model: str | None
    prompt_version: str
    purpose: Literal["extraction"] = "extraction"
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    created_at: datetime
