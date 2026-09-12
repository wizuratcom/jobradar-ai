from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.jobs.service import normalize_text
from app.modules.matching.schemas import MatchResult, ScoreBreakdown

TITLE_WEIGHT = 25
CORE_SKILLS_WEIGHT = 40
SECONDARY_SKILLS_WEIGHT = 20
LOCATION_WEIGHT = 15


def _matching_items(required: list[str], candidate_skills: list[str]) -> list[str]:
    candidate_by_normalized = {normalize_text(skill): skill for skill in candidate_skills}
    return [
        candidate_by_normalized[normalize_text(skill)]
        for skill in required
        if normalize_text(skill) in candidate_by_normalized
    ]


def _proportional_score(matches: list[str], available: list[str], weight: int) -> int:
    if not available:
        return 0
    return round(weight * len(matches) / len(available))


def _title_score(title: str, desired_titles: list[str]) -> int:
    normalized_title = normalize_text(title)
    has_relevant_title = any(
        normalize_text(item) in normalized_title for item in desired_titles
    )
    return TITLE_WEIGHT if has_relevant_title else 0


def _location_score(job: JobPosting, candidate: CandidateProfile) -> int:
    if job.remote and candidate.preferred_remote:
        return LOCATION_WEIGHT
    is_preferred_location = job.location and any(
        normalize_text(location) == normalize_text(job.location)
        for location in candidate.preferred_locations
    )
    if is_preferred_location:
        return LOCATION_WEIGHT
    return 0


def recommendation_for(score: int) -> str:
    if score >= 80:
        return "strong_apply"
    if score >= 60:
        return "apply"
    if score >= 40:
        return "maybe"
    return "skip"


def calculate_match(job: JobPosting, candidate: CandidateProfile) -> MatchResult:
    required_skills = job.required_skills
    matched_core = _matching_items(required_skills, candidate.core_skills)
    matched_secondary = _matching_items(required_skills, candidate.secondary_skills)
    all_candidate_skills = candidate.core_skills + candidate.secondary_skills
    known_skills = {normalize_text(skill) for skill in all_candidate_skills}
    missing_skills = [
        skill for skill in required_skills if normalize_text(skill) not in known_skills
    ]
    breakdown = ScoreBreakdown(
        title=_title_score(job.title, candidate.desired_titles),
        core_skills=_proportional_score(matched_core, candidate.core_skills, CORE_SKILLS_WEIGHT),
        secondary_skills=_proportional_score(
            matched_secondary,
            candidate.secondary_skills,
            SECONDARY_SKILLS_WEIGHT,
        ),
        location=_location_score(job, candidate),
    )
    score = sum(breakdown.model_dump().values())
    return MatchResult(
        score=score,
        recommendation=recommendation_for(score),
        breakdown=breakdown,
        matched_core_skills=matched_core,
        matched_secondary_skills=matched_secondary,
        missing_skills=missing_skills,
    )
