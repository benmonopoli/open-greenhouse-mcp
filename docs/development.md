# Development

## Setup

```bash
git clone https://github.com/benmonopoli/open-greenhouse-mcp.git
cd open-greenhouse-mcp
pip install -e ".[dev]"
```

## Tests

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/greenhouse_mcp/ --ignore-missing-imports
```

## Project Structure

```
src/greenhouse_mcp/
  server.py          # FastMCP server, tool registration, profile filtering
  client.py          # Shared async HTTP client with retry/rate-limit handling
  logging.py         # Structured JSON logging
  harvest/           # 148 Harvest API tools + 13 composite workflows
  job_board/         # 13 Job Board API tools
  ingestion/         # 6 Ingestion API tools
  webhook_tools/     # 8 webhook management tools
  webhook_receiver/  # HTTP receiver with HMAC verification and SQLite storage
tests/               # pytest suite with respx HTTP mocking
```

## Adding a New Tool

1. Add the function to the appropriate module in `src/greenhouse_mcp/harvest/`
2. The function's first parameter must be `client: GreenhouseClient` (injected automatically)
3. The function's docstring becomes the tool description in MCP
4. If it's a write operation, decide if it belongs in the recruiter profile — add to `_RECRUITER_WRITE_TOOLS` in `server.py` if so
5. Run `pytest`, `ruff check`, and `mypy` before committing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
