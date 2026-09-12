from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import JobPosting
from app.modules.jobs.schemas import JobCreate


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: JobCreate) -> JobPosting:
        posting = JobPosting(
            **job.model_dump(exclude={"url"}),
            url=str(job.url) if job.url else None,
        )
        self.session.add(posting)
        await self.session.commit()
        await self.session.refresh(posting)
        return posting

    async def get_by_id(self, job_id: int) -> JobPosting | None:
        return await self.session.get(JobPosting, job_id)

    async def list(self, limit: int, offset: int) -> tuple[list[JobPosting], int]:
        query = select(JobPosting).order_by(JobPosting.id.desc()).limit(limit).offset(offset)
        postings = list((await self.session.scalars(query)).all())
        total = await self.session.scalar(select(func.count()).select_from(JobPosting))
        return postings, total or 0
