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
