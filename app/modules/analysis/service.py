from fastapi import HTTPException, status

from app.integrations.llm.base import LLMProvider
from app.modules.analysis.models import JobAnalysis
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import JobAnalysisRead, JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult


def to_analysis_read(record: JobAnalysis) -> JobAnalysisRead:
    return JobAnalysisRead(
        id=record.id,
        job_id=record.job_id,
        provider=record.provider,
        model=record.model,
        recommendation=record.recommendation,
        analysis=JobAnalysisResult.model_validate(record.analysis_payload),
        created_at=record.created_at,
    )


class AnalysisService:
    def __init__(self, repository: AnalysisRepository, provider: LLMProvider) -> None:
        self.repository = repository
        self.provider = provider

    async def analyze_and_store(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
    ) -> JobAnalysisRead:
        analysis = await self.provider.analyze_job(job, candidate, deterministic_match)
        record = await self.repository.create(
            job_id=job.id,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            analysis=analysis,
        )
        return to_analysis_read(record)

    async def get_analysis(self, analysis_id: int) -> JobAnalysisRead:
        record = await self.repository.get_by_id(analysis_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return to_analysis_read(record)
