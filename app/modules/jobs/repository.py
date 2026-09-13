from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import JobPosting, JobSourceRecord, UserJob
from app.modules.jobs.normalization import NormalizationResult, RawJobData


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_user(
        self, result: NormalizationResult, raw: RawJobData, user_id: int
    ) -> JobPosting:
        job = result.job
        posting = JobPosting(
            company=job.company,
            title=job.title,
            description=job.description,
            application_url=job.application_url,
            location_text=job.location_text,
            work_mode=job.work_mode,
            employment_type=job.employment_type,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            salary_gross=job.salary_gross,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
        )
        self.session.add(posting)
        await self.session.flush()
        self.session.add(
            JobSourceRecord(
                job_id=posting.id,
                source_name=raw.source_name,
                source_url=raw.source_url,
                raw_payload=raw.raw_payload,
                raw_text=raw.raw_text,
                extracted_data={
                    "title": raw.raw_title,
                    "company": raw.raw_company,
                    "salary": raw.raw_salary,
                },
                normalization_warnings=result.warnings,
                normalization_version=result.normalization_version,
            )
        )
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
