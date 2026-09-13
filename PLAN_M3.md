# JobRadar AI — Milestone 3 plan

## Goal and compatibility

Add an optional LLM-assisted analysis layer without changing the existing job
API or deterministic matching rules. Deterministic matching remains
authoritative and all existing endpoints must work when LLM support is disabled
or unavailable.

## Proposed request flow

```text
POST /api/v1/jobs/{job_id}/analyze
    -> Analysis router validates the path and creates AnalysisService
    -> JobService loads the existing JobPosting
    -> candidate YAML profile is loaded
    -> deterministic calculate_match(job, candidate) is calculated unchanged
    -> configured LLMProvider analyzes the three inputs
    -> provider response is validated as a Pydantic JobAnalysisResult
    -> AnalysisRepository persists an immutable JobAnalysis history row
    -> structured analysis response is returned
```

The provider interface is asynchronous and vendor-neutral. The analysis module
depends on the interface, not on HTTP or a vendor-specific SDK.

## Provider behavior and failure policy

- `DisabledLLMProvider` is the default. An analysis request returns a clear
  controlled `503` response explaining that LLM analysis is disabled; it does
  not affect jobs or deterministic matching.
- `FakeLLMProvider` works locally without network or credentials and returns a
  repeatable, structured result derived only from the supplied profile, job,
  and deterministic match.
- `OpenAICompatibleLLMProvider` uses `httpx` against an OpenAI-compatible
  chat-completions endpoint. It uses configurable timeout, bounded retry count,
  exponential backoff, and retries only transport failures, HTTP 429, and HTTP
  5xx responses.
- Empty content, malformed JSON, and JSON that fails Pydantic validation are
  integration failures. They are logged without secrets, returned as a useful
  application-level error, and never persisted.

The prompt lives in a dedicated integration module. It explicitly separates
candidate profile, job posting, deterministic result, instructions, and JSON
schema. Its anti-fabrication rule prohibits claims not directly supported by
those inputs; missing requirements are presented as gaps.

## Persistence decision

Analysis history will be preserved. Each successful result becomes a
`job_analyses` row containing `job_id`, provider, optional model name,
recommendation, validated JSON payload, and timestamp. History is useful for
auditing provider/model changes and does not alter a job or deterministic match.
API keys, raw provider responses, and secrets are never stored. PostgreSQL will
use JSONB for the structured payload; SQLite test runs use a portable JSON
variant.

## New files

- `app/integrations/__init__.py`
- `app/integrations/llm/__init__.py`
- `app/integrations/llm/base.py`
- `app/integrations/llm/disabled.py`
- `app/integrations/llm/fake.py`
- `app/integrations/llm/openai_compatible.py`
- `app/integrations/llm/prompt.py`
- `app/integrations/llm/exceptions.py`
- `app/modules/analysis/__init__.py`
- `app/modules/analysis/models.py`
- `app/modules/analysis/schemas.py`
- `app/modules/analysis/repository.py`
- `app/modules/analysis/service.py`
- `app/modules/analysis/router.py`
- `alembic/versions/0003_add_job_analyses.py`
- `tests/test_llm_providers.py`
- `tests/test_analysis.py`

## Existing files to change

- `app/core/config.py` — optional LLM settings and safe defaults.
- `app/main.py` — register the analysis router.
- `alembic/env.py` — load analysis metadata for autogeneration.
- `pyproject.toml` — make existing `httpx` a runtime dependency for the
  optional generic HTTP adapter.
- `.env.example` — disabled-by-default placeholders only.
- `README.md` — LLM analysis documentation, fake mode, real-provider setup,
  failure behavior, Mermaid architecture diagram, and completed roadmap item.
- `tests/conftest.py` and `tests/test_api.py` — ensure deterministic test
  configuration and cover the API flow alongside the existing endpoints.

Docker Compose and CI need no credentials: `.env` defaults to disabled mode,
and tests use the fake provider or mocks only.

## Verification sequence

1. Install dependencies, run Ruff and the full test suite with no API key.
2. Build/start Docker Compose and check Alembic migration plus `/health`.
3. Verify existing job creation and deterministic match unchanged.
4. Enable `LLM_ENABLED=true` and `LLM_PROVIDER=fake`, then create, analyze,
   retrieve, and restart to confirm persisted analysis history.
5. Return to disabled mode and confirm startup plus non-LLM endpoints remain
   usable while the analysis endpoint gives a controlled disabled response.
