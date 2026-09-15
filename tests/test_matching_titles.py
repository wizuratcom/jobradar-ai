import pytest

from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match


@pytest.mark.parametrize(
    ("desired", "vacancy", "expected"),
    [
        ("Python Backend Developer", "Python Backend Engineer", 25),
        ("Backend Developer", "Backend Engineer", 25),
        ("Python Backend Developer", "Java Backend Engineer", 15),
        ("Backend Engineer", "Data Engineer", 0),
        ("Frontend Developer", "Backend Engineer", 0),
    ],
)
def test_title_job_family_similarity(desired: str, vacancy: str, expected: int) -> None:
    candidate = CandidateProfile(name="Candidate", desired_titles=[desired], core_skills=["Python"])
    job = JobPosting(
        company="Acme", title=vacancy, description="Role", work_mode="unknown", required_skills=[]
    )
    assert calculate_match(job, candidate).breakdown.title == expected
