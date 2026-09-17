from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CapabilityName = Literal[
    "backend_api_development",
    "rest_api_development",
    "http",
    "async_python",
    "relational_databases",
    "database_migrations",
    "external_api_integration",
    "llm_integration",
    "structured_llm_output",
    "background_processing",
    "object_storage",
    "message_queues",
    "media_processing",
    "testing",
    "ci_cd",
    "observability",
]
SkillLevel = Literal["basic", "practical", "strong"]
EvidenceType = Literal["project", "work_task", "education", "manual_statement", "certification"]


class CandidateSkill(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    canonical_name: str | None = Field(default=None, max_length=100)
    level: SkillLevel | None = None
    experience_months: int | None = Field(default=None, ge=0, le=600)
    last_used: str | None = Field(default=None, max_length=32)
    evidence_ids: list[int] = Field(default_factory=list)


class CandidateCapability(BaseModel):
    name: CapabilityName
    level: SkillLevel | None = None
    evidence_ids: list[int] = Field(default_factory=list)


class CandidateExperience(BaseModel):
    backend_experience_text: str | None = Field(default=None, max_length=2000)
    backend_experience_months: int | None = Field(default=None, ge=0, le=600)
    commercial_backend_experience: bool | None = None
    domain_experience: list[str] = Field(default_factory=list)


class CandidateLanguage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=50)


class CandidateProjectContext(BaseModel):
    id: int
    title: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityName] = Field(default_factory=list)


class CandidateEvidenceContext(BaseModel):
    id: int
    evidence_type: EvidenceType
    title: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityName] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    desired_titles: list[str] = Field(min_length=1)
    core_skills: list[str] = Field(min_length=1)
    secondary_skills: list[str] = Field(default_factory=list)
    preferred_remote: bool = True
    preferred_locations: list[str] = Field(default_factory=list)
    skills: list[CandidateSkill] = Field(default_factory=list)
    capabilities: list[CandidateCapability] = Field(default_factory=list)
    experience: CandidateExperience = Field(default_factory=CandidateExperience)
    languages: list[CandidateLanguage] = Field(default_factory=list)
    preferred_work_modes: list[Literal["remote", "hybrid", "onsite"]] = Field(default_factory=list)
    target_seniority: str | None = Field(default=None, max_length=50)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    employment_types: list[str] = Field(default_factory=list)
    relocation_willing: bool | None = None
    projects: list[CandidateProjectContext] = Field(default_factory=list, exclude=True)
    evidence: list[CandidateEvidenceContext] = Field(default_factory=list, exclude=True)

    @field_validator("salary_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class CandidateProfileRead(CandidateProfile):
    id: int


class CandidateProjectBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    role: str | None = Field(default=None, max_length=200)
    technologies: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityName] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    started_at: str | None = Field(default=None, max_length=32)
    ended_at: str | None = Field(default=None, max_length=32)


class CandidateProjectCreate(CandidateProjectBase):
    pass


class CandidateProjectRead(CandidateProjectBase):
    id: int


class CandidateEvidenceBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    project_id: int | None = None
    evidence_type: EvidenceType
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityName] = Field(default_factory=list)
    source_label: str | None = Field(default=None, max_length=200)
    started_at: str | None = Field(default=None, max_length=32)
    ended_at: str | None = Field(default=None, max_length=32)


class CandidateEvidenceCreate(CandidateEvidenceBase):
    pass


class CandidateEvidenceRead(CandidateEvidenceBase):
    id: int


class ProfileCompletenessRead(BaseModel):
    completeness_score: int = Field(ge=0, le=100)
    missing_sections: list[str]
    weak_sections: list[str]
