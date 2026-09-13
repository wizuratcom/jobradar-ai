import httpx
import pytest

from app.core.config import Settings
from app.core.database import init_test_database
from app.main import app
from app.modules.analysis import router as analysis_router


def job_payload() -> dict[str, object]:
    return {
        "company": "Analysis Co",
        "title": "Python Backend Developer",
        "description": "Build backend services.",
        "remote": True,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
    }


@pytest.mark.asyncio
async def test_analysis_api_is_disabled_by_default() -> None:
    await init_test_database()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/jobs", json=job_payload())
        response = await client.post(f"/api/v1/jobs/{created.json()['id']}/analyze")
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].casefold()


@pytest.mark.asyncio
async def test_fake_analysis_api_persists_valid_result(monkeypatch: pytest.MonkeyPatch) -> None:
    await init_test_database()
    fake_settings = Settings(llm_enabled=True, llm_provider="fake")
    monkeypatch.setattr(analysis_router, "get_settings", lambda: fake_settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/jobs", json=job_payload())
        job_id = created.json()["id"]
        response = await client.post(f"/api/v1/jobs/{job_id}/analyze")
        assert response.status_code == 201
        analysis_id = response.json()["id"]

        retrieved = await client.get(f"/api/v1/analyses/{analysis_id}")
        listing = await client.get(f"/api/v1/analyses?job_id={job_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["provider"] == "fake"
    assert retrieved.json()["analysis"]["recommendation"] == "apply"
    assert listing.json()["total"] >= 1
