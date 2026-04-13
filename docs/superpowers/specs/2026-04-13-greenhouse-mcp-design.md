# greenhouse-mcp Design Spec

## Overview

A comprehensive, open-source MCP server covering the full Greenhouse API surface. Serves everyone in a recruiting org: recruiters, hiring managers, recruiting ops/HR, data analysts, sourcers, and admin/IT. Includes a webhook receiver companion for event-driven workflows.

- **Package**: `greenhouse-mcp` (pip-installable via PyPI)
- **License**: MIT
- **Author**: Ben Monopoli (ben.monopoli@ahrefs.com)
- **Stack**: Python, FastMCP, httpx, FastAPI (receiver), SQLite (webhook rules)

---

## Architecture

### Package Structure

```
greenhouse-mcp/
  pyproject.toml          — package config, two CLI entry points
  README.md
  LICENSE                 — MIT

  src/greenhouse_mcp/
    __init__.py
    __main__.py           — python -m greenhouse_mcp
    server.py             — FastMCP instance, tool registration, CLI
    client.py             — async HTTP client, auth, rate limiting, cache

    harvest/
      candidates.py       — list, get, create, update, delete, merge, anonymize,
                             add prospect, add/remove education, add/remove employment,
                             add attachment, add note, add email note (15 tools)
      applications.py     — list, get, create, update, delete, advance,
                             move (same job), move (different job), reject,
                             unreject, update rejection reason, hire,
                             convert prospect, add attachment (14 tools)
      jobs.py             — list, get, create, update (4 tools)
      job_posts.py        — list, list for job, get, get for job,
                             custom locations, update, update status (7 tools)
      job_stages.py       — list, list for job, get (3 tools)
      job_openings.py     — list, get, create, update, delete (5 tools)
      offers.py           — list, list for application, get,
                             get current for application, update current (5 tools)
      scorecards.py       — list, list for application, get (3 tools)
      interviews.py       — list, list for application, get, create, update, delete (6 tools)
      users.py            — list, get, create, update, disable, enable,
                             change permission level, add email (8 tools)
      user_permissions.py — list job permissions, add job permission,
                             remove job permission, list future job permissions,
                             add future job permission, remove future job permission (6 tools)
      departments.py      — list, get, create, update (4 tools)
      offices.py          — list, get, create, update (4 tools)
      custom_fields.py    — list, get, create, update, delete,
                             list options, create options, update options,
                             delete options (9 tools)
      sources.py          — list (1 tool)
      rejection_reasons.py — list (1 tool)
      email_templates.py  — list, get (2 tools)
      tags.py             — list tags, create tag, delete tag,
                             list tags on candidate, add tag to candidate,
                             remove tag from candidate (6 tools)
      activity_feed.py    — get for candidate (1 tool)
      eeoc.py             — list, get for application (2 tools)
      demographics.py     — list question sets, get question set,
                             list questions, list questions for question set,
                             get question, list answer options,
                             list answer options for question, get answer option,
                             list answers, list answers for application,
                             get answer (11 tools)
      approvals.py        — list for job, get approval flow, request approvals,
                             pending for user, replace approver,
                             create/replace flow (6 tools)
      hiring_team.py      — get, replace, add members, remove member (4 tools)
      prospect_pools.py   — list, get (2 tools)
      close_reasons.py    — list (1 tool)
      tracking_links.py   — get by token (1 tool)
      user_roles.py       — list (1 tool)
      education.py        — list degrees, list disciplines, list schools (3 tools)
    job_board/
      board.py            — get board metadata (1 tool)
      jobs.py             — list published jobs, get with questions (2 tools)
      departments.py      — list, get (2 tools)
      offices.py          — list, get (2 tools)
      prospects.py        — list prospect post sections, get section (2 tools)
      educations.py       — list degrees, list disciplines, list schools (3 tools)
      applications.py     — submit application (1 tool)

    ingestion/
      candidates.py       — post candidates (1 tool)
      jobs.py             — retrieve jobs (1 tool)
      prospects.py        — retrieve prospect pools (1 tool)
      users.py            — retrieve current user (1 tool)
      tracking.py         — post tracking link (1 tool)
      retrieve.py         — retrieve candidates (1 tool)

    webhook_receiver/
      receiver.py         — FastAPI app, HMAC verification, event routing
      models.py           — SQLite models for rules, event log
      actions.py          — action executors (forward URL, log, filter)

    webhook_tools/
      rules.py            — webhook_list_rules, webhook_create_rule,
                             webhook_update_rule, webhook_delete_rule (4 tools)
      events.py           — webhook_list_events, webhook_list_recent (2 tools)
      testing.py          — webhook_test_rule (1 tool)
      setup.py            — webhook_setup_guide (1 tool)
```

### Tool Count

| Group | Tools |
|---|---|
| Harvest API | ~129 |
| Job Board API | ~13 |
| Ingestion API | ~6 |
| Webhook Management (MCP tools) | 8 |
| **Total** | **~156** |

### Data Flow

