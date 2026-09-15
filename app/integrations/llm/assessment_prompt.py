import json

from app.modules.assessment.schemas import AssessmentResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult

ASSESSMENT_PROMPT_VERSION = "assessment-v1"


def build_assessment_messages(
    job: JobPosting, candidate: CandidateProfile, match: MatchResult, grade: int
) -> list[dict[str, str]]:
    system = (
        "Assess this vacancy using only the supplied candidate profile, canonical vacancy, "
        "and deterministic match. Never invent experience, employers, years, technologies, "
        "metrics, education, or certifications. The deterministic score is authoritative. "
        "Return only JSON matching the schema. Grade is depth, not permission to fabricate."
    )
    payload = {
        "grade": grade,
        "candidate_profile": candidate.model_dump(mode="json"),
        "job": {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location_text": job.location_text,
            "work_mode": job.work_mode,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
        },
        "deterministic_match": match.model_dump(mode="json"),
    }
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(
                {"input": payload, "expected_schema": AssessmentResult.model_json_schema()},
                ensure_ascii=False,
            ),
        },
    ]
