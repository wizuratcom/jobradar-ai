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
- [ ] LLM-assisted job analysis
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

## Candidate profile

`candidate.example.yaml` is deliberately fictional. Copy it to a separate
local YAML file, adjust it, and set `CANDIDATE_PROFILE_PATH` in `.env` if you
want to test another profile. Do not commit private data.

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
