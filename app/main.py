from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import close_database
from app.modules.candidate.schemas import CandidateProfile
from app.modules.candidate.service import load_candidate_profile
from app.modules.jobs.router import router as jobs_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_candidate_profile()
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


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/candidate", response_model=CandidateProfile, tags=["candidate"])
async def get_candidate() -> CandidateProfile:
    return load_candidate_profile()
