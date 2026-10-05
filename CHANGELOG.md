# Changelog

## 0.5.0

Greenhouse retired Harvest v1/v2 on 31 Aug 2026. This release moves every Harvest tool to **Harvest v3**. It includes the 0.4.0 features below, which were never published to PyPI.

### Breaking
- **Authentication is OAuth 2.0 (client credentials).** Replace `GREENHOUSE_API_KEY` with `GREENHOUSE_CLIENT_ID` and `GREENHOUSE_CLIENT_SECRET` from a Harvest V3 (OAuth) credential. Starting with only the old key set fails with a message explaining the migration.
- **Cursor pagination.** List tools take `cursor` (the `next_cursor` from the previous response) instead of `page`.
- `GREENHOUSE_ON_BEHALF_OF` is replaced by `GREENHOUSE_USER_ID` (the old name still works as an alias). Writes use a token minted for that user, so Greenhouse attributes them correctly; reads use the credential's service user, because v3 list endpoints need Site Admin authorization.
- Ingestion and Job Board submission use their own keys: `GREENHOUSE_INGESTION_API_KEY`, `GREENHOUSE_BOARD_API_KEY`.
- `reject_application` and `bulk_reject` require `rejection_reason_id` (v3 requires it).
- `update_job` can no longer set job status (v3 derives it from openings) — use the opening tools.
- `change_user_permission_level` can only demote a user to Basic (v3 has no promote endpoint).
- `anonymize_candidate` requires `fields`.
- `add_attachment` attaches to an application (v3 has no candidate-level attachments); it uses the candidate's most recently active application if none is given.
- `create_interview` records the interview without sending a calendar invite; v3 requires an external event id and a placeholder is generated if none is given.

### Changed
- v3 no longer embeds child records, so tools resolve them with batched lookups (50 ids per request): `get_candidate` includes applications (with job names), attachments, educations and employments; applications carry `job_name`; stages, interviews, scorecards, approvals and the hiring team come back with names filled in. If a lookup fails the tool still returns its data with a `warnings` list.
- Date filters accept `YYYY-MM-DD` and send midnight UTC (v3 rejects date-only values).
- Custom field updates (`update_candidate`, `update_job`, `update_job_opening`, `bulk_update_job_openings`) merge with the record's current values, because v3 replaces the whole custom field list on PATCH. If the current values can't be read, nothing is written.
- `hire_application` accepts a date or date-time for `start_date` and sends a date-time.
- `pipeline_summary` reports real `days_in_stage`; `pipeline_metrics` reports a true funnel (`total_reached`, `conversion_to_next_pct`, `avg_days_in_stage`) from stage history.
- `bulk_advance` and `bulk_tag` skip records that don't apply and report them; `bulk_tag` creates a missing tag.
- `get_activity_feed` is built from v3 notes and keeps the `notes`/`emails`/`activities` shape.
- 403 errors explain v3 scopes; tokens are cached and refreshed automatically.

### Added
- `get_bulk_request_status`, `bulk_create_job_openings`, `bulk_update_job_openings`, `bulk_delete_job_openings`, `add_job_post_location`, `remove_job_post_location`.

### Fixed
- With `GREENHOUSE_USER_ID` set, tool calls failed with "Event loop is closed" because the startup permission check left the HTTP client bound to a closed event loop.
- Pinned `mcp<2`: mcp 2.x renamed `FastMCP`, so fresh installs failed to start.

## 0.4.0

