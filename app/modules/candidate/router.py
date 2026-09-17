from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.candidate.repository import (
    CandidateEvidenceRepository,
    CandidateProfileRepository,
    CandidateProjectRepository,
)
from app.modules.candidate.schemas import (
    CandidateEvidenceCreate,
    CandidateEvidenceRead,
    CandidateProfile,
    CandidateProfileRead,
    CandidateProjectCreate,
    CandidateProjectRead,
    ProfileCompletenessRead,
)
from app.modules.candidate.service import (
    profile_completeness,
    to_evidence_read,
    to_profile,
    to_profile_read,
    to_project_read,
)
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
    repository = CandidateProfileRepository(session)
    evidence_ids = {
        evidence_id for skill in profile.skills for evidence_id in skill.evidence_ids
    } | {
        evidence_id
        for capability in profile.capabilities
        for evidence_id in capability.evidence_ids
    }
    if await repository.owned_evidence_ids(current_user.id, evidence_ids) != evidence_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Profile evidence references must belong to the current user.",
        )
    record = await repository.upsert(current_user.id, profile)
    return to_profile_read(record)


@router.get("/profile/completeness", response_model=ProfileCompletenessRead)
async def get_profile_completeness(
    current_user: CurrentUser, session: SessionDependency
) -> ProfileCompletenessRead:
    profile_record = await CandidateProfileRepository(session).get_by_user_id(current_user.id)
    if profile_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile not found"
        )
    projects = await CandidateProjectRepository(session).list_for_user(current_user.id)
    evidence = await CandidateEvidenceRepository(session).list_for_user(current_user.id)
    return profile_completeness(
        to_profile(profile_record), project_count=len(projects), evidence_count=len(evidence)
    )


@router.get("/projects", response_model=list[CandidateProjectRead])
async def list_projects(
    current_user: CurrentUser, session: SessionDependency
) -> list[CandidateProjectRead]:
    return [
        to_project_read(item)
        for item in await CandidateProjectRepository(session).list_for_user(current_user.id)
    ]


@router.post("/projects", response_model=CandidateProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: CandidateProjectCreate, current_user: CurrentUser, session: SessionDependency
) -> CandidateProjectRead:
    return to_project_read(
        await CandidateProjectRepository(session).create(current_user.id, project)
    )


@router.put("/projects/{project_id}", response_model=CandidateProjectRead)
async def update_project(
    project_id: int,
    project: CandidateProjectCreate,
    current_user: CurrentUser,
    session: SessionDependency,
) -> CandidateProjectRead:
    repository = CandidateProjectRepository(session)
    record = await repository.get_for_user(project_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return to_project_read(await repository.update(record, project))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int, current_user: CurrentUser, session: SessionDependency
) -> None:
    repository = CandidateProjectRepository(session)
    record = await repository.get_for_user(project_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await repository.delete(record)


@router.get("/evidence", response_model=list[CandidateEvidenceRead])
async def list_evidence(
    current_user: CurrentUser, session: SessionDependency
) -> list[CandidateEvidenceRead]:
    return [
        to_evidence_read(item)
        for item in await CandidateEvidenceRepository(session).list_for_user(current_user.id)
    ]


async def _ensure_project_is_owned(
    project_id: int | None, user_id: int, session: AsyncSession
) -> None:
    if (
        project_id is not None
        and await CandidateProjectRepository(session).get_for_user(project_id, user_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Project must belong to the current user",
        )


@router.post("/evidence", response_model=CandidateEvidenceRead, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    evidence: CandidateEvidenceCreate, current_user: CurrentUser, session: SessionDependency
) -> CandidateEvidenceRead:
    await _ensure_project_is_owned(evidence.project_id, current_user.id, session)
    return to_evidence_read(
        await CandidateEvidenceRepository(session).create(current_user.id, evidence)
    )


@router.put("/evidence/{evidence_id}", response_model=CandidateEvidenceRead)
async def update_evidence(
    evidence_id: int,
    evidence: CandidateEvidenceCreate,
    current_user: CurrentUser,
    session: SessionDependency,
) -> CandidateEvidenceRead:
    await _ensure_project_is_owned(evidence.project_id, current_user.id, session)
    repository = CandidateEvidenceRepository(session)
    record = await repository.get_for_user(evidence_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    return to_evidence_read(await repository.update(record, evidence))


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int, current_user: CurrentUser, session: SessionDependency
) -> None:
    repository = CandidateEvidenceRepository(session)
    record = await repository.get_for_user(evidence_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await repository.delete(record)
