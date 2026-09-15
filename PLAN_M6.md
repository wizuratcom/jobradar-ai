# Milestone 6 plan: Smart Vacancy Import & Graded Assessment

## Scope

Milestone 6 adds a user-supplied vacancy workflow for pasted text, arbitrary
JSON, and safe public URLs. Existing manual structured job creation remains
backward compatible. No crawling, scheduled discovery, browser automation,
Telegram, or automatic applications are included.

## Flow

`ImportRequest -> extractor -> RawJobData -> JobNormalizer -> JobPosting +
JobSourceRecord + UserJob -> deterministic JobMatch -> optional graded
assessment -> persisted history`.

Text and JSON use deterministic field extraction first. Grade 1+ may use the
configured provider as a structured extraction/assessment fallback. Grade 0
never calls an AI provider. URL imports validate every redirect target, fetch
only bounded public HTTP content, then inspect JSON-LD and cleaned text.

## Grades and models

Grade 0 is deterministic only. Grades 1, 2, and 3 use strict Pydantic result
schemas with increasing depth. A single grade-routing configuration maps each
grade to model/reasoning settings; business logic does not hardcode vendors.
The fake provider supports all grades and extraction in tests. Real provider
usage is optional and credentials are environment-only.

## Persistence

Existing JobAnalysis is extended with grade, prompt version, fit score,
structured result, and usage metadata. Every assessment is historical; a new
grade never overwrites an earlier result. Usage rows or fields record model,
purpose, token counts, and optional latency. A failed assessment leaves the
canonical job, UserJob, and deterministic match committed and can be retried.

## Security

URL imports allow only HTTP(S), reject local/private/link-local/metadata and
reserved addresses after DNS resolution, revalidate redirects, limit redirects
and response size, enforce timeouts, and accept only HTML/JSON content types.
No authentication bypass or JavaScript execution is performed.

## API additions

- `POST /api/v1/jobs/import` performs extraction, normalization, persistence,
  matching, and optional assessment in one product-oriented workflow.
- `GET /api/v1/jobs/{job_id}/review` returns canonical vacancy, provenance,
  latest match, and latest assessment for the authenticated user.
- Existing analysis endpoints remain available for retries and history.
- Authenticated job listing exposes review summaries and score sorting.

## Files

New modules will live under `app/modules/imports`, `app/modules/assessment`,
and `app/integrations/llm` prompt/provider extensions. Existing jobs,
matching, analysis, configuration, migrations, tests, README, and architecture
documentation will be modified only where needed to preserve the v0.5 API and
business boundaries.

## Migration strategy

Do not edit migrations 0001-0007. Add new migration(s) for assessment grades,
usage metadata, and any explicit contact/application fields. A clean temporary
PostgreSQL database must upgrade from 0001 to the new head.
