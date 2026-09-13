import httpx
import pytest
from sqlalchemy import select

from app.core.database import SessionLocal, init_test_database
from app.main import app
from app.modules.jobs.models import JobSourceRecord


def job_payload() -> dict[str, object]:
    return {
        "company": "Acme",
        "title": "Senior Python Backend Developer",
        "description": "Build reliable APIs.",
        "url": "https://example.com/jobs/1",
        "remote": True,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    }


async def authenticated_headers(
    client: httpx.AsyncClient, email: str = "api@example.com"
) -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


PROFILE = {
    "name": "Test",
    "desired_titles": ["Python Backend Developer"],
    "core_skills": ["Python", "FastAPI", "PostgreSQL"],
    "secondary_skills": ["Docker"],
    "preferred_remote": True,
    "preferred_locations": [],
}


@pytest.mark.asyncio
async def test_job_api_workflow_and_validation() -> None:
    await init_test_database()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await authenticated_headers(client)
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        created = await client.post("/api/v1/jobs", json=job_payload(), headers=headers)
        assert created.status_code == 201
        job_id = created.json()["id"]
        assert created.json()["work_mode"] == "remote"

        async with SessionLocal() as session:
            source = await session.scalar(
                select(JobSourceRecord).where(JobSourceRecord.job_id == job_id)
            )
            assert source is not None
            assert source.source_name == "manual"
            assert source.normalization_version == "1"
            assert source.raw_payload["title"] == "Senior Python Backend Developer"

        retrieved = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert retrieved.status_code == 200
        assert retrieved.json()["company"] == "Acme"
        assert retrieved.json()["required_skills"] == [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
            "Redis",
        ]

        listing = await client.get("/api/v1/jobs?limit=1&offset=0", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["limit"] == 1
        assert listing.json()["total"] >= len(listing.json()["items"])

        await client.put("/api/v1/me/profile", json=PROFILE, headers=headers)
        match = await client.post(f"/api/v1/jobs/{job_id}/match", headers=headers)
        assert match.status_code == 201
        assert match.json()["breakdown"]["title"] == 25
        assert match.json()["matched_core_skills"] == ["Python", "FastAPI", "PostgreSQL"]
        assert match.json()["matched_secondary_skills"] == ["Docker"]
        assert match.json()["missing_skills"] == ["Redis"]

        invalid = await client.post("/api/v1/jobs", json={"company": "Acme"}, headers=headers)
        assert invalid.status_code == 422
