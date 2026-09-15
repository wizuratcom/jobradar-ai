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


def raw_from_mapping(payload: Mapping[str, object], *, source_name: str, source_url: str | None = None) -> RawJobData:
    employer = _first(payload, "employer", "hiringOrganization", "company", "company_name")
    if isinstance(employer, Mapping):
        employer = _first(employer, "name", "title")
    location = _first(payload, "location_text", "location", "city")
    if isinstance(location, Mapping):
        location = _first(location, "name", "addressLocality", "address")
    skills = _first(payload, "required_skills", "requiredSkills", "skills", "requirements")
    preferred = _first(payload, "preferred_skills", "preferredSkills")
    return RawJobData(
        source_name=source_name,
        raw_title=_string(_first(payload, "title", "job_title", "position")) or "Unknown title",
        raw_company=_string(employer) or "Unknown company",
        raw_description=_string(_first(payload, "description", "job_description", "body", "text")) or "",
        source_url=source_url,
        application_url=_string(_first(payload, "application_url", "url", "apply_url")),
        raw_location=_string(location),
        raw_work_mode=_first(payload, "work_mode", "workplace", "remote"),
        raw_employment_type=_string(_first(payload, "employment_type", "employmentType")),
        raw_salary=_string(_first(payload, "salary", "salary_text", "compensation")),
        raw_required_skills=[_string(item) or "" for item in skills] if isinstance(skills, list) else None,
        raw_preferred_skills=[_string(item) or "" for item in preferred] if isinstance(preferred, list) else None,
        raw_payload=dict(payload),
    )


def extract_text(text: str, *, source_name: str = "text") -> RawJobData:
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]
    title = next((line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith(("title:", "position:"))), lines[0] if lines else "Unknown title")
    company = next((line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith(("company:", "employer:"))), "Unknown company")
    location = next((line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith("location:")), None)
    salary = next((line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith("salary:")), None)
    mode = next((line.split(":", 1)[1].strip() for line in lines if line.casefold().startswith(("work mode:", "remote:"))), None)
    required_line = next((line.split(":", 1)[1] for line in lines if line.casefold().startswith(("required skills:", "requirements:"))), "")
    required = [item.strip() for item in re.split(r"[,;|]", required_line) if item.strip()]
    return RawJobData(
        source_name=source_name,
        raw_title=title,
        raw_company=company,
        raw_description=text.strip(),
        raw_location=location,
        raw_work_mode=mode,
        raw_salary=salary,
        raw_required_skills=required,
        raw_text=text,
    )


def extract_json(payload: dict[str, object]) -> RawJobData:
    return raw_from_mapping(payload, source_name="json")


def extract_json_ld(html: str, source_url: str) -> RawJobData | None:
    scripts = re.findall(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", html, re.I | re.S)
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
