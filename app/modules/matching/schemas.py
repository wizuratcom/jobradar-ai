from typing import Literal

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    title: int = Field(ge=0, le=25)
    required_requirements: int = Field(ge=0, le=35)
    preferred_requirements: int = Field(ge=0, le=15)
    # Default keeps historical JobMatch JSON created before stack scoring readable.
    stack_skills: int = Field(default=0, ge=0, le=10)
    location: int = Field(ge=0, le=15)


class RequirementExplanation(BaseModel):
    requirement: str
    status: Literal["matched", "unverified_duration", "missing"]
    matched_by: str | None = None
    evidence_ids: list[int] = Field(default_factory=list)


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    recommendation: Literal["strong_apply", "apply", "maybe", "skip"]
    breakdown: ScoreBreakdown
    matched_required_requirements: list[str]
    matched_preferred_requirements: list[str] = Field(default_factory=list)
    matched_stack_skills: list[str] = Field(default_factory=list)
    missing_required_requirements: list[str]
    missing_preferred_requirements: list[str] = Field(default_factory=list)
    required_requirement_explanations: list[RequirementExplanation] = Field(default_factory=list)
    preferred_requirement_explanations: list[RequirementExplanation] = Field(default_factory=list)
    experience_requirements: list[RequirementExplanation] = Field(default_factory=list)
