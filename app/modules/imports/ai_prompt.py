import json

from app.modules.imports.ai_schemas import AIExtractionResult
from app.modules.jobs.normalization import RawJobData

EXTRACTION_PROMPT_VERSION = "extraction-v1"


def build_extraction_messages(raw: RawJobData) -> list[dict[str, str]]:
    source = {
        "raw_text": raw.raw_text,
        "raw_payload": raw.raw_payload,
        "deterministic_fields": {
            "title": raw.raw_title,
            "company": raw.raw_company,
            "description": raw.raw_description,
            "location": raw.raw_location,
            "work_mode": raw.raw_work_mode,
            "salary": raw.raw_salary,
            "required_skills": raw.raw_required_skills,
            "preferred_skills": raw.raw_preferred_skills,
        },
    }
    system = (
        "Extract only information supported by the supplied vacancy. Do not invent missing "
        "information. Do not convert assumptions into facts. Distinguish must-have/required "
        "requirements from nice-to-have/preferred requirements. Put technologies/tools only in "
        "required_skills or preferred_skills. Put broader non-skill conditions (experience, "
        "language, work authorization, degree) in hard_requirements or preferred_requirements. "
        "Return only JSON matching the schema."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"source": source, "schema": AIExtractionResult.model_json_schema()})},
    ]
