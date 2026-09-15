from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.integrations.llm.exceptions import LLMProviderError
from app.integrations.llm.openai_compatible import OpenAICompatibleLLMProvider
from app.modules.assessment.config import grade_config
from app.modules.assessment.repository import AssessmentRepository
from app.modules.assessment.schemas import AssessmentRead
from app.modules.assessment.service import PROMPT_VERSION, fake_assessment
from app.modules.candidate.schemas import CandidateProfile
from app.modules.imports.ai_models import AIExtraction
from app.modules.imports.ai_prompt import EXTRACTION_PROMPT_VERSION
from app.modules.imports.ai_repository import AIExtractionRepository
from app.modules.imports.ai_service import extraction_is_useful, fake_extraction, merge_extraction
from app.modules.imports.extractors import (
    extract_json,
    extract_json_ld,
    extract_text,
    raw_from_mapping,
)
from app.modules.imports.schemas import JobImportRequest
from app.modules.imports.url_fetch import fetch_public_url
from app.modules.jobs.models import JobPosting, JobSourceRecord
from app.modules.jobs.normalization import JobNormalizer, RawJobData
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobRead
from app.modules.matches.models import JobMatch
from app.modules.matches.repository import JobMatchRepository
from app.modules.matches.schemas import JobMatchRead
from app.modules.matching.schemas import MatchResult
from app.modules.matching.service import calculate_match


class ImportService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def extract(self, request: JobImportRequest) -> RawJobData:
        if request.input_type == "text":
            return extract_text(request.text or "")
        if request.input_type == "json":
            return extract_json(request.payload or {})
        final_url, content_type, content = await fetch_public_url(str(request.url))
        if "json" in content_type:
            return raw_from_mapping(__import__("json").loads(content), source_name="url-json", source_url=final_url)
        jsonld = extract_json_ld(content, final_url)
        if jsonld is not None:
            return jsonld
        return extract_text(content, source_name="url-text")

    async def _extract_with_ai(
        self, raw: RawJobData, user_id: int, grade: int
    ) -> tuple[RawJobData, AIExtraction | None]:
        if grade == 0 or not extraction_is_useful(raw):
            return raw, None
        if not self.settings.llm_enabled or self.settings.llm_provider == "disabled":
            return raw, None
        usage: dict[str, int] = {}
        if self.settings.llm_provider == "fake":
            result = fake_extraction(raw)
            provider_name = "fake"
            model = "fake-v1"
        elif self.settings.llm_provider == "openai_compatible":
            config = grade_config(1, self.settings)
            provider = OpenAICompatibleLLMProvider.from_settings(self.settings)
            provider.model_name = config.model or provider.model_name
            provider.reasoning_effort = config.reasoning
            result = await provider.extract_job(raw)
            provider_name = provider.provider_name
            model = provider.model_name
            usage = provider.last_usage
        else:
            raise LLMProviderError("Unsupported extraction provider.")
        record = await AIExtractionRepository(self.session).create(
            user_id=user_id, result=result, provider=provider_name, model=model,
            prompt_version=EXTRACTION_PROMPT_VERSION,
            input_tokens=usage.get("input_tokens"),
            cached_input_tokens=usage.get("cached_input_tokens"),
            output_tokens=usage.get("output_tokens"),
            reasoning_tokens=usage.get("reasoning_tokens"),
        )
        return merge_extraction(raw, result), record

    async def run(
        self, request: JobImportRequest, user_id: int, profile: CandidateProfile, profile_id: int
    ) -> dict[str, Any]:
        raw = await self.extract(request)
        grade = request.grade if request.grade is not None else self.settings.ai_default_grade
        extraction_record = None
        try:
            raw, extraction_record = await self._extract_with_ai(raw, user_id, grade)
        except LLMProviderError:
            # The original source still remains eligible for deterministic import.
            pass
        normalized = JobNormalizer().normalize(raw)
        posting = await JobRepository(self.session).create_for_user(normalized, raw, user_id)
        if extraction_record is not None:
            source_record = await self.session.scalar(
                select(JobSourceRecord).where(JobSourceRecord.job_id == posting.id)
            )
            extraction_record.job_id = posting.id
            extraction_record.source_record_id = source_record.id if source_record else None
            await self.session.commit()
        match = await self._create_match(posting, profile, profile_id, user_id)
        assessment = None
        warnings = list(normalized.warnings)
        if grade > 0:
            try:
                assessment = await self._assess(posting, profile, match, user_id, grade)
            except LLMProviderError as exc:
                warnings.append(f"assessment failed: {exc}")
        source = await self.session.scalar(select(JobSourceRecord).where(JobSourceRecord.job_id == posting.id))
        source_data = {
            "id": source.id,
            "job_id": source.job_id,
            "source_name": source.source_name,
            "source_url": source.source_url,
            "normalization_warnings": source.normalization_warnings,
            "normalization_version": source.normalization_version,
        } if source else {}
        return {
            "job": JobRead.model_validate(posting).model_dump(mode="json"),
            "source": source_data,
            "match": JobMatchRead.model_validate(match).model_dump(mode="json"),
            "assessment": assessment.model_dump(mode="json") if assessment else None,
            "warnings": warnings,
        }

    async def _create_match(
        self, job: JobPosting, profile: CandidateProfile, profile_id: int, user_id: int
    ) -> JobMatch:
        result = calculate_match(job, profile)
        return await JobMatchRepository(self.session).create(
            user_id=user_id, job_id=job.id, profile_id=profile_id,
            profile_snapshot=profile.model_dump(mode="json"), result=result,
        )

    async def _assess(
        self, job: JobPosting, profile: CandidateProfile, match_record: JobMatch,
        user_id: int, grade: int,
    ) -> AssessmentRead:
        config = grade_config(grade, self.settings)
        if not self.settings.llm_enabled or self.settings.llm_provider == "disabled":
            raise LLMProviderError("AI assessment is disabled.")
        match = MatchResult.model_validate(match_record, from_attributes=True)
        if self.settings.llm_provider == "fake":
            result = fake_assessment(job, profile, match, config)
            provider_name = "fake"
        elif self.settings.llm_provider == "openai_compatible":
            provider = OpenAICompatibleLLMProvider.from_settings(self.settings)
            provider.model_name = config.model or provider.model_name
            provider.reasoning_effort = config.reasoning
            result = await provider.assess_job(job, profile, match, grade)
            provider_name = provider.provider_name
            usage = provider.last_usage
        else:
            raise LLMProviderError("Unsupported assessment provider.")
        if self.settings.llm_provider == "fake":
            usage = {}
        record = await AssessmentRepository(self.session).create(
            job_id=job.id, user_id=user_id, job_match_id=match_record.id,
            provider=provider_name, model=config.model, grade=grade,
            purpose=f"grade{grade}_" + ("screening" if grade == 1 else "application" if grade == 2 else "interview"),
            analysis=result, prompt_version=PROMPT_VERSION,
            input_tokens=usage.get("input_tokens"),
            cached_input_tokens=usage.get("cached_input_tokens"),
            output_tokens=usage.get("output_tokens"),
            reasoning_tokens=usage.get("reasoning_tokens"),
        )
        return AssessmentRead(
            **result.model_dump(), id=record.id, job_id=record.job_id,
            job_match_id=record.job_match_id, provider=record.provider,
            model=record.model, prompt_version=record.prompt_version,
            input_tokens=record.input_tokens, cached_input_tokens=record.cached_input_tokens,
            output_tokens=record.output_tokens,
            reasoning_tokens=record.reasoning_tokens, purpose=record.purpose,
            created_at=record.created_at,
        )
