import asyncio
import logging

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.integrations.llm.exceptions import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMUnavailableError,
)
from app.integrations.llm.prompt import build_analysis_messages
from app.modules.analysis.schemas import JobAnalysisResult
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.transport = transport

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
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await self._post_with_retries(client, payload, headers)
        return self._parse_response(response)

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
                    raise LLMUnavailableError(
                        f"LLM provider returned HTTP {response.status_code}."
                    )
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
