from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult


class LLMProvider(Protocol):
    provider_name: str
    model_name: str | None

    async def analyze_job(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
    ) -> JobAnalysisResult: ...


def create_llm_provider(settings: Settings) -> LLMProvider:
    from app.integrations.llm.disabled import DisabledLLMProvider
    from app.integrations.llm.fake import FakeLLMProvider
    from app.integrations.llm.openai_compatible import OpenAICompatibleLLMProvider

    if not settings.llm_enabled or settings.llm_provider == "disabled":
        return DisabledLLMProvider()
    if settings.llm_provider == "fake":
        return FakeLLMProvider()
    return OpenAICompatibleLLMProvider.from_settings(settings)
