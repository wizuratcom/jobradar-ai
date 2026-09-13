import json

from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult

SYSTEM_PROMPT = """You are an assistant that produces a factual job-application brief.
The deterministic match score is authoritative: do not recalculate, replace, or invent a score.
Never invent candidate experience, years, employers, projects, achievements, metrics,
certifications, or technologies. Use only the supplied candidate profile and deterministic
match. Any vacancy requirement not supported by those inputs must be described as a gap.
Return only a JSON object matching the requested schema."""


def build_analysis_messages(
    job: JobPosting,
    candidate: CandidateProfile,
    deterministic_match: MatchResult,
) -> list[dict[str, str]]:
    job_data = {
        "company": job.company,
        "title": job.title,
        "description": job.description,
        "application_url": job.application_url,
        "location_text": job.location_text,
        "work_mode": job.work_mode,
        "employment_type": job.employment_type,
        "required_skills": job.required_skills,
        "preferred_skills": job.preferred_skills,
    }
    user_content = "\n\n".join(
        [
            "CANDIDATE PROFILE\n" + candidate.model_dump_json(indent=2),
            "JOB POSTING\n" + json.dumps(job_data, ensure_ascii=False, indent=2),
            "DETERMINISTIC MATCH RESULT\n" + deterministic_match.model_dump_json(indent=2),
            "EXPECTED OUTPUT JSON SCHEMA\n"
            + json.dumps(JobAnalysisResult.model_json_schema(), indent=2),
            "INSTRUCTIONS\nAnalyze fit using only these inputs. Keep the recommendation aligned "
            "with the deterministic recommendation and provide factual, concise guidance.",
        ]
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
