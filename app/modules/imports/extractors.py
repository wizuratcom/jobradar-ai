import json
import re
from collections.abc import Mapping

from app.modules.jobs.normalization import RawJobData, clean_text


def _first(payload: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in payload and payload[key] not in (None, "", []):
            return payload[key]
    return None


def _string(value: object | None) -> str | None:
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, Mapping):
        nested = _first(value, "name", "title", "value")
        return _string(nested)
    return str(value) if value is not None else None


def raw_from_mapping(
    payload: Mapping[str, object], *, source_name: str, source_url: str | None = None
) -> RawJobData:
    employer = _first(payload, "employer", "hiringOrganization", "company", "company_name")
    if isinstance(employer, Mapping):
        employer = _first(employer, "name", "title")
    location = _first(payload, "location_text", "location", "city")
    if isinstance(location, Mapping):
        location = _first(location, "name", "addressLocality", "address")
    skills = _first(payload, "required_skills", "requiredSkills", "skills", "requirements")
    preferred = _first(payload, "preferred_skills", "preferredSkills")
    stack = _first(payload, "stack_skills", "stack", "technologies", "tech_stack")
    return RawJobData(
        source_name=source_name,
        raw_title=_string(_first(payload, "title", "job_title", "position")) or "Unknown title",
        raw_company=_string(employer) or "Unknown company",
        raw_description=_string(_first(payload, "description", "job_description", "body", "text"))
        or "",
        source_url=source_url,
        application_url=_string(_first(payload, "application_url", "url", "apply_url")),
        raw_location=_string(location),
        raw_work_mode=_first(payload, "work_mode", "workplace", "remote"),
        raw_employment_type=_string(_first(payload, "employment_type", "employmentType")),
        raw_salary=_string(_first(payload, "salary", "salary_text", "compensation")),
        raw_required_skills=[_string(item) or "" for item in skills]
        if isinstance(skills, list)
        else None,
        raw_preferred_skills=[_string(item) or "" for item in preferred]
        if isinstance(preferred, list)
        else None,
        raw_stack_skills=[_string(item) or "" for item in stack]
        if isinstance(stack, list)
        else None,
        raw_payload=dict(payload),
    )


def extract_text(text: str, *, source_name: str = "text") -> RawJobData:
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    title = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines
            if line.casefold().startswith(("title:", "position:"))
        ),
        lines[0] if lines else "Unknown title",
    )
    company = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines
            if line.casefold().startswith(("company:", "employer:"))
        ),
        "Unknown company",
    )
    location = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines
            if line.casefold().startswith("location:")
        ),
        None,
    )
    salary = next(
        (line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith("salary:")),
        None,
    )
    if salary is None:
        salary = _salary_from_text(text)
    mode = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines
            if line.casefold().startswith(("work mode:", "remote:"))
        ),
        None,
    )
    if mode is None:
        has_remote = bool(re.search(r"\bremote\b|удален", text, re.I))
        has_onsite = bool(re.search(r"\boffice\b|\bonsite\b|офис", text, re.I))
        has_hybrid = bool(re.search(r"\bhybrid\b|гибрид", text, re.I))
        # Keep a mixed arrangement intact so normalization can record every
        # explicitly offered option (for example, "office / remote").
        if has_hybrid or (has_remote and has_onsite):
            mode = text
        elif has_remote:
            mode = "remote"
        elif has_onsite:
            mode = "onsite"
    required_line = next(
        (
            line.split(":", 1)[1]
            for line in lines
            if line.casefold().startswith(
                ("required skills:", "required:", "requirements:", "обязательные требования:")
            )
        ),
        "",
    )
    preferred_line = next(
        (
            line.split(":", 1)[1]
            for line in lines
            if line.casefold().startswith(("preferred:", "будет плюсом:"))
        ),
        "",
    )
    stack_line = next(
        (
            line.split(":", 1)[1]
            for line in lines
            if line.casefold().startswith(("stack:", "tech stack:"))
        ),
        "",
    )
    required = [item.strip() for item in re.split(r"[,;|]", required_line) if item.strip()]
    preferred = [item.strip() for item in re.split(r"[,;|]", preferred_line) if item.strip()]
    stack = [item.strip() for item in re.split(r"[,;|]", stack_line) if item.strip()]
    required_experience, minimum_years, experience_area = _required_experience_from_text(text)
    return RawJobData(
        source_name=source_name,
        raw_title=title,
        raw_company=company,
        raw_description=text.strip(),
        raw_location=location,
        raw_work_mode=mode,
        raw_salary=salary,
        raw_required_skills=required,
        raw_preferred_skills=preferred,
        raw_stack_skills=stack,
        raw_hard_requirements=[required_experience] if required_experience else None,
        raw_required_experience=required_experience,
        raw_required_experience_min_years=minimum_years,
        raw_required_experience_area=experience_area,
        raw_text=text,
    )


def extract_json(payload: dict[str, object]) -> RawJobData:
    return raw_from_mapping(payload, source_name="json")


def _salary_from_text(text: str) -> str | None:
    """Find a plainly currency-marked salary without guessing its period."""
    number = r"\d(?:[\d, ]*\d)?(?:\.\d+)?\s*k?"
    suffix = r"(?:\s+(?:gross|net))?(?:\s+(?:(?:per\s+)?monthly|month|year|annual))?"
    pattern = (
        rf"(?:[$€]\s*{number}(?:\s*-\s*[$€]?\s*{number})?{suffix}"
        rf"|{number}\s*-\s*{number}\s*[$€]{suffix}"
        rf"|{number}\s*[$€]{suffix})"
    )
    match = re.search(pattern, text)
    return clean_text(match.group(0)) if match else None


def _required_experience_from_text(text: str) -> tuple[str | None, int | None, str | None]:
    russian = re.search(
        r"опыт\s+(?P<area>[^.!\n]*?)\s+(?:от|не менее)\s*(?P<years>\d+)\s*(?:года?|лет)",
        text,
        re.I,
    )
    if russian:
        return (
            clean_text(russian.group(0)),
            int(russian.group("years")),
            clean_text(russian.group("area")),
        )
    match = re.search(
        r"(?:requirements?\s*:|must have|at least)\s*([^.!\n]*\b\d+\+?\s+years[^.!\n]*)",
        text,
        re.I,
    )
    if not match:
        return None, None, None
    value = clean_text(match.group(1))
    years = re.search(r"(\d+)\+?\s+years", value, re.I)
    area = re.search(r"years?(?:\s+of)?\s+(.+?)\s+experience", value, re.I)
    return (
        value,
        int(years.group(1)) if years else None,
        clean_text(area.group(1)) if area else None,
    )


def extract_json_ld(html: str, source_url: str) -> RawJobData | None:
    scripts = re.findall(
        r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", html, re.I | re.S
    )
    for script in scripts:
        try:
            payload = json.loads(script)
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if isinstance(candidate, dict) and (
                candidate.get("@type") == "JobPosting"
                or "JobPosting" in (candidate.get("@type") or [])
            ):
                return raw_from_mapping(candidate, source_name="jsonld", source_url=source_url)
    return None
