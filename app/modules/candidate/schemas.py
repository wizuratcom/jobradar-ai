from pydantic import BaseModel, ConfigDict, Field


class CandidateProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    desired_titles: list[str] = Field(min_length=1)
    core_skills: list[str] = Field(min_length=1)
    secondary_skills: list[str] = Field(default_factory=list)
    preferred_remote: bool = True
    preferred_locations: list[str] = Field(default_factory=list)


class CandidateProfileRead(CandidateProfile):
    id: int
