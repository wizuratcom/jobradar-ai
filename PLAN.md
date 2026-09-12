# JobRadar AI — Milestone 1 plan

## Scope

This milestone is a local FastAPI core only. It uses SQLite, async SQLAlchemy,
a local candidate YAML file, and deterministic Python matching. It deliberately
does not include Docker, PostgreSQL, Telegram, scraping, or external AI APIs.

## Proposed file tree

```text
.
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   └── modules/
│       ├── candidate/
│       │   ├── schemas.py
│       │   └── service.py
│       ├── jobs/
│       │   ├── models.py
│       │   ├── repository.py
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       └── matching/
│           ├── schemas.py
│           └── service.py
├── tests/
├── candidate.example.yaml
├── .env.example
├── pyproject.toml
├── README.md
└── PLAN.md
```

## How a request travels through the application

1. FastAPI receives and validates the HTTP request against a Pydantic schema.
2. The jobs router calls the jobs service.
3. The service normalizes strings and skill names, then asks the repository to
   save or read the SQLAlchemy job model.
4. The repository uses an async SQLAlchemy session connected to SQLite.
5. For a match request, the matching service loads the configured candidate
   profile, compares it with the normalized job, and returns an explainable
   score and breakdown.
6. FastAPI serializes the response schema and exposes it in Swagger UI.

## SQLite database

The application creates the database tables automatically during FastAPI
startup. By default, the SQLite file is `./data/jobradar.db`, relative to the
directory in which Uvicorn is started. The `DATABASE_URL` environment variable
can override this for local tests or another local file.

## Local start commands

From a clean clone, using Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI and
`http://127.0.0.1:8000/health` for the health check.

## Implementation and verification sequence

1. Create configuration, async SQLite lifecycle, modules, schemas, and routes.
2. Add deterministic scoring with explicit constants.
3. Add pytest coverage for the required API and matching behavior.
4. Install dependencies when possible, run Ruff and pytest, then start the app
   and request `/health`.
