import re

from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.jobs.normalization import clean_text
from app.modules.matching.schemas import MatchResult, RequirementExplanation, ScoreBreakdown


def normalize_text(value: str) -> str:
    return clean_text(value).casefold()


TITLE_WEIGHT = 25
REQUIRED_REQUIREMENTS_WEIGHT = 35
PREFERRED_REQUIREMENTS_WEIGHT = 15
STACK_SKILLS_WEIGHT = 10
LOCATION_WEIGHT = 15
TITLE_STOP_WORDS = {"senior", "junior", "lead", "staff", "principal", "the", "a", "an"}
TITLE_EQUIVALENTS = {"developer": "software_builder", "engineer": "software_builder"}
TITLE_DOMAINS = {"backend", "frontend", "data", "devops", "mobile"}
TITLE_TECHNOLOGIES = {"python", "java", "javascript", "typescript", "golang", "ruby", "php"}
SKILL_ALIASES = {"postgres": "postgresql"}
CAPABILITY_SATISFIERS = {"relational_databases": {"postgresql"}}
STACK_SKILL_BONUS = 3
MAX_EXPLANATION_EVIDENCE = 3


def _skill_key(value: str) -> str:
    """Map only explicit, controlled technical aliases before comparison."""
    normalized = normalize_text(value)
    if re.fullmatch(r"python(?:\s+\d+(?:\.\d+)*)?", normalized):
        return "python"
    normalized = normalized.replace("http(s)", "http")
    aliases = {
        "http/rest": "rest_api_development",
        "rest": "rest_api_development",
        "rest api": "rest_api_development",
        "restful api": "rest_api_development",
        "restful apis": "rest_api_development",
        "relational database experience": "relational_databases",
        "relational databases": "relational_databases",
        "rdbms": "relational_databases",
        "реляционные субд": "relational_databases",
        "реляционные базы данных": "relational_databases",
        "external api integration": "external_api_integration",
        "external api integrations": "external_api_integration",
        "third-party api integration": "external_api_integration",
        "third party api integration": "external_api_integration",
        "интеграция с внешними api": "external_api_integration",
        "llm api integration": "llm_integration",
        "llm integration": "llm_integration",
    }
    normalized = aliases.get(normalized, normalized)
    return SKILL_ALIASES.get(normalized, normalized)


def _candidate_match(required: str, candidate_by_key: dict[str, str]) -> str | None:
    key = _skill_key(required)
    if key in candidate_by_key:
        return candidate_by_key[key]
    for candidate_key in CAPABILITY_SATISFIERS.get(key, set()):
        if candidate_key in candidate_by_key:
            return candidate_by_key[candidate_key]
    return None


def _matching_items(required: list[str], candidate_skills: list[str]) -> list[str]:
    candidate_by_normalized = {_skill_key(skill): skill for skill in candidate_skills}
    return [
        match for skill in required if (match := _candidate_match(skill, candidate_by_normalized))
    ]


def _candidate_facts(candidate: CandidateProfile) -> tuple[dict[str, str], dict[str, list[int]]]:
    """Return only explicit user-provided skills/capabilities and their evidence."""
    values = candidate.core_skills + candidate.secondary_skills
    by_key = {_skill_key(value): value for value in values}
    evidence_by_key: dict[str, list[int]] = {}
    for skill in candidate.skills:
        value = skill.canonical_name or skill.name
        key = _skill_key(value)
        by_key.setdefault(key, skill.name)
        evidence_by_key[key] = skill.evidence_ids
    for capability in candidate.capabilities:
        key = _skill_key(capability.name)
        by_key.setdefault(key, capability.name)
        evidence_by_key[key] = capability.evidence_ids
    return by_key, evidence_by_key


def _proportional_score(matches: list[str], available: list[str], weight: int) -> int:
    if not available:
        return 0
    return round(weight * len(matches) / len(available))


def _stack_bonus(matches: list[str]) -> int:
    """Award relevance for each matched stack skill without penalising extra stack items."""
    return min(STACK_SKILLS_WEIGHT, len(matches) * STACK_SKILL_BONUS)


