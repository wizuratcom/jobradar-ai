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
    assert result.breakdown.core_skills == 35
    assert result.breakdown.secondary_skills == 8
    assert result.breakdown.stack_skills == 0
    assert result.breakdown.location == 15
    assert result.score == 83
    assert result.recommendation == "strong_apply"
    assert result.missing_skills == ["Redis"]


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
    assert result.matched_core_skills == ["PostgreSQL"]
    assert result.missing_skills == []


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
    assert result.missing_skills == []
    assert result.matched_core_skills == ["Python", "HTTP", "REST", "PostgreSQL"]


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
    assert result.matched_core_skills == ["Python", "PostgreSQL"]
    assert result.matched_stack_skills == ["FastAPI", "PostgreSQL", "Docker"]
    assert result.missing_skills == ["HTTP(S)", "REST", "Интеграция с внешними API"]
    assert result.breakdown.stack_skills == 5
    assert result.breakdown.location == 15
    assert result.score == 59
