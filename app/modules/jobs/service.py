from fastapi import HTTPException, status

from app.modules.jobs.extraction import ManualJobExtractor
from app.modules.jobs.models import JobPosting
from app.modules.jobs.normalization import JobNormalizer
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreate


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def create_job(self, job: JobCreate, user_id: int) -> JobPosting:
        raw = ManualJobExtractor().extract(job)
        return await self.repository.create_for_user(JobNormalizer().normalize(raw), raw, user_id)

    async def get_job(self, job_id: int, user_id: int) -> JobPosting:
        job = await self.repository.get_for_user(job_id, user_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job
