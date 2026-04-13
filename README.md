# open-greenhouse-mcp

[![CI](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/benmonopoli/open-greenhouse-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The most comprehensive open-source MCP server for the Greenhouse recruiting API. 175 tools covering the Harvest API, Job Board API, Ingestion API, webhook management, plus high-level composite tools for pipeline views, analytics, batch operations, candidate search, and resume reading.

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

Add to your MCP client config:

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

## Tool Categories

### Composite Tools (13 tools)

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

### Harvest API (148 tools)

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License -- Ben Monopoli. See [LICENSE](LICENSE).

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please report unacceptable behavior to ben.monopoli@ahrefs.com.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).
