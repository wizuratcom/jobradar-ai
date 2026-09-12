from typing import Literal

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    title: int = Field(ge=0, le=25)
    core_skills: int = Field(ge=0, le=40)
    secondary_skills: int = Field(ge=0, le=20)
    location: int = Field(ge=0, le=15)


class MatchResult(BaseModel):
    score: int = Field(ge=0, le=100)
    recommendation: Literal["strong_apply", "apply", "maybe", "skip"]
    breakdown: ScoreBreakdown
    matched_core_skills: list[str]
    matched_secondary_skills: list[str]
    missing_skills: list[str]
