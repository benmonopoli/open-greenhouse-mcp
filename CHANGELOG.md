# Changelog

## 0.4.0

### Added
- **`screen_candidate` tool** — Assembles a complete, analysis-ready screening package for a candidate in a single call. Returns decoded candidate profile, plain-text job description, screening answers, full resume text (PDF/DOCX extracted), detected location, and application history. Replaces 4-5 separate tool calls.
- **`fetch_new_applications` tool** — Fetches applications created after a date, grouped by job with candidate names and screening answers. The "what's new since yesterday" query for daily recruiter workflows. Supports `job_id` filtering.
- **`search_pipeline_candidates` tool** — Search within job pipelines for candidates matching structured criteria (title, company, education, experience years, tags). Resurface past applicants or find internal candidates for similar roles.
- **`scan_all_candidates` tool** — Database-wide candidate search using structured fields with optional date bounds. For proactive sourcing across the entire ATS.
- **`batch_read_resumes` tool** — Batch-fetch and extract resume text for multiple candidates. Use after narrowing with structured search to check for skills, technologies, or other details only found in resumes.
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
