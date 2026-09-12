# JobRadar AI

JobRadar AI is a portfolio-grade Python backend project. This first milestone
is a fully local core: it accepts job postings through a REST API, saves them
to SQLite, loads a public example candidate profile from YAML, and produces an
explainable deterministic match score. No API keys, Docker, external services,
or cloud accounts are needed.

## Roadmap

- [x] FastAPI application
- [x] SQLite persistence
- [x] Async SQLAlchemy
- [x] Candidate profile configuration
- [x] Deterministic job matching
- [x] Automated tests
- [ ] PostgreSQL
- [ ] Alembic migrations
- [ ] Docker Compose
- [ ] LLM-assisted job analysis
- [ ] Telegram notifications
- [ ] Automated job-source adapters
- [ ] Prometheus metrics
- [ ] Production deployment

## Running locally

Start from a clean clone with Python 3.12 installed:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger UI is available at `http://127.0.0.1:8000/docs`. The health check is
available at `http://127.0.0.1:8000/health`.

The default SQLite file is `data/jobradar.db`. It and its tables are created
automatically when the application starts. You can use a different local file
by changing `DATABASE_URL` in `.env`.

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

## Project map

- `app/main.py` wires the FastAPI app and routes.
- `app/core/database.py` owns async SQLite setup and sessions.
- `app/modules/jobs/` validates, normalizes, persists, and serves vacancies.
- `app/modules/candidate/service.py` reads the YAML candidate profile.
- `app/modules/matching/service.py` contains all scoring rules.
