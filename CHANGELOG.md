# Changelog

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
