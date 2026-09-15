import re

from app.modules.imports.ai_schemas import AIExtractionResult
from app.modules.jobs.normalization import RawJobData


def fake_extraction(raw: RawJobData) -> AIExtractionResult:
    text = raw.raw_text or raw.raw_description
    lower = text.casefold()
    required = _skills_before(text, r"\s+(?:are|is)\s+(?:strictly\s+)?required")
    if not required:
        required = _skills_after(text, r"(?:requirements?|must have|required)\s*[:\-]?\s*([^.!\n]+)")
    known_required = [
        skill
        for skill in ["Python", "FastAPI", "PostgreSQL", "Docker"]
        if skill.casefold() in lower and "required" in lower
    ]
    if known_required:
        required = known_required
    if not required:
        required = [skill for skill in ["Python", "FastAPI", "PostgreSQL", "Docker"] if skill.casefold() in lower]
    preferred = _skills_before(text, r"\s+(?:are|is)\s+(?:a\s+)?(?:plus|preferred|nice to have|an advantage)")
    if not preferred:
        preferred = _skills_after(text, r"(?:nice to have|preferred|plus|advantage)\s*[:\-]?\s*([^.!\n]+)")
    if re.search(r"\baws\b[^.\n]{0,40}\b(?:plus|preferred|nice to have|advantage)\b", text, re.I):
        preferred = ["AWS"]
    title = raw.raw_title if raw.raw_title != "Unknown title" else _title_from_text(text)
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
        hard_requirements=[required_experience] if required_experience else [],
        preferred_requirements=[preferred_experience] if preferred_experience else [],
        required_experience=required_experience,
        preferred_experience=preferred_experience,
    )


def merge_extraction(raw: RawJobData, extracted: AIExtractionResult) -> RawJobData:
    return RawJobData(
        source_name=raw.source_name, source_url=raw.source_url, raw_payload=raw.raw_payload,
        raw_text=raw.raw_text, raw_title=extracted.title or raw.raw_title,
        raw_company=extracted.company or raw.raw_company,
        raw_description=extracted.description or raw.raw_description,
        application_url=extracted.application_url or raw.application_url,
        raw_location=extracted.location or raw.raw_location,
        raw_work_mode=extracted.work_mode or raw.raw_work_mode,
        raw_employment_type=raw.raw_employment_type,
        raw_salary=extracted.raw_salary or raw.raw_salary,
        raw_salary_min=extracted.salary_min or raw.raw_salary_min,
        raw_salary_max=extracted.salary_max or raw.raw_salary_max,
        raw_salary_currency=extracted.currency or raw.raw_salary_currency,
        raw_salary_period=extracted.salary_period or raw.raw_salary_period,
        raw_salary_gross=extracted.salary_gross if extracted.salary_gross is not None else raw.raw_salary_gross,
        raw_required_skills=extracted.required_skills or raw.raw_required_skills,
        raw_preferred_skills=extracted.preferred_skills or raw.raw_preferred_skills,
        raw_hard_requirements=extracted.hard_requirements,
        raw_preferred_requirements=extracted.preferred_requirements,
        raw_required_experience=extracted.required_experience,
        raw_preferred_experience=extracted.preferred_experience,
        company_website=extracted.company_website,
        contact_name=extracted.contact_name,
        contact_email=extracted.contact_email,
        contact_phone=extracted.contact_phone,
        application_instructions=extracted.application_instructions,
        source_published_at=extracted.published_at,
    )


def extraction_is_useful(raw: RawJobData) -> bool:
    return raw.raw_title == "Unknown title" or raw.raw_company == "Unknown company" or not raw.raw_required_skills


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
    match = re.search(r"(?:looking for|hiring) (?:an? )?([A-Z][A-Za-z ]+(?:Engineer|Developer))", text)
    return match.group(1).strip().rstrip(".") if match else None


def _salary_from_text(text: str) -> str | None:
    match = re.search(r"(?:salary|compensation)\s*[:\-]?\s*([^\n]+)", text, re.I)
    return match.group(1).strip().rstrip(".") if match else None


def _experience_after(text: str, qualifier: str) -> str | None:
    match = re.search(qualifier + r"[^.\n]{0,80}(\d+\+?\s+years[^.\n]*)", text, re.I)
    return match.group(1).strip() if match else None
