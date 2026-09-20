from fastapi import HTTPException, status

from app.modules.candidate.models import CandidateProfileRecord
from app.modules.candidate.service import to_profile
from app.modules.jobs.models import JobPosting
from app.modules.matches.models import JobMatch
from app.modules.matches.repository import JobMatchRepository
from app.modules.matches.schemas import JobMatchRead
from app.modules.matching.schemas import MatchResult
from app.modules.matching.service import calculate_match


def to_match_result(record: JobMatch) -> MatchResult:
    breakdown = dict(record.breakdown)
    if "required_requirements" not in breakdown:
        breakdown = {
            "title": breakdown.get("title", 0),
            "required_requirements": breakdown.get("core_skills", 0),
            "preferred_requirements": breakdown.get("secondary_skills", 0),
            "stack_skills": breakdown.get("stack_skills", 0),
            "location": breakdown.get("location", 0),
        }
    return MatchResult(
        score=record.score,
        recommendation=record.recommendation,
        breakdown=breakdown,
        matched_required_requirements=record.matched_core_skills,
        matched_preferred_requirements=record.matched_secondary_skills,
        matched_stack_skills=record.matched_stack_skills or [],
        missing_required_requirements=record.missing_skills,
        missing_preferred_requirements=[],
        required_requirement_explanations=record.requirement_explanations or [],
        preferred_requirement_explanations=record.preferred_requirement_explanations or [],
        experience_requirements=record.experience_requirements or [],
    )


def to_match_read(record: JobMatch) -> JobMatchRead:
    result = to_match_result(record)
    return JobMatchRead(
        id=record.id,
        job_id=record.job_id,
        candidate_profile_id=record.candidate_profile_id,
        candidate_profile_snapshot=record.candidate_profile_snapshot,
        created_at=record.created_at,
        **result.model_dump(),
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
