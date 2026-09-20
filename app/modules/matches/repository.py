from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.matches.models import JobMatch
from app.modules.matching.schemas import MatchResult


class JobMatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        job_id: int,
        profile_id: int,
        profile_snapshot: dict[str, object],
        result: MatchResult,
    ) -> JobMatch:
        payload = result.model_dump(mode="json")
        record = JobMatch(
            user_id=user_id,
            job_id=job_id,
            candidate_profile_id=profile_id,
            candidate_profile_snapshot=profile_snapshot,
            score=payload["score"],
            recommendation=payload["recommendation"],
            breakdown=payload["breakdown"],
            # Keep pre-v0.7.1 storage columns readable while public API fields
            # describe vacancy-oriented requirement semantics.
            matched_core_skills=payload["matched_required_requirements"],
            matched_secondary_skills=payload["matched_preferred_requirements"],
            matched_stack_skills=payload["matched_stack_skills"],
            missing_skills=payload["missing_required_requirements"],
            requirement_explanations=payload["required_requirement_explanations"],
            preferred_requirement_explanations=payload["preferred_requirement_explanations"],
            experience_requirements=payload["experience_requirements"],
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_for_user(self, match_id: int, user_id: int) -> JobMatch | None:
        return await self.session.scalar(
            select(JobMatch).where(JobMatch.id == match_id, JobMatch.user_id == user_id)
        )

    async def list_for_user(
        self, user_id: int, limit: int, offset: int
    ) -> tuple[list[JobMatch], int]:
        base = select(JobMatch).where(JobMatch.user_id == user_id)
        records = list(
            (
                await self.session.scalars(
                    base.order_by(JobMatch.id.desc()).limit(limit).offset(offset)
                )
            ).all()
        )
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        return records, total or 0