### Added
- **`screen_candidate` tool** — Assembles a complete, analysis-ready screening package for a candidate in a single call. Returns decoded candidate profile, plain-text job description, screening answers, full resume text (PDF/DOCX extracted), detected location, and application history. Replaces 4-5 separate tool calls.
- **`fetch_new_applications` tool** — Fetches applications created after a date, grouped by job with candidate names and screening answers. The "what's new since yesterday" query for daily recruiter workflows. Supports `job_id` filtering.
- **`search_pipeline_candidates` tool** — Search within job pipelines for candidates matching structured criteria (title, company, education, experience years, tags). Resurface past applicants or find internal candidates for similar roles.
- **`scan_all_candidates` tool** — Database-wide candidate search using structured fields with optional date bounds. For proactive sourcing across the entire ATS.
- **`batch_read_resumes` tool** — Batch-fetch and extract resume text for multiple candidates. Use after narrowing with structured search to check for skills, technologies, or other details only found in resumes.
- **`scan_pipeline_resumes` tool** — The primary sourcing tool: searches resume text within job pipelines for specific skills and keywords. Supports boolean search — `required_keywords` (AND gate), `keywords` (OR ranking), and `exclude_keywords` (NOT filter). Returns matched candidates with context snippets around each keyword hit. Handles the reality that ~90% of candidate data lives in resumes, not structured fields.
- **Resume text extraction** — PDF and DOCX resumes are extracted to plain text server-side using pdfplumber and python-docx.
- **Location detection** — 5-step cascade detects candidate location from screening answers, application fields, candidate addresses, resume text patterns, and phone dial codes (150+ countries).

### Dependencies
- Added `pdfplumber>=0.11.0` for PDF text extraction
- Added `python-docx>=1.1.0` for DOCX text extraction

## 0.3.0

### Added
- **Tool profiles** (`GREENHOUSE_TOOL_PROFILE`): full (175 tools), recruiter (121 tools), read-only (97 tools)
  - Recruiter profile includes pipeline management, bulk operations, and candidate interaction
  - Recruiter profile excludes admin operations (job creation, user management, custom fields, candidate deletion)
  - `GREENHOUSE_READ_ONLY=true` continues to work as shorthand for read-only profile
- **Structured JSON logging** to stderr or file
  - `GREENHOUSE_LOG_LEVEL` (debug, info, warning, error) controls verbosity
  - `GREENHOUSE_LOG_FILE` for file output instead of stderr
  - Every API call logged with method, URL, status, and latency
  - Auto-escalation: info for 2xx, warning for 4xx, error for 5xx

## 0.2.1

### Improved
- PyPI metadata: added keywords, classifiers, and project URLs for better discoverability

## 0.2.0

### Added
- **13 composite tools** for recruiter workflows:
  - `pipeline_summary` — full pipeline view with candidates grouped by stage
  - `candidates_needing_action` — find stale applications and missing scorecards
  - `stale_applications` — applications with no activity for N days
  - `pipeline_metrics` — conversion rates, hire/rejection rates per stage
  - `source_effectiveness` — which candidate sources produce the best results
  - `time_to_hire` — average, median, min, max days from application to hire
  - `bulk_reject`, `bulk_tag`, `bulk_advance` — batch operations with rate-limit handling
  - `search_candidates_by_name`, `search_candidates_by_email` — candidate lookup
  - `read_candidate_resume`, `download_attachment` — attachment reading
- `paginate="all"` option on list endpoints to auto-fetch every page
- `force_refresh` on cached reference data (departments, offices, rejection reasons)
- `harvest_get_one()` for clean single-resource responses without pagination wrapper
- `On-Behalf-Of` header on all write operations for audit trail
- Tool gating — board-token-only mode registers only Job Board tools
- Retry jitter on 429 rate limit responses
- Webhook forward failure logging
- Partial results with warnings on mid-flow API errors in composite tools
- Batch candidate name resolution (fixes numeric ID display)
- Cross-references between atomic and composite tools for better routing
- CODE_OF_CONDUCT.md, CONTRIBUTING.md, SECURITY.md
- GitHub issue templates for bugs and feature requests

## 0.1.0

### Added
- 148 Harvest API tools covering all endpoints
- 13 Job Board API tools
- 6 Ingestion API tools
- 8 webhook management tools
- Webhook receiver with HMAC verification and SQLite routing
- CI pipeline with pytest and ruff
- README with quick start and tool reference
