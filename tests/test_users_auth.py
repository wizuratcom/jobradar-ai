import httpx
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal, init_test_database
from app.main import app
from app.modules.analysis import router as analysis_router
from app.modules.jobs.models import UserJob
from app.modules.users.models import User

PROFILE_A = {
    "name": "Candidate A",
    "desired_titles": ["Python Backend Developer"],
    "core_skills": ["Python", "FastAPI", "PostgreSQL"],
    "secondary_skills": ["Docker"],
    "preferred_remote": True,
    "preferred_locations": ["Remote"],
}
PROFILE_B = {
    "name": "Candidate B",
    "desired_titles": ["Frontend Developer"],
    "core_skills": ["JavaScript"],
    "secondary_skills": [],
    "preferred_remote": False,
    "preferred_locations": ["Serbia"],
}
JOB = {
    "company": "Acme",
    "title": "Python Backend Developer",
    "description": "Build APIs.",
    "remote": True,
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
}


async def register_and_login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201
    login = await client.post(
        "/api/v1/auth/login", json={"email": email.lower(), "password": "password123"}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_authentication_security_and_email_normalization() -> None:
    await init_test_database()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/auth/register",
            json={"email": "  USER@Example.com ", "password": "password123"},
        )
        assert created.status_code == 201
        assert created.json()["email"] == "user@example.com"
        assert "password_hash" not in created.json()
        assert (
            await client.post(
                "/api/v1/auth/register",
                json={"email": "user@example.com", "password": "password123"},
            )
        ).status_code == 409
        assert (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "wrong-password"},
            )
        ).status_code == 401
        assert (await client.get("/api/v1/me")).status_code == 401
        assert (
            await client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"})
        ).status_code == 401
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert user.password_hash != "password123"
        assert user.password_hash.startswith("$argon2")


@pytest.mark.asyncio
async def test_two_user_isolation_history_and_fake_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    monkeypatch.setattr(
        analysis_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers_a = await register_and_login(client, "a@example.com")
        headers_b = await register_and_login(client, "b@example.com")
        assert (
            await client.put("/api/v1/me/profile", json=PROFILE_A, headers=headers_a)
        ).status_code == 200
        assert (
            await client.put("/api/v1/me/profile", json=PROFILE_B, headers=headers_b)
        ).status_code == 200
        job = await client.post("/api/v1/jobs", json=JOB, headers=headers_a)
        assert job.status_code == 201
        job_id = job.json()["id"]
        assert (await client.get("/api/v1/jobs", headers=headers_b)).json()["total"] == 0
        match_one = await client.post(f"/api/v1/jobs/{job_id}/match", headers=headers_a)
        assert match_one.status_code == 201
        match_one_id = match_one.json()["id"]
        assert match_one.json()["candidate_profile_snapshot"]["name"] == "Candidate A"
        assert (
            await client.get(f"/api/v1/matches/{match_one_id}", headers=headers_b)
        ).status_code == 404
        assert (
            await client.post(f"/api/v1/jobs/{job_id}/match", headers=headers_b)
        ).status_code == 404
        changed = {**PROFILE_A, "core_skills": ["Python"], "secondary_skills": []}
        await client.put("/api/v1/me/profile", json=changed, headers=headers_a)
        match_two = await client.post(f"/api/v1/jobs/{job_id}/match", headers=headers_a)
        assert match_two.status_code == 201
        assert match_two.json()["id"] != match_one_id
        assert match_two.json()["score"] < match_one.json()["score"]
        old_match = await client.get(f"/api/v1/matches/{match_one_id}", headers=headers_a)
        assert (
            old_match.json()["candidate_profile_snapshot"]["core_skills"]
            == PROFILE_A["core_skills"]
        )
        analysis = await client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers_a)
        assert analysis.status_code == 201
        analysis_id = analysis.json()["id"]
        assert analysis.json()["provider"] == "fake"
        assert (
            await client.get(f"/api/v1/analyses/{analysis_id}", headers=headers_b)
        ).status_code == 404
        assert (
            await client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers_b)
        ).status_code == 404
    async with SessionLocal() as session:
        assert (
            len((await session.scalars(select(UserJob).where(UserJob.job_id == job_id))).all()) == 1
        )
