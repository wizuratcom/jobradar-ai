from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candidate.models import CandidateProfileRecord
from app.modules.candidate.schemas import CandidateProfile


class CandidateProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: int) -> CandidateProfileRecord | None:
        return await self.session.scalar(
            select(CandidateProfileRecord).where(CandidateProfileRecord.user_id == user_id)
        )

    async def upsert(self, user_id: int, profile: CandidateProfile) -> CandidateProfileRecord:
        record = await self.get_by_user_id(user_id)
        values = profile.model_dump()
        if record is None:
            record = CandidateProfileRecord(user_id=user_id, **values)
            self.session.add(record)
        else:
            for field, value in values.items():
                setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return record
