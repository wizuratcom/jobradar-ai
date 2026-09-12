# JobRadar AI — Milestone 2 migration plan

## Goal and compatibility

Move normal runtime persistence from SQLite to PostgreSQL through async
SQLAlchemy and `asyncpg`. The REST API, candidate profile, normalization, and
deterministic matching rules will remain unchanged.

## Architecture decision

- `DATABASE_URL` is the single runtime database setting. Docker supplies a
  PostgreSQL URL from `.env`; it points at the Compose `db` service.
- Alembic owns the production schema. Application startup validates the
  candidate profile but never calls `Base.metadata.create_all()`.
- In Docker development, the API command runs `alembic upgrade head` before
  Uvicorn. A migration failure stops the API container, rather than being
  ignored.
- Unit/domain tests remain independent of PostgreSQL. The API persistence test
  defaults to a temporary local SQLite database. CI also runs that test suite
  against a PostgreSQL service container using `TEST_DATABASE_URL`.

## Existing files to modify

- `app/core/config.py` — PostgreSQL-oriented environment configuration.
- `app/core/database.py` — engine/session lifecycle, test-only schema helper,
  and disposal; remove production `create_all()` initialization.
- `app/main.py` — clean startup/shutdown without schema creation.
- `tests/conftest.py` and `tests/test_api.py` — configurable test database and
  explicit test-schema setup.
- `pyproject.toml` — add `asyncpg` and Alembic.
- `.env.example` and `.gitignore` — safe Docker configuration and ignored
  local state.
- `.github/workflows/ci.yml` — keep Ruff/pytest and run pytest against a
  PostgreSQL service container.
- `README.md` — Docker, migrations, persistence, reset, and quality commands.

## New files to create

- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/0001_initial_job_postings.py`
- `alembic/versions/0002_make_created_at_not_null.py`
- `Dockerfile`
- `compose.yaml`
- `.dockerignore`

## Verification sequence

1. Install the added Python packages, then run Ruff and the full tests.
2. Build and start Compose.
3. Confirm Alembic is at the initial revision, health and Swagger respond,
   then create and match a vacancy.
4. Restart the Compose services and confirm that the vacancy remains in the
   named PostgreSQL volume.
