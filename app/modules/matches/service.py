from fastapi import HTTPException, status

from app.modules.candidate.models import CandidateProfileRecord
from app.modules.candidate.service import to_profile
from app.modules.jobs.models import JobPosting
from app.modules.matches.models import JobMatch
from app.modules.matches.repository import JobMatchRepository
from app.modules.matches.schemas import JobMatchRead
from app.modules.matching.service import calculate_match


def to_match_read(record: JobMatch) -> JobMatchRead:
    return JobMatchRead(
        id=record.id,
        job_id=record.job_id,
        candidate_profile_id=record.candidate_profile_id,
        candidate_profile_snapshot=record.candidate_profile_snapshot,
        created_at=record.created_at,
        score=record.score,
        recommendation=record.recommendation,
        breakdown=record.breakdown,
        matched_core_skills=record.matched_core_skills,
        matched_secondary_skills=record.matched_secondary_skills,
        missing_skills=record.missing_skills,
    )


class JobMatchService:
    def __init__(self, repository: JobMatchRepository) -> None:
        self.repository = repository

    async def create(
        self, *, user_id: int, job: JobPosting, profile: CandidateProfileRecord
    ) -> JobMatchRead:
        candidate = to_profile(profile)
        result = calculate_match(job, candidate)
        record = await self.repository.create(
            user_id=user_id,
            job_id=job.id,
            profile_id=profile.id,
            profile_snapshot=candidate.model_dump(mode="json"),
            result=result,
        )
        return to_match_read(record)

    async def get(self, match_id: int, user_id: int) -> JobMatchRead:
        record = await self.repository.get_for_user(match_id, user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
        return to_match_read(record)
