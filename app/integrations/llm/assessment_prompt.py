import json

from app.modules.assessment.schemas import AssessmentResult
from app.modules.candidate.context import CandidateAssessmentContext
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult

ASSESSMENT_PROMPT_VERSION = "assessment-v1"


def build_assessment_messages(
    job: JobPosting, candidate_context: CandidateAssessmentContext, match: MatchResult, grade: int
) -> list[dict[str, str]]:
    system = (
        "Assess this vacancy using only the supplied candidate profile, canonical vacancy, "
        "and deterministic match. Never invent experience, employers, years, technologies, "
        "metrics, education, or certifications. Compare the candidate profile independently "
        "with the vacancy requirements. The deterministic match is an auxiliary, transparent "
        "signal, not ground truth. Never describe the JobRadar score itself as a blocker or "
        "vacancy requirement. Blockers must be actual candidate/vacancy incompatibilities. "
        "For Grade 2/3, recommendations that assert a candidate fact must cite one or more "
        "IDs from candidate_evidence in grounded_recommendations. Do not cite nonexistent IDs. "
        "Return only JSON matching the schema. Grade is depth, not permission to fabricate."
    )
    payload = {
        "grade": grade,
        "candidate_context": candidate_context.prompt_payload(),
        "job": {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location_text": job.location_text,
            "work_mode": job.work_mode,
            "remote_allowed": job.remote_allowed,
            "onsite_allowed": job.onsite_allowed,
            "hybrid_allowed": job.hybrid_allowed,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "stack_skills": job.stack_skills,
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
