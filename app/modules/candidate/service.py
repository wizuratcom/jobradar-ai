from fastapi import HTTPException, status

from app.modules.candidate.models import CandidateProfileRecord
from app.modules.candidate.schemas import CandidateProfile, CandidateProfileRead


def to_profile(record: CandidateProfileRecord) -> CandidateProfile:
    return CandidateProfile.model_validate(
        {
            "name": record.name,
            "desired_titles": record.desired_titles,
            "core_skills": record.core_skills,
            "secondary_skills": record.secondary_skills,
            "preferred_remote": record.preferred_remote,
            "preferred_locations": record.preferred_locations,
        }
    )


def to_profile_read(record: CandidateProfileRecord) -> CandidateProfileRead:
    return CandidateProfileRead(id=record.id, **to_profile(record).model_dump())


def require_profile(record: CandidateProfileRecord | None) -> CandidateProfileRecord:
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a candidate profile before matching jobs.",
        )
    return record
