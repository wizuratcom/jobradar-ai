from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SkillList = Annotated[list[str], Field(default_factory=list)]


class JobCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=200)
    remote: bool = False
    employment_type: str | None = Field(default=None, max_length=50)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    required_skills: SkillList

    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, salary_max: float | None, info: object) -> float | None:
        salary_min = getattr(info, "data", {}).get("salary_min")
        if salary_min is not None and salary_max is not None and salary_max < salary_min:
            raise ValueError("salary_max must be greater than or equal to salary_min")
        return salary_max

    @field_validator("required_skills")
    @classmethod
    def remove_duplicate_skills(cls, skills: list[str]) -> list[str]:
        unique_skills: list[str] = []
        seen: set[str] = set()
        for skill in skills:
            normalized = skill.strip()
            if normalized and normalized.casefold() not in seen:
                unique_skills.append(normalized)
                seen.add(normalized.casefold())
        return unique_skills


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    title: str
    description: str
    url: str | None
    location: str | None
    remote: bool
    employment_type: str | None
    salary_min: float | None
    salary_max: float | None
    currency: str | None
    required_skills: list[str]
    created_at: datetime


class JobPage(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int
