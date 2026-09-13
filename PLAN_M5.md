# Milestone 5: canonical job schema and normalization

## Current state

`JobPosting` currently stores `company`, `title`, `description`, `url`,
`location`, `remote`, `employment_type`, float salary bounds, `currency`, and
`required_skills`. `JobCreate` is simultaneously the manual API contract and
the service input. Matching reads title, required skills, remote, and location;
the optional LLM receives the same ORM record. There is no source provenance.

## Proposed boundaries

`ManualJobCreate` stays the public request. `ManualJobExtractor` converts it to
`RawJobData`; `JobNormalizer` converts raw fields into pure
`CanonicalJobData` plus warnings and a version. Persistence stores canonical
data in global `JobPosting`, raw/provenance data in `JobSourceRecord`, and the
existing current user's `UserJob` association in one transaction.

External schemas end at extraction. Neither matching nor LLM code sees source
names, payloads, external identifiers, or raw salary text.

## Canonical data

Keep required title/company/description and introduce `location_text`,
`work_mode` (`remote`, `hybrid`, `onsite`, `unknown`), Decimal salary bounds,
`salary_currency`, `salary_period`, `salary_gross`, `required_skills`,
`preferred_skills`, optional experience years, and timestamps. Legacy API
fields (`location`, `remote`, `currency`) are accepted as compatibility input
and translated by the manual extractor; responses expose canonical fields.

## Provenance

`JobSourceRecord` stores source name, optional external ID/URL, raw payload or
raw text, extracted representation, warnings, normalization version, optional
source timestamps, and its canonical job FK. A partial unique index protects
`(source_name, external_id)` only when an external ID exists.

## Migration

Create `0005` after `0004`; add canonical columns, migrate legacy values
without guessing (`remote=true` => `remote`; false => `unknown`), copy location
and currency into canonical columns, retain old values only long enough for a
safe data migration, then remove replaced legacy columns. Use NUMERIC for money.
Create `job_source_records`. Released migrations remain untouched.

## Compatibility and tests

Existing manual payloads continue to work through `ManualJobExtractor`.
Matching changes only to use canonical work mode/location and required skills;
preferred skills are not treated as requirements. LLM remains unchanged because
it consumes the canonical ORM model. Add pure normalization tests, source
provenance/manual-flow tests, and keep auth, fake LLM, and disabled behavior.
