# open-greenhouse-mcp

[![PyPI](https://img.shields.io/pypi/v/open-greenhouse-mcp)](https://pypi.org/project/open-greenhouse-mcp/)
[![CI](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Connect your AI assistant to Greenhouse.** Most Greenhouse MCP servers mirror the API endpoint-by-endpoint. This one is built around how recruiting teams actually work — safe defaults, role-based profiles, and workflow tools that replace 10 API calls with one.

## Choose a Profile

Start with read-only to explore safely. Switch to recruiter for day-to-day work. Use full when you need admin access.

| Profile | Tools | Best for |
|---|---|---|
| `read-only` | 97 | Reporting, analytics, safe trial against production |
| `recruiter` | 121 | Pipeline management, candidates, interviews, bulk operations |
| `full` (default) | 175 | Admins and developers with full API access |

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "open-greenhouse-mcp",
      "env": {
        "GREENHOUSE_API_KEY": "your-harvest-api-key",
        "GREENHOUSE_TOOL_PROFILE": "recruiter"
      }
    }
  }
}
```

**Recruiter** includes all read tools, all 13 composite workflows, and recruiter-safe writes: reject, advance, hire, move, tag, notes, attachments, interviews, prospects, and bulk operations. It excludes job creation, user management, custom fields, candidate deletion, and webhook config.

**Read-only** skips all write operations. `GREENHOUSE_READ_ONLY=true` also works.

## Install

```bash
pip install open-greenhouse-mcp
```

Set your API key (found in Greenhouse under Configure > Dev Center > API Credential Management):

```bash
export GREENHOUSE_API_KEY=your-harvest-api-key
```

Add the config block above to your MCP client (Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`, Cursor: Settings > MCP) and restart.

## What You Can Ask

Ask your AI assistant questions like these — it picks the right tool automatically:

| Prompt | What happens |
|---|---|
| "Show me candidates stuck in interview for more than 7 days" | `candidates_needing_action` finds stale applications across your pipeline |
| "What's the pipeline look like for the Engineering Manager role?" | `pipeline_summary` returns candidates grouped by stage with days-in-stage |
| "Which sources are actually producing hires?" | `source_effectiveness` compares hire rates across all candidate sources |
| "Find that candidate Sarah from last week" | `search_candidates_by_name` scans all candidates by name |
| "Reject the 30 stale candidates on that old req" | `bulk_reject` handles them in one call with rate limiting |
| "How long does it take us to hire engineers?" | `time_to_hire` returns average, median, min, max from application to hire |

See [more examples with full output](docs/examples.md).

### See it in action

![Demo](docs/demo.gif)

## Safety

- **Profiles** control what tools are available. Start with `read-only` — zero write operations.
- **Audit trail** via `GREENHOUSE_ON_BEHALF_OF` — all writes are attributed to a specific Greenhouse user, not just "API".
- **Rate limiting** built into bulk operations (`bulk_reject`, `bulk_tag`, `bulk_advance`).
- **Explicit targets only** — destructive actions require specific IDs. The server never infers what to delete or reject.
- **Key-scoped permissions** — the server only has the access your Greenhouse API key grants.

## Compatibility

| Client | Supported | Transport |
|---|---|---|
| [Claude Desktop](https://claude.ai/download) | Yes | stdio |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Yes | stdio |
| [Cursor](https://docs.cursor.com/context/model-context-protocol) | Yes | stdio |
| Any [MCP-compatible client](https://modelcontextprotocol.io/clients) | Yes | stdio |

## What's Included

### Composite Tools (13)

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

### API Coverage

148 Harvest API tools, 13 Job Board tools, 6 Ingestion API tools, and 8 webhook management tools. See [docs/api-reference.md](docs/api-reference.md) for the full breakdown.

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `GREENHOUSE_API_KEY` | Yes* | Harvest API key (Configure > Dev Center in Greenhouse) |
| `GREENHOUSE_BOARD_TOKEN` | Yes* | Job board URL slug (public, no auth). *At least one of API key or board token required |
| `GREENHOUSE_TOOL_PROFILE` | No | `full` (default), `recruiter`, or `read-only` |
| `GREENHOUSE_ON_BEHALF_OF` | No | Greenhouse user ID for write operation audit trail |
| `GREENHOUSE_LOG_LEVEL` | No | `debug`, `info`, `warning` (default), `error` |
| `GREENHOUSE_LOG_FILE` | No | Log file path. Defaults to stderr |

## Logging

Structured JSON logging for observability. Set `GREENHOUSE_LOG_LEVEL=info` to enable:

```json
{"ts": "2026-04-14T12:31:58", "level": "info", "event": "api_call", "method": "GET", "url": "...", "status": 200, "latency_ms": 245.0}
```

Logs go to stderr by default (won't interfere with MCP stdio). Use `GREENHOUSE_LOG_FILE` for file output.

## More Documentation

- **[API Reference](docs/api-reference.md)** — Full tool breakdown by category (Harvest, Job Board, Ingestion, Webhooks)
- **[Usage Examples](docs/examples.md)** — Real conversations with full output
- **[Advanced Setup](docs/advanced.md)** — Webhook receiver, ingestion API, development setup

## Feedback

- **Bugs and features:** [Open an issue](https://github.com/benmonopoli/open-greenhouse-mcp/issues)
- **Questions:** [Start a discussion](https://github.com/benmonopoli/open-greenhouse-mcp/discussions)
- **Security:** See [SECURITY.md](SECURITY.md)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License -- Ben Monopoli. See [LICENSE](LICENSE).
