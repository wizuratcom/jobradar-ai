from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.analysis.models import JobAnalysis
from app.modules.candidate.repository import CandidateProfileRepository
from app.modules.candidate.service import require_profile
from app.modules.jobs.models import JobPosting, UserJob
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import (
    JobCreate,
    JobPage,
    JobRead,
    JobReviewListItem,
    JobReviewListPage,
)
from app.modules.jobs.service import JobService
from app.modules.matches.models import JobMatch
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


@router.get("/review-list", response_model=JobReviewListPage)
async def review_list(
    current_user: CurrentUser,
    session: SessionDependency,
    sort: Annotated[Literal["score_desc", "newest"], Query()] = "newest",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobReviewListPage:
    latest_match = (
        select(JobMatch.score).where(JobMatch.job_id == JobPosting.id, JobMatch.user_id == current_user.id)
        .order_by(JobMatch.id.desc()).limit(1).correlate(JobPosting).scalar_subquery()
    )
    latest_ai = (
        select(JobAnalysis.fit_score).where(JobAnalysis.job_id == JobPosting.id, JobAnalysis.user_id == current_user.id)
        .order_by(JobAnalysis.id.desc()).limit(1).correlate(JobPosting).scalar_subquery()
    )
    query = select(JobPosting, UserJob).join(UserJob, UserJob.job_id == JobPosting.id).where(UserJob.user_id == current_user.id)
    if sort == "score_desc":
        query = query.order_by(func.coalesce(latest_ai, latest_match).desc(), UserJob.created_at.desc())
    else:
        query = query.order_by(UserJob.created_at.desc())
    rows = (await session.execute(query.limit(limit).offset(offset))).all()
    total = await session.scalar(select(func.count()).select_from(UserJob).where(UserJob.user_id == current_user.id))
    items: list[JobReviewListItem] = []
    for job, user_job in rows:
        match = await session.scalar(select(JobMatch).where(JobMatch.job_id == job.id, JobMatch.user_id == current_user.id).order_by(JobMatch.id.desc()))
        analysis = await session.scalar(select(JobAnalysis).where(JobAnalysis.job_id == job.id, JobAnalysis.user_id == current_user.id).order_by(JobAnalysis.id.desc()))
        payload = analysis.analysis_payload if analysis else {}
        salary = None
        if job.salary_min is not None:
            upper = f"-{job.salary_max}" if job.salary_max is not None else ""
            salary = f"{job.salary_min}{upper} {job.salary_currency or ''} {job.salary_period or ''}".strip()
        items.append(JobReviewListItem(
            job_id=job.id, title=job.title, company=job.company, location_text=job.location_text,
            work_mode=job.work_mode, salary_summary=salary,
            deterministic_score=match.score if match else None,
            deterministic_recommendation=match.recommendation if match else None,
            latest_assessment_grade=analysis.grade if analysis else None,
            ai_fit_score=analysis.fit_score if analysis else None,
            ai_verdict=analysis.recommendation if analysis else None,
            matched_required_count=len(payload.get("required_matched", [])),
            missing_required_count=len(payload.get("required_missing", [])),
            preferred_gap_count=len(payload.get("preferred_missing", [])),
            blocker_count=len(payload.get("blockers", [])), imported_at=user_job.created_at,
        ))
    return JobReviewListPage(items=items, total=total or 0, limit=limit, offset=offset)


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
