# JobRadar AI

JobRadar AI is a portfolio-grade Python backend project. It accepts job
postings through a REST API, saves them to PostgreSQL, loads a public example
candidate profile from YAML, and produces an explainable deterministic match
score. No cloud account or API key is required.

## Roadmap

- [x] FastAPI application
- [x] PostgreSQL persistence
- [x] Async SQLAlchemy
- [x] Candidate profile configuration
- [x] Deterministic job matching
- [x] Automated tests
- [x] Alembic migrations
- [x] Docker Compose
- [x] LLM-assisted job analysis
- [x] Canonical vacancy normalization and provenance
- [ ] Telegram notifications
- [ ] Automated job-source adapters
- [ ] Prometheus metrics
- [ ] Production deployment

## Running with Docker

The supported development runtime is Docker Compose with PostgreSQL. From a
clean clone:

```bash
cp .env.example .env
docker compose up --build
```

The API container applies `alembic upgrade head` before starting Uvicorn. If a
migration fails, the API container exits and exposes the failure in its logs.

Swagger UI is available at `http://localhost:8000/docs`. The health check is
`http://localhost:8000/health`.

PostgreSQL data is stored in the named `postgres_data` Docker volume, so it
survives normal container restarts and `docker compose down`. To permanently
reset all local data, stop the stack and delete that volume:

```bash
docker compose down -v
```

## Running without Docker

This is useful when you already have a local PostgreSQL server. Create `.env`
from the example, change its host from `db` to `localhost` if necessary, and
then run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger UI is available at `http://127.0.0.1:8000/docs`. The health check is
available at `http://127.0.0.1:8000/health`.

Before launching the app, apply the database schema:

```bash
alembic upgrade head
```

`DATABASE_URL` supplies the async PostgreSQL connection, for example:
`postgresql+asyncpg://jobradar:jobradar@db:5432/jobradar` in Docker Compose.

## Alembic migrations

Alembic is the only production schema-management mechanism. Useful commands:

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"
```

For the Docker stack, invoke Alembic inside the API container if needed:

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade -1
docker compose exec api alembic revision --autogenerate -m "description"
```

## API overview

- `GET /health` — local service health check.
- `POST /api/v1/jobs` — create a job posting.
- `GET /api/v1/jobs?limit=20&offset=0` — list stored jobs with pagination.
- `GET /api/v1/jobs/{job_id}` — retrieve one job.
- `POST /api/v1/jobs/{job_id}/match` — calculate its candidate match.
- `GET /api/v1/candidate` — view the loaded example candidate profile.

### Add a vacancy through Swagger

1. Open `/docs`, expand `POST /api/v1/jobs`, select **Try it out**, and use:

```json
{
  "company": "Acme",
  "title": "Senior Python Backend Developer",
  "description": "Build and maintain reliable backend APIs.",
  "url": "https://example.com/jobs/python-backend",
  "location": "Remote",
  "remote": true,
  "employment_type": "full-time",
  "salary_min": 3500,
  "salary_max": 5000,
  "currency": "EUR",
  "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"]
}
```

2. Select **Execute** and copy the returned `id`.
3. Expand `POST /api/v1/jobs/{job_id}/match`, enter that id, and select
   **Execute** to see the score and its explanation.

## Matching rules

Matching is deterministic: it calls no AI service and uses no hidden model.
The constants live at the top of `app/modules/matching/service.py`.

| Criterion | Maximum | Rule |
| --- | ---: | --- |
| Title relevance | 25 | A desired title is contained in the vacancy title. |
| Core skills | 40 | Proportional to candidate core skills listed by the vacancy. |
| Secondary skills | 20 | Proportional to candidate secondary skills listed by the vacancy. |
| Remote/location | 15 | Remote fits the preference, or the location is preferred. |

Recommendations are `strong_apply` (80–100), `apply` (60–79), `maybe`
(40–59), and `skip` (0–39).

## Authentication

