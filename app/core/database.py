from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def ensure_sqlite_directory() -> None:
    prefix = "sqlite+aiosqlite:///"
    if settings.database_url.startswith(prefix):
        database_path = settings.database_url.removeprefix(prefix)
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)


async def init_database() -> None:
    ensure_sqlite_directory()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
