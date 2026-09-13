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
    assert result.breakdown.core_skills == 40
    assert result.breakdown.secondary_skills == 10
    assert result.breakdown.location == 15
    assert result.score == 90
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
    result = calculate_match(job, candidate())
    assert result.score == 0
    assert result.recommendation == "skip"