```
LLM (Claude Code / Claude Desktop)
  |  stdio / MCP protocol
  v
FastMCP Server (greenhouse-mcp)
  |  tool calls
  v
harvest/*.py | job_board/*.py | ingestion/*.py | webhook_tools/*.py
  |  all use shared client          |  reads/writes SQLite
  v                                  v
client.py                     webhooks.db (~/.greenhouse-mcp/)
  |  HTTPS                          ^
  v                                  |
harvest.greenhouse.io         webhook_receiver/receiver.py
boards-api.greenhouse.io        |  HTTP POST from Greenhouse
api.greenhouse.io               |  verifies HMAC-SHA256
                                |  executes routing rules
```

### Entry Points

```
greenhouse-mcp            → MCP server (stdio mode)
greenhouse-mcp-receiver   → webhook receiver (HTTP server)
python -m greenhouse_mcp  → MCP server
```

---

## Auth Model

**`GREENHOUSE_API_KEY` set** — Full access. All ~148 API tools available. Harvest, Job Board (via Harvest endpoints), Ingestion all work. The API key supersedes the board token entirely.

**`GREENHOUSE_BOARD_TOKEN` only** — Fallback for users without API access. Only the ~13 public Job Board tools are available. GETs are unauthenticated (token is in the URL path). The `submit_application` POST requires a Harvest API key for Basic Auth.

**Neither** — Clear error on startup explaining what's needed and how to get credentials.

**Ingestion API** — Uses same Basic Auth pattern as Harvest but also requires an `On-Behalf-Of` header containing a Greenhouse user email address.

---

## Client Design (client.py)

### HTTP Client
- `httpx.AsyncClient` with connection pooling
- Lazy initialization on first request, reused across all calls
- Configurable timeout (default 30s)

### Authentication
- **Harvest**: HTTP Basic Auth — `base64(api_key:)` (key as username, empty password)
- **Job Board**: No auth for GETs — board token is part of URL path
- **Ingestion**: Basic Auth + `On-Behalf-Of: user@company.com` header

### Rate Limiting
- Read `X-RateLimit-Limit` header dynamically (typically 50 req/10s, but can vary)
- On 429: read `Retry-After` header, exponential backoff with jitter, max 3 retries
- During auto-pagination: 200ms inter-page delay
- After retries exhausted: return structured error with wait time

### Pagination
- Parse `Link` header for `rel="next"` URL
- `paginate="single"` (default): one page + metadata `{items, total, page, per_page, has_next, next_page}`
- `paginate="all"`: follow all `next` links, accumulate, return flat list with total
- Default `per_page=500` (Greenhouse max) to minimize requests

### TTL Cache
- In-memory dict: `{cache_key: (data, expires_at)}`
- 5-minute TTL for static entities only:
  - departments, offices, job stages, sources, rejection reasons, email templates, user roles, close reasons, education (degrees/disciplines/schools), tags
- Cache key: `f"{method}:{url}:{sorted_params}"`
- `force_refresh=True` parameter bypasses and refreshes cache
- Dynamic entities (candidates, applications, jobs, offers, interviews, scorecards) are never cached

### Error Handling
All errors return structured dicts — never raise exceptions to the LLM:

| Status | Response |
|---|---|
| 401 | "Invalid API key. Check GREENHOUSE_API_KEY." |
| 403 | "Your API key doesn't have permission for this endpoint. Check Greenhouse permissions." |
| 404 | "Resource not found. Verify the ID exists." |
| 422 | Forward Greenhouse's validation error details |
| 429 | Retry (as above), then "Rate limited. Try again in X seconds." |
| 5xx | "Greenhouse API error. Try again shortly." |

### Base URLs
```python
HARVEST_BASE   = "https://harvest.greenhouse.io/v1"
BOARD_BASE     = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"
```

---

## Webhook Receiver

### Purpose
Enables non-developer users (recruiters, hiring managers) to set up event-driven workflows through the MCP without needing developer support.

### Setup Flow
1. User asks MCP: "I want notifications when candidates are hired"
2. `webhook_setup_guide` generates:
   - The receiver's public URL
   - A secure random secret key
   - Which events to subscribe to
   - Copy-pasteable values for each Greenhouse UI field
   - Step-by-step instructions with screenshots references
3. User follows guide in Greenhouse UI (Configure > Dev Center > Webhooks) — one-time setup
4. `webhook_create_rule` sets up routing: event → action
5. Events flow automatically

### Receiver Architecture
- **FastAPI** app with single endpoint: `POST /webhooks/greenhouse`
- Verifies `Signature` header: `sha256 <hmac_hex_digest>` using stored secret key
- Unicode-aware: computes HMAC against raw body as received (Greenhouse escapes Unicode before signing)
- Stores received events in SQLite for history/debugging
- Evaluates routing rules and executes matching actions

### Routing Rules
A rule consists of:
- **event_type**: one of 27 Greenhouse webhook events (or `*` for all)
- **filter** (optional): field-level conditions (e.g., department contains "Engineering", job_id = 12345)
- **action**: what to do when matched
- **active**: boolean to enable/disable without deleting

