import httpx
import pytest

from app.core.database import init_test_database
from app.main import app
from app.modules.assessment.config import GradeConfig
from app.modules.assessment.service import fake_assessment
from app.modules.candidate.schemas import CandidateProfile
from app.modules.imports import router as imports_router
from app.modules.imports.ai_service import fake_extraction
from app.modules.imports.extractors import extract_json, extract_json_ld, extract_text
from app.modules.imports.url_fetch import URLImportError, _validate_host
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match
from tests.test_api import PROFILE, authenticated_headers


def test_text_and_json_extractors_preserve_source_content() -> None:
    text = "Title: Backend Engineer\nCompany: Acme\nWork mode: hybrid\nRequired skills: Python, FastAPI"
    extracted = extract_text(text)
    assert extracted.raw_title == "Backend Engineer"
    assert extracted.raw_company == "Acme"
    assert extracted.raw_text == text

    structured = extract_json(
        {"position": "Backend Engineer", "employer": {"title": "Acme"}, "body": "Build APIs"}
    )
    assert structured.raw_title == "Backend Engineer"
    assert structured.raw_company == "Acme"
    assert structured.raw_payload["position"] == "Backend Engineer"


def test_json_ld_jobposting_is_extracted() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"Backend Engineer",'
        '"hiringOrganization":{"name":"Acme"},"description":"Build APIs"}'
        "</script>"
    )
    extracted = extract_json_ld(html, "https://example.com/jobs/1")
    assert extracted is not None
    assert extracted.raw_title == "Backend Engineer"
    assert extracted.raw_company == "Acme"
    assert extracted.source_url == "https://example.com/jobs/1"


def test_fake_assessment_supports_all_depth_grades_without_fabrication() -> None:
    candidate = CandidateProfile(
        name="Candidate", desired_titles=["Backend Engineer"], core_skills=["Python"]
    )
    job = JobPosting(company="Acme", title="Backend Engineer", description="Build APIs", work_mode="remote", required_skills=["Python", "Redis"], preferred_skills=[])
    match = calculate_match(job, candidate)
    for grade in (1, 2, 3):
        result = fake_assessment(job, candidate, match, GradeConfig(grade, "fake", "low"))
        assert result.grade == grade
        assert "Redis" in result.required_missing
        assert result.do_not_claim


def test_ssrf_rejects_localhost() -> None:
    with pytest.raises(URLImportError):
        _validate_host("localhost")


def test_fake_extraction_separates_required_and_preferred() -> None:
    raw = extract_text(
        "We are looking for a Python Backend Engineer. Python, FastAPI, PostgreSQL and "
        "Docker are required. AWS experience is a plus. The position is fully remote. "
        "Salary: €2k-2.8k gross monthly."
    )
    result = fake_extraction(raw)
    assert "Python" in result.required_skills
    assert "AWS" in result.preferred_skills
    assert result.work_mode == "remote"
    assert result.raw_salary == "€2k-2.8k gross monthly"


@pytest.mark.asyncio
async def test_import_endpoint_creates_job_and_match() -> None:
    await init_test_database()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "import@example.com")
        profile = await client.put("/api/v1/me/profile", json=PROFILE, headers=headers)
        assert profile.status_code == 200
        response = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={
                "input_type": "text",
                "text": "Title: Python Backend Developer\nCompany: Acme\nWork mode: remote\nRequired skills: Python, FastAPI",
                "grade": 0,
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["job"]["work_mode"] == "remote"
    assert body["match"]["job_id"] == body["job"]["id"]
    assert body["assessment"] is None


@pytest.mark.asyncio
async def test_fake_import_creates_extraction_assessment_and_review_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    from app.core.config import Settings

    monkeypatch.setattr(imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = await authenticated_headers(client, "smart-import@example.com")
        profile = {**PROFILE, "secondary_skills": ["AWS"]}
        assert (await client.put("/api/v1/me/profile", json=profile, headers=headers)).status_code == 200
        response = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={
                "input_type": "text",
                "grade": 1,
                "text": (
                    "We are looking for a Python Backend Engineer to join Acme. "
                    "Python, FastAPI, PostgreSQL and Docker are required. AWS is a plus. "
                    "The position is fully remote. Salary: €2k-2.8k gross monthly."
                ),
            },
        )
        assert response.status_code == 201
        body = response.json()
        job_id = body["job"]["id"]
        assert body["assessment"]["grade"] == 1
        assert "AWS" in body["job"]["preferred_skills"]
        review = await client.get(f"/api/v1/jobs/{job_id}/review", headers=headers)
        review_list = await client.get("/api/v1/jobs/review-list?sort=score_desc", headers=headers)
    assert review.status_code == 200
    assert review.json()["assessment"]["fit_score"] is not None
    assert review.json()["assessment"]["preferred_matched"] == ["AWS"]
    assert review_list.status_code == 200
    assert review_list.json()["items"][0]["ai_fit_score"] is not None


@pytest.mark.asyncio
async def test_real_smoke_shape_regression_uses_canonical_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    from app.core.config import Settings

    monkeypatch.setattr(
        imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    text = (
        "We are looking for a Python Backend Engineer. Python, FastAPI, PostgreSQL and Docker "
        "are required. AWS is a plus. At least 3 years of commercial backend experience is required. "
        "The role is fully remote. Salary: €2,000-2,800 gross per month."
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        headers = await authenticated_headers(client, "smoke-shape@example.com")
        profile = {**PROFILE, "desired_titles": ["Python Backend Developer"], "secondary_skills": ["AWS"]}
        await client.put("/api/v1/me/profile", json=profile, headers=headers)
        response = await client.post(
            "/api/v1/jobs/import", headers=headers, json={"input_type": "text", "grade": 1, "text": text}
        )
        body = response.json()
        review = await client.get(f"/api/v1/jobs/{body['job']['id']}/review", headers=headers)
    assert response.status_code == 201
    assert body["job"]["salary_min"] == 2000
    assert body["job"]["salary_max"] == 2800
    assert body["job"]["title"] == "Python Backend Engineer"
    assert body["match"]["breakdown"]["title"] == 25
    assert body["job"]["required_skills"] == ["Python", "FastAPI", "PostgreSQL", "Docker"]
    assert body["job"]["preferred_skills"] == ["AWS"]
    assert "3 years of commercial backend experience" in review.json()["source"]["requirements"][0]
    assert review.json()["source"]["preferred_requirements"] == []
    assert review.json()["assessment"]["preferred_matched"] == ["AWS"]
