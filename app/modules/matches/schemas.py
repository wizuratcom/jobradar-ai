from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.matching.schemas import MatchResult


class JobMatchRead(MatchResult):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    candidate_profile_id: int
    candidate_profile_snapshot: dict[str, object]
    created_at: datetime


class JobMatchPage(BaseModel):
    items: list[JobMatchRead]
    total: int
    limit: int
    offset: int
