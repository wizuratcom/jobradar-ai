from fastapi import HTTPException, status

from app.modules.candidate.models import CandidateEvidence, CandidateProfileRecord, CandidateProject
from app.modules.candidate.schemas import (
    CandidateEvidenceContext,
    CandidateEvidenceRead,
    CandidateProfile,
    CandidateProfileRead,
    CandidateProjectContext,
    CandidateProjectRead,
    ProfileCompletenessRead,
)


def to_profile(record: CandidateProfileRecord) -> CandidateProfile:
    migrated_skills = record.skills or [
        {"name": skill} for skill in (record.core_skills or []) + (record.secondary_skills or [])
    ]
    return CandidateProfile.model_validate(
        {
            "name": record.name,
            "desired_titles": record.desired_titles,
            "core_skills": record.core_skills,
            "secondary_skills": record.secondary_skills,
            "preferred_remote": record.preferred_remote,
            "preferred_locations": record.preferred_locations,
            "skills": migrated_skills,
            "capabilities": record.capabilities or [],
            "experience": record.experience or {},
            "languages": record.languages or [],
            "preferred_work_modes": record.preferred_work_modes or [],
            "target_seniority": record.target_seniority,
            "salary_min": record.salary_min,
            "salary_currency": record.salary_currency,
            "employment_types": record.employment_types or [],
            "relocation_willing": record.relocation_willing,
        }
    )


def to_profile_read(record: CandidateProfileRecord) -> CandidateProfileRead:
    return CandidateProfileRead(id=record.id, **to_profile(record).model_dump())


def require_profile(record: CandidateProfileRecord | None) -> CandidateProfileRecord:
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Create a candidate profile before matching jobs.",
        )
    return record


def to_project_read(record: CandidateProject) -> CandidateProjectRead:
    return CandidateProjectRead.model_validate(record, from_attributes=True)


def to_evidence_read(record: CandidateEvidence) -> CandidateEvidenceRead:
    return CandidateEvidenceRead.model_validate(
        {**record.__dict__, "evidence_type": record.evidence_type}
    )


def to_assessment_context(
    profile: CandidateProfile,
    projects: list[CandidateProject],
    evidence: list[CandidateEvidence],
) -> CandidateProfile:
    return profile.model_copy(
        update={
            "projects": [
                CandidateProjectContext(
                    id=item.id,
                    title=item.title,
                    description=item.description,
                    technologies=item.technologies or [],
                    capabilities=item.capabilities or [],
                )
                for item in projects
            ],
            "evidence": [
                CandidateEvidenceContext(
                    id=item.id,
                    evidence_type=item.evidence_type,
                    title=item.title,
                    description=item.description,
                    technologies=item.technologies or [],
                    capabilities=item.capabilities or [],
                )
                for item in evidence
            ],
        }
    )


def profile_completeness(
    profile: CandidateProfile, *, project_count: int, evidence_count: int
) -> ProfileCompletenessRead:
    score = 0
    missing: list[str] = []
    weak: list[str] = []
    if profile.name:
        score += 10
    if profile.desired_titles:
        score += 15
    else:
        missing.append("target titles")
    if profile.core_skills or profile.skills:
        score += 20
    else:
        missing.append("skills")
    if profile.capabilities:
        score += 15
    else:
        weak.append("capabilities")
    if (
        profile.experience.backend_experience_text
        or profile.experience.commercial_backend_experience
    ):
        score += 10
    else:
        missing.append("experience context")
    if profile.experience.backend_experience_months is not None:
        score += 5
    else:
        weak.append("experience duration")
    if project_count or evidence_count:
        score += 15
    else:
        missing.append("projects or evidence")
    if profile.languages:
        score += 5
    else:
        missing.append("languages")
    if profile.preferred_locations or profile.preferred_work_modes or profile.preferred_remote:
        score += 5
    else:
        weak.append("work preferences")
    return ProfileCompletenessRead(
        completeness_score=score, missing_sections=missing, weak_sections=weak
    )
