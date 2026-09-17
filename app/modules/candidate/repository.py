from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candidate.models import CandidateEvidence, CandidateProfileRecord, CandidateProject
from app.modules.candidate.schemas import (
    CandidateEvidenceBase,
    CandidateProfile,
    CandidateProjectBase,
)


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

    async def owned_evidence_ids(self, user_id: int, evidence_ids: set[int]) -> set[int]:
        if not evidence_ids:
            return set()
        return set(
            (
                await self.session.scalars(
                    select(CandidateEvidence.id).where(
                        CandidateEvidence.user_id == user_id,
                        CandidateEvidence.id.in_(evidence_ids),
                    )
                )
            ).all()
        )


class CandidateProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[CandidateProject]:
        return list(
            (
                await self.session.scalars(
                    select(CandidateProject)
                    .where(CandidateProject.user_id == user_id)
                    .order_by(CandidateProject.id)
                )
            ).all()
        )

    async def get_for_user(self, project_id: int, user_id: int) -> CandidateProject | None:
        return await self.session.scalar(
            select(CandidateProject).where(
                CandidateProject.id == project_id, CandidateProject.user_id == user_id
            )
        )

    async def create(self, user_id: int, data: CandidateProjectBase) -> CandidateProject:
        record = CandidateProject(user_id=user_id, **data.model_dump())
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update(
        self, record: CandidateProject, data: CandidateProjectBase
    ) -> CandidateProject:
        for field, value in data.model_dump().items():
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete(self, record: CandidateProject) -> None:
        await self.session.delete(record)
        await self.session.commit()


class CandidateEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: int) -> list[CandidateEvidence]:
        return list(
            (
                await self.session.scalars(
                    select(CandidateEvidence)
                    .where(CandidateEvidence.user_id == user_id)
                    .order_by(CandidateEvidence.id)
                )
            ).all()
        )

    async def get_for_user(self, evidence_id: int, user_id: int) -> CandidateEvidence | None:
        return await self.session.scalar(
            select(CandidateEvidence).where(
                CandidateEvidence.id == evidence_id, CandidateEvidence.user_id == user_id
            )
        )

    async def create(self, user_id: int, data: CandidateEvidenceBase) -> CandidateEvidence:
        record = CandidateEvidence(user_id=user_id, **data.model_dump())
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update(
        self, record: CandidateEvidence, data: CandidateEvidenceBase
    ) -> CandidateEvidence:
        for field, value in data.model_dump().items():
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def delete(self, record: CandidateEvidence) -> None:
        await self.session.delete(record)
        await self.session.commit()
