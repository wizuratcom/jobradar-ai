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

## Smart import and assessment

User-supplied text, JSON, or a public URL enters a source-specific extractor
and becomes `RawJobData`. The normalizer produces canonical data before one
workflow creates `JobPosting`, `JobSourceRecord`, `UserJob`, and a
deterministic `JobMatch`. Grade 0 stops there. Grades 1–3 add a validated,
historical assessment without replacing the deterministic score.

For Grade 1+, the import service invokes AI extraction only when deterministic
extraction leaves important facts unstructured. `AIExtraction` preserves the
validated factual output, model, prompt version, and per-call usage separately
from `JobAnalysis`. It then merges only supported facts into `RawJobData` and
runs the existing pure normalizer. Assessment consumes only the canonical job,
profile, and deterministic match.

`required_skills` and `preferred_skills` contain technologies/tools. Broader
non-skill conditions are stored separately as hard/preferred requirements in
source extraction metadata. The review response combines both groups so a
preferred technology such as AWS remains visible without duplicated storage.

Development measurement only: one synthetic real Grade 1 import used 1,223
input / 455 output tokens for extraction and 1,361 input / 1,229 output tokens
for assessment (4,268 tracked total). This is not a production cost estimate.
Per-call latency is not persisted yet, and extraction plus assessment execute
sequentially; performance/batch processing is intentionally deferred.

Assessment failures are warnings: the job and match remain available. URL
fetching is constrained public HTTP with DNS/IP SSRF checks, redirect
revalidation, timeouts, content-type allowlisting, and response-size limits.
No browser, JavaScript execution, crawling, or authenticated scraping is used.
