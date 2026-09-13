from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.matches.repository import JobMatchRepository
from app.modules.matches.schemas import JobMatchPage, JobMatchRead
from app.modules.matches.service import JobMatchService, to_match_read
from app.modules.users.dependencies import CurrentUser

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=JobMatchPage)
async def list_matches(
    current_user: CurrentUser,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobMatchPage:
    records, total = await JobMatchRepository(session).list_for_user(current_user.id, limit, offset)
    return JobMatchPage(
        items=[to_match_read(record) for record in records], total=total, limit=limit, offset=offset
    )


@router.get("/{match_id}", response_model=JobMatchRead)
async def get_match(
    match_id: int, current_user: CurrentUser, session: SessionDependency
) -> JobMatchRead:
    return await JobMatchService(JobMatchRepository(session)).get(match_id, current_user.id)
