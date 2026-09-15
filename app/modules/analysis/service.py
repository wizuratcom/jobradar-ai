from fastapi import HTTPException, status

from app.integrations.llm.base import LLMProvider
from app.modules.analysis.models import JobAnalysis
from app.modules.analysis.repository import AnalysisRepository
from app.modules.analysis.schemas import JobAnalysisRead, JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult


def to_analysis_read(record: JobAnalysis) -> JobAnalysisRead:
    payload = record.analysis_payload
    if "recommendation" not in payload:
        payload = {
            "recommendation": payload.get("verdict", record.recommendation),
            "summary": payload.get("concise_summary", "Structured graded assessment."),
            "strengths": payload.get("candidate_strengths", []),
            "gaps": payload.get("required_missing", []),
            "risk_factors": payload.get("risks", []),
            "cv_emphasis": payload.get("cv_emphasis", []),
            "recruiter_message": payload.get("recruiter_message") or "Review the assessment before applying.",
            "interview_topics": payload.get("likely_technical_topics", []),
            "questions_to_prepare": payload.get("questions_to_prepare", []),
        }
    return JobAnalysisRead(
        id=record.id,
        job_id=record.job_id,
        job_match_id=record.job_match_id,
        provider=record.provider,
        model=record.model,
        recommendation=record.recommendation,
        grade=record.grade,
        fit_score=record.fit_score,
        prompt_version=record.prompt_version,
        purpose=record.purpose,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        reasoning_tokens=record.reasoning_tokens,
        analysis=JobAnalysisResult.model_validate(payload),
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
        user_id: int,
        job_match_id: int,
    ) -> JobAnalysisRead:
        analysis = await self.provider.analyze_job(job, candidate, deterministic_match)
        record = await self.repository.create(
            job_id=job.id,
            user_id=user_id,
            job_match_id=job_match_id,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            analysis=analysis,
        )
        return to_analysis_read(record)

    async def get_analysis(self, analysis_id: int, user_id: int) -> JobAnalysisRead:
        record = await self.repository.get_for_user(analysis_id, user_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        return to_analysis_read(record)
