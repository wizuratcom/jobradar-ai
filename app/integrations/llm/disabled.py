from app.integrations.llm.exceptions import LLMDisabledError
from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.schemas import MatchResult


class DisabledLLMProvider:
    provider_name = "disabled"
    model_name: str | None = None

    async def analyze_job(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
    ) -> JobAnalysisResult:
        raise LLMDisabledError("LLM analysis is disabled. Set LLM_ENABLED=true to enable it.")
