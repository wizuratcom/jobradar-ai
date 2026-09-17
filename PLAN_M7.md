# Milestone 7 plan: Rich Candidate Profile & Evidence

## Current-state audit

### Candidate profile and API

`CandidateProfileRecord` is currently a one-to-one `candidate_profiles` row per
user. It stores `name`, `desired_titles`, `core_skills`, `secondary_skills`,
`preferred_remote`, and `preferred_locations`; list values are JSON/JSONB.
`GET` and `PUT /api/v1/me/profile` expose the same flat Pydantic model.

### Matching and snapshots

The pure matcher receives `CandidateProfile` and a canonical `JobPosting`. It
uses desired titles, core and secondary skill lists, remote/location
preferences, and the controlled skill/capability aliases added in v0.6.x.
`JobMatch` persists the score, breakdown, matched/missing lists, and a JSON
snapshot generated from the profile Pydantic model. Historical snapshots are
therefore already independent of later profile edits, but lack projects,
evidence, capabilities, languages, and experience facts.

### AI context

Grade 1 remains extraction/enrichment only. Grade 2/3 assessment prompts
receive the profile model, canonical job, and deterministic result. They
currently have anti-fabrication instructions but cannot cite stable candidate
evidence identifiers. AI output is persisted as `JobAnalysis` / assessment
history.

### Relevant migration history

`0004_add_users_and_user_data` created `candidate_profiles` and `job_matches`.
Migrations through `0010_add_vacancy_semantics` are released and must not be
edited. M7 will add a new linear migration.

## Proposed storage design

Use a pragmatic hybrid schema:

* Keep `candidate_profiles` as the one-to-one owner and retain legacy columns
  for backward-compatible reads and writes.
* Add validated JSONB profile fields for rich skills, capabilities, experience,
  languages, and additional search/work preferences. These are profile-sized,
  ordered data and do not need lookup tables.
* Add `candidate_projects` and `candidate_evidence` tables. Their stable IDs
  let recommendations explain which user-provided facts support a claim.
  Both rows are user-owned; evidence may optionally link to a project.
* Add canonical experience-requirement fields to `JobPosting` only where
  required to make deterministic experience matching source-independent. Raw
  source details remain in `JobSourceRecord`.

No migration fabricates skill level, years, projects, or evidence. Legacy
`core_skills` and `secondary_skills` remain usable and are also represented as
rich skills without invented metadata at service/read time.

## Rich domain schema

`CandidateProfile` will preserve all existing fields and add:

* `skills`: concrete technology entries (`name`, optional canonical name,
  optional user-supplied level, duration, last-used value, evidence IDs).
* `capabilities`: controlled backend capability entries with optional level and
  evidence IDs.
* `experience`: explicit text/context and optional confirmed duration; unknown
  duration stays null.
* `languages`: user-supplied language and level pairs.
* richer preferences: preferred work modes, target seniority, salary floor and
  currency, employment types, and relocation willingness.

Projects contain real title, description, optional role/dates, technologies,
capabilities, responsibilities, and achievements. Evidence contains explicit
user-provided facts only: type, title, description, technologies,
capabilities, optional project/context/dates. The supported evidence types are
project, work task, education, manual statement, and certification.

## Authentication and authorization

All profile, project, evidence, completeness, and grounding operations derive
the user from `get_current_user`. Request schemas never accept `user_id`.
Repositories scope every lookup by `user_id`; cross-user private lookups return
404. Profile skill/capability evidence references are validated against
evidence owned by the current user.

## API plan

Keep `GET`/`PUT /api/v1/me/profile` compatible while accepting/returning the
rich profile fields. Add:

* `GET /api/v1/me/profile/completeness`
* `GET/POST /api/v1/me/projects`
* `PUT/DELETE /api/v1/me/projects/{project_id}`
* `GET/POST /api/v1/me/evidence`
* `PUT/DELETE /api/v1/me/evidence/{evidence_id}`

The profile endpoint remains the source for preferences and inline
skills/capabilities; projects and evidence have dedicated CRUD resources.

## Matching and experience behavior

The matcher remains pure Python and consumes the canonical vacancy plus the
rich profile only. Concrete skills and explicit capabilities are normalized by
the existing small controlled mapping. Evidence does not invent capabilities;
it supplies explanation IDs only when linked by the user.

Experience requirements produce transparent states:

* `matched`: a confirmed relevant duration meets the explicit minimum;
* `unverified_duration`: relevant backend/project experience is present but
  exact duration is unknown;
* `missing`: no relevant experience fact is present, or the confirmed duration
  is below the stated minimum.

The match response gains compact requirement explanations, including the
candidate skill/capability and valid evidence IDs that justified a match. The
immutable profile snapshot will include the richer matching-relevant fields so
old matches stay explainable after edits.

## Grade 2/3 claim grounding

Assessment prompts will receive a clearly separated candidate-facts section
containing skills, capabilities, projects, and evidence. The prompt will allow
recommendations only when grounded in those supplied facts. Structured Grade
2/3 output gains optional evidence references for CV emphasis, CV bullets,
recruiter claims, and interview examples. Before persistence, references are
filtered/validated against the authenticated user's available evidence IDs;
nonexistent or another user's IDs cannot be retained. Grade 1 semantics and
its no-assessment behavior do not change.

## Completeness report

Implement a deterministic input-completeness score, not a candidate-quality
score. It reports missing and weak sections (for example target preferences,
experience duration, languages, or evidence for listed capabilities). It does
not call AI or infer facts from absence.

## Transactions

Each profile upsert validates evidence references before changing the profile.
Project/evidence CRUD commits one local database transaction per operation.
Assessment grounding validation runs before its persistence. Existing job and
match transaction boundaries remain unchanged.

## Files to add

* `app/modules/candidate/projects_models.py` (or equivalent project/evidence
  ORM models)
* `app/modules/candidate/projects_repository.py`
* `app/modules/candidate/projects_router.py`
* `app/modules/candidate/completeness.py`
* `alembic/versions/0011_add_rich_candidate_profile.py`
* focused rich-profile, matching, grounding, and API tests

The final paths may be consolidated into the existing candidate module when
that is clearer than artificial submodules.

## Files to modify

* candidate models, schemas, repository, service, and router;
* matching schemas/service and persistent match models/read schemas;
* canonical job schemas/models/normalization only for experience fields;
* assessment schemas/service/prompt and persistence serialization for grounded
  references;
* application model registration/router wiring;
* Alembic environment imports if needed;
* README and architecture documentation with synthetic examples.

## Backward compatibility and verification

Legacy profile payloads and existing profile rows remain valid. New fields have
safe empty/null defaults, and snapshots created before M7 remain readable via
Pydantic defaults. A fresh database must migrate from `0001` through the M7
head. Tests will cover CRUD/isolation, evidence ownership, rich matching,
experience states, historical snapshots, Grade 1 invariance, grounded Grade
2/3 FakeLLM output, completeness, and no-external-network operation.
