import httpx
import pytest

from app.core.database import init_test_database
from app.main import app


def job_payload() -> dict[str, object]:
    return {
        "company": "Acme",
        "title": "Senior Python Backend Developer",
        "description": "Build reliable APIs.",
        "url": "https://example.com/jobs/1",
        "remote": True,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    }


@pytest.mark.asyncio
async def test_job_api_workflow_and_validation() -> None:
    await init_test_database()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        created = await client.post("/api/v1/jobs", json=job_payload())
        assert created.status_code == 201
        job_id = created.json()["id"]

        retrieved = await client.get(f"/api/v1/jobs/{job_id}")
        assert retrieved.status_code == 200
        assert retrieved.json()["company"] == "Acme"
        assert retrieved.json()["required_skills"] == [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "Docker",
            "Redis",
        ]

        listing = await client.get("/api/v1/jobs?limit=1&offset=0")
        assert listing.status_code == 200
        assert listing.json()["limit"] == 1
        assert listing.json()["total"] >= len(listing.json()["items"])

        match = await client.post(f"/api/v1/jobs/{job_id}/match")
        assert match.status_code == 200
        assert match.json()["breakdown"]["title"] == 25
        assert match.json()["matched_core_skills"] == ["Python", "FastAPI", "PostgreSQL"]
        assert match.json()["matched_secondary_skills"] == ["Docker"]
        assert match.json()["missing_skills"] == ["Redis"]

        invalid = await client.post("/api/v1/jobs", json={"company": "Acme"})
        assert invalid.status_code == 422
