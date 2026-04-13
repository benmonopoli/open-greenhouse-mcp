# open-greenhouse-mcp

[![CI](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Connect your AI assistant to Greenhouse.** [MCP](https://modelcontextprotocol.io/) (Model Context Protocol) lets AI tools like Claude, Cursor, and others talk directly to your software. This server gives them full access to Greenhouse — 175 tools covering recruiting pipelines, candidate search, analytics, batch operations, and the complete Greenhouse API.

### Works with

- [Claude Desktop](https://claude.ai/download) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [Cursor](https://docs.cursor.com/context/model-context-protocol)
- Any [MCP-compatible client](https://modelcontextprotocol.io/clients)

## What Can It Do?

Ask your AI assistant questions like these — it handles the Greenhouse API calls automatically:

| You say | The tool used |
|---|---|
| "Show me the pipeline for the Engineering Manager role" | `pipeline_summary` |
| "What are our conversion rates for this job?" | `pipeline_metrics` |
| "Find that candidate Sarah from Google" | `search_candidates_by_name` |
| "What needs my attention this week?" | `candidates_needing_action` |
| "Which sources are actually producing hires?" | `source_effectiveness` |
| "How long does it take us to hire?" | `time_to_hire` |
| "Reject all 30 stale candidates from that old req" | `bulk_reject` |
| "Pull up this candidate's resume" | `read_candidate_resume` |

Plus 148 tools covering every Greenhouse Harvest API endpoint, 13 Job Board tools, 6 Ingestion API tools, and 8 webhook management tools.

### Example: "Show me the pipeline for the Senior Engineer role"

```
Job: Senior Engineer
Active candidates: 42

Application Review (27)
  Chris A. — 48 days since activity
  Meghana T. — 41 days since activity
  Tom Z. — 39 days since activity
  ... 24 more

Recruiter Screen (5)
  Zach S. — 67 days since activity
  ... 4 more

Department Screen (4)    Face to Face (1)    Offer (2)
```

One call. No manual pagination. Candidate names resolved automatically. See [more examples](docs/examples.md).

## Quick Start

```bash
pip install git+https://github.com/benmonopoli/open-greenhouse-mcp.git
```

Or install from source:

```bash
git clone https://github.com/benmonopoli/open-greenhouse-mcp.git
cd open-greenhouse-mcp
pip install -e .
```

Set your API key:

```bash
export GREENHOUSE_API_KEY=your-harvest-api-key
```

Add to your MCP client config (Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`, Cursor: Settings > MCP):

```json
{
  "mcpServers": {
    "greenhouse": {
      "command": "open-greenhouse-mcp",
      "env": {
        "GREENHOUSE_API_KEY": "your-harvest-api-key"
      }
    }
  }
}
```

Restart your client and start asking questions.

## Composite Tools (13 tools)

High-level tools that match how recruiters actually work. These combine multiple API calls into single operations.

| Tool | What it does |
|---|---|
| `pipeline_summary` | Full pipeline view — candidates grouped by stage with names, days-in-stage, last activity |
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

## Harvest API (148 tools)

Full coverage of every Greenhouse Harvest API endpoint.

| Category | Tools | Category | Tools |
|---|---|---|---|
| Candidates | 15 | Applications | 14 |
| Jobs | 4 | Job Posts | 7 |
| Job Stages | 3 | Job Openings | 5 |
| Offers | 5 | Scorecards | 3 |
| Interviews | 6 | Users | 8 |
| User Permissions | 6 | User Roles | 1 |
| Departments | 4 | Offices | 4 |
| Custom Fields | 9 | Sources | 1 |
| Rejection Reasons | 1 | Email Templates | 2 |
| Tags | 6 | Activity Feed | 1 |
| EEOC | 2 | Demographics | 11 |
| Approvals | 6 | Hiring Team | 4 |
| Prospect Pools | 2 | Close Reasons | 1 |
| Tracking Links | 1 | Education | 3 |

## Other APIs

### Job Board API (13 tools)

List boards, jobs, posts, departments, offices, and questions from public job boards.

### Ingestion API (6 tools)

Submit applications and prospects programmatically. Requires `GREENHOUSE_ON_BEHALF_OF`.

### Webhook Management (8 tools)

Create, list, update, and delete webhook subscriptions. Query received events with filtering.

## Authentication

| Credential | Access |
|---|---|
| `GREENHOUSE_API_KEY` | Full Harvest API, Ingestion API, Webhooks |
| `GREENHOUSE_BOARD_TOKEN` | Job Board API only (public, no auth required) |

Set at least one. Both can be configured simultaneously.

You can find your API key in Greenhouse under Configure > Dev Center > API Credential Management.

## Webhook Receiver

The built-in webhook receiver stores Greenhouse events in SQLite for querying via MCP tools.

```bash
# Set your webhook secret (from Greenhouse settings)
export GREENHOUSE_WEBHOOK_SECRET=your-secret

# Start the receiver
open-greenhouse-mcp-receiver
```

Configure the webhook URL in Greenhouse to point to `http://your-host:8080/webhooks/greenhouse`.

## Development

```bash
git clone https://github.com/benmonopoli/open-greenhouse-mcp.git
cd open-greenhouse-mcp
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/greenhouse_mcp/ --ignore-missing-imports
```

## Feedback and Issues

- **Bug reports and feature requests:** [Open an issue](https://github.com/benmonopoli/open-greenhouse-mcp/issues)
- **Questions and discussion:** [Start a discussion](https://github.com/benmonopoli/open-greenhouse-mcp/discussions)
- **Security vulnerabilities:** See [SECURITY.md](SECURITY.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License -- Ben Monopoli. See [LICENSE](LICENSE).

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
