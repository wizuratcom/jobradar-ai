from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.dependencies import CurrentUser
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/api/v1", tags=["authentication"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def normalize_email(email: str) -> str:
    return email.strip().casefold()


@router.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDependency) -> UserRead:
    repository = UserRepository(session)
    email = normalize_email(str(payload.email))
    if await repository.get_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return await repository.create(email=email, password_hash=hash_password(payload.password))


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDependency) -> TokenResponse:
    user = await UserRepository(session).get_by_email(normalize_email(str(payload.email)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return TokenResponse(access_token=create_access_token(user_id=user.id, settings=get_settings()))


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser) -> UserRead:
    return current_user
