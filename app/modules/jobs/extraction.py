from typing import Protocol

from app.modules.jobs.normalization import RawJobData
from app.modules.jobs.schemas import JobCreate


class JobExtractor(Protocol):
    def extract(self, value: object) -> RawJobData: ...


class ManualJobExtractor:
    def extract(self, value: JobCreate) -> RawJobData:
        return RawJobData(
            source_name="manual",
            raw_title=value.title,
            raw_company=value.company,
            raw_description=value.description,
            application_url=str(value.application_url or value.url)
            if value.application_url or value.url
            else None,
            raw_location=value.location_text or value.location,
            raw_work_mode=value.work_mode if value.work_mode else value.remote,
            raw_employment_type=value.employment_type,
            raw_salary=value.salary_text,
            raw_salary_min=value.salary_min,
            raw_salary_max=value.salary_max,
            raw_salary_currency=value.salary_currency or value.currency,
            raw_required_skills=value.required_skills,
            raw_preferred_skills=value.preferred_skills,
            raw_stack_skills=value.stack_skills,
            raw_payload=value.model_dump(mode="json"),
        )
