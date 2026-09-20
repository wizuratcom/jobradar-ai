import httpx
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal, init_test_database
from app.integrations.llm.assessment_prompt import build_assessment_messages
from app.main import app
from app.modules.assessment.config import GradeConfig
from app.modules.assessment.service import fake_assessment
from app.modules.candidate.context import CandidateContextBuilder
from app.modules.candidate.schemas import CandidateProfile
from app.modules.imports import router as imports_router
from app.modules.imports.ai_models import AIExtraction
from app.modules.imports.ai_schemas import AIExtractionResult
from app.modules.imports.ai_service import fake_extraction, merge_extraction
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


def test_text_extractor_finds_remote_and_currency_marked_salary_without_labels() -> None:
    extracted = extract_text(
        "Senior Python Developer. $6,000 - $8,000. Flexible work setup: remote model in Serbia."
    )
    assert extracted.raw_work_mode == "remote"
    assert extracted.raw_salary == "$6,000 - $8,000"


def test_text_extractor_preserves_explicit_experience_requirement() -> None:
    extracted = extract_text(
        "Requirements: 9+ years of backend development experience. Strong Python proficiency."
    )
    assert extracted.raw_required_experience == "9+ years of backend development experience"
    assert extracted.raw_hard_requirements == ["9+ years of backend development experience"]


def test_ai_merge_preserves_full_user_supplied_description() -> None:
    raw = extract_text("Senior Python Developer\nFull vacancy text with all requirements.")
    extracted = AIExtractionResult(title="Senior Python Developer", description="Short summary.")
    assert merge_extraction(raw, extracted).raw_description == raw.raw_description


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


def test_fake_assessment_supports_assessment_grades_without_fabrication() -> None:
    candidate = CandidateProfile(
        name="Candidate", desired_titles=["Backend Engineer"], core_skills=["Python"]
    )
    job = JobPosting(
        company="Acme",
        title="Backend Engineer",
        description="Build APIs",
        work_mode="remote",
        required_skills=["Python", "Redis"],
        preferred_skills=[],
    )
    match = calculate_match(job, candidate)
    for grade in (2, 3):
        result = fake_assessment(job, candidate, match, GradeConfig(grade, "fake", "low"))
        assert result.grade == grade
        assert "Redis" in result.required_missing
        assert result.do_not_claim


def test_grade_two_prompt_treats_deterministic_match_as_auxiliary() -> None:
    candidate = CandidateProfile(
        name="Candidate", desired_titles=["Backend Engineer"], core_skills=["Python"]
    )
    job = JobPosting(
        company="Acme", title="Backend Engineer", description="Build APIs", required_skills=[]
    )
    context = CandidateContextBuilder(Settings()).build(
        profile=candidate,
        projects=[],
        evidence=[],
        job=job,
        match=calculate_match(job, candidate),
        grade=2,
    )
    prompt = build_assessment_messages(job, context, calculate_match(job, candidate), grade=2)
    assert "auxiliary, transparent signal, not ground truth" in prompt[0]["content"]
    assert "Never describe the JobRadar score itself as a blocker" in prompt[0]["content"]


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
async def test_grade_one_import_creates_extraction_without_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    from app.core.config import Settings

    monkeypatch.setattr(
        imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "smart-import@example.com")
        profile = {**PROFILE, "secondary_skills": ["AWS"]}
        assert (
            await client.put("/api/v1/me/profile", json=profile, headers=headers)
        ).status_code == 200
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
        assert body["assessment"] is None
        assert "AWS" in body["job"]["preferred_skills"]
        review = await client.get(f"/api/v1/jobs/{job_id}/review", headers=headers)
        review_list = await client.get("/api/v1/jobs/review-list?sort=score_desc", headers=headers)
    assert review.status_code == 200
    assert review.json()["assessment"] is None
    assert review_list.status_code == 200
    assert review_list.json()["items"][0]["ai_fit_score"] is None


@pytest.mark.asyncio
async def test_grade_two_import_creates_assessment_after_enrichment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    from app.core.config import Settings

    monkeypatch.setattr(
        imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "grade-two@example.com")
        assert (
            await client.put("/api/v1/me/profile", json=PROFILE, headers=headers)
        ).status_code == 200
        response = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={
                "input_type": "text",
                "grade": 2,
                "text": "Python and FastAPI are required. The role is remote.",
            },
        )
    assert response.status_code == 201
    assert response.json()["assessment"]["grade"] == 2


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
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "smoke-shape@example.com")
        profile = {
            **PROFILE,
            "desired_titles": ["Python Backend Developer"],
            "secondary_skills": ["AWS"],
        }
        await client.put("/api/v1/me/profile", json=profile, headers=headers)
        response = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={"input_type": "text", "grade": 1, "text": text},
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
    assert review.json()["assessment"] is None


@pytest.mark.asyncio
async def test_russian_grade_one_semantic_enrichment_without_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await init_test_database()
    from app.core.config import Settings

    monkeypatch.setattr(
        imports_router, "get_settings", lambda: Settings(llm_enabled=True, llm_provider="fake")
    )
    text = """Title: Backend Developer Python (junior)
Stack: FastAPI, PostgreSQL, Redis, Docker, Kafka, AI API
Required: Python 3.13, HTTP(S), REST, Реляционные СУБД, Интеграция с внешними API
Preferred: chatbot development, AI / LLM API integration, Kafka
Опыт backend-разработки от 1 года
Work conditions: офис/удаленно"""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        headers = await authenticated_headers(client, "russian-grade-one@example.com")
        await client.put(
            "/api/v1/me/profile",
            json={
                **PROFILE,
                "desired_titles": ["Python Backend Developer"],
                "core_skills": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Docker"],
                "secondary_skills": [],
            },
            headers=headers,
        )
        response = await client.post(
            "/api/v1/jobs/import",
            headers=headers,
            json={"input_type": "text", "grade": 1, "text": text},
        )
        body = response.json()
        review = await client.get(f"/api/v1/jobs/{body['job']['id']}/review", headers=headers)
    assert response.status_code == 201
    assert body["assessment"] is None
    assert body["job"]["remote_allowed"] is True
    assert body["job"]["work_mode"] == "unknown"
    assert body["job"]["hybrid_allowed"] is False
    assert body["job"]["stack_skills"] == [
        "FastAPI",
        "PostgreSQL",
        "Redis",
        "Docker",
        "Kafka",
        "AI API",
    ]
    assert {"PostgreSQL", "FastAPI", "Docker"}.issubset(set(body["match"]["matched_stack_skills"]))
    assert "Kafka" not in body["match"]["missing_required_requirements"]
    assert body["match"]["breakdown"]["stack_skills"] == 9
    assert body["match"]["score"] == 61
    assert review.json()["source"]["required_experience_min_years"] == 1
    assert review.json()["source"]["required_experience_area"] == "backend-разработки"
    async with SessionLocal() as session:
        assert await session.scalar(select(AIExtraction)) is not None
