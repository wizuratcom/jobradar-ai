from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.modules.analysis.models import JobAnalysis
from app.modules.assessment.schemas import AssessmentRead, AssessmentResult
from app.modules.candidate.repository import CandidateProfileRepository
from app.modules.candidate.service import require_profile, to_profile
from app.modules.imports.schemas import JobImportRequest, JobImportResponse
from app.modules.imports.service import ImportService
from app.modules.imports.url_fetch import URLImportError
from app.modules.jobs.models import JobSourceRecord
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobRead
from app.modules.matches.models import JobMatch
from app.modules.matches.schemas import JobMatchRead
from app.modules.users.dependencies import CurrentUser

router = APIRouter(prefix="/api/v1/jobs", tags=["smart import"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/import", response_model=JobImportResponse, status_code=status.HTTP_201_CREATED)
async def import_job(
    request: JobImportRequest, current_user: CurrentUser, session: SessionDependency
) -> JobImportResponse:
    profile_record = await CandidateProfileRepository(session).get_by_user_id(current_user.id)
    profile = require_profile(profile_record)
    try:
        result = await ImportService(session, get_settings()).run(
            request, current_user.id, to_profile(profile), profile.id
        )
    except URLImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JobImportResponse(**result)


@router.post("/{job_id}/assess", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def assess_job(
    job_id: int,
    current_user: CurrentUser,
    session: SessionDependency,
    grade: Annotated[int, Query(ge=1, le=3)] = 1,
) -> AssessmentRead:
    profile_record = await CandidateProfileRepository(session).get_by_user_id(current_user.id)
    profile = require_profile(profile_record)
    job = await JobRepository(session).get_for_user(job_id, current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    service = ImportService(session, get_settings())
    match = await service._create_match(job, to_profile(profile), profile.id, current_user.id)
    try:
        return await service._assess(job, to_profile(profile), match, current_user.id, grade)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{job_id}/review")
async def review_job(job_id: int, current_user: CurrentUser, session: SessionDependency) -> dict[str, object]:
    job = await JobRepository(session).get_for_user(job_id, current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    match = await session.scalar(
        select(JobMatch).where(JobMatch.job_id == job_id, JobMatch.user_id == current_user.id).order_by(JobMatch.id.desc())
    )
    assessment = await session.scalar(
        select(JobAnalysis).where(JobAnalysis.job_id == job_id, JobAnalysis.user_id == current_user.id).order_by(JobAnalysis.id.desc())
    )
    source = await session.scalar(select(JobSourceRecord).where(JobSourceRecord.job_id == job_id))
    assessment_data = None
    if assessment and assessment.grade >= 1:
        assessment_data = AssessmentResult.model_validate(assessment.analysis_payload).model_dump(mode="json")
        assessment_data.update(
            {
                "id": assessment.id,
                "grade": assessment.grade,
                "provider": assessment.provider,
                "model": assessment.model,
                "purpose": assessment.purpose,
                "input_tokens": assessment.input_tokens,
                "cached_input_tokens": assessment.cached_input_tokens,
                "output_tokens": assessment.output_tokens,
                "reasoning_tokens": assessment.reasoning_tokens,
            }
        )
    return {
        "job": JobRead.model_validate(job).model_dump(mode="json"),
        "source": {
            "source_name": source.source_name,
            "source_url": source.source_url,
            "warnings": source.normalization_warnings,
            "contact": source.contact_data,
            "requirements": source.extracted_data.get("hard_requirements", []),
            "preferred_requirements": source.extracted_data.get("preferred_requirements", []),
            "required_experience": source.extracted_data.get("required_experience"),
            "preferred_experience": source.extracted_data.get("preferred_experience"),
        } if source else None,
        "match": JobMatchRead.model_validate(match).model_dump(mode="json") if match else None,
        "assessment": assessment_data,
    }
