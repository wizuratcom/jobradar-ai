import asyncio
import logging

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.llm.assessment_prompt import build_assessment_messages
from app.integrations.llm.exceptions import (
    LLMConfigurationError,
    LLMHTTPError,
    LLMInvalidResponseError,
    LLMUnavailableError,
)
from app.integrations.llm.prompt import build_analysis_messages
from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.assessment.schemas import AssessmentResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.imports.ai_prompt import build_extraction_messages
from app.modules.imports.ai_schemas import AIExtractionResult
from app.modules.jobs.models import JobPosting
from app.modules.jobs.normalization import RawJobData
from app.modules.matching.schemas import MatchResult

logger = logging.getLogger(__name__)


class OpenAICompatibleLLMProvider:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        max_retries: int,
        reasoning_effort: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.reasoning_effort = reasoning_effort
        self.transport = transport
        self.last_usage: dict[str, int] = {}

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenAICompatibleLLMProvider":
        api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
        if not settings.llm_base_url or not api_key or not settings.llm_model:
            raise LLMConfigurationError(
                "OpenAI-compatible LLM requires LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL."
            )
        return cls(
            base_url=settings.llm_base_url,
            api_key=api_key,
            model_name=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def analyze_job(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
    ) -> JobAnalysisResult:
        payload = {
            "model": self.model_name,
            "messages": build_analysis_messages(job, candidate, deterministic_match),
            "response_format": {"type": "json_object"},
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await self._post_with_retries(client, payload, headers)
        self.last_usage = _usage_from_response(response)
        return self._parse_response(response)

    async def assess_job(
        self,
        job: JobPosting,
        candidate: CandidateProfile,
        deterministic_match: MatchResult,
        grade: int,
    ) -> AssessmentResult:
        payload = {
            "model": self.model_name,
            "messages": build_assessment_messages(job, candidate, deterministic_match, grade),
            "response_format": {"type": "json_object"},
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
            response = await self._post_with_retries(client, payload, headers)
        self.last_usage = _usage_from_response(response)
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return AssessmentResult.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise LLMInvalidResponseError("LLM provider returned invalid assessment JSON.") from exc

    async def extract_job(self, raw: RawJobData) -> AIExtractionResult:
        payload = {
            "model": self.model_name,
            "messages": build_extraction_messages(raw),
            "response_format": {"type": "json_object"},
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds, transport=self.transport) as client:
            response = await self._post_with_retries(client, payload, headers)
        self.last_usage = _usage_from_response(response)
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return AIExtractionResult.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise LLMInvalidResponseError("LLM provider returned invalid extraction JSON.") from exc


    async def _post_with_retries(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if response.status_code < 400:
                    return response
                if response.status_code != 429 and response.status_code < 500:
                    raise _http_error(response)
                error = f"HTTP {response.status_code}"
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                error = type(exc).__name__

            if attempt == self.max_retries:
                raise LLMUnavailableError(
                    f"LLM provider was unavailable after {attempt + 1} attempt(s): {error}."
                )
            logger.warning("Retrying LLM request after transient failure: %s", error)
            await asyncio.sleep(2**attempt)
        raise AssertionError("Retry loop should always return or raise.")

    @staticmethod
    def _parse_response(response: httpx.Response) -> JobAnalysisResult:
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMInvalidResponseError(
                "LLM provider returned no valid message content."
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMInvalidResponseError("LLM provider returned empty message content.")
        try:
            return JobAnalysisResult.model_validate_json(content)
        except ValidationError as exc:
            raise LLMInvalidResponseError("LLM provider returned invalid analysis JSON.") from exc


def _usage_from_response(response: httpx.Response) -> dict[str, int]:
    usage = response.json().get("usage", {})
    if not isinstance(usage, dict):
        return {}
    return {
        key: int(value)
        for key, value in {
            "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
            "cached_input_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens")
            if isinstance(usage.get("prompt_tokens_details"), dict)
            else None,
            "output_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
            "reasoning_tokens": usage.get("reasoning_tokens"),
        }.items()
        if isinstance(value, int)
    }


def _http_error(response: httpx.Response) -> LLMHTTPError:
    error = response.json().get("error", {})
    if not isinstance(error, dict):
        error = {}
    return LLMHTTPError(
        status=response.status_code,
        error_type=error.get("type") if isinstance(error.get("type"), str) else None,
        code=error.get("code") if isinstance(error.get("code"), str) else None,
        param=error.get("param") if isinstance(error.get("param"), str) else None,
        message=error.get("message") if isinstance(error.get("message"), str) else None,
    )
