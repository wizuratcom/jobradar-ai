from app.core.config import Settings
from app.modules.candidate.context import CandidateContextBuilder
from app.modules.candidate.models import CandidateEvidence, CandidateProject
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match


def _profile() -> CandidateProfile:
    return CandidateProfile(
        name="Synthetic candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI", "PostgreSQL"],
        capabilities=[{"name": "external_api_integration", "evidence_ids": [1]}],
        experience={"backend_experience_text": "Backend project work"},
        preferred_remote=True,
    )


def _job() -> JobPosting:
    return JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build backend APIs.",
        remote_allowed=True,
        required_skills=["Python", "FastAPI", "PostgreSQL", "external API integration"],
        preferred_skills=["Docker"],
        stack_skills=["FastAPI", "PostgreSQL", "Docker"],
    )


def _evidence(evidence_id: int, *, relevant: bool) -> CandidateEvidence:
    return CandidateEvidence(
        id=evidence_id,
        user_id=1,
        evidence_type="work_task",
        title="Relevant API evidence" if relevant else f"Unrelated item {evidence_id}",
        description="Built Python FastAPI and PostgreSQL integration."
        if relevant
        else "Unrelated domain work.",
        technologies=["Python", "FastAPI", "PostgreSQL"] if relevant else ["Kotlin"],
        capabilities=["external_api_integration"] if relevant else ["media_processing"],
    )


def _project(project_id: int, *, relevant: bool) -> CandidateProject:
    return CandidateProject(
        id=project_id,
        user_id=1,
        title="Relevant backend project" if relevant else f"Unrelated project {project_id}",
        description="Built a Python backend service."
        if relevant
        else "Built unrelated mobile screens.",
        technologies=["Python", "FastAPI"] if relevant else ["Swift"],
        capabilities=["external_api_integration"] if relevant else ["media_processing"],
    )


def test_irrelevant_evidence_does_not_expand_grade_two_context() -> None:
    profile = _profile()
    job = _job()
    match = calculate_match(job, profile)
    builder = CandidateContextBuilder(Settings())
    relevant_evidence = [_evidence(1, relevant=True)]
    relevant_projects = [_project(1, relevant=True)]
    before = builder.build(
        profile=profile,
        projects=relevant_projects,
        evidence=relevant_evidence,
        job=job,
        match=match,
        grade=2,
    )
    after = builder.build(
        profile=profile,
        projects=relevant_projects,
        evidence=relevant_evidence + [_evidence(item, relevant=False) for item in range(2, 102)],
        job=job,
        match=match,
        grade=2,
    )
    assert after.selected_evidence_ids == {1}
    assert after.evidence == before.evidence
    assert after.character_count == before.character_count
    assert after.character_count <= Settings().candidate_context_grade2_max_total_chars


def test_relevant_overflow_is_bounded_and_has_stable_ordering() -> None:
    profile = _profile()
    job = _job()
    match = calculate_match(job, profile)
    settings = Settings()
    evidence = [_evidence(item, relevant=True) for item in range(1, 51)]
    projects = [_project(item, relevant=True) for item in range(1, 21)]
    builder = CandidateContextBuilder(settings)
    first = builder.build(
        profile=profile, projects=projects, evidence=evidence, job=job, match=match, grade=2
    )
    second = builder.build(
        profile=profile, projects=projects, evidence=evidence, job=job, match=match, grade=2
    )
    assert [item["id"] for item in first.evidence] == list(
        range(1, settings.candidate_context_grade2_max_evidence + 1)
    )
    assert [item["id"] for item in first.projects] == list(
        range(1, settings.candidate_context_grade2_max_projects + 1)
    )
    assert first.prompt_payload() == second.prompt_payload()
    assert first.character_count <= settings.candidate_context_grade2_max_total_chars
    grade_three = builder.build(
        profile=profile, projects=projects, evidence=evidence, job=job, match=match, grade=3
    )
    assert len(grade_three.evidence) == settings.candidate_context_grade3_max_evidence
    assert len(grade_three.projects) == settings.candidate_context_grade3_max_projects
    assert grade_three.character_count <= settings.candidate_context_grade3_max_total_chars
