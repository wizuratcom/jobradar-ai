from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.integrations.llm.base import create_llm_provider
from app.integrations.llm.exceptions import LLMDisabledError, LLMProviderError
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import JobAnalysisPage, JobAnalysisRead
from app.modules.analysis.service import AnalysisService, to_analysis_read
from app.modules.candidate.service import load_candidate_profile
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.service import JobService
from app.modules.matching.service import calculate_match

router = APIRouter(prefix="/api/v1", tags=["analysis"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_analysis_service(session: SessionDependency) -> AnalysisService:
    try:
        provider = create_llm_provider(get_settings())
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return AnalysisService(
        repository=AnalysisRepository(session),
        provider=provider,
    )


AnalysisServiceDependency = Annotated[AnalysisService, Depends(get_analysis_service)]


@router.post(
    "/jobs/{job_id}/analyze",
    response_model=JobAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_job(
    job_id: int,
    service: AnalysisServiceDependency,
    session: SessionDependency,
) -> JobAnalysisRead:
    job = await JobService(JobRepository(session)).get_job(job_id)
    candidate = load_candidate_profile()
    deterministic_match = calculate_match(job, candidate)
    try:
        return await service.analyze_and_store(job, candidate, deterministic_match)
    except LLMDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/analyses", response_model=JobAnalysisPage)
async def list_analyses(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    job_id: Annotated[int | None, Query(ge=1)] = None,
) -> JobAnalysisPage:
    records, total = await AnalysisRepository(session).list(
        limit=limit,
        offset=offset,
        job_id=job_id,
    )
    return JobAnalysisPage(
        items=[to_analysis_read(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/analyses/{analysis_id}", response_model=JobAnalysisRead)
async def get_analysis(analysis_id: int, service: AnalysisServiceDependency) -> JobAnalysisRead:
    return await service.get_analysis(analysis_id)
