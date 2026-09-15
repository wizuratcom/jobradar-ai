from decimal import Decimal

import pytest

from app.modules.jobs.extraction import ManualJobExtractor
from app.modules.jobs.normalization import (
    JobNormalizer,
    RawJobData,
    normalize_salary,
    normalize_work_mode,
)
from app.modules.jobs.schemas import JobCreate


def test_normalizer_creates_canonical_salary_and_skills() -> None:
    result = JobNormalizer().normalize(
        RawJobData(
            source_name="test",
            raw_title=" Python Backend Developer ",
            raw_company=" Acme ",
            raw_description=" Work ",
            raw_work_mode="fully remote",
            raw_salary="€2k-2.5k gross monthly",
            raw_required_skills=["Python", " FastAPI ", "python"],
            raw_preferred_skills=["Docker", "docker"],
        )
    )
    assert result.job.title == "Python Backend Developer"
    assert result.job.work_mode == "remote"
    assert result.job.salary_min == 2000
    assert result.job.salary_max == 2500
    assert result.job.salary_currency == "EUR"
    assert result.job.salary_period == "month"
    assert result.job.salary_gross is True
    assert result.job.required_skills == ["Python", "FastAPI"]
    assert result.job.preferred_skills == ["Docker"]


def test_ambiguous_salary_stays_unknown() -> None:
    result = JobNormalizer().normalize(
        RawJobData(
            source_name="test",
            raw_title="Role",
            raw_company="Acme",
            raw_description="Work",
            raw_salary="competitive",
        )
    )
    assert result.job.salary_min is None
    assert result.warnings == ["salary could not be deterministically normalized"]


def test_legacy_structured_salary_is_preserved() -> None:
    result = JobNormalizer().normalize(
        RawJobData(
            source_name="test",
            raw_title="Role",
            raw_company="Acme",
            raw_description="Work",
            raw_salary_min=1000,
            raw_salary_max=2000,
            raw_salary_currency="eur",
        )
    )
    assert result.job.salary_min == 1000
    assert result.job.salary_max == 2000
    assert result.job.salary_currency == "EUR"
    assert result.warnings == []


def test_manual_extractor_preserves_raw_source_representation() -> None:
    raw = ManualJobExtractor().extract(
        JobCreate(company="Acme", title="Role", description="Work", required_skills=[])
    )
    assert raw.source_name == "manual"
    assert raw.raw_title == "Role"
    assert raw.raw_payload == {
        "company": "Acme",
        "title": "Role",
        "description": "Work",
        "url": None,
        "application_url": None,
        "location": None,
        "location_text": None,
        "remote": False,
        "work_mode": None,
        "employment_type": None,
        "salary_min": None,
        "salary_max": None,
        "currency": None,
        "salary_currency": None,
        "salary_text": None,
        "required_skills": [],
        "preferred_skills": [],
    }


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("remote", "remote"),
        ("fully remote", "remote"),
        ("hybrid", "hybrid"),
        ("onsite", "onsite"),
        ("on-site", "onsite"),
        ("distributed", "unknown"),
    ],
)
def test_work_mode_normalization(raw_value: str, expected: str) -> None:
    assert normalize_work_mode(raw_value) == expected


@pytest.mark.parametrize(
    ("value", "minimum", "maximum", "currency", "period"),
    [
        ("€2,000-2,800 gross per month", "2000", "2800", "EUR", "month"),
        ("$3,500-$5,000 annual", "3500", "5000", "USD", "year"),
        ("2,000 EUR monthly", "2000", None, "EUR", "month"),
        ("2500 EUR monthly", "2500", None, "EUR", "month"),
        ("€2k-2.8k gross monthly", "2000", "2800", "EUR", "month"),
    ],
)
def test_salary_normalizes_thousands_and_k_notation(
    value: str, minimum: str, maximum: str | None, currency: str, period: str
) -> None:
    result = normalize_salary(value)
    assert result[0] == Decimal(minimum)
    assert result[1] == Decimal(maximum) if maximum is not None else result[1] is None
    assert result[2:] == (currency, period, True if "gross" in value else None)


def test_salary_leaves_ambiguous_comma_decimal_unparsed() -> None:
    assert normalize_salary("€2,50 monthly") == (None, None, None, None, None)
