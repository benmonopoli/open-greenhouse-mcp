# open-greenhouse-mcp

<!-- mcp-name: io.github.benmonopoli/greenhouse-mcp -->

[![PyPI](https://img.shields.io/pypi/v/open-greenhouse-mcp)](https://pypi.org/project/open-greenhouse-mcp/)
[![CI](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![open-greenhouse-mcp MCP server](https://glama.ai/mcp/servers/benmonopoli/open-greenhouse-mcp/badges/score.svg)](https://glama.ai/mcp/servers/benmonopoli/open-greenhouse-mcp)

Production-ready MCP server for Greenhouse, designed for recruiters and hiring teams.

Most Greenhouse MCP servers mirror the API endpoint by endpoint. This one is built for recruiting teams: safe defaults, role-based profiles, and workflow tools that turn multi-step API operations into single actions.

## Choose a Profile

| Profile | Tools | Can write? | Recommended for |
|---|---|---|---|
| `read-only` | 104 | No | First-time setup, reporting, hiring managers |
| `recruiter` | 128 | Yes (safe ops) | Day-to-day recruiting work |
| `full` | 187 | Yes (all) | Admins, ops, advanced automation |

> **Harvest v3.** Greenhouse retired Harvest v1/v2 on 31 Aug 2026. From 0.5.0 this server uses Harvest v3 with OAuth 2.0 credentials. Upgrading from 0.4 or earlier? See [Migrating from v1/v2](docs/advanced.md#migrating-from-04-and-earlier-harvest-v1v2).

## Quick Start

```bash
pip install open-greenhouse-mcp
```

Add to your MCP client config (Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`, Cursor: Settings > MCP):

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "open-greenhouse-mcp",
      "env": {
        "GREENHOUSE_CLIENT_ID": "your-harvest-v3-client-id",
        "GREENHOUSE_CLIENT_SECRET": "your-harvest-v3-client-secret",
        "GREENHOUSE_TOOL_PROFILE": "read-only"
      }
    }
  }
}
```

Start in read-only mode to validate connectivity and tool behaviour, then switch to `recruiter` or `full` when you need write access.

Create the credentials in Greenhouse under **Configure > Dev Center > API Credentials > Create new API credentials > Harvest V3 (OAuth)**, and grant the scopes for the tools you plan to use. The client secret is shown once. See [Advanced Setup](docs/advanced.md#creating-harvest-v3-credentials) for how tokens and scopes work.

## What You Can Ask

- "Show me the pipeline for our Senior Engineer role"
- "Who needs my attention this week?"
- "What are our conversion rates for the Backend Intern role?"
- "Find Sarah Chen and pull up her resume"
- "Which sources are actually producing hires?"
- "Bulk reject everything inactive for 30+ days on the Account Manager role"
- "Screen this candidate for the Backend Engineer role — give me the full picture"
- "Search our engineering pipelines for anyone with Rust and distributed systems experience"
- "What new applications came in since yesterday?"

See [more examples with full output](docs/examples.md).

### See it in action

![Demo](docs/demo.gif)

## Safety

- Access is limited by the scopes on your Harvest v3 credential and the acting user's permissions
- Read-only profile is recommended for first setup
- Destructive actions require explicit IDs — the server never infers targets
- Set `GREENHOUSE_USER_ID` and writes are made as that user (OAuth `sub`), so Greenhouse's audit trail shows who did what
- Bulk actions are rate-limited to stay within API limits

## Compatibility

| Client | Status |
|---|---|
| [Claude Desktop](https://claude.ai/download) | Supported |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Supported |
| [Cursor](https://docs.cursor.com/context/model-context-protocol) | Supported |
| Transport | stdio |
| Python | 3.10+ |

## Startup

When the server starts, it logs its configuration:

```
open-greenhouse-mcp v0.5.0
Profile: recruiter | Tools: 128 | Writes: recruiter-safe | APIs: harvest-v3
```

## What's Included

- **Screening & sourcing tools** — 6 tools for candidate screening, resume search with boolean keywords, daily digest, and location detection
- **Recruiter workflow tools** — 13 composite tools for pipeline views, analytics, search, and bulk operations
- **Harvest v3 API coverage** — 154 tools across candidates, applications, jobs, offers, interviews, and more
- **Job Board API** — 13 tools for public job listings and application submission
- **Optional webhooks and ingestion** — 14 tools for event-driven workflows and partner integrations

---

## Reference

### Screening & Sourcing Tools

Tools for candidate evaluation and proactive talent search.

| Tool | What it does |
|---|---|
| `screen_candidate` | Complete screening package — profile, resume text, location, screening answers, job description, history |
| `fetch_new_applications` | Applications since a date, grouped by job — the daily recruiter digest |
| `scan_pipeline_resumes` | Search resume text across pipelines with boolean keywords (required/preferred/exclude) |
| `search_pipeline_candidates` | Search pipelines by structured fields — title, company, education, experience, tags |
| `scan_all_candidates` | Database-wide candidate search by structured fields with date bounds |
| `batch_read_resumes` | Batch-fetch and extract resume text for multiple candidates |

### Composite Tools

High-level tools that combine multiple API calls into single operations.

| Tool | What it does |
|---|---|
| `pipeline_summary` | Full pipeline view — candidates grouped by stage with names and days-in-stage |
| `candidates_needing_action` | Find stale applications and interviews missing scorecards |
| `stale_applications` | Applications with no activity for N days, sorted by stalest |
| `pipeline_metrics` | Conversion rates, hire/rejection rates, time-in-stage per stage |
| `source_effectiveness` | Which candidate sources produce the best hire rates |
| `time_to_hire` | Average, median, min, max days from application to hire |
| `bulk_reject` | Reject multiple applications in one call with rate-limit handling |
| `bulk_tag` | Tag multiple candidates in one call |
| `bulk_advance` | Advance multiple applications to next stage |
| `get_bulk_request_status` | Track a Greenhouse asynchronous bulk request (openings, custom field options) |
| `search_candidates_by_name` | Find candidates by first or last name |
| `search_candidates_by_email` | Look up a candidate by exact email |
| `read_candidate_resume` | Download and return a candidate's most recent resume |
| `download_attachment` | Download any Greenhouse attachment by URL |

### Profile Details

**Recruiter** includes all read tools, all screening/sourcing tools, all composite workflows, and recruiter-safe writes: reject, advance, hire, move, tag, notes, attachments, interviews, prospects, and bulk operations. It excludes job creation, user management, custom field configuration, candidate deletion, and webhook management.

**Read-only** skips all write operations. `GREENHOUSE_READ_ONLY=true` also works as a shorthand.

### Configuration

| Variable | Required | Description |
|---|---|---|
| `GREENHOUSE_CLIENT_ID` | Yes* | Harvest v3 OAuth client ID |
| `GREENHOUSE_CLIENT_SECRET` | Yes* | Harvest v3 OAuth client secret |
| `GREENHOUSE_BOARD_TOKEN` | Yes* | Job board URL slug. *Harvest credentials and/or a board token required |
| `GREENHOUSE_USER_ID` | No | Greenhouse user ID: writes are made as this user, and the tool profile is derived from their role |
| `GREENHOUSE_TOOL_PROFILE` | No | `full` (default), `recruiter`, or `read-only` (ignored when `GREENHOUSE_USER_ID` is set) |
| `GREENHOUSE_BOARD_API_KEY` | No | Job Board API key, for submitting applications through the board |
| `GREENHOUSE_INGESTION_API_KEY` | No | Ingestion API key, for partner candidate submission |
| `GREENHOUSE_LOG_LEVEL` | No | `debug`, `info`, `warning` (default), `error` |
| `GREENHOUSE_LOG_FILE` | No | Log file path (defaults to stderr) |

### Logging

Structured JSON logging for observability. Set `GREENHOUSE_LOG_LEVEL=info` to enable:

```json
{"ts": "2026-04-14T12:31:58", "level": "info", "event": "api_call", "method": "GET", "url": "...", "status": 200, "latency_ms": 245.0}
```

### More Documentation

- **[API Reference](docs/api-reference.md)** — Full tool breakdown by category
- **[Usage Examples](docs/examples.md)** — Real conversations with full output
- **[Advanced Setup](docs/advanced.md)** — Harvest v3 credentials and scopes, migrating from v1/v2, webhook receiver, ingestion API, board-token mode
- **[Development](docs/development.md)** — Contributing, testing, project structure

## Feedback

- **Bugs and features:** [Open an issue](https://github.com/benmonopoli/open-greenhouse-mcp/issues)
- **Questions:** [Start a discussion](https://github.com/benmonopoli/open-greenhouse-mcp/discussions)
- **Security:** See [SECURITY.md](SECURITY.md)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License -- Ben Monopoli. See [LICENSE](LICENSE).
