import asyncio
import json

import httpx
import pytest

from app.integrations.llm.disabled import DisabledLLMProvider
from app.integrations.llm.exceptions import (
    LLMDisabledError,
    LLMInvalidResponseError,
    LLMUnavailableError,
)
from app.integrations.llm.fake import FakeLLMProvider
from app.integrations.llm.openai_compatible import OpenAICompatibleLLMProvider
from app.modules.candidate.schemas import CandidateProfile
from app.modules.jobs.models import JobPosting
from app.modules.matching.service import calculate_match


def candidate() -> CandidateProfile:
    return CandidateProfile(
        name="Example Candidate",
        desired_titles=["Python Backend Developer"],
        core_skills=["Python", "FastAPI", "PostgreSQL"],
        secondary_skills=["Docker"],
        preferred_remote=True,
        preferred_locations=["Remote"],
    )


def job() -> JobPosting:
    return JobPosting(
        company="Acme",
        title="Python Backend Developer",
        description="Build APIs",
        remote=True,
        required_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
    )


def valid_analysis_payload() -> dict[str, object]:
    return {
        "recommendation": "apply",
        "summary": "The profile lists relevant backend skills.",
        "strengths": ["Python", "FastAPI"],
        "gaps": ["Redis"],
        "risk_factors": [],
        "cv_emphasis": ["Keep claims tied to the profile."],
        "recruiter_message": "My profile lists Python and FastAPI.",
        "interview_topics": ["FastAPI"],
        "questions_to_prepare": ["How is Redis used?"],
    }


@pytest.mark.asyncio
async def test_disabled_provider_returns_controlled_error() -> None:
    vacancy = job()
    profile = candidate()
    with pytest.raises(LLMDisabledError):
        await DisabledLLMProvider().analyze_job(
            vacancy,
            profile,
            calculate_match(vacancy, profile),
        )


@pytest.mark.asyncio
async def test_fake_provider_returns_grounded_structured_analysis() -> None:
    vacancy = job()
    profile = candidate()
    result = await FakeLLMProvider().analyze_job(
        vacancy,
        profile,
        calculate_match(vacancy, profile),
    )
    assert result.recommendation == "strong_apply"
    assert result.gaps == ["Redis"]
    assert "years" not in result.recruiter_message.casefold()


@pytest.mark.asyncio
async def test_openai_compatible_provider_validates_json_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(valid_analysis_payload())}}]},
            request=request,
        )

    provider = OpenAICompatibleLLMProvider(
        base_url="https://llm.example/v1",
        api_key="test-key",
        model_name="test-model",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    result = await provider.analyze_job(job(), candidate(), calculate_match(job(), candidate()))
    assert result.summary == "The profile lists relevant backend skills."


@pytest.mark.asyncio
async def test_openai_compatible_provider_rejects_invalid_schema() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "{}"}}]},
            request=request,
        )

    provider = OpenAICompatibleLLMProvider(
        base_url="https://llm.example/v1",
        api_key="test-key",
        model_name="test-model",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMInvalidResponseError):
        await provider.analyze_job(job(), candidate(), calculate_match(job(), candidate()))


@pytest.mark.asyncio
async def test_openai_compatible_provider_retries_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(valid_analysis_payload())}}]},
            request=request,
        )

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    provider = OpenAICompatibleLLMProvider(
        base_url="https://llm.example/v1",
        api_key="test-key",
        model_name="test-model",
        timeout_seconds=1,
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )
    await provider.analyze_job(job(), candidate(), calculate_match(job(), candidate()))
    assert calls == 2


@pytest.mark.asyncio
async def test_openai_compatible_provider_reports_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    provider = OpenAICompatibleLLMProvider(
        base_url="https://llm.example/v1",
        api_key="test-key",
        model_name="test-model",
        timeout_seconds=1,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMUnavailableError):
        await provider.analyze_job(job(), candidate(), calculate_match(job(), candidate()))
