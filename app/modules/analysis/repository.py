from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import JobAnalysis
from app.modules.analysis.schemas import JobAnalysisResult


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        job_id: int,
        provider: str,
        model: str | None,
        analysis: JobAnalysisResult,
    ) -> JobAnalysis:
        record = JobAnalysis(
            job_id=job_id,
            provider=provider,
            model=model,
            recommendation=analysis.recommendation,
            analysis_payload=analysis.model_dump(mode="json"),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_id(self, analysis_id: int) -> JobAnalysis | None:
        return await self.session.get(JobAnalysis, analysis_id)

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        job_id: int | None,
    ) -> tuple[list[JobAnalysis], int]:
        query = select(JobAnalysis).order_by(JobAnalysis.id.desc())
        count_query = select(func.count()).select_from(JobAnalysis)
        if job_id is not None:
            query = query.where(JobAnalysis.job_id == job_id)
            count_query = count_query.where(JobAnalysis.job_id == job_id)
        records = list((await self.session.scalars(query.limit(limit).offset(offset))).all())
        total = await self.session.scalar(count_query)
        return records, total or 0
