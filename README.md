# open-greenhouse-mcp

[![PyPI](https://img.shields.io/pypi/v/open-greenhouse-mcp)](https://pypi.org/project/open-greenhouse-mcp/)
[![CI](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-ready MCP server for Greenhouse, designed for recruiters and hiring teams.

Most Greenhouse MCP servers mirror the API endpoint by endpoint. This one is built for recruiting teams: safe defaults, role-based profiles, and workflow tools that turn multi-step API operations into single actions.

## Choose a Profile

| Profile | Tools | Can write? | Recommended for |
|---|---|---|---|
| `read-only` | 97 | No | First-time setup, reporting, hiring managers |
| `recruiter` | 121 | Yes (safe ops) | Day-to-day recruiting work |
| `full` | 175 | Yes (all) | Admins, ops, advanced automation |

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
        "GREENHOUSE_API_KEY": "your-harvest-api-key",
        "GREENHOUSE_TOOL_PROFILE": "read-only"
      }
    }
  }
}
```

Start in read-only mode to validate connectivity and tool behaviour, then switch to `recruiter` or `full` when you need write access.

Your API key is in Greenhouse under Configure > Dev Center > API Credential Management.

## What You Can Ask

- "Show me the pipeline for our Senior Engineer role"
- "Who needs my attention this week?"
- "What are our conversion rates for the Backend Intern role?"
- "Find Sarah Chen and pull up her resume"
- "Which sources are actually producing hires?"
- "Bulk reject everything inactive for 30+ days on the Account Manager role"

See [more examples with full output](docs/examples.md).

### See it in action

![Demo](docs/demo.gif)

## Safety

- Access is limited by your Greenhouse API key permissions
- Read-only profile is recommended for first setup
- Destructive actions require explicit IDs — the server never infers targets
- Write operations support audit attribution via `GREENHOUSE_ON_BEHALF_OF`
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
open-greenhouse-mcp v0.3.0
Profile: recruiter | Tools: 121 | Writes: recruiter-safe | APIs: harvest, ingestion
```

## What's Included

- **Recruiter workflow tools** — 13 composite tools for pipeline views, analytics, search, and bulk operations
- **Harvest API coverage** — 148 tools across candidates, applications, jobs, offers, interviews, and more
- **Job Board API** — 13 tools for public job listings and application submission
- **Optional webhooks and ingestion** — 14 tools for event-driven workflows and partner integrations

---

## Reference

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
| `search_candidates_by_name` | Find candidates by first or last name |
| `search_candidates_by_email` | Look up a candidate by exact email |
| `read_candidate_resume` | Download and return a candidate's most recent resume |
| `download_attachment` | Download any Greenhouse attachment by URL |

### Profile Details

**Recruiter** includes all read tools, all composite workflows, and recruiter-safe writes: reject, advance, hire, move, tag, notes, attachments, interviews, prospects, and bulk operations. It excludes job creation, user management, custom field configuration, candidate deletion, and webhook management.

**Read-only** skips all write operations. `GREENHOUSE_READ_ONLY=true` also works as a shorthand.

### Configuration

| Variable | Required | Description |
|---|---|---|
| `GREENHOUSE_API_KEY` | Yes* | Harvest API key |
| `GREENHOUSE_BOARD_TOKEN` | Yes* | Job board URL slug. *At least one required |
| `GREENHOUSE_TOOL_PROFILE` | No | `full` (default), `recruiter`, or `read-only` |
| `GREENHOUSE_ON_BEHALF_OF` | No | Greenhouse user ID for write audit trail |
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
- **[Advanced Setup](docs/advanced.md)** — Webhook receiver, ingestion API, board-token mode
- **[Development](docs/development.md)** — Contributing, testing, project structure

## Feedback

- **Bugs and features:** [Open an issue](https://github.com/benmonopoli/open-greenhouse-mcp/issues)
- **Questions:** [Start a discussion](https://github.com/benmonopoli/open-greenhouse-mcp/discussions)
- **Security:** See [SECURITY.md](SECURITY.md)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License -- Ben Monopoli. See [LICENSE](LICENSE).
