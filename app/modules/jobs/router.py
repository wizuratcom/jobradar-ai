from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.candidate.service import load_candidate_profile
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreate, JobPage, JobRead
from app.modules.jobs.service import JobService
from app.modules.matching.schemas import MatchResult
from app.modules.matching.service import calculate_match

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_job_service(session: SessionDependency) -> JobService:
    return JobService(JobRepository(session))


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(job: JobCreate, service: JobServiceDependency) -> JobRead:
    return await service.create_job(job)


@router.get("", response_model=JobPage)
async def list_jobs(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobPage:
    postings, total = await JobRepository(session).list(limit=limit, offset=offset)
    return JobPage(items=postings, total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, service: JobServiceDependency) -> JobRead:
    return await service.get_job(job_id)


@router.post("/{job_id}/match", response_model=MatchResult)
async def match_job(job_id: int, service: JobServiceDependency) -> MatchResult:
    return calculate_match(await service.get_job(job_id), load_candidate_profile())
