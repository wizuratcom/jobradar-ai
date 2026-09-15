import re

from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.jobs.normalization import clean_text
from app.modules.matching.schemas import MatchResult, ScoreBreakdown


def normalize_text(value: str) -> str:
    return clean_text(value).casefold()


TITLE_WEIGHT = 25
CORE_SKILLS_WEIGHT = 40
SECONDARY_SKILLS_WEIGHT = 20
LOCATION_WEIGHT = 15
TITLE_STOP_WORDS = {"senior", "junior", "lead", "staff", "principal", "the", "a", "an"}
TITLE_EQUIVALENTS = {"developer": "software_builder", "engineer": "software_builder"}
TITLE_DOMAINS = {"backend", "frontend", "data", "devops", "mobile"}
TITLE_TECHNOLOGIES = {"python", "java", "javascript", "typescript", "golang", "ruby", "php"}
SKILL_ALIASES = {"postgres": "postgresql"}


def _skill_key(value: str) -> str:
    """Map only explicit, controlled technical aliases before comparison."""
    normalized = normalize_text(value)
    return SKILL_ALIASES.get(normalized, normalized)


def _matching_items(required: list[str], candidate_skills: list[str]) -> list[str]:
    candidate_by_normalized = {_skill_key(skill): skill for skill in candidate_skills}
    return [
        candidate_by_normalized[_skill_key(skill)]
        for skill in required
        if _skill_key(skill) in candidate_by_normalized
    ]


def _proportional_score(matches: list[str], available: list[str], weight: int) -> int:
    if not available:
        return 0
    return round(weight * len(matches) / len(available))


def _title_score(title: str, desired_titles: list[str]) -> int:
    job_tokens = _title_tokens(title)
    return max((_title_similarity(job_tokens, _title_tokens(item)) for item in desired_titles), default=0)


def _title_tokens(value: str) -> set[str]:
    return {
        TITLE_EQUIVALENTS.get(token, token)
        for token in re.findall(r"[a-z0-9+#]+", normalize_text(value))
        if token not in TITLE_STOP_WORDS
    }


def _title_similarity(job_tokens: set[str], desired_tokens: set[str]) -> int:
    if not job_tokens or not desired_tokens:
        return 0
    job_domains = job_tokens & TITLE_DOMAINS
    desired_domains = desired_tokens & TITLE_DOMAINS
    if job_domains and desired_domains and not job_domains.intersection(desired_domains):
        return 0
    overlap = len(job_tokens.intersection(desired_tokens))
    if not overlap:
        return 0
    if job_tokens.issuperset(desired_tokens) or desired_tokens.issuperset(job_tokens):
        return TITLE_WEIGHT
    ratio = overlap / max(len(job_tokens), len(desired_tokens))
    score = 18 if ratio >= 2 / 3 else 12 if ratio >= 1 / 2 else 0
    job_technologies = job_tokens & TITLE_TECHNOLOGIES
    desired_technologies = desired_tokens & TITLE_TECHNOLOGIES
    if job_technologies and desired_technologies and not job_technologies.intersection(desired_technologies):
        score = min(score, 15)
    return score


def _location_score(job: JobPosting, candidate: CandidateProfile) -> int:
    if job.work_mode == "remote" and candidate.preferred_remote:
        return LOCATION_WEIGHT
    is_preferred_location = job.location_text and any(
        normalize_text(location) == normalize_text(job.location_text or "")
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
    known_skills = {_skill_key(skill) for skill in all_candidate_skills}
    missing_skills = [
        skill for skill in required_skills if _skill_key(skill) not in known_skills
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
