import re

from app.modules.imports.ai_schemas import AIExtractionResult
from app.modules.jobs.normalization import RawJobData


def fake_extraction(raw: RawJobData) -> AIExtractionResult:
    text = raw.raw_text or raw.raw_description
    lower = text.casefold()
    required = raw.raw_required_skills or _skills_before(
        text, r"\s+(?:are|is)\s+(?:strictly\s+)?required"
    )
    if not required:
        required = _skills_after(
            text, r"(?:requirements?|must have|required)\s*[:\-]?\s*([^.!\n]+)"
        )
    known_required = (
        [
            skill
            for skill in ["Python", "FastAPI", "PostgreSQL", "Docker"]
            if skill.casefold() in lower and "required" in lower
        ]
        if not raw.raw_required_skills
        else []
    )
    if known_required:
        required = known_required
    if not required:
        required = [
            skill
            for skill in ["Python", "FastAPI", "PostgreSQL", "Docker"]
            if skill.casefold() in lower
        ]
    preferred = raw.raw_preferred_skills or _skills_before(
        text, r"\s+(?:are|is)\s+(?:a\s+)?(?:plus|preferred|nice to have|an advantage)"
    )
    if not preferred:
        preferred = _skills_after(
            text, r"(?:nice to have|preferred|plus|advantage)\s*[:\-]?\s*([^.!\n]+)"
        )
    if re.search(r"\baws\b[^.\n]{0,40}\b(?:plus|preferred|nice to have|advantage)\b", text, re.I):
        preferred = ["AWS"]
    stack = raw.raw_stack_skills or _skills_after(
        text, r"(?:stack|tech stack)\s*[:\-]?\s*([^.!\n]+)"
    )
    title = raw.raw_title
    if title == "Unknown title" or len(title) > 200:
        title = _title_from_text(text)
    company = raw.raw_company if raw.raw_company != "Unknown company" else None
    required_experience = _experience_after(text, r"(?:required|must have|at least)")
    preferred_experience = _experience_after(text, r"(?:preferred|nice to have|plus)")
    return AIExtractionResult(
        title=title,
        company=company,
        description=text,
        location=raw.raw_location,
        work_mode="remote" if "fully remote" in lower or "remote" in lower else None,
        raw_salary=raw.raw_salary or _salary_from_text(text),
        required_skills=required,
        preferred_skills=preferred,
        stack_skills=stack,
        hard_requirements=[required_experience] if required_experience else [],
        preferred_requirements=[preferred_experience] if preferred_experience else [],
        required_experience=required_experience,
        preferred_experience=preferred_experience,
        required_experience_min_years=raw.raw_required_experience_min_years,
        required_experience_area=raw.raw_required_experience_area,
    )


def merge_extraction(raw: RawJobData, extracted: AIExtractionResult) -> RawJobData:
    structured_source = raw.source_name in {"json", "jsonld", "url-json", "manual"}
    preserve_title = structured_source and raw.raw_title != "Unknown title"
    preserve_company = structured_source and raw.raw_company != "Unknown company"
    return RawJobData(
        source_name=raw.source_name,
        source_url=raw.source_url,
        raw_payload=raw.raw_payload,
        raw_text=raw.raw_text,
        raw_title=raw.raw_title if preserve_title else extracted.title or raw.raw_title,
        raw_company=raw.raw_company if preserve_company else extracted.company or raw.raw_company,
        # The user-supplied source is authoritative; an extraction summary must not
        # silently discard the full vacancy text needed for later review.
        raw_description=raw.raw_description or extracted.description or "",
        application_url=raw.application_url or extracted.application_url,
        raw_location=raw.raw_location or extracted.location,
        # Deterministic source extraction is authoritative when it found an
        # explicit arrangement. AI enrichment may fill an absent value but
        # must not reinterpret "office / remote" as hybrid.
        raw_work_mode=(
            raw.raw_work_mode
            if raw.raw_work_mode is not None
            else extracted.work_mode
        ),
        raw_employment_type=raw.raw_employment_type,
        raw_salary=extracted.raw_salary or raw.raw_salary,
        raw_salary_min=extracted.salary_min or raw.raw_salary_min,
        raw_salary_max=extracted.salary_max or raw.raw_salary_max,
        raw_salary_currency=extracted.currency or raw.raw_salary_currency,
        raw_salary_period=extracted.salary_period or raw.raw_salary_period,
        raw_salary_gross=extracted.salary_gross
        if extracted.salary_gross is not None
        else raw.raw_salary_gross,
        raw_required_skills=extracted.required_skills or raw.raw_required_skills,
        raw_preferred_skills=extracted.preferred_skills or raw.raw_preferred_skills,
        raw_stack_skills=extracted.stack_skills or raw.raw_stack_skills,
        raw_hard_requirements=extracted.hard_requirements or raw.raw_hard_requirements,
        raw_preferred_requirements=(
            extracted.preferred_requirements or raw.raw_preferred_requirements
        ),
        raw_required_experience=extracted.required_experience or raw.raw_required_experience,
        raw_preferred_experience=extracted.preferred_experience or raw.raw_preferred_experience,
        raw_required_experience_min_years=(
            extracted.required_experience_min_years or raw.raw_required_experience_min_years
        ),
        raw_required_experience_area=(
            extracted.required_experience_area or raw.raw_required_experience_area
        ),
        company_website=extracted.company_website,
        contact_name=extracted.contact_name,
        contact_email=extracted.contact_email,
        contact_phone=extracted.contact_phone,
        application_instructions=extracted.application_instructions,
        source_published_at=extracted.published_at,
    )


def extraction_is_useful(raw: RawJobData) -> bool:
    """AI enrichment is useful for every non-empty vacancy description at Grade 1+."""
    return bool(raw.raw_description.strip())


def _skills_after(text: str, pattern: str) -> list[str]:
    match = re.search(pattern, text, re.I)
    if not match:
        return []
    return _split_skills(match.group(1))


def _skills_before(text: str, suffix: str) -> list[str]:
    match = re.search(r"([A-Za-z0-9+#. /,]+?)" + suffix, text, re.I)
    return _split_skills(match.group(1)) if match else []


def _split_skills(value: str) -> list[str]:
    return [
        item.strip(" -.,")
        for item in re.split(r"\s*(?:,|/|;|\band\b|•)\s*", value, flags=re.I)
        if item.strip(" -.,")
    ]


def _title_from_text(text: str) -> str | None:
    match = re.search(
        r"(?:looking for|hiring) (?:an? )?([A-Z][A-Za-z ]+(?:Engineer|Developer))", text
    )
    return match.group(1).strip().rstrip(".") if match else None


def _salary_from_text(text: str) -> str | None:
    match = re.search(r"(?:salary|compensation)\s*[:\-]?\s*([^\n]+)", text, re.I)
    return match.group(1).strip().rstrip(".") if match else None


def _experience_after(text: str, qualifier: str) -> str | None:
    match = re.search(qualifier + r"[^.\n]{0,80}(\d+\+?\s+years[^.\n]*)", text, re.I)
    return match.group(1).strip() if match else None
