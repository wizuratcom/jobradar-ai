from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import close_database
from app.modules.analysis.router import router as analysis_router
from app.modules.candidate.router import router as candidate_router
from app.modules.imports.router import router as imports_router
from app.modules.jobs.router import router as jobs_router
from app.modules.matches.router import router as matches_router
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await close_database()


app = FastAPI(
    title="JobRadar AI",
    version="0.1.0",
    description="Local, deterministic job-to-candidate matching core.",
    lifespan=lifespan,
)
app.include_router(jobs_router)
app.include_router(analysis_router)
app.include_router(users_router)
app.include_router(candidate_router)
app.include_router(matches_router)
app.include_router(imports_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
