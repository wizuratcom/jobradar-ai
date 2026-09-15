import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

WorkMode = Literal["remote", "hybrid", "onsite", "unknown"]
NORMALIZATION_VERSION = "1"


@dataclass(frozen=True)
class RawJobData:
    source_name: str
    raw_title: str
    raw_company: str
    raw_description: str
    source_url: str | None = None
    application_url: str | None = None
    raw_location: str | None = None
    raw_work_mode: str | bool | None = None
    raw_employment_type: str | None = None
    raw_salary: str | None = None
    raw_salary_min: Decimal | float | int | None = None
    raw_salary_max: Decimal | float | int | None = None
    raw_salary_currency: str | None = None
    raw_salary_period: str | None = None
    raw_salary_gross: bool | None = None
    raw_required_skills: list[str] | None = None
    raw_preferred_skills: list[str] | None = None
    raw_hard_requirements: list[str] | None = None
    raw_preferred_requirements: list[str] | None = None
    raw_required_experience: str | None = None
    raw_preferred_experience: str | None = None
    company_website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    application_instructions: str | None = None
    source_published_at: str | None = None
    raw_payload: dict[str, object] | None = None
    raw_text: str | None = None


@dataclass(frozen=True)
class CanonicalJobData:
    title: str
    company: str
    description: str
    application_url: str | None
    location_text: str | None
    work_mode: WorkMode
    employment_type: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    salary_period: str | None
    salary_gross: bool | None
    required_skills: list[str]
    preferred_skills: list[str]


@dataclass(frozen=True)
class NormalizationResult:
    job: CanonicalJobData
    warnings: list[str]
    normalization_version: str = NORMALIZATION_VERSION


def clean_text(value: str) -> str:
    return " ".join(value.split())


def normalize_skills(values: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = clean_text(value)
        if cleaned and cleaned.casefold() not in seen:
            result.append(cleaned)
            seen.add(cleaned.casefold())
    return result


def normalize_work_mode(value: str | bool | None) -> WorkMode:
    if value is True:
        return "remote"
    if value is False or value is None:
        return "unknown"
    normalized = clean_text(value).casefold()
    if "remote" in normalized:
        return "remote"
    if "hybrid" in normalized:
        return "hybrid"
    if normalized in {"onsite", "on-site", "office", "in office"}:
        return "onsite"
    return "unknown"


def normalize_salary(
    value: str | None,
) -> tuple[Decimal | None, Decimal | None, str | None, str | None, bool | None]:
    if not value:
        return None, None, None, None, None
    text = clean_text(value).casefold()
    currency = (
        "EUR" if "€" in text or "eur" in text else "USD" if "$" in text or "usd" in text else None
    )
    period = (
        "month"
        if "month" in text or "monthly" in text
        else "year"
        if "year" in text or "annual" in text
        else None
    )
    gross = True if "gross" in text else False if "net" in text else None
    # A comma followed by one or two digits is ambiguous across locales (for example,
    # 2,50 may be a decimal amount), so do not guess.
    if re.search(r"\d+,\d{1,2}(?!\d)", text):
        return None, None, None, None, None
    numbers = re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?\s*k?", text)
    if not currency or not period or not numbers or len(numbers) > 2:
        return None, None, None, None, None

    def amount(item: str) -> Decimal:
        normalized = item.replace(",", "").replace("k", "")
        return Decimal(normalized) * (1000 if item.endswith("k") else 1)

    values = [amount(item) for item in numbers]
    return values[0], values[1] if len(values) == 2 else None, currency, period, gross


def normalize_structured_salary(
    minimum: Decimal | float | int | None,
    maximum: Decimal | float | int | None,
    currency: str | None,
    period: str | None = None,
    gross: bool | None = None,
) -> tuple[Decimal | None, Decimal | None, str | None, str | None, bool | None]:
    normalized_currency = currency.strip().upper() if currency else None
    if normalized_currency and len(normalized_currency) != 3:
        normalized_currency = None
    return (
        Decimal(str(minimum)) if minimum is not None else None,
        Decimal(str(maximum)) if maximum is not None else None,
        normalized_currency,
        period if period in {"month", "year"} else None,
        gross,
    )


class JobNormalizer:
    def normalize(self, raw: RawJobData) -> NormalizationResult:
        salary = (
            normalize_salary(raw.raw_salary)
            if raw.raw_salary
            else normalize_structured_salary(
                raw.raw_salary_min, raw.raw_salary_max, raw.raw_salary_currency,
                raw.raw_salary_period, raw.raw_salary_gross,
            )
        )
        warnings: list[str] = []
        if raw.raw_salary and salary[0] is None:
            warnings.append("salary could not be deterministically normalized")
        return NormalizationResult(
            job=CanonicalJobData(
                title=clean_text(raw.raw_title),
                company=clean_text(raw.raw_company),
                description=raw.raw_description.strip(),
                application_url=raw.application_url,
                location_text=clean_text(raw.raw_location) if raw.raw_location else None,
                work_mode=normalize_work_mode(raw.raw_work_mode),
                employment_type=clean_text(raw.raw_employment_type)
                if raw.raw_employment_type
                else None,
                salary_min=salary[0],
                salary_max=salary[1],
                salary_currency=salary[2],
                salary_period=salary[3],
                salary_gross=salary[4],
                required_skills=normalize_skills(raw.raw_required_skills),
                preferred_skills=normalize_skills(raw.raw_preferred_skills),
            ),
            warnings=warnings,
        )
