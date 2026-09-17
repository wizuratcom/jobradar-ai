from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import JobAnalysis
from app.modules.assessment.schemas import AssessmentResult


class AssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        job_id: int,
        user_id: int,
        job_match_id: int | None,
        provider: str,
        model: str | None,
        grade: int,
        purpose: str,
        analysis: AssessmentResult,
        prompt_version: str,
        input_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int | None = None,
    ) -> JobAnalysis:
        record = JobAnalysis(
            job_id=job_id,
            user_id=user_id,
            job_match_id=job_match_id,
            provider=provider,
            model=model,
            recommendation=analysis.verdict,
            analysis_payload=analysis.model_dump(mode="json"),
            grade=grade,
            prompt_version=prompt_version,
            fit_score=analysis.fit_score,
            purpose=purpose,
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list_for_user(self, user_id: int, limit: int, offset: int, job_id: int | None = None):
        query = select(JobAnalysis).where(JobAnalysis.user_id == user_id)
        count = select(func.count()).select_from(JobAnalysis).where(JobAnalysis.user_id == user_id)
        if job_id is not None:
            query = query.where(JobAnalysis.job_id == job_id)
            count = count.where(JobAnalysis.job_id == job_id)
        records = list(
            (
                await self.session.scalars(
                    query.order_by(JobAnalysis.id.desc()).limit(limit).offset(offset)
                )
            ).all()
        )
        total = await self.session.scalar(count)
        return records, total or 0
