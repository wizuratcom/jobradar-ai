from fastapi import HTTPException, status

from app.modules.jobs.models import JobPosting
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreate


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def normalize_job(job: JobCreate) -> JobCreate:
    data = job.model_dump()
    data["company"] = " ".join(job.company.split())
    data["title"] = " ".join(job.title.split())
    data["description"] = job.description.strip()
    data["required_skills"] = [" ".join(skill.split()) for skill in job.required_skills]
    if job.location:
        data["location"] = " ".join(job.location.split())
    if job.currency:
        data["currency"] = job.currency.upper()
    return JobCreate.model_validate(data)


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def create_job(self, job: JobCreate) -> JobPosting:
        return await self.repository.create(normalize_job(job))

    async def get_job(self, job_id: int) -> JobPosting:
        job = await self.repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job