### Actions
- **Forward to URL**: POST the event payload to a webhook URL (Slack incoming webhook, Zapier, custom endpoint)
- **Log**: Write to SQLite event log (searchable history)
- **Filter + Forward**: Combine field filters with URL forwarding

### 27 Webhook Event Types

**Application events (8):**
`new_candidate_application`, `delete_application`, `application_updated`, `offer_created`, `offer_approved`, `offer_updated`, `offer_deleted`, `new_prospect_application`

**Candidate events (9):**
`delete_candidate`, `hire_candidate`, `merge_candidate`, `candidate_stage_change`, `unhire_candidate`, `reject_candidate`, `unreject_candidate`, `update_candidate`, `candidate_anonymized`

**Interview events (2):**
`interview_deleted`, `scorecard_deleted`

**Job events (7):**
`job_created`, `job_deleted`, `job_updated`, `job_approved`, `job_post_created`, `job_post_updated`, `job_post_deleted`, `job_interview_stage_deleted`

**Organization events (2):**
`department_deleted`, `office_deleted`

### Webhook Retry Behavior (Greenhouse-side)
7 retries over ~15 hours: 1min, 15min, 1hr, 2hr, 4hr, 8hr, final attempt. If initial ping fails, webhook is created in disabled state.

### MCP Webhook Tools (8)

| Tool | Description |
|---|---|
| `webhook_list_rules` | List all active routing rules |
| `webhook_create_rule` | Create: "when {event} [matching {filter}] → {action}" |
| `webhook_update_rule` | Update an existing rule |
| `webhook_delete_rule` | Delete a rule |
| `webhook_list_events` | List all 27 event types with descriptions |
| `webhook_list_recent` | Show recent webhook deliveries received |
| `webhook_test_rule` | Dry-run a rule against a recent event |
| `webhook_setup_guide` | Generate Greenhouse UI setup instructions + secret key |

### Storage
- SQLite database at `~/.greenhouse-mcp/webhooks.db`
- Shared between MCP server (reads/writes rules) and receiver (reads rules, writes events)
- Tables: `rules`, `events`, `secrets`

---

## Testing

### Unit Tests
- `pytest` + `pytest-asyncio`
- Mock HTTP with `respx` (httpx mock library)
- Test per tool module: correct URL construction, param passing, error handling
- Test client.py: auth headers, pagination link parsing, 429 retry, cache hit/miss/expiry, `force_refresh`
- Test auth model: API key → all tools, board token only → Job Board tools, neither → error
- Test webhook receiver: HMAC verification, rule matching, action execution
- No real API calls — all mocked

### CI
- GitHub Actions: lint (`ruff`) + type check (`mypy`) + tests
- Python 3.10, 3.11, 3.12 matrix
- Runs on push and PR

---

## Distribution

### PyPI Package
- `pip install greenhouse-mcp`
- Two entry points in `pyproject.toml`:
  ```
  greenhouse-mcp = "greenhouse_mcp.server:main"
  greenhouse-mcp-receiver = "greenhouse_mcp.webhook_receiver.receiver:main"
  ```

### Dependencies
- `mcp` (FastMCP)
- `httpx`
- `python-dotenv`
- `fastapi` + `uvicorn` (for webhook receiver)

### MCP Client Config
```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "greenhouse-mcp",
      "env": {
        "GREENHOUSE_API_KEY": "your-key-here"
      }
    }
  }
}
```

### Receiver Deployment
- Local + tunnel (ngrok, Cloudflare Tunnel) for testing
- Any cloud platform (Render, Railway, Fly.io) for production
- `greenhouse-mcp-receiver` with env vars:
  - `GREENHOUSE_WEBHOOK_SECRET` — HMAC secret key
  - `WEBHOOK_DB_PATH` — optional, defaults to `~/.greenhouse-mcp/webhooks.db`
  - `PORT` — optional, defaults to 8080

---

## Personas and Tool Access

### Recruiters (~21+ tools)
Candidates (list, get, create, update, tags, notes), Applications (list, get, advance, move, reject, unreject), Activity Feed, Sources, Interviews (list, get)

### Hiring Managers (~11+ tools)
Scorecards (list, get), Interviews (list, get, create), Applications (list, get), Hiring Team (get), Offers (get current)

### Recruiting Ops / HR (~33+ tools)
Jobs (full CRUD), Job Posts (full CRUD), Job Openings (full CRUD), Offers (full CRUD), Departments/Offices (full CRUD), Custom Fields (full CRUD), Approvals, EEOC, Demographics, Webhook management

### Data Analysts (~11+ tools)
All list endpoints with pagination, EEOC, Demographics, Activity Feed, Scorecards, Tracking Links

### Admin / IT (~14+ tools)
Users (full CRUD), User Roles, User Permissions, Webhooks, Custom Fields, Education reference data

### Sourcers (~9+ tools)
Job Board tools (browse published roles), Ingestion (create candidates/prospects), Prospect Pools, Candidates (create, add prospect)

*All personas have access to all tools — these groupings show primary use cases. The API key's Greenhouse permissions determine actual access.*
