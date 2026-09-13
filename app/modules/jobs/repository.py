from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import JobPosting, UserJob
from app.modules.jobs.schemas import JobCreate


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_user(self, job: JobCreate, user_id: int) -> JobPosting:
        posting = JobPosting(
            **job.model_dump(exclude={"url"}),
            url=str(job.url) if job.url else None,
        )
        self.session.add(posting)
        await self.session.flush()
        self.session.add(UserJob(user_id=user_id, job_id=posting.id))
        await self.session.commit()
        await self.session.refresh(posting)
        return posting

    async def get_for_user(self, job_id: int, user_id: int) -> JobPosting | None:
        return await self.session.scalar(
            select(JobPosting)
            .join(UserJob, UserJob.job_id == JobPosting.id)
            .where(UserJob.job_id == job_id, UserJob.user_id == user_id)
        )

    async def list_for_user(
        self, user_id: int, limit: int, offset: int
    ) -> tuple[list[JobPosting], int]:
        base = (
            select(JobPosting)
            .join(UserJob, UserJob.job_id == JobPosting.id)
            .where(UserJob.user_id == user_id)
        )
        query = base.order_by(JobPosting.id.desc()).limit(limit).offset(offset)
        postings = list((await self.session.scalars(query)).all())
        total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
        return postings, total or 0
