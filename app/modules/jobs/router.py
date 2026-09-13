from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.candidate.repository import CandidateProfileRepository
from app.modules.candidate.service import require_profile
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobCreate, JobPage, JobRead
from app.modules.jobs.service import JobService
from app.modules.matches.repository import JobMatchRepository
from app.modules.matches.schemas import JobMatchRead
from app.modules.matches.service import JobMatchService
from app.modules.users.dependencies import CurrentUser

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_job_service(session: SessionDependency) -> JobService:
    return JobService(JobRepository(session))


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobCreate, current_user: CurrentUser, service: JobServiceDependency
) -> JobRead:
    return await service.create_job(job, current_user.id)


@router.get("", response_model=JobPage)
async def list_jobs(
    current_user: CurrentUser,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobPage:
    postings, total = await JobRepository(session).list_for_user(
        current_user.id, limit=limit, offset=offset
    )
    return JobPage(items=postings, total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, current_user: CurrentUser, service: JobServiceDependency) -> JobRead:
    return await service.get_job(job_id, current_user.id)


@router.post("/{job_id}/match", response_model=JobMatchRead, status_code=status.HTTP_201_CREATED)
async def match_job(
    job_id: int,
    current_user: CurrentUser,
    service: JobServiceDependency,
    session: SessionDependency,
) -> JobMatchRead:
    job = await service.get_job(job_id, current_user.id)
    profile = require_profile(
        await CandidateProfileRepository(session).get_by_user_id(current_user.id)
    )
    return await JobMatchService(JobMatchRepository(session)).create(
        user_id=current_user.id, job=job, profile=profile
    )
