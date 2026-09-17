import httpx
import pytest

from app.core.config import Settings
from app.core.database import init_test_database
from app.main import app
from app.modules.candidate.schemas import CandidateProfile
from app.modules.imports import router as imports_router
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match
from tests.test_api import authenticated_headers

RICH_PROFILE = {
    "name": "Synthetic Backend Candidate",
    "desired_titles": ["Python Backend Developer"],
    "core_skills": ["Python", "FastAPI", "PostgreSQL"],
    "secondary_skills": ["Docker"],
    "preferred_remote": True,
    "preferred_locations": ["Remote"],
    "skills": [{"name": "AWS S3", "level": "practical"}],
    "capabilities": [
        {"name": "external_api_integration", "level": "practical"},
    ],
    "experience": {
        "backend_experience_text": "Commercial backend project experience.",
        "commercial_backend_experience": True,
    },
    "languages": [{"name": "English", "level": "B2"}],
    "preferred_work_modes": ["remote"],
}


@pytest.mark.asyncio
async def test_rich_profile_projects_evidence_and_isolation() -> None:
    await init_test_database()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        a = await authenticated_headers(client, "rich-a@example.com")
        b = await authenticated_headers(client, "rich-b@example.com")
        profile = await client.put("/api/v1/me/profile", json=RICH_PROFILE, headers=a)
        assert profile.status_code == 200
        assert profile.json()["capabilities"][0]["name"] == "external_api_integration"
        project = await client.post(
            "/api/v1/me/projects",
            headers=a,
            json={
                "title": "Synthetic integration service",
                "description": "Built a backend integration service.",
                "technologies": ["Python", "FastAPI"],
                "capabilities": ["external_api_integration"],
            },
        )
        assert project.status_code == 201
        evidence = await client.post(
            "/api/v1/me/evidence",
            headers=a,
            json={
                "project_id": project.json()["id"],
                "evidence_type": "project",
                "title": "Implemented retrying external API integration",
                "description": "Used a documented third-party HTTP API.",
                "capabilities": ["external_api_integration"],
            },
        )
        assert evidence.status_code == 201
        enriched = {
            **RICH_PROFILE,
            "capabilities": [
                {"name": "external_api_integration", "evidence_ids": [evidence.json()["id"]]}
            ],
        }
        assert (await client.put("/api/v1/me/profile", json=enriched, headers=a)).status_code == 200
        assert (
            await client.put(
                f"/api/v1/me/evidence/{evidence.json()['id']}",
                headers=b,
                json={
                    "evidence_type": "manual_statement",
                    "title": "Other user edit",
                    "description": "Must not be allowed.",
                },
            )
        ).status_code == 404
        assert (await client.put("/api/v1/me/profile", json=enriched, headers=b)).status_code == 422
        completeness = await client.get("/api/v1/me/profile/completeness", headers=a)
    assert completeness.status_code == 200
    assert completeness.json()["completeness_score"] > 50


def test_rich_capabilities_and_experience_matching_are_explicit() -> None:
    profile = CandidateProfile.model_validate(RICH_PROFILE)
    job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build APIs",
        remote_allowed=True,
        required_skills=["Python", "relational databases", "external API integration"],
        stack_skills=["FastAPI", "AWS S3"],
        required_experience_min_years=3,
        required_experience_area="backend development",
    )
    result = calculate_match(job, profile)
    assert result.missing_skills == []
    assert result.matched_stack_skills == ["FastAPI", "AWS S3"]
    assert result.experience_requirements[0].status == "unverified_duration"
    assert result.requirement_explanations[1].matched_by == "PostgreSQL"
    assert result.requirement_explanations[2].matched_by == "external_api_integration"


def test_confirmed_experience_does_not_overclaim() -> None:
    job = JobPosting(
        company="Acme",
        title="Backend Developer",
        description="",
        required_skills=[],
        required_experience_min_years=3,
        required_experience_area="backend development",
    )
    one_year = CandidateProfile.model_validate(
        {**RICH_PROFILE, "experience": {"backend_experience_months": 12}}
    )
    three_years = CandidateProfile.model_validate(
        {**RICH_PROFILE, "experience": {"backend_experience_months": 36}}
    )
    assert calculate_match(job, one_year).experience_requirements[0].status == "missing"
    assert calculate_match(job, three_years).experience_requirements[0].status == "matched"


@pytest.mark.asyncio
async def test_grade_one_remains_extraction_only_and_grade_two_grounding_is_owned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    monkeypatch.setattr(
        imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "grounded@example.com")
        evidence = await client.post(
            "/api/v1/me/evidence",
            headers=headers,
            json={
                "evidence_type": "manual_statement",
                "title": "External API work",
                "description": "Integrated a documented partner API.",
                "capabilities": ["external_api_integration"],
            },
        )
        profile = {
            **RICH_PROFILE,
            "capabilities": [
                {"name": "external_api_integration", "evidence_ids": [evidence.json()["id"]]}
            ],
        }
        assert (
            await client.put("/api/v1/me/profile", json=profile, headers=headers)
        ).status_code == 200
        grade_one = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={"input_type": "text", "grade": 1, "text": "Python is required. Remote role."},
        )
        assert grade_one.status_code == 201
        assert grade_one.json()["assessment"] is None
        grade_two = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={
                "input_type": "text",
                "grade": 2,
                    "text": "Required: Python, external API integration\nRemote role.",
            },
        )
    assert grade_two.status_code == 201
    grounded = grade_two.json()["assessment"]["grounded_recommendations"]
    assert grounded and grounded[0]["evidence_ids"] == [evidence.json()["id"]]
