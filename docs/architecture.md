# Architecture

`JobPosting` is a global vacancy record. User-specific state is isolated in
`UserJob`, `JobMatch`, and `JobAnalysis`; no request accepts a trusted user id.
JWT bearer authentication resolves the current user before private queries.

```text
Client -> JWT -> Current User
                    |- CandidateProfile
                    |    |- CandidateProject
                    |    `- CandidateEvidence
                    |- UserJob -> JobPosting
                    |- JobMatch (profile snapshot)
                    `- JobAnalysis -> JobMatch
```

Matches are immutable history records. Editing a profile affects only future
matches; the stored snapshot explains an earlier score. Analyses create a fresh
match and link to it, so their deterministic context is preserved.

## Rich profile grounding

CandidateProfile retains legacy skill lists for compatibility and adds
structured skills, explicit controlled capabilities, experience facts,
languages, and target/work preferences. `CandidateProject` and
`CandidateEvidence` are separate user-owned records with stable IDs. Evidence
is created only from user-provided data; AI never creates it.

The matcher consumes explicit skills and capabilities, then emits compact
requirement explanations with the exact matching fact and any linked evidence
IDs. Numeric experience requirements are reported as `matched`,
`unverified_duration`, or `missing`; unknown duration never satisfies a
numeric requirement.

Its deterministic score is vacancy-oriented: title (25), required requirements
(35), preferred requirements (15), positive-only stack relevance (10), and
location/work-mode compatibility (15). Required coverage includes structured
numeric experience when present. Preferred gaps are not blockers, and extra
unmatched stack technologies cannot reduce an already earned stack bonus.

Grade 2/3 receive candidate facts separately from recommendations. Their
grounded recommendation references are filtered against evidence owned by the
authenticated user before persistence. Grade 1 remains extraction only.

`CandidateContextBuilder` bounds Grade 2/3 model input. It selects only facts
relevant to canonical required/preferred/stack skills and capabilities, then
adds compact projects and evidence using deterministic overlap ranking. Grade
2 is limited to 3 projects, 8 evidence items, and 8,000 characters; Grade 3 is
limited to 5 projects, 15 evidence items, and 14,000 characters. An evidence
reference must be both user-owned and present in that selected context.

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
deterministic `JobMatch`. Grade 0 stops there. Grade 1 adds factual AI
extraction/enrichment only; it does not create a candidate assessment. Grades
2–3 add a validated historical assessment without replacing the deterministic
score.

For Grade 1+, the import service invokes AI extraction/enrichment for a
meaningful vacancy description. Structured title/company/location data remain
authoritative, while enrichment extracts semantics embedded in the description.
`AIExtraction` preserves validated factual output, model, prompt version, and
per-call usage separately from `JobAnalysis`. It then merges only supported
facts into `RawJobData` and runs the existing pure normalizer. Assessment
consumes only the canonical job, profile, and deterministic match; its prompt
treats the deterministic result as an auxiliary signal, never as a blocker.

`required_skills` and `preferred_skills` contain technologies/tools. Broader
non-skill conditions are stored separately as hard/preferred requirements in
source extraction metadata. The review response combines both groups so a
preferred technology such as AWS remains visible without duplicated storage.
`stack_skills` captures explicitly mentioned technology stacks without turning
every stack entry into a hard requirement. Work availability is stored through
remote/onsite/hybrid flags in addition to the canonical display `work_mode`.

Candidate capabilities are intentionally bounded by the database-backed
CandidateProfile. Safe controlled aliases and the PostgreSQL → relational
database capability relation help compare equivalent wording, but absent REST,
external API integration, LLM, chatbot, or experience evidence remains an
unknown/gap until the user adds truthful profile data.

Development measurement only: one synthetic real Grade 1 import used 1,223
input / 455 output tokens for extraction and 1,361 input / 1,229 output tokens
for assessment (4,268 tracked total). This is not a production cost estimate.
Per-call latency is not persisted yet, and extraction plus assessment execute
sequentially; performance/batch processing is intentionally deferred.

Assessment failures are warnings: the job and match remain available. URL
fetching is constrained public HTTP with DNS/IP SSRF checks, redirect
revalidation, timeouts, content-type allowlisting, and response-size limits.
No browser, JavaScript execution, crawling, or authenticated scraping is used.
