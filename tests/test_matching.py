from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match


def candidate() -> CandidateProfile:
    return CandidateProfile(
        name="Test Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI"],
        secondary_skills=["Docker", "AWS"],
        preferred_remote=True,
        preferred_locations=["Serbia"],
    )


def test_title_and_skill_scoring() -> None:
    job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build APIs",
        work_mode="remote",
        required_skills=["Python", "FastAPI", "Docker", "Redis"],
    )
    result = calculate_match(job, candidate())
    assert result.breakdown.title == 25
    assert result.breakdown.required_requirements == 26
    assert result.breakdown.preferred_requirements == 0
    assert result.breakdown.stack_skills == 0
    assert result.breakdown.location == 15
    assert result.score == 66
    assert result.recommendation == "apply"
    assert result.missing_required_requirements == ["Redis"]


def test_unrelated_title_and_location_do_not_score() -> None:
    job = JobPosting(
        company="Acme",
        title="Frontend Developer",
        description="Build interfaces",
        location_text="France",
        work_mode="onsite",
        required_skills=[],
    )
    profile = CandidateProfile(
        name="Test Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["PostgreSQL"],
    )
    result = calculate_match(job, profile)
    assert result.score == 0
    assert result.recommendation == "skip"


def test_controlled_postgres_alias_matches_postgresql_skill() -> None:
    job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build APIs",
        work_mode="remote",
        required_skills=["Postgres"],
    )
    profile = CandidateProfile(
        name="Test Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["PostgreSQL"],
    )
    result = calculate_match(job, profile)
    assert result.matched_required_requirements == ["PostgreSQL"]
    assert result.missing_required_requirements == []


def test_controlled_skill_aliases_and_capability_matching() -> None:
    job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build APIs",
        work_mode="remote",
        required_skills=["Python 3.13", "HTTP(S)", "RESTful API", "relational databases"],
    )
    profile = CandidateProfile(
        name="Test Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "HTTP", "REST", "PostgreSQL"],
    )
    result = calculate_match(job, profile)
    assert result.missing_required_requirements == []
    assert result.matched_required_requirements == ["Python", "HTTP", "REST", "PostgreSQL"]


def test_russian_capability_aliases_and_stack_bonus_are_controlled() -> None:
    job = JobPosting(
        company="Tetrika",
        title="Python Backend Developer",
        description="Build APIs",
        work_mode="remote",
        remote_allowed=True,
        required_skills=[
            "Python 3.13",
            "HTTP(S)",
            "REST",
            "Реляционные СУБД",
            "Интеграция с внешними API",
        ],
        stack_skills=["FastAPI", "PostgreSQL", "Redis", "Docker", "Kafka", "AI API"],
    )
    profile = CandidateProfile(
        name="Test Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Docker"],
        preferred_remote=True,
    )
    result = calculate_match(job, profile)
    assert result.matched_required_requirements == ["Python", "PostgreSQL"]
    assert result.matched_stack_skills == ["FastAPI", "PostgreSQL", "Docker"]
    assert result.missing_required_requirements == ["HTTP(S)", "REST", "Интеграция с внешними API"]
    assert result.breakdown.stack_skills == 9
    assert result.breakdown.location == 15
    assert result.score == 63


def test_vacancy_oriented_scoring_can_reach_one_hundred() -> None:
    job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="",
        remote_allowed=True,
        required_skills=["Python", "REST API", "relational databases"],
        preferred_skills=["LLM API integration"],
        stack_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        required_experience_min_years=1,
        required_experience_area="backend development",
    )
    profile = CandidateProfile.model_validate(
        {
            "name": "Candidate",
            "desired_titles": ["Python Backend Developer"],
            "core_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "secondary_skills": ["Unrelated legacy skill"],
            "preferred_remote": True,
            "capabilities": [
                {"name": "rest_api_development"},
                {"name": "relational_databases"},
                {"name": "llm_integration"},
            ],
            "experience": {"backend_experience_months": 12},
        }
    )
    result = calculate_match(job, profile)

    assert result.breakdown.required_requirements == 35
    assert result.breakdown.preferred_requirements == 15
    assert result.breakdown.stack_skills == 10
    assert result.score == 100


def test_extra_profile_skills_and_unmatched_stack_items_do_not_reduce_score() -> None:
    base = CandidateProfile(
        name="Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI"],
        preferred_remote=True,
    )
    enriched = CandidateProfile(
        name="Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI", "Kotlin", "Terraform", "GraphQL"],
        preferred_remote=True,
    )
    base_job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="",
        remote_allowed=True,
        required_skills=["Python", "FastAPI"],
        stack_skills=["Python", "FastAPI"],
    )
    extended_stack_job = JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="",
        remote_allowed=True,
        required_skills=["Python", "FastAPI"],
        stack_skills=["Python", "FastAPI", "Kafka", "Redis", "MAX"],
    )

    assert calculate_match(base_job, enriched).score == calculate_match(base_job, base).score
    assert (
        calculate_match(extended_stack_job, base).breakdown.stack_skills
        >= calculate_match(base_job, base).breakdown.stack_skills
    )
