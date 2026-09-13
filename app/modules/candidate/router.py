from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.candidate.repository import CandidateProfileRepository
from app.modules.candidate.schemas import CandidateProfile, CandidateProfileRead
from app.modules.candidate.service import to_profile_read
from app.modules.users.dependencies import CurrentUser

router = APIRouter(prefix="/api/v1/me", tags=["candidate"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("/profile", response_model=CandidateProfileRead)
async def get_profile(
    current_user: CurrentUser, session: SessionDependency
) -> CandidateProfileRead:
    record = await CandidateProfileRepository(session).get_by_user_id(current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found"
        )
    return to_profile_read(record)


@router.put("/profile", response_model=CandidateProfileRead)
async def put_profile(
    profile: CandidateProfile, current_user: CurrentUser, session: SessionDependency
) -> CandidateProfileRead:
    record = await CandidateProfileRepository(session).upsert(current_user.id, profile)
    return to_profile_read(record)
