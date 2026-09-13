# Architecture

`JobPosting` is a global vacancy record. User-specific state is isolated in
`UserJob`, `JobMatch`, and `JobAnalysis`; no request accepts a trusted user id.
JWT bearer authentication resolves the current user before private queries.

```text
Client -> JWT -> Current User
                    |- CandidateProfile
                    |- UserJob -> JobPosting
                    |- JobMatch (profile snapshot)
                    `- JobAnalysis -> JobMatch
```

Matches are immutable history records. Editing a profile affects only future
matches; the stored snapshot explains an earlier score. Analyses create a fresh
match and link to it, so their deterministic context is preserved.

## Vacancy normalization

External schemas stop at the extraction boundary. A source-specific extractor
produces `RawJobData`; the pure `JobNormalizer` produces canonical job data,
warnings, and a normalization version. Persistence stores the canonical global
`JobPosting`, its `JobSourceRecord` provenance, and a user's `UserJob` in one
transaction. Unknown or ambiguous values remain null; raw source information
and warnings preserve why no value was inferred.

`JobPosting.application_url` means the canonical employer application
destination. `JobSourceRecord.source_url` means the source page where JobRadar
found the vacancy. They may have the same value for a manual entry, but they
remain distinct concepts. Legacy API aliases (`url`, `location`, `remote`,
`currency`) are converted at extraction time and are not persisted as duplicate
canonical columns.