def _title_score(title: str, desired_titles: list[str]) -> int:
    job_tokens = _title_tokens(title)
    return max(
        (_title_similarity(job_tokens, _title_tokens(item)) for item in desired_titles), default=0
    )


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
    if (
        job_technologies
        and desired_technologies
        and not job_technologies.intersection(desired_technologies)
    ):
        score = min(score, 15)
    return score


def _location_score(job: JobPosting, candidate: CandidateProfile) -> int:
    if (job.remote_allowed or job.work_mode in {"remote", "hybrid"}) and candidate.preferred_remote:
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
    candidate_by_key, evidence_by_key = _candidate_facts(candidate)
    matched_required = _matching_items(required_skills, list(candidate_by_key.values()))
    missing_required = [
        skill for skill in required_skills if _candidate_match(skill, candidate_by_key) is None
    ]
    preferred_skills = job.preferred_skills or []
    matched_preferred = _matching_items(preferred_skills, list(candidate_by_key.values()))
    missing_preferred = [
        skill for skill in preferred_skills if _candidate_match(skill, candidate_by_key) is None
    ]
    all_candidate_skills = list(candidate_by_key.values())
    experience_requirements: list[RequirementExplanation] = []
    experience_matched = False
    if job.required_experience_min_years is not None:
        requirement = f"{job.required_experience_min_years}+ years" + (
            f" {job.required_experience_area}"
            if job.required_experience_area
            else " relevant experience"
        )
        months = candidate.experience.backend_experience_months
        relevant = bool(
            candidate.experience.backend_experience_text
            or candidate.experience.commercial_backend_experience
        )
        required_months = job.required_experience_min_years * 12
        if months is not None and months >= required_months:
            status = "matched"
            context = f"confirmed {months // 12} years"
            experience_matched = True
        elif months is None and relevant:
            status = "unverified_duration"
            context = "relevant experience exists but duration is not supplied"
        else:
            status = "missing"
            context = "confirmed duration is below the requirement" if months is not None else None
        experience_requirements.append(
            RequirementExplanation(requirement=requirement, status=status, matched_by=context)
        )
    required_total = len(required_skills) + int(job.required_experience_min_years is not None)
    breakdown = ScoreBreakdown(
        title=_title_score(job.title, candidate.desired_titles),
        required_requirements=round(
            REQUIRED_REQUIREMENTS_WEIGHT * (len(matched_required) + int(experience_matched))
            / required_total
        ) if required_total else 0,
        preferred_requirements=_proportional_score(
            matched_preferred, preferred_skills, PREFERRED_REQUIREMENTS_WEIGHT
        ),
        stack_skills=_stack_bonus(_matching_items(job.stack_skills or [], all_candidate_skills)),
        location=_location_score(job, candidate),
    )
    score = sum(breakdown.model_dump().values())
    required_explanations = [
        RequirementExplanation(
            requirement=skill,
            status="matched"
            if (matched := _candidate_match(skill, candidate_by_key))
            else "missing",
            matched_by=matched,
            evidence_ids=(evidence_by_key.get(_skill_key(matched), [])[:MAX_EXPLANATION_EVIDENCE]
                if matched else []),
        )
        for skill in required_skills
    ]
    preferred_explanations = [
        RequirementExplanation(
            requirement=skill,
            status="matched" if (matched := _candidate_match(skill, candidate_by_key)) else "missing",
            matched_by=matched,
            evidence_ids=(evidence_by_key.get(_skill_key(matched), [])[:MAX_EXPLANATION_EVIDENCE]
                if matched else []),
        )
        for skill in preferred_skills
    ]
    return MatchResult(
        score=score,
        recommendation=recommendation_for(score),
        breakdown=breakdown,
        matched_required_requirements=matched_required,
        matched_preferred_requirements=matched_preferred,
        matched_stack_skills=_matching_items(job.stack_skills or [], all_candidate_skills),
        missing_required_requirements=missing_required,
        missing_preferred_requirements=missing_preferred,
        required_requirement_explanations=required_explanations,
        preferred_requirement_explanations=preferred_explanations,
        experience_requirements=experience_requirements,
    )
