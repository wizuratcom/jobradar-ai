# Milestone 4 plan: users, authentication, and database-backed profiles

## Current assumptions to replace

- `CandidateProfile` is loaded once from `candidate.example.yaml` and cached for
  the whole process.
- `JobPosting` is global and the jobs API currently lists every row.
- `calculate_match` is pure Python and returns an in-memory `MatchResult`.
- `JobAnalysis` has a job foreign key but no user, profile, or match ownership.
- There is no authenticated identity or authorization boundary.

The pure matcher and optional LLM integration will remain unchanged as domain
components. Routing and services will supply the authenticated user's database
profile instead of the YAML profile.

## Proposed schema

```text
users
  id, email (unique), password_hash, is_active, created_at, updated_at

candidate_profiles
  id, user_id (unique FK), name, desired_titles JSONB, core_skills JSONB,
  secondary_skills JSONB, preferred_remote, preferred_locations JSONB,
  created_at, updated_at

job_postings                         # global vacancy catalogue; unchanged

user_jobs
  id, user_id FK, job_id FK, status, created_at, updated_at
  UNIQUE (user_id, job_id)

job_matches
  id, user_id FK, job_id FK, candidate_profile_id FK, score, recommendation,
  breakdown JSONB, matched_core_skills JSONB, matched_secondary_skills JSONB,
  missing_skills JSONB, candidate_profile_snapshot JSONB, created_at

job_analyses
  existing columns plus user_id FK and job_match_id FK
```

`JobPosting` stays global because one vacancy can be relevant to many users.
`UserJob`, `JobMatch`, and `JobAnalysis` hold each user's private relationship,
historical score, and application brief.

## Authentication and authorization

- Add a `users` module with Argon2 password hashing and JWT bearer tokens.
- `POST /api/v1/auth/register` normalizes email, hashes the password, and never
  returns its hash.
- `POST /api/v1/auth/login` verifies the password and issues a short-lived JWT.
- `get_current_user` validates the bearer token and loads an active user.
- Every private route receives identity exclusively through this dependency;
  clients never provide a trusted `user_id`.
- Private lookups filter by `user_id` in repository queries and return `404`
  when a requested resource is absent or belongs to another user.

## Candidate profile migration

The current Pydantic `CandidateProfile` fields are the source of truth:
`name`, desired titles, core and secondary skills, remote preference, and
preferred locations. The PostgreSQL model uses JSONB for the list fields.
`candidate.example.yaml` remains documentation and a test/seed-style example,
but runtime matching reads the authenticated user's profile from PostgreSQL.

`GET /api/v1/me/profile` returns only the current user's profile and
`PUT /api/v1/me/profile` creates or updates that one-to-one profile.

## Match and analysis history

`POST /jobs/{job_id}/match` first verifies that the job is associated with the
current user, loads the current database profile, calls the existing pure
matcher, and creates a new `JobMatch`. No historical match is overwritten.
The full profile is stored as a JSON snapshot so later profile edits do not
make an old score unexplained.

`POST /jobs/{job_id}/analyze` creates a fresh persisted match and passes it to
the existing LLM provider abstraction. A successful `JobAnalysis` is stored
with the authenticated user and that exact match. Failed/disabled provider
calls do not persist analysis data. This makes every analysis explainable even
after the candidate profile changes.

## Migration strategy

Create a new Alembic revision after `0003_add_job_analyses` that creates
`users`, `candidate_profiles`, `user_jobs`, and `job_matches`, and adds
`user_id` plus `job_match_id` to `job_analyses` with indexes and foreign keys.
The new analysis ownership columns are nullable for legacy v0.3 demo rows so
an upgrade does not fail on an existing local database; application code will
always populate them for new rows. Legacy analyses are not exposed through
user-scoped API queries. A future cleanup migration can make them non-null
after legacy rows are removed or assigned.

## Endpoints affected

- New public: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`.
- New protected: `GET /api/v1/me`, `GET/PUT /api/v1/me/profile`, `GET
  /api/v1/matches`, `GET /api/v1/matches/{match_id}`.
- Existing jobs, matching, and analyses routes become protected and scoped to
  the current user's `UserJob` association.
- `GET /health` remains public. Swagger remains available for local use.

## Files to add

- `app/core/security.py`
- `app/modules/users/{models,schemas,repository,service,router}.py`
- `app/modules/matches/{models,schemas,repository,service,router}.py`
- `app/modules/candidate/{models,repository,router}.py`
- an Alembic `0004` migration
- `docs/architecture.md`
- focused authentication and user-isolation tests

## Files to modify

- configuration, dependencies, and `app/main.py`
- candidate service/schemas
- job models/repository/service/router
- analysis models/repository/service/router/schemas
- Alembic metadata imports
- `.env.example`, `pyproject.toml`, CI configuration, README, and tests.

## Transaction boundaries

Manual job creation creates `JobPosting` and `UserJob` in the same database
transaction. A failed association rolls back the new posting. Match and
analysis persistence use their own explicit successful transactions; provider
errors occur before analysis persistence and leave no partial analysis record.