Create an account with `POST /api/v1/auth/register`, then obtain a bearer token
through `POST /api/v1/auth/login`. In Swagger (`/docs`), click **Authorize**
and enter `Bearer <access_token>`. Private jobs, profiles, matches, and
analyses are scoped to the token's user.

```json
{"email":"candidate@example.com","password":"password123"}
```

Manage the authenticated profile with `PUT /api/v1/me/profile`. The
`candidate.example.yaml` file is now documentation/example input only; runtime
matching reads the database-backed profile.

## Vacancy normalization

Manual vacancy creation uses the same deterministic pipeline planned for future
sources: `ManualJobCreate -> RawJobData -> JobNormalizer -> JobPosting +
JobSourceRecord`. `JobPosting` is canonical; `JobSourceRecord` stores the
manual/source provenance. `application_url` is the source-independent employer
application destination. `JobSourceRecord.source_url` is the page where a
source discovered the vacancy; future sources may create several provenance
records for one canonical job. Legacy request fields `url`, `location`,
`remote`, and `currency` are accepted only as compatibility aliases and are
converted to `application_url`, `location_text`, `work_mode`, and
`salary_currency` respectively. Supported work modes are `remote`, `hybrid`,
`onsite`, and `unknown`. Ambiguous salary text is preserved as raw data with a
warning rather than guessed. `candidate.example.yaml` is demo/reference data,
not the runtime profile.

## LLM-assisted analysis

Deterministic matching remains the source of truth for the score and its
recommendation. Optional LLM analysis adds a structured application brief:
strengths, gaps, factual CV emphasis, a recruiter message, and interview
preparation topics. It never replaces or recalculates the deterministic score.

```mermaid
flowchart TD
    J[Job posting] --> M[Deterministic matcher]
    C[Candidate profile] --> M
    M --> S[Authoritative score]
    J --> A[Optional LLM analysis]
    C --> A
    S --> A
    A --> B[Persisted application brief]
```

LLM support is disabled by default, so no API key is needed to start the
project. When disabled, all existing endpoints continue working and
`POST /api/v1/jobs/{job_id}/analyze` returns a clear `503` response without
changing job or matching data.

### Fake provider for local development

Set these values in `.env`, then rebuild the API container:

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=fake
```

```bash
docker compose up --build -d
```

Create a job in Swagger, run `/match` if you want to inspect the authoritative
score, then call `POST /api/v1/jobs/{job_id}/analyze`. The fake provider uses
no network or credentials and persists a structured history record. Retrieve
history through `GET /api/v1/analyses` or `GET /api/v1/analyses/{analysis_id}`.

### Future OpenAI-compatible provider

Use a provider only when you have an appropriate endpoint and secret outside
version control:

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=replace-with-your-secret
LLM_MODEL=provider-model-name
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

The adapter retries only timeouts, network failures, HTTP `429`, and HTTP
`5xx`, with bounded exponential backoff. Other HTTP failures, malformed JSON,
empty content, or invalid structured output return a controlled API error and
are never persisted. API keys and raw provider responses are neither logged
nor stored.

The prompt explicitly forbids fabricated candidate experience, employers,
years, achievements, metrics, certifications, or unlisted technologies. A job
requirement absent from the profile is reported as a gap instead.

## Candidate profile

`candidate.example.yaml` is deliberately fictional reference data. Runtime
matching uses the authenticated user's PostgreSQL-backed profile managed via
`PUT /api/v1/me/profile`. Do not commit private data.

## Quality checks

```bash
pytest
ruff check .
```

CI runs these checks against a PostgreSQL GitHub Actions service container on
every push and pull request to `main`.

## Project map

- `app/main.py` wires the FastAPI app and routes.
- `app/core/database.py` owns the async PostgreSQL engine and session lifecycle.
- `app/modules/jobs/` validates, normalizes, persists, and serves vacancies.
- `app/modules/candidate/service.py` reads the YAML candidate profile.
- `app/modules/matching/service.py` contains all scoring rules.
- `app/integrations/llm/` isolates optional provider adapters and prompt rules.
- `app/modules/analysis/` validates and persists successful analysis history.
