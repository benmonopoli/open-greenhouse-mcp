# Contributing

Thanks for your interest in contributing to open-greenhouse-mcp.

## Getting Started

```bash
git clone https://github.com/benmonopoli/open-greenhouse-mcp.git
cd open-greenhouse-mcp
pip install -e ".[dev]"
```

## Development Workflow

1. Fork the repo and create a branch from `main`
2. Write tests for any new functionality
3. Run the full test suite: `pytest tests/ -v`
4. Run the linter: `ruff check src/ tests/`
5. Open a pull request

## Project Structure

```
src/greenhouse_mcp/
  client.py              # Shared async HTTP client (all API calls go through here)
  server.py              # FastMCP server, tool registration, CLI entry point
  harvest/               # Harvest API tools (one module per resource type)
    applications.py      # CRUD + workflow operations on applications
    candidates.py        # Candidate management
    jobs.py              # Job listings
    workflows.py         # Composite tools (pipeline_summary, etc.)
    analytics.py         # Reporting tools (pipeline_metrics, etc.)
    batch.py             # Bulk operations (bulk_reject, etc.)
    search.py            # Name/email search
    attachments.py       # Resume reading and file downloads
    ...                  # ~20 more resource modules
  job_board/             # Job Board API tools (public, no auth)
  ingestion/             # Ingestion API tools (partner integrations)
  webhook_receiver/      # Webhook HTTP receiver with HMAC verification
  webhook_tools/         # Webhook management MCP tools
```

## Adding a New Tool

Each tool is an async function in the appropriate module under `harvest/`, `job_board/`, or `ingestion/`. The server auto-discovers and registers all public functions.

```python
async def my_new_tool(
    client: GreenhouseClient,
    *,
    required_param: int,
    optional_param: str | None = None,
) -> dict[str, Any]:
    """Short description of what this does.

    Use this when [describe the scenario in recruiter language].
    Longer explanation of behavior and return value.
    """
    return await client.harvest_get(f"/endpoint/{required_param}")
```

Key conventions:
- First parameter is always `client: GreenhouseClient` (injected automatically)
- All other parameters are keyword-only (`*`)
- Return `dict[str, Any]` — never raise exceptions to the LLM
- Docstring first line is the tool description shown to the LLM
- Include "Use this when..." in the docstring for routing hints

## Adding Tests

Tests live in `tests/` and use `pytest` with `httpx`'s mock transport. See existing test files for patterns.

```python
@pytest.mark.asyncio
async def test_my_new_tool(client):
    result = await my_new_tool(client, required_param=123)
    assert result["id"] == 123
```

## Code Style

- Python 3.10+ with type hints
- `ruff` for linting (config in `pyproject.toml`)
- No exceptions to the LLM — return error dicts instead
- Keep tool functions focused — one API concept per function
- Composite tools that make multiple API calls go in `workflows.py`, `analytics.py`, or `batch.py`

## Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Your Python version and OS
- The Greenhouse API endpoint involved (if applicable)
