# greenhouse-mcp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive MCP server covering the full Greenhouse API surface (~156 tools) with a webhook receiver companion for event-driven workflows.

**Architecture:** Single Python package with two entry points: `greenhouse-mcp` (FastMCP stdio server) and `greenhouse-mcp-receiver` (FastAPI webhook receiver). All API tools share a common async HTTP client (`client.py`) with auth, rate limiting, pagination, and TTL caching. Webhook rules stored in SQLite.

**Tech Stack:** Python 3.10+, FastMCP, httpx, FastAPI, uvicorn, SQLite, pytest + respx

**Existing code:** There is a prototype in `src/` with ~16 tools and a basic client. We will replace this entirely with the new `src/greenhouse_mcp/` package structure. The old `src/greenhouse_mcp.py`, `src/greenhouse_client.py`, `src/models.py` will be removed.

---

## File Map

### Root
- Modify: `pyproject.toml` — new package structure, two entry points, updated deps
- Delete: `src/__init__.py`, `src/greenhouse_mcp.py`, `src/greenhouse_client.py`, `src/models.py`, `src/__pycache__/`, `greenhouse_mcp.egg-info/`, `example_usage.py`, `test_server.py`, `requirements.txt`, `setup_mcpd.sh`, `.mcpd.toml`

### Core
- Create: `src/greenhouse_mcp/__init__.py`
- Create: `src/greenhouse_mcp/__main__.py`
- Create: `src/greenhouse_mcp/server.py`
- Create: `src/greenhouse_mcp/client.py`

### Harvest (26 modules)
- Create: `src/greenhouse_mcp/harvest/__init__.py`
- Create: `src/greenhouse_mcp/harvest/candidates.py` (15 tools)
- Create: `src/greenhouse_mcp/harvest/applications.py` (14 tools)
- Create: `src/greenhouse_mcp/harvest/jobs.py` (4 tools)
- Create: `src/greenhouse_mcp/harvest/job_posts.py` (7 tools)
- Create: `src/greenhouse_mcp/harvest/job_stages.py` (3 tools)
- Create: `src/greenhouse_mcp/harvest/job_openings.py` (5 tools)
- Create: `src/greenhouse_mcp/harvest/offers.py` (5 tools)
- Create: `src/greenhouse_mcp/harvest/scorecards.py` (3 tools)
- Create: `src/greenhouse_mcp/harvest/interviews.py` (6 tools)
- Create: `src/greenhouse_mcp/harvest/users.py` (8 tools)
- Create: `src/greenhouse_mcp/harvest/user_permissions.py` (6 tools)
- Create: `src/greenhouse_mcp/harvest/departments.py` (4 tools)
- Create: `src/greenhouse_mcp/harvest/offices.py` (4 tools)
- Create: `src/greenhouse_mcp/harvest/custom_fields.py` (9 tools)
- Create: `src/greenhouse_mcp/harvest/sources.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/rejection_reasons.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/email_templates.py` (2 tools)
- Create: `src/greenhouse_mcp/harvest/tags.py` (6 tools)
- Create: `src/greenhouse_mcp/harvest/activity_feed.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/eeoc.py` (2 tools)
- Create: `src/greenhouse_mcp/harvest/demographics.py` (11 tools)
- Create: `src/greenhouse_mcp/harvest/approvals.py` (6 tools)
- Create: `src/greenhouse_mcp/harvest/hiring_team.py` (4 tools)
- Create: `src/greenhouse_mcp/harvest/prospect_pools.py` (2 tools)
- Create: `src/greenhouse_mcp/harvest/close_reasons.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/tracking_links.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/user_roles.py` (1 tool)
- Create: `src/greenhouse_mcp/harvest/education.py` (3 tools)

### Job Board (7 modules)
- Create: `src/greenhouse_mcp/job_board/__init__.py`
- Create: `src/greenhouse_mcp/job_board/board.py` (1 tool)
- Create: `src/greenhouse_mcp/job_board/jobs.py` (2 tools)
- Create: `src/greenhouse_mcp/job_board/departments.py` (2 tools)
- Create: `src/greenhouse_mcp/job_board/offices.py` (2 tools)
- Create: `src/greenhouse_mcp/job_board/prospects.py` (2 tools)
- Create: `src/greenhouse_mcp/job_board/educations.py` (3 tools)
- Create: `src/greenhouse_mcp/job_board/applications.py` (1 tool)

### Ingestion (6 modules)
- Create: `src/greenhouse_mcp/ingestion/__init__.py`
- Create: `src/greenhouse_mcp/ingestion/candidates.py` (1 tool)
- Create: `src/greenhouse_mcp/ingestion/jobs.py` (1 tool)
- Create: `src/greenhouse_mcp/ingestion/prospects.py` (1 tool)
- Create: `src/greenhouse_mcp/ingestion/users.py` (1 tool)
- Create: `src/greenhouse_mcp/ingestion/tracking.py` (1 tool)
- Create: `src/greenhouse_mcp/ingestion/retrieve.py` (1 tool)

### Webhook Receiver
- Create: `src/greenhouse_mcp/webhook_receiver/__init__.py`
- Create: `src/greenhouse_mcp/webhook_receiver/receiver.py`
- Create: `src/greenhouse_mcp/webhook_receiver/models.py`
- Create: `src/greenhouse_mcp/webhook_receiver/actions.py`

### Webhook MCP Tools
- Create: `src/greenhouse_mcp/webhook_tools/__init__.py`
- Create: `src/greenhouse_mcp/webhook_tools/rules.py` (4 tools)
- Create: `src/greenhouse_mcp/webhook_tools/events.py` (2 tools)
- Create: `src/greenhouse_mcp/webhook_tools/testing.py` (1 tool)
- Create: `src/greenhouse_mcp/webhook_tools/setup.py` (1 tool)

### Tests
- Create: `tests/__init__.py`
- Create: `tests/conftest.py` — shared fixtures (mock client, respx routes)
- Create: `tests/test_client.py`
- Create: `tests/test_server.py`
- Create: `tests/harvest/test_candidates.py`
- Create: `tests/harvest/test_applications.py`
- Create: `tests/harvest/test_jobs.py`
- Create: `tests/harvest/test_simple_modules.py` (bulk test for small modules)
- Create: `tests/test_job_board.py`
- Create: `tests/test_ingestion.py`
- Create: `tests/test_webhook_receiver.py`
- Create: `tests/test_webhook_tools.py`

### CI
- Create: `.github/workflows/ci.yml`

---

### Task 1: Project Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Delete: `src/__init__.py`, `src/greenhouse_mcp.py`, `src/greenhouse_client.py`, `src/models.py`, `example_usage.py`, `test_server.py`, `requirements.txt`, `setup_mcpd.sh`, `.mcpd.toml`
- Create: `src/greenhouse_mcp/__init__.py`, `src/greenhouse_mcp/__main__.py`
- Create: `src/greenhouse_mcp/harvest/__init__.py`
- Create: `src/greenhouse_mcp/job_board/__init__.py`
- Create: `src/greenhouse_mcp/ingestion/__init__.py`
- Create: `src/greenhouse_mcp/webhook_receiver/__init__.py`
- Create: `src/greenhouse_mcp/webhook_tools/__init__.py`
- Create: `tests/__init__.py`, `tests/harvest/__init__.py`

- [ ] **Step 1: Remove old code**

```bash
rm -f src/__init__.py src/greenhouse_mcp.py src/greenhouse_client.py src/models.py
rm -rf src/__pycache__ greenhouse_mcp.egg-info
rm -f example_usage.py test_server.py requirements.txt setup_mcpd.sh .mcpd.toml
```

- [ ] **Step 2: Rewrite pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "greenhouse-mcp"
version = "0.2.0"
description = "Comprehensive MCP server for the full Greenhouse API"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Ben Monopoli", email = "ben.monopoli@ahrefs.com"}
]
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "respx>=0.21.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]

[project.scripts]
greenhouse-mcp = "greenhouse_mcp.server:main"
greenhouse-mcp-receiver = "greenhouse_mcp.webhook_receiver.receiver:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
strict = true
```

- [ ] **Step 3: Create package structure**

`src/greenhouse_mcp/__init__.py`:
```python
"""Comprehensive MCP server for the full Greenhouse API."""

__version__ = "0.2.0"
```

`src/greenhouse_mcp/__main__.py`:
```python
"""Allow running with python -m greenhouse_mcp."""

from greenhouse_mcp.server import main

main()
```

`src/greenhouse_mcp/harvest/__init__.py`:
```python
```

`src/greenhouse_mcp/job_board/__init__.py`:
```python
```

`src/greenhouse_mcp/ingestion/__init__.py`:
```python
```

`src/greenhouse_mcp/webhook_receiver/__init__.py`:
```python
```

`src/greenhouse_mcp/webhook_tools/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/harvest/__init__.py`:
```python
```

- [ ] **Step 4: Verify package installs**

```bash
pip install -e ".[dev]"
```

Expected: installs without errors.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Scaffold new package structure, remove old prototype"
```

---

### Task 2: HTTP Client — Core Request Handling

**Files:**
- Create: `src/greenhouse_mcp/client.py`
- Create: `tests/test_client.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write conftest with shared fixtures**

`tests/conftest.py`:
```python
import pytest
import respx
from greenhouse_mcp.client import GreenhouseClient


@pytest.fixture
def api_key():
    return "test-api-key-12345"


@pytest.fixture
def client(api_key):
    return GreenhouseClient(api_key=api_key)


@pytest.fixture
def board_client():
    return GreenhouseClient(board_token="test-board")


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock
```

- [ ] **Step 2: Write failing tests for basic request handling**

`tests/test_client.py`:
```python
import httpx
import pytest
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


class TestClientInit:
    def test_requires_some_credentials(self):
        with pytest.raises(ValueError, match="GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN"):
            GreenhouseClient()

    def test_api_key_only(self, api_key):
        client = GreenhouseClient(api_key=api_key)
        assert client.api_key == api_key
        assert client.board_token is None

    def test_board_token_only(self):
        client = GreenhouseClient(board_token="my-board")
        assert client.board_token == "my-board"
        assert client.api_key is None


class TestHarvestAuth:
    @respx.mock
    async def test_basic_auth_header(self, client, api_key):
        import base64

        route = respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.harvest_get("jobs")
        assert route.called
        request = route.calls[0].request
        expected_auth = base64.b64encode(f"{api_key}:".encode()).decode()
        assert request.headers["authorization"] == f"Basic {expected_auth}"

    @respx.mock
    async def test_get_with_params(self, client):
        route = respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        result = await client.harvest_get("jobs", params={"per_page": 100, "status": "open"})
        assert result == {"items": [{"id": 1}], "has_next": False, "next_page": None}
        assert "per_page=100" in str(route.calls[0].request.url)

    @respx.mock
    async def test_post_with_json(self, client):
        route = respx.post(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(201, json={"id": 42})
        )
        result = await client.harvest_post("candidates", json_data={"first_name": "Ada"})
        assert result == {"id": 42}

    @respx.mock
    async def test_patch(self, client):
        route = respx.patch(f"{HARVEST_BASE}/candidates/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "first_name": "Ada"})
        )
        result = await client.harvest_patch("candidates/1", json_data={"first_name": "Ada"})
        assert result == {"id": 1, "first_name": "Ada"}

    @respx.mock
    async def test_delete(self, client):
        route = respx.delete(f"{HARVEST_BASE}/candidates/1").mock(
            return_value=httpx.Response(200, json={"message": "deleted"})
        )
        result = await client.harvest_delete("candidates/1")
        assert result == {"message": "deleted"}

    @respx.mock
    async def test_put(self, client):
        route = respx.put(f"{HARVEST_BASE}/jobs/1/hiring_team").mock(
            return_value=httpx.Response(200, json={"success": True})
        )
        result = await client.harvest_put("jobs/1/hiring_team", json_data={"members": []})
        assert result == {"success": True}
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: FAIL — `greenhouse_mcp.client` does not exist yet.

- [ ] **Step 4: Implement client core**

`src/greenhouse_mcp/client.py`:
```python
"""Shared async HTTP client for all Greenhouse API interactions."""

from __future__ import annotations

import base64
import re
import time
from typing import Any

import httpx

HARVEST_BASE = "https://harvest.greenhouse.io/v1"
BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"

_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class GreenhouseClient:
    """Async HTTP client with auth, rate limiting, pagination, and caching."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        board_token: str | None = None,
        on_behalf_of: str | None = None,
    ) -> None:
        if not api_key and not board_token:
            raise ValueError(
                "At least one of GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN is required. "
                "Set them as environment variables or pass directly."
            )
        self.api_key = api_key
        self.board_token = board_token
        self.on_behalf_of = on_behalf_of
        self._http: httpx.AsyncClient | None = None
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    def _harvest_headers(self) -> dict[str, str]:
        assert self.api_key is not None
        encoded = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    def _ingestion_headers(self) -> dict[str, str]:
        headers = self._harvest_headers()
        if self.on_behalf_of:
            headers["On-Behalf-Of"] = self.on_behalf_of
        return headers

    def _parse_link_next(self, link_header: str | None) -> str | None:
        if not link_header:
            return None
        match = _LINK_NEXT_RE.search(link_header)
        return match.group(1) if match else None

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        _retries: int = 3,
    ) -> httpx.Response:
        http = await self._get_http()
        response = await http.request(
            method, url, headers=headers, params=params, json=json_data
        )

        if response.status_code == 429 and _retries > 0:
            retry_after = int(response.headers.get("Retry-After", "10"))
            import asyncio
            await asyncio.sleep(retry_after)
            return await self._request(
                method, url, headers=headers, params=params,
                json_data=json_data, _retries=_retries - 1,
            )

        return response

    def _handle_error(self, response: httpx.Response) -> dict[str, Any]:
        status = response.status_code
        detail = ""
        try:
            detail = response.json()
        except Exception:
            detail = response.text

        messages = {
            401: "Invalid API key. Check GREENHOUSE_API_KEY.",
            403: "Your API key doesn't have permission for this endpoint. Check Greenhouse permissions.",
            404: "Resource not found. Verify the ID exists.",
            429: f"Rate limited. Try again in {response.headers.get('Retry-After', '10')} seconds.",
        }
        message = messages.get(status, f"Greenhouse API error (HTTP {status}).")

        if status == 422:
            message = "Validation error."

        return {"error": message, "status_code": status, "detail": detail}

    async def harvest_get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        headers = self._harvest_headers()
        response = await self._request("GET", url, headers=headers, params=params)

        if response.status_code >= 400:
            return self._handle_error(response)

        data = response.json()
        next_url = self._parse_link_next(response.headers.get("link"))

        if paginate == "all" and next_url:
            all_items = list(data) if isinstance(data, list) else [data]
            while next_url:
                import asyncio
                await asyncio.sleep(0.2)  # inter-page delay
                response = await self._request("GET", next_url, headers=headers)
                if response.status_code >= 400:
                    return self._handle_error(response)
                page_data = response.json()
                if isinstance(page_data, list):
                    all_items.extend(page_data)
                next_url = self._parse_link_next(response.headers.get("link"))
            return {"items": all_items, "total": len(all_items)}

        items = data if isinstance(data, list) else data
        result: dict[str, Any] = {
            "items": items if isinstance(items, list) else items,
            "has_next": next_url is not None,
            "next_page": next_url,
        }
        return result

    async def harvest_post(
        self, endpoint: str, *, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        response = await self._request(
            "POST", url, headers=self._harvest_headers(), json_data=json_data
        )
        if response.status_code >= 400:
            return self._handle_error(response)
        if response.status_code == 204:
            return {"success": True}
        return response.json()

    async def harvest_patch(
        self, endpoint: str, *, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        response = await self._request(
            "PATCH", url, headers=self._harvest_headers(), json_data=json_data
        )
        if response.status_code >= 400:
            return self._handle_error(response)
        if response.status_code == 204:
            return {"success": True}
        return response.json()

    async def harvest_delete(self, endpoint: str) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        response = await self._request("DELETE", url, headers=self._harvest_headers())
        if response.status_code >= 400:
            return self._handle_error(response)
        if response.status_code == 204:
            return {"success": True}
        return response.json()

    async def harvest_put(
        self, endpoint: str, *, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        response = await self._request(
            "PUT", url, headers=self._harvest_headers(), json_data=json_data
        )
        if response.status_code >= 400:
            return self._handle_error(response)
        if response.status_code == 204:
            return {"success": True}
        return response.json()

    # --- Job Board API ---

    async def board_get(
        self, endpoint: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        assert self.board_token is not None
        url = f"{BOARD_BASE}/{self.board_token}/{endpoint}"
        response = await self._request("GET", url, headers={}, params=params)
        if response.status_code >= 400:
            return self._handle_error(response)
        return response.json()

    async def board_post(
        self, endpoint: str, *, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        assert self.board_token is not None
        url = f"{BOARD_BASE}/{self.board_token}/{endpoint}"
        headers = self._harvest_headers() if self.api_key else {}
        response = await self._request("POST", url, headers=headers, json_data=json_data)
        if response.status_code >= 400:
            return self._handle_error(response)
        return response.json()

    # --- Ingestion API ---

    async def ingestion_get(
        self, endpoint: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{INGESTION_BASE}/{endpoint}"
        response = await self._request(
            "GET", url, headers=self._ingestion_headers(), params=params
        )
        if response.status_code >= 400:
            return self._handle_error(response)
        return response.json()

    async def ingestion_post(
        self, endpoint: str, *, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{INGESTION_BASE}/{endpoint}"
        response = await self._request(
            "POST", url, headers=self._ingestion_headers(), json_data=json_data
        )
        if response.status_code >= 400:
            return self._handle_error(response)
        return response.json()

    # --- Cache ---

    def _cache_key(self, method: str, url: str, params: dict[str, Any] | None) -> str:
        sorted_params = sorted((params or {}).items())
        return f"{method}:{url}:{sorted_params}"

    async def harvest_get_cached(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}/{endpoint}"
        key = self._cache_key("GET", url, params)

        if not force_refresh and key in self._cache:
            data, expires = self._cache[key]
            if time.time() < expires:
                return data

        result = await self.harvest_get(endpoint, params=params, paginate=paginate)
        if "error" not in result:
            self._cache[key] = (result, time.time() + self._cache_ttl)
        return result

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_client.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/greenhouse_mcp/client.py tests/conftest.py tests/test_client.py
git commit -m "Add async HTTP client with auth, pagination, caching, error handling"
```

---

### Task 3: Client — Error Handling, Rate Limiting, and Cache Tests

**Files:**
- Modify: `tests/test_client.py`

- [ ] **Step 1: Write error handling tests**

Add to `tests/test_client.py`:
```python
class TestErrorHandling:
    @respx.mock
    async def test_401_returns_structured_error(self, client):
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(401, json={"message": "unauthorized"})
        )
        result = await client.harvest_get("jobs")
        assert result["error"] == "Invalid API key. Check GREENHOUSE_API_KEY."
        assert result["status_code"] == 401

    @respx.mock
    async def test_403_returns_permission_error(self, client):
        respx.get(f"{HARVEST_BASE}/users").mock(
            return_value=httpx.Response(403, json={"message": "forbidden"})
        )
        result = await client.harvest_get("users")
        assert result["status_code"] == 403
        assert "permission" in result["error"].lower()

    @respx.mock
    async def test_404_returns_not_found(self, client):
        respx.get(f"{HARVEST_BASE}/candidates/999").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )
        result = await client.harvest_get("candidates/999")
        assert result["status_code"] == 404

    @respx.mock
    async def test_422_returns_validation_detail(self, client):
        respx.post(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(
                422, json={"errors": [{"field": "first_name", "message": "required"}]}
            )
        )
        result = await client.harvest_post("candidates", json_data={})
        assert result["status_code"] == 422
        assert "errors" in result["detail"]

    @respx.mock
    async def test_500_returns_server_error(self, client):
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        result = await client.harvest_get("jobs")
        assert result["status_code"] == 500


class TestRateLimiting:
    @respx.mock
    async def test_429_retries_with_backoff(self, client):
        route = respx.get(f"{HARVEST_BASE}/jobs").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json=[{"id": 1}]),
            ]
        )
        result = await client.harvest_get("jobs")
        assert route.call_count == 2
        assert "error" not in result

    @respx.mock
    async def test_429_exhausts_retries(self, client):
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "0"})
        )
        result = await client.harvest_get("jobs")
        assert result["status_code"] == 429


class TestPagination:
    @respx.mock
    async def test_single_page_no_link(self, client):
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        result = await client.harvest_get("jobs")
        assert result["items"] == [{"id": 1}]
        assert result["has_next"] is False

    @respx.mock
    async def test_single_page_with_link(self, client):
        next_url = f"{HARVEST_BASE}/jobs?page=2&per_page=100"
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"Link": f'<{next_url}>; rel="next"'},
            )
        )
        result = await client.harvest_get("jobs", paginate="single")
        assert result["has_next"] is True
        assert result["next_page"] == next_url

    @respx.mock
    async def test_paginate_all(self, client):
        page2_url = f"{HARVEST_BASE}/jobs?page=2&per_page=100"
        respx.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"Link": f'<{page2_url}>; rel="next"'},
            )
        )
        respx.get(page2_url).mock(
            return_value=httpx.Response(200, json=[{"id": 2}])
        )
        result = await client.harvest_get("jobs", paginate="all")
        assert result["items"] == [{"id": 1}, {"id": 2}]
        assert result["total"] == 2


class TestCache:
    @respx.mock
    async def test_cache_hit(self, client):
        route = respx.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 1, "name": "Eng"}])
        )
        result1 = await client.harvest_get_cached("departments")
        result2 = await client.harvest_get_cached("departments")
        assert route.call_count == 1  # only one HTTP call
        assert result1 == result2

    @respx.mock
    async def test_force_refresh_bypasses_cache(self, client):
        route = respx.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        await client.harvest_get_cached("departments")
        await client.harvest_get_cached("departments", force_refresh=True)
        assert route.call_count == 2

    @respx.mock
    async def test_cache_does_not_store_errors(self, client):
        respx.get(f"{HARVEST_BASE}/departments").mock(
            side_effect=[
                httpx.Response(500, text="error"),
                httpx.Response(200, json=[{"id": 1}]),
            ]
        )
        result1 = await client.harvest_get_cached("departments")
        assert "error" in result1
        result2 = await client.harvest_get_cached("departments")
        assert "error" not in result2


class TestBoardClient:
    @respx.mock
    async def test_board_get_no_auth(self, board_client):
        route = respx.get(f"https://boards-api.greenhouse.io/v1/boards/test-board/jobs").mock(
            return_value=httpx.Response(200, json={"jobs": [{"id": 1}]})
        )
        result = await board_client.board_get("jobs")
        assert result == {"jobs": [{"id": 1}]}
        assert "authorization" not in route.calls[0].request.headers


class TestIngestionClient:
    @respx.mock
    async def test_ingestion_includes_on_behalf_of(self):
        client = GreenhouseClient(api_key="key123", on_behalf_of="user@co.com")
        route = respx.post(f"https://api.greenhouse.io/v1/partner/candidates").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )
        await client.ingestion_post("candidates", json_data={"first_name": "Ada"})
        assert route.calls[0].request.headers["on-behalf-of"] == "user@co.com"
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_client.py -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_client.py
git commit -m "Add comprehensive client tests: errors, rate limiting, pagination, cache"
```

---

### Task 4: Server Core and Auth Model

**Files:**
- Create: `src/greenhouse_mcp/server.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write failing server tests**

`tests/test_server.py`:
```python
import os
from unittest.mock import patch

import pytest

from greenhouse_mcp.server import create_server, get_client


class TestGetClient:
    @patch.dict(os.environ, {"GREENHOUSE_API_KEY": "test-key"}, clear=False)
    def test_api_key_creates_client(self):
        client = get_client()
        assert client.api_key == "test-key"

    @patch.dict(os.environ, {"GREENHOUSE_BOARD_TOKEN": "my-board"}, clear=False)
    def test_board_token_creates_client(self):
        # Remove API key if present
        env = {k: v for k, v in os.environ.items() if k != "GREENHOUSE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            client = get_client()
            assert client.board_token == "my-board"

    def test_no_credentials_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN"):
                get_client()


class TestCreateServer:
    def test_returns_fastmcp_instance(self):
        server = create_server()
        assert server.name == "Greenhouse"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_server.py -v
```

Expected: FAIL — `greenhouse_mcp.server` does not exist.

- [ ] **Step 3: Implement server.py**

`src/greenhouse_mcp/server.py`:
```python
"""FastMCP server with tool registration and CLI entry point."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from greenhouse_mcp.client import GreenhouseClient

load_dotenv()

_client: GreenhouseClient | None = None


def get_client() -> GreenhouseClient:
    """Get or create the shared Greenhouse client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GREENHOUSE_API_KEY")
    board_token = os.environ.get("GREENHOUSE_BOARD_TOKEN")
    on_behalf_of = os.environ.get("GREENHOUSE_ON_BEHALF_OF")

    if not api_key and not board_token:
        raise ValueError(
            "At least one of GREENHOUSE_API_KEY or GREENHOUSE_BOARD_TOKEN is required.\n"
            "Harvest API key: Configure > Dev Center > API Credential Management in Greenhouse.\n"
            "Board token: your public job board URL slug."
        )

    _client = GreenhouseClient(
        api_key=api_key,
        board_token=board_token,
        on_behalf_of=on_behalf_of,
    )
    return _client


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all tools."""
    mcp = FastMCP("Greenhouse")
    mcp.description = "Comprehensive MCP server for the full Greenhouse API"

    # Tool modules are registered by importing them and passing the server + client getter
    from greenhouse_mcp.harvest import candidates as _  # noqa: F401
    # More imports will be added as modules are built

    return mcp


# Global server instance — tool modules register against this
mcp = create_server()


def main() -> None:
    """CLI entry point."""
    try:
        get_client()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    mcp.run()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_server.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/greenhouse_mcp/server.py tests/test_server.py
git commit -m "Add FastMCP server core with auth model"
```

---

### Task 5: Harvest — Candidates Module (Pattern-Setting)

This is the first and largest harvest module. It establishes the pattern all other modules follow: each tool is a thin async function decorated with `@mcp.tool` that calls the shared client.

**Files:**
- Create: `src/greenhouse_mcp/harvest/candidates.py`
- Create: `tests/harvest/test_candidates.py`

- [ ] **Step 1: Write tests for candidate list and get**

`tests/harvest/test_candidates.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@respx.mock
async def test_list_candidates():
    from greenhouse_mcp.harvest.candidates import list_candidates

    respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "first_name": "Ada"}])
    )
    client = GreenhouseClient(api_key="test")
    result = await list_candidates(client)
    assert result["items"] == [{"id": 1, "first_name": "Ada"}]


@respx.mock
async def test_list_candidates_with_filters():
    from greenhouse_mcp.harvest.candidates import list_candidates

    route = respx.get(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = GreenhouseClient(api_key="test")
    await list_candidates(client, per_page=100, email="ada@example.com")
    assert "per_page=100" in str(route.calls[0].request.url)
    assert "email=ada" in str(route.calls[0].request.url)


@respx.mock
async def test_get_candidate():
    from greenhouse_mcp.harvest.candidates import get_candidate

    respx.get(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "first_name": "Ada"})
    )
    client = GreenhouseClient(api_key="test")
    result = await get_candidate(client, candidate_id=42)
    assert result["items"]["id"] == 42


@respx.mock
async def test_create_candidate():
    from greenhouse_mcp.harvest.candidates import create_candidate

    respx.post(f"{HARVEST_BASE}/candidates").mock(
        return_value=httpx.Response(201, json={"id": 42})
    )
    client = GreenhouseClient(api_key="test")
    result = await create_candidate(client, first_name="Ada", last_name="Lovelace")
    assert result["id"] == 42


@respx.mock
async def test_delete_candidate():
    from greenhouse_mcp.harvest.candidates import delete_candidate

    respx.delete(f"{HARVEST_BASE}/candidates/42").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )
    client = GreenhouseClient(api_key="test")
    result = await delete_candidate(client, candidate_id=42)
    assert result["message"] == "deleted"


@respx.mock
async def test_add_note_to_candidate():
    from greenhouse_mcp.harvest.candidates import add_note_to_candidate

    respx.post(f"{HARVEST_BASE}/candidates/42/activity_feed/notes").mock(
        return_value=httpx.Response(201, json={"id": 1, "body": "Great call"})
    )
    client = GreenhouseClient(api_key="test")
    result = await add_note_to_candidate(
        client, candidate_id=42, body="Great call", visibility="private"
    )
    assert result["body"] == "Great call"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/harvest/test_candidates.py -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement candidates.py**

`src/greenhouse_mcp/harvest/candidates.py`:
```python
"""Harvest API — Candidate tools (15 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_candidates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    email: str | None = None,
    candidate_ids: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List candidates in Greenhouse. Use paginate='all' to fetch every page."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if email:
        params["email"] = email
    if candidate_ids:
        params["candidate_id"] = candidate_ids
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if updated_after:
        params["updated_after"] = updated_after
    if updated_before:
        params["updated_before"] = updated_before
    return await client.harvest_get("candidates", params=params, paginate=paginate)


async def get_candidate(
    client: GreenhouseClient, *, candidate_id: int
) -> dict[str, Any]:
    """Get a single candidate by ID."""
    return await client.harvest_get(f"candidates/{candidate_id}")


async def create_candidate(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, str]] | None = None,
    email_addresses: list[dict[str, str]] | None = None,
    addresses: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new candidate."""
    data: dict[str, Any] = {"first_name": first_name, "last_name": last_name}
    if company:
        data["company"] = company
    if title:
        data["title"] = title
    if phone_numbers:
        data["phone_numbers"] = phone_numbers
    if email_addresses:
        data["email_addresses"] = email_addresses
    if addresses:
        data["addresses"] = addresses
    if tags:
        data["tags"] = tags
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_post("candidates", json_data=data)


async def update_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, str]] | None = None,
    email_addresses: list[dict[str, str]] | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update an existing candidate."""
    data: dict[str, Any] = {}
    if first_name:
        data["first_name"] = first_name
    if last_name:
        data["last_name"] = last_name
    if company:
        data["company"] = company
    if title:
        data["title"] = title
    if phone_numbers:
        data["phone_numbers"] = phone_numbers
    if email_addresses:
        data["email_addresses"] = email_addresses
    if tags:
        data["tags"] = tags
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_patch(f"candidates/{candidate_id}", json_data=data)


async def delete_candidate(
    client: GreenhouseClient, *, candidate_id: int
) -> dict[str, Any]:
    """Delete a candidate. This action cannot be undone."""
    return await client.harvest_delete(f"candidates/{candidate_id}")


async def merge_candidates(
    client: GreenhouseClient,
    *,
    primary_candidate_id: int,
    duplicate_candidate_id: int,
) -> dict[str, Any]:
    """Merge two candidate records. The duplicate is merged into the primary."""
    return await client.harvest_put(
        f"candidates/merge",
        json_data={
            "primary_candidate_id": primary_candidate_id,
            "duplicate_candidate_id": duplicate_candidate_id,
        },
    )


async def anonymize_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Anonymize a candidate (GDPR). Specify fields to anonymize or anonymize all."""
    data: dict[str, Any] = {}
    if fields:
        data["fields"] = fields
    return await client.harvest_put(
        f"candidates/{candidate_id}/anonymize", json_data=data
    )


async def add_prospect(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    company: str | None = None,
    title: str | None = None,
    phone_numbers: list[dict[str, str]] | None = None,
    email_addresses: list[dict[str, str]] | None = None,
    prospect_pool_id: int | None = None,
    prospect_stage_id: int | None = None,
    prospect_owner_id: int | None = None,
) -> dict[str, Any]:
    """Add a new prospect."""
    data: dict[str, Any] = {"first_name": first_name, "last_name": last_name}
    if company:
        data["company"] = company
    if title:
        data["title"] = title
    if phone_numbers:
        data["phone_numbers"] = phone_numbers
    if email_addresses:
        data["email_addresses"] = email_addresses
    if prospect_pool_id:
        data["prospect_pool_id"] = prospect_pool_id
    if prospect_stage_id:
        data["prospect_stage_id"] = prospect_stage_id
    if prospect_owner_id:
        data["prospect_owner_id"] = prospect_owner_id
    return await client.harvest_post("candidates", json_data={**data, "is_prospect": True})


async def add_education(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    school_id: int | None = None,
    discipline_id: int | None = None,
    degree_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Add an education entry to a candidate."""
    data: dict[str, Any] = {}
    if school_id:
        data["school_id"] = school_id
    if discipline_id:
        data["discipline_id"] = discipline_id
    if degree_id:
        data["degree_id"] = degree_id
    if start_date:
        data["start_date"] = start_date
    if end_date:
        data["end_date"] = end_date
    return await client.harvest_post(
        f"candidates/{candidate_id}/educations", json_data=data
    )


async def remove_education(
    client: GreenhouseClient, *, candidate_id: int, education_id: int
) -> dict[str, Any]:
    """Remove an education entry from a candidate."""
    return await client.harvest_delete(
        f"candidates/{candidate_id}/educations/{education_id}"
    )


async def add_employment(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    company_name: str | None = None,
    title: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Add an employment entry to a candidate."""
    data: dict[str, Any] = {}
    if company_name:
        data["company_name"] = company_name
    if title:
        data["title"] = title
    if start_date:
        data["start_date"] = start_date
    if end_date:
        data["end_date"] = end_date
    return await client.harvest_post(
        f"candidates/{candidate_id}/employments", json_data=data
    )


async def remove_employment(
    client: GreenhouseClient, *, candidate_id: int, employment_id: int
) -> dict[str, Any]:
    """Remove an employment entry from a candidate."""
    return await client.harvest_delete(
        f"candidates/{candidate_id}/employments/{employment_id}"
    )


async def add_attachment(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    filename: str,
    type: str,
    content: str | None = None,
    url: str | None = None,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    """Add an attachment to a candidate (resume, cover letter, etc.)."""
    data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content:
        data["content"] = content
    if url:
        data["url"] = url
    return await client.harvest_post(
        f"candidates/{candidate_id}/attachments", json_data=data
    )


async def add_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    body: str,
    visibility: str = "private",
) -> dict[str, Any]:
    """Add a note to a candidate's activity feed."""
    return await client.harvest_post(
        f"candidates/{candidate_id}/activity_feed/notes",
        json_data={"body": body, "visibility": visibility},
    )


async def add_email_note_to_candidate(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    to: str,
    from_: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Add an email note to a candidate's activity feed."""
    return await client.harvest_post(
        f"candidates/{candidate_id}/activity_feed/emails",
        json_data={"to": to, "from": from_, "subject": subject, "body": body},
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/harvest/test_candidates.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/greenhouse_mcp/harvest/candidates.py tests/harvest/test_candidates.py
git commit -m "Add candidates module with 15 harvest tools"
```

---

### Task 6: Harvest — Applications Module

**Files:**
- Create: `src/greenhouse_mcp/harvest/applications.py`
- Create: `tests/harvest/test_applications.py`

- [ ] **Step 1: Write tests**

`tests/harvest/test_applications.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@respx.mock
async def test_list_applications():
    from greenhouse_mcp.harvest.applications import list_applications

    respx.get(f"{HARVEST_BASE}/applications").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    client = GreenhouseClient(api_key="test")
    result = await list_applications(client)
    assert result["items"] == [{"id": 1}]


@respx.mock
async def test_advance_application():
    from greenhouse_mcp.harvest.applications import advance_application

    respx.post(f"{HARVEST_BASE}/applications/1/advance").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    client = GreenhouseClient(api_key="test")
    result = await advance_application(client, application_id=1, from_stage_id=10)
    assert result["success"] is True


@respx.mock
async def test_reject_application():
    from greenhouse_mcp.harvest.applications import reject_application

    respx.post(f"{HARVEST_BASE}/applications/1/reject").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    client = GreenhouseClient(api_key="test")
    result = await reject_application(client, application_id=1)
    assert result["success"] is True


@respx.mock
async def test_hire_application():
    from greenhouse_mcp.harvest.applications import hire_application

    respx.post(f"{HARVEST_BASE}/applications/1/hire").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    client = GreenhouseClient(api_key="test")
    result = await hire_application(client, application_id=1)
    assert result["success"] is True


@respx.mock
async def test_move_application_different_job():
    from greenhouse_mcp.harvest.applications import move_application

    respx.post(f"{HARVEST_BASE}/applications/1/transfer_to_job").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    client = GreenhouseClient(api_key="test")
    result = await move_application(client, application_id=1, new_job_id=5)
    assert result["success"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/harvest/test_applications.py -v
```

- [ ] **Step 3: Implement applications.py**

`src/greenhouse_mcp/harvest/applications.py`:
```python
"""Harvest API — Application tools (14 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_applications(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    job_id: int | None = None,
    candidate_id: int | None = None,
    status: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    last_activity_after: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List applications. Filter by job, candidate, status, or date."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if job_id:
        params["job_id"] = job_id
    if candidate_id:
        params["candidate_id"] = candidate_id
    if status:
        params["status"] = status
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    if last_activity_after:
        params["last_activity_after"] = last_activity_after
    return await client.harvest_get("applications", params=params, paginate=paginate)


async def get_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """Get a single application by ID."""
    return await client.harvest_get(f"applications/{application_id}")


async def create_application(
    client: GreenhouseClient,
    *,
    candidate_id: int,
    job_id: int,
    source_id: int | None = None,
    referrer: dict[str, Any] | None = None,
    initial_stage_id: int | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add an application to an existing candidate for a specific job."""
    data: dict[str, Any] = {"candidate_id": candidate_id, "job_id": job_id}
    if source_id:
        data["source_id"] = source_id
    if referrer:
        data["referrer"] = referrer
    if initial_stage_id:
        data["initial_stage_id"] = initial_stage_id
    if attachments:
        data["attachments"] = attachments
    return await client.harvest_post(
        f"candidates/{candidate_id}/applications", json_data=data
    )


async def update_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    source_id: int | None = None,
    referrer: dict[str, Any] | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update an application."""
    data: dict[str, Any] = {}
    if source_id:
        data["source_id"] = source_id
    if referrer:
        data["referrer"] = referrer
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_patch(f"applications/{application_id}", json_data=data)


async def delete_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """Delete an application. Cannot be undone."""
    return await client.harvest_delete(f"applications/{application_id}")


async def advance_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    from_stage_id: int,
    to_stage_id: int | None = None,
) -> dict[str, Any]:
    """Advance an application to the next stage."""
    data: dict[str, Any] = {"from_stage_id": from_stage_id}
    if to_stage_id:
        data["to_stage_id"] = to_stage_id
    return await client.harvest_post(
        f"applications/{application_id}/advance", json_data=data
    )


async def move_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    new_job_id: int,
    new_stage_id: int | None = None,
) -> dict[str, Any]:
    """Move an application to a different job."""
    data: dict[str, Any] = {"new_job_id": new_job_id}
    if new_stage_id:
        data["new_stage_id"] = new_stage_id
    return await client.harvest_post(
        f"applications/{application_id}/transfer_to_job", json_data=data
    )


async def move_application_same_job(
    client: GreenhouseClient,
    *,
    application_id: int,
    from_stage_id: int,
    to_stage_id: int,
) -> dict[str, Any]:
    """Move an application to a different stage within the same job."""
    return await client.harvest_post(
        f"applications/{application_id}/move",
        json_data={"from_stage_id": from_stage_id, "to_stage_id": to_stage_id},
    )


async def reject_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    rejection_reason_id: int | None = None,
    notes: str | None = None,
    rejection_email: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reject an application."""
    data: dict[str, Any] = {}
    if rejection_reason_id:
        data["rejection_reason_id"] = rejection_reason_id
    if notes:
        data["notes"] = notes
    if rejection_email:
        data["rejection_email"] = rejection_email
    return await client.harvest_post(
        f"applications/{application_id}/reject", json_data=data
    )


async def unreject_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """Unreject a previously rejected application."""
    return await client.harvest_post(f"applications/{application_id}/unreject")


async def update_rejection_reason(
    client: GreenhouseClient,
    *,
    application_id: int,
    rejection_reason_id: int,
) -> dict[str, Any]:
    """Update the rejection reason on a rejected application."""
    return await client.harvest_patch(
        f"applications/{application_id}/reject",
        json_data={"rejection_reason_id": rejection_reason_id},
    )


async def hire_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    start_date: str | None = None,
    opening_id: int | None = None,
    close_reason_id: int | None = None,
) -> dict[str, Any]:
    """Hire an application (mark candidate as hired for this job)."""
    data: dict[str, Any] = {}
    if start_date:
        data["start_date"] = start_date
    if opening_id:
        data["opening_id"] = opening_id
    if close_reason_id:
        data["close_reason_id"] = close_reason_id
    return await client.harvest_post(
        f"applications/{application_id}/hire", json_data=data
    )


async def convert_prospect(
    client: GreenhouseClient,
    *,
    application_id: int,
    job_id: int,
) -> dict[str, Any]:
    """Convert a prospect application to a candidate application."""
    return await client.harvest_patch(
        f"applications/{application_id}/convert_to_candidate",
        json_data={"job_id": job_id},
    )


async def add_attachment_to_application(
    client: GreenhouseClient,
    *,
    application_id: int,
    filename: str,
    type: str,
    content: str | None = None,
    url: str | None = None,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    """Add an attachment to an application."""
    data: dict[str, Any] = {"filename": filename, "type": type, "content_type": content_type}
    if content:
        data["content"] = content
    if url:
        data["url"] = url
    return await client.harvest_post(
        f"applications/{application_id}/attachments", json_data=data
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/harvest/test_applications.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/greenhouse_mcp/harvest/applications.py tests/harvest/test_applications.py
git commit -m "Add applications module with 14 harvest tools"
```

---

### Task 7: Harvest — Jobs, Job Posts, Job Stages, Job Openings

**Files:**
- Create: `src/greenhouse_mcp/harvest/jobs.py`
- Create: `src/greenhouse_mcp/harvest/job_posts.py`
- Create: `src/greenhouse_mcp/harvest/job_stages.py`
- Create: `src/greenhouse_mcp/harvest/job_openings.py`
- Create: `tests/harvest/test_jobs.py`

- [ ] **Step 1: Write tests**

`tests/harvest/test_jobs.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@respx.mock
async def test_list_jobs():
    from greenhouse_mcp.harvest.jobs import list_jobs

    respx.get(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "SWE"}])
    )
    client = GreenhouseClient(api_key="test")
    result = await list_jobs(client)
    assert result["items"] == [{"id": 1, "name": "SWE"}]


@respx.mock
async def test_create_job():
    from greenhouse_mcp.harvest.jobs import create_job

    respx.post(f"{HARVEST_BASE}/jobs").mock(
        return_value=httpx.Response(201, json={"id": 10})
    )
    client = GreenhouseClient(api_key="test")
    result = await create_job(client, template_job_id=1, number_of_openings=2, job_post_name="SWE")
    assert result["id"] == 10


@respx.mock
async def test_list_job_posts_for_job():
    from greenhouse_mcp.harvest.job_posts import list_job_posts_for_job

    respx.get(f"{HARVEST_BASE}/jobs/1/job_posts").mock(
        return_value=httpx.Response(200, json=[{"id": 5}])
    )
    client = GreenhouseClient(api_key="test")
    result = await list_job_posts_for_job(client, job_id=1)
    assert result["items"] == [{"id": 5}]


@respx.mock
async def test_list_job_stages_for_job():
    from greenhouse_mcp.harvest.job_stages import list_job_stages_for_job

    respx.get(f"{HARVEST_BASE}/jobs/1/stages").mock(
        return_value=httpx.Response(200, json=[{"id": 100, "name": "Phone Screen"}])
    )
    client = GreenhouseClient(api_key="test")
    result = await list_job_stages_for_job(client, job_id=1)
    assert result["items"] == [{"id": 100, "name": "Phone Screen"}]


@respx.mock
async def test_create_job_opening():
    from greenhouse_mcp.harvest.job_openings import create_job_opening

    respx.post(f"{HARVEST_BASE}/jobs/1/openings").mock(
        return_value=httpx.Response(201, json={"id": 200})
    )
    client = GreenhouseClient(api_key="test")
    result = await create_job_opening(client, job_id=1)
    assert result["id"] == 200
```

- [ ] **Step 2: Implement all four modules**

`src/greenhouse_mcp/harvest/jobs.py`:
```python
"""Harvest API — Job tools (4 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_jobs(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    status: str | None = None,
    department_id: int | None = None,
    office_id: int | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all jobs. Filter by status (open, closed, draft), department, or office."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if status:
        params["status"] = status
    if department_id:
        params["department_id"] = department_id
    if office_id:
        params["office_id"] = office_id
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    return await client.harvest_get("jobs", params=params, paginate=paginate)


async def get_job(client: GreenhouseClient, *, job_id: int) -> dict[str, Any]:
    """Get a single job by ID."""
    return await client.harvest_get(f"jobs/{job_id}")


async def create_job(
    client: GreenhouseClient,
    *,
    template_job_id: int,
    number_of_openings: int = 1,
    job_post_name: str | None = None,
    job_name: str | None = None,
    department_id: int | None = None,
    office_ids: list[int] | None = None,
    requisition_id: str | None = None,
) -> dict[str, Any]:
    """Create a new job from a template job."""
    data: dict[str, Any] = {
        "template_job_id": template_job_id,
        "number_of_openings": number_of_openings,
    }
    if job_post_name:
        data["job_post_name"] = job_post_name
    if job_name:
        data["job_name"] = job_name
    if department_id:
        data["department_id"] = department_id
    if office_ids:
        data["office_ids"] = office_ids
    if requisition_id:
        data["requisition_id"] = requisition_id
    return await client.harvest_post("jobs", json_data=data)


async def update_job(
    client: GreenhouseClient,
    *,
    job_id: int,
    name: str | None = None,
    status: str | None = None,
    department_id: int | None = None,
    office_ids: list[int] | None = None,
    requisition_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update a job. Use status='open' or 'closed' to open/close."""
    data: dict[str, Any] = {}
    if name:
        data["name"] = name
    if status:
        data["status"] = status
    if department_id:
        data["department_id"] = department_id
    if office_ids:
        data["office_ids"] = office_ids
    if requisition_id:
        data["requisition_id"] = requisition_id
    if notes:
        data["notes"] = notes
    return await client.harvest_patch(f"jobs/{job_id}", json_data=data)
```

`src/greenhouse_mcp/harvest/job_posts.py`:
```python
"""Harvest API — Job Post tools (7 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_posts(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    live: bool | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all job posts."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if live is not None:
        params["live"] = str(live).lower()
    return await client.harvest_get("job_posts", params=params, paginate=paginate)


async def list_job_posts_for_job(
    client: GreenhouseClient, *, job_id: int
) -> dict[str, Any]:
    """List job posts for a specific job."""
    return await client.harvest_get(f"jobs/{job_id}/job_posts")


async def get_job_post(
    client: GreenhouseClient, *, job_post_id: int
) -> dict[str, Any]:
    """Get a single job post."""
    return await client.harvest_get(f"job_posts/{job_post_id}")


async def get_job_post_for_job(
    client: GreenhouseClient, *, job_id: int, job_post_id: int
) -> dict[str, Any]:
    """Get a specific job post for a specific job."""
    return await client.harvest_get(f"jobs/{job_id}/job_posts/{job_post_id}")


async def get_job_post_custom_locations(
    client: GreenhouseClient, *, job_post_id: int
) -> dict[str, Any]:
    """Get custom location options for a job post."""
    return await client.harvest_get(f"job_posts/{job_post_id}/custom_locations")


async def update_job_post(
    client: GreenhouseClient,
    *,
    job_post_id: int,
    title: str | None = None,
    location: str | None = None,
    content: str | None = None,
) -> dict[str, Any]:
    """Update a job post."""
    data: dict[str, Any] = {}
    if title:
        data["title"] = title
    if location:
        data["location"] = location
    if content:
        data["content"] = content
    return await client.harvest_patch(f"job_posts/{job_post_id}", json_data=data)


async def update_job_post_status(
    client: GreenhouseClient,
    *,
    job_post_id: int,
    status: str,
) -> dict[str, Any]:
    """Update job post status (live or offline)."""
    return await client.harvest_patch(
        f"job_posts/{job_post_id}", json_data={"status": status}
    )
```

`src/greenhouse_mcp/harvest/job_stages.py`:
```python
"""Harvest API — Job Stage tools (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_stages(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all job stages across all jobs."""
    return await client.harvest_get(
        "job_stages", params={"per_page": per_page, "page": page}, paginate=paginate
    )


async def list_job_stages_for_job(
    client: GreenhouseClient, *, job_id: int
) -> dict[str, Any]:
    """List stages for a specific job."""
    return await client.harvest_get(f"jobs/{job_id}/stages")


async def get_job_stage(
    client: GreenhouseClient, *, job_stage_id: int
) -> dict[str, Any]:
    """Get a single job stage by ID."""
    return await client.harvest_get(f"job_stages/{job_stage_id}")
```

`src/greenhouse_mcp/harvest/job_openings.py`:
```python
"""Harvest API — Job Opening tools (5 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_openings(
    client: GreenhouseClient,
    *,
    job_id: int,
    status: str | None = None,
) -> dict[str, Any]:
    """List openings for a job. Filter by status (open, closed)."""
    params: dict[str, Any] = {}
    if status:
        params["status"] = status
    return await client.harvest_get(f"jobs/{job_id}/openings", params=params)


async def get_job_opening(
    client: GreenhouseClient, *, job_id: int, opening_id: int
) -> dict[str, Any]:
    """Get a single opening for a job."""
    return await client.harvest_get(f"jobs/{job_id}/openings/{opening_id}")


async def create_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: str | None = None,
    status: str | None = None,
    close_reason_id: int | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new opening for a job."""
    data: dict[str, Any] = {}
    if opening_id:
        data["opening_id"] = opening_id
    if status:
        data["status"] = status
    if close_reason_id:
        data["close_reason_id"] = close_reason_id
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_post(f"jobs/{job_id}/openings", json_data=data)


async def update_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: int,
    status: str | None = None,
    close_reason_id: int | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update a job opening."""
    data: dict[str, Any] = {}
    if status:
        data["status"] = status
    if close_reason_id:
        data["close_reason_id"] = close_reason_id
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"jobs/{job_id}/openings/{opening_id}", json_data=data
    )


async def delete_job_opening(
    client: GreenhouseClient, *, job_id: int, opening_id: int
) -> dict[str, Any]:
    """Delete a job opening."""
    return await client.harvest_delete(f"jobs/{job_id}/openings/{opening_id}")
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/harvest/test_jobs.py -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/greenhouse_mcp/harvest/jobs.py src/greenhouse_mcp/harvest/job_posts.py \
  src/greenhouse_mcp/harvest/job_stages.py src/greenhouse_mcp/harvest/job_openings.py \
  tests/harvest/test_jobs.py
git commit -m "Add jobs, job posts, job stages, job openings modules (19 tools)"
```

---

### Task 8: Harvest — Offers, Scorecards, Interviews

**Files:**
- Create: `src/greenhouse_mcp/harvest/offers.py`
- Create: `src/greenhouse_mcp/harvest/scorecards.py`
- Create: `src/greenhouse_mcp/harvest/interviews.py`

- [ ] **Step 1: Implement all three modules**

`src/greenhouse_mcp/harvest/offers.py`:
```python
"""Harvest API — Offer tools (5 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_offers(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all offers."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    return await client.harvest_get("offers", params=params, paginate=paginate)


async def list_offers_for_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """List all offers for a specific application."""
    return await client.harvest_get(f"applications/{application_id}/offers")


async def get_offer(
    client: GreenhouseClient, *, offer_id: int
) -> dict[str, Any]:
    """Get a single offer by ID."""
    return await client.harvest_get(f"offers/{offer_id}")


async def get_current_offer(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """Get the current offer for an application."""
    return await client.harvest_get(f"applications/{application_id}/offers/current_offer")


async def update_current_offer(
    client: GreenhouseClient,
    *,
    application_id: int,
    starts_at: str | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update the current offer for an application."""
    data: dict[str, Any] = {}
    if starts_at:
        data["starts_at"] = starts_at
    if custom_fields:
        data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"applications/{application_id}/offers/current_offer", json_data=data
    )
```

`src/greenhouse_mcp/harvest/scorecards.py`:
```python
"""Harvest API — Scorecard tools (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_scorecards(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all scorecards."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    return await client.harvest_get("scorecards", params=params, paginate=paginate)


async def list_scorecards_for_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """List scorecards for a specific application."""
    return await client.harvest_get(f"applications/{application_id}/scorecards")


async def get_scorecard(
    client: GreenhouseClient, *, scorecard_id: int
) -> dict[str, Any]:
    """Get a single scorecard by ID."""
    return await client.harvest_get(f"scorecards/{scorecard_id}")
```

`src/greenhouse_mcp/harvest/interviews.py`:
```python
"""Harvest API — Scheduled Interview tools (6 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_interviews(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all scheduled interviews."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    return await client.harvest_get("scheduled_interviews", params=params, paginate=paginate)


async def list_interviews_for_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """List scheduled interviews for a specific application."""
    return await client.harvest_get(f"applications/{application_id}/scheduled_interviews")


async def get_interview(
    client: GreenhouseClient, *, interview_id: int
) -> dict[str, Any]:
    """Get a single scheduled interview by ID."""
    return await client.harvest_get(f"scheduled_interviews/{interview_id}")


async def create_interview(
    client: GreenhouseClient,
    *,
    application_id: int,
    interview_id: int,
    interviewer_ids: list[int],
    start: str,
    end: str,
) -> dict[str, Any]:
    """Create a scheduled interview for an application."""
    return await client.harvest_post(
        f"applications/{application_id}/scheduled_interviews",
        json_data={
            "interview_id": interview_id,
            "interviewer_ids": interviewer_ids,
            "start": start,
            "end": end,
        },
    )


async def update_interview(
    client: GreenhouseClient,
    *,
    interview_id: int,
    start: str | None = None,
    end: str | None = None,
    interviewer_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Update a scheduled interview."""
    data: dict[str, Any] = {}
    if start:
        data["start"] = start
    if end:
        data["end"] = end
    if interviewer_ids:
        data["interviewer_ids"] = interviewer_ids
    return await client.harvest_patch(
        f"scheduled_interviews/{interview_id}", json_data=data
    )


async def delete_interview(
    client: GreenhouseClient, *, interview_id: int
) -> dict[str, Any]:
    """Delete a scheduled interview."""
    return await client.harvest_delete(f"scheduled_interviews/{interview_id}")
```

- [ ] **Step 2: Write quick validation tests and run**

```bash
pytest tests/harvest/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 3: Commit**

```bash
git add src/greenhouse_mcp/harvest/offers.py src/greenhouse_mcp/harvest/scorecards.py \
  src/greenhouse_mcp/harvest/interviews.py
git commit -m "Add offers, scorecards, interviews modules (14 tools)"
```

---

### Task 9: Harvest — Users, User Permissions, User Roles

**Files:**
- Create: `src/greenhouse_mcp/harvest/users.py`
- Create: `src/greenhouse_mcp/harvest/user_permissions.py`
- Create: `src/greenhouse_mcp/harvest/user_roles.py`

- [ ] **Step 1: Implement all three modules**

`src/greenhouse_mcp/harvest/users.py`:
```python
"""Harvest API — User tools (8 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_users(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    email: str | None = None,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all users."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if email:
        params["email"] = email
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    return await client.harvest_get("users", params=params, paginate=paginate)


async def get_user(client: GreenhouseClient, *, user_id: int) -> dict[str, Any]:
    """Get a single user by ID."""
    return await client.harvest_get(f"users/{user_id}")


async def create_user(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    email: str,
    send_email: bool = True,
) -> dict[str, Any]:
    """Create a new user."""
    return await client.harvest_post(
        "users",
        json_data={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "send_email": send_email,
        },
    )


async def update_user(
    client: GreenhouseClient,
    *,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    """Update a user."""
    data: dict[str, Any] = {}
    if first_name:
        data["first_name"] = first_name
    if last_name:
        data["last_name"] = last_name
    return await client.harvest_patch(f"users/{user_id}", json_data=data)


async def disable_user(client: GreenhouseClient, *, user_id: int) -> dict[str, Any]:
    """Disable a user account."""
    return await client.harvest_patch(f"users/{user_id}/disable")


async def enable_user(client: GreenhouseClient, *, user_id: int) -> dict[str, Any]:
    """Enable a disabled user account."""
    return await client.harvest_patch(f"users/{user_id}/enable")


async def change_user_permission_level(
    client: GreenhouseClient,
    *,
    user_id: int,
    permission_level: str,
) -> dict[str, Any]:
    """Change a user's permission level."""
    return await client.harvest_patch(
        f"users/{user_id}/permissions/permission_level",
        json_data={"permission_level": permission_level},
    )


async def add_email_to_user(
    client: GreenhouseClient,
    *,
    user_id: int,
    email: str,
    send_verification: bool = True,
) -> dict[str, Any]:
    """Add an email address to a user."""
    return await client.harvest_post(
        f"users/{user_id}/email_addresses",
        json_data={"email": email, "send_verification": send_verification},
    )
```

`src/greenhouse_mcp/harvest/user_permissions.py`:
```python
"""Harvest API — User Permission tools (6 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_permissions(
    client: GreenhouseClient, *, user_id: int
) -> dict[str, Any]:
    """List job-level permissions for a user."""
    return await client.harvest_get(f"users/{user_id}/permissions/jobs")


async def add_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    job_id: int,
    user_role_id: int,
) -> dict[str, Any]:
    """Grant a user permission on a specific job."""
    return await client.harvest_post(
        f"users/{user_id}/permissions/jobs",
        json_data={"job_id": job_id, "user_role_id": user_role_id},
    )


async def remove_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    job_permission_id: int,
) -> dict[str, Any]:
    """Remove a user's permission on a specific job."""
    return await client.harvest_delete(
        f"users/{user_id}/permissions/jobs/{job_permission_id}"
    )


async def list_future_job_permissions(
    client: GreenhouseClient, *, user_id: int
) -> dict[str, Any]:
    """List future job permissions for a user."""
    return await client.harvest_get(f"users/{user_id}/permissions/future_jobs")


async def add_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    office_id: int | None = None,
    department_id: int | None = None,
    user_role_id: int,
) -> dict[str, Any]:
    """Grant a user future job permissions for a department/office."""
    data: dict[str, Any] = {"user_role_id": user_role_id}
    if office_id:
        data["office_id"] = office_id
    if department_id:
        data["department_id"] = department_id
    return await client.harvest_post(
        f"users/{user_id}/permissions/future_jobs", json_data=data
    )


async def remove_future_job_permission(
    client: GreenhouseClient,
    *,
    user_id: int,
    future_job_permission_id: int,
) -> dict[str, Any]:
    """Remove a user's future job permission."""
    return await client.harvest_delete(
        f"users/{user_id}/permissions/future_jobs/{future_job_permission_id}"
    )
```

`src/greenhouse_mcp/harvest/user_roles.py`:
```python
"""Harvest API — User Role tools (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_user_roles(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """List all user roles."""
    return await client.harvest_get_cached(
        "user_roles", params={"per_page": per_page, "page": page}
    )
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add src/greenhouse_mcp/harvest/users.py src/greenhouse_mcp/harvest/user_permissions.py \
  src/greenhouse_mcp/harvest/user_roles.py
git commit -m "Add users, user permissions, user roles modules (15 tools)"
```

---

### Task 10: Harvest — Departments, Offices, Custom Fields, Education

**Files:**
- Create: `src/greenhouse_mcp/harvest/departments.py`
- Create: `src/greenhouse_mcp/harvest/offices.py`
- Create: `src/greenhouse_mcp/harvest/custom_fields.py`
- Create: `src/greenhouse_mcp/harvest/education.py`

- [ ] **Step 1: Implement all four modules**

`src/greenhouse_mcp/harvest/departments.py`:
```python
"""Harvest API — Department tools (4 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_departments(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all departments."""
    return await client.harvest_get_cached(
        "departments",
        params={"per_page": per_page, "page": page},
        paginate=paginate,
        force_refresh=force_refresh,
    )


async def get_department(
    client: GreenhouseClient, *, department_id: int
) -> dict[str, Any]:
    """Get a single department."""
    return await client.harvest_get(f"departments/{department_id}")


async def create_department(
    client: GreenhouseClient, *, name: str, parent_id: int | None = None
) -> dict[str, Any]:
    """Create a new department."""
    data: dict[str, Any] = {"name": name}
    if parent_id:
        data["parent_id"] = parent_id
    return await client.harvest_post("departments", json_data=data)


async def update_department(
    client: GreenhouseClient,
    *,
    department_id: int,
    name: str | None = None,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Update a department."""
    data: dict[str, Any] = {}
    if name:
        data["name"] = name
    if parent_id:
        data["parent_id"] = parent_id
    return await client.harvest_patch(f"departments/{department_id}", json_data=data)
```

`src/greenhouse_mcp/harvest/offices.py`:
```python
"""Harvest API — Office tools (4 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_offices(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all offices."""
    return await client.harvest_get_cached(
        "offices",
        params={"per_page": per_page, "page": page},
        paginate=paginate,
        force_refresh=force_refresh,
    )


async def get_office(
    client: GreenhouseClient, *, office_id: int
) -> dict[str, Any]:
    """Get a single office."""
    return await client.harvest_get(f"offices/{office_id}")


async def create_office(
    client: GreenhouseClient,
    *,
    name: str,
    parent_id: int | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Create a new office."""
    data: dict[str, Any] = {"name": name}
    if parent_id:
        data["parent_id"] = parent_id
    if location:
        data["location"] = location
    return await client.harvest_post("offices", json_data=data)


async def update_office(
    client: GreenhouseClient,
    *,
    office_id: int,
    name: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Update an office."""
    data: dict[str, Any] = {}
    if name:
        data["name"] = name
    if location:
        data["location"] = location
    return await client.harvest_patch(f"offices/{office_id}", json_data=data)
```

`src/greenhouse_mcp/harvest/custom_fields.py`:
```python
"""Harvest API — Custom Field tools (9 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_custom_fields(
    client: GreenhouseClient,
    *,
    field_type: str | None = None,
) -> dict[str, Any]:
    """List custom fields. Optionally filter by type (job, candidate, application, offer, etc.)."""
    params: dict[str, Any] = {}
    if field_type:
        params["field_type"] = field_type
    return await client.harvest_get("custom_fields", params=params)


async def get_custom_field(
    client: GreenhouseClient, *, custom_field_id: int
) -> dict[str, Any]:
    """Get a single custom field."""
    return await client.harvest_get(f"custom_fields/{custom_field_id}")


async def create_custom_field(
    client: GreenhouseClient,
    *,
    name: str,
    field_type: str,
    value_type: str,
    private: bool = False,
    generate_email_token: bool = False,
) -> dict[str, Any]:
    """Create a custom field."""
    return await client.harvest_post(
        "custom_fields",
        json_data={
            "name": name,
            "field_type": field_type,
            "value_type": value_type,
            "private": private,
            "generate_email_token": generate_email_token,
        },
    )


async def update_custom_field(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    name: str | None = None,
    private: bool | None = None,
) -> dict[str, Any]:
    """Update a custom field."""
    data: dict[str, Any] = {}
    if name:
        data["name"] = name
    if private is not None:
        data["private"] = private
    return await client.harvest_patch(f"custom_fields/{custom_field_id}", json_data=data)


async def delete_custom_field(
    client: GreenhouseClient, *, custom_field_id: int
) -> dict[str, Any]:
    """Delete a custom field."""
    return await client.harvest_delete(f"custom_fields/{custom_field_id}")


async def list_custom_field_options(
    client: GreenhouseClient, *, custom_field_id: int
) -> dict[str, Any]:
    """List options for a custom field."""
    return await client.harvest_get(f"custom_fields/{custom_field_id}/custom_field_options")


async def create_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create options for a custom field."""
    return await client.harvest_post(
        f"custom_fields/{custom_field_id}/custom_field_options",
        json_data={"options": options},
    )


async def update_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    options: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update options for a custom field."""
    return await client.harvest_patch(
        f"custom_fields/{custom_field_id}/custom_field_options",
        json_data={"options": options},
    )


async def delete_custom_field_options(
    client: GreenhouseClient,
    *,
    custom_field_id: int,
    option_ids: list[int],
) -> dict[str, Any]:
    """Delete options from a custom field."""
    return await client.harvest_delete(
        f"custom_fields/{custom_field_id}/custom_field_options"
    )
```

`src/greenhouse_mcp/harvest/education.py`:
```python
"""Harvest API — Education reference data (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_degrees(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all degree types."""
    return await client.harvest_get_cached(
        "degrees",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )


async def list_disciplines(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all academic disciplines."""
    return await client.harvest_get_cached(
        "disciplines",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )


async def list_schools(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all schools."""
    return await client.harvest_get_cached(
        "schools",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add src/greenhouse_mcp/harvest/departments.py src/greenhouse_mcp/harvest/offices.py \
  src/greenhouse_mcp/harvest/custom_fields.py src/greenhouse_mcp/harvest/education.py
git commit -m "Add departments, offices, custom fields, education modules (20 tools)"
```

---

### Task 11: Harvest — Remaining Small Modules

All remaining Harvest modules with 1-6 tools each: sources, rejection_reasons, email_templates, tags, activity_feed, eeoc, demographics, approvals, hiring_team, prospect_pools, close_reasons, tracking_links.

**Files:**
- Create: all 12 remaining harvest modules
- Create: `tests/harvest/test_simple_modules.py`

- [ ] **Step 1: Implement all small modules**

`src/greenhouse_mcp/harvest/sources.py`:
```python
"""Harvest API — Sources (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_sources(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all sources."""
    return await client.harvest_get_cached(
        "sources",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )
```

`src/greenhouse_mcp/harvest/rejection_reasons.py`:
```python
"""Harvest API — Rejection Reasons (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_rejection_reasons(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all rejection reasons."""
    return await client.harvest_get_cached(
        "rejection_reasons",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )
```

`src/greenhouse_mcp/harvest/email_templates.py`:
```python
"""Harvest API — Email Templates (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_email_templates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all email templates."""
    return await client.harvest_get_cached(
        "email_templates",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )


async def get_email_template(
    client: GreenhouseClient, *, email_template_id: int
) -> dict[str, Any]:
    """Get a single email template."""
    return await client.harvest_get(f"email_templates/{email_template_id}")
```

`src/greenhouse_mcp/harvest/tags.py`:
```python
"""Harvest API — Tag tools (6 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_tags(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all candidate tags."""
    return await client.harvest_get_cached(
        "tags/candidate",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )


async def create_tag(
    client: GreenhouseClient, *, name: str
) -> dict[str, Any]:
    """Create a new candidate tag."""
    return await client.harvest_post("tags/candidate", json_data={"name": name})


async def delete_tag(
    client: GreenhouseClient, *, tag_id: int
) -> dict[str, Any]:
    """Delete a candidate tag."""
    return await client.harvest_delete(f"tags/candidate/{tag_id}")


async def list_tags_on_candidate(
    client: GreenhouseClient, *, candidate_id: int
) -> dict[str, Any]:
    """List tags applied to a candidate."""
    return await client.harvest_get(f"candidates/{candidate_id}/tags")


async def add_tag_to_candidate(
    client: GreenhouseClient, *, candidate_id: int, tag_id: int
) -> dict[str, Any]:
    """Add a tag to a candidate."""
    return await client.harvest_put(
        f"candidates/{candidate_id}/tags/{tag_id}"
    )


async def remove_tag_from_candidate(
    client: GreenhouseClient, *, candidate_id: int, tag_id: int
) -> dict[str, Any]:
    """Remove a tag from a candidate."""
    return await client.harvest_delete(f"candidates/{candidate_id}/tags/{tag_id}")
```

`src/greenhouse_mcp/harvest/activity_feed.py`:
```python
"""Harvest API — Activity Feed (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_activity_feed(
    client: GreenhouseClient, *, candidate_id: int
) -> dict[str, Any]:
    """Get the activity feed for a candidate."""
    return await client.harvest_get(f"candidates/{candidate_id}/activity_feed")
```

`src/greenhouse_mcp/harvest/eeoc.py`:
```python
"""Harvest API — EEOC tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_eeoc(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all EEOC data."""
    return await client.harvest_get(
        "eeoc", params={"per_page": per_page, "page": page}, paginate=paginate
    )


async def get_eeoc_for_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """Get EEOC data for a specific application."""
    return await client.harvest_get(f"applications/{application_id}/eeoc")
```

`src/greenhouse_mcp/harvest/demographics.py`:
```python
"""Harvest API — Demographics tools (11 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_question_sets(client: GreenhouseClient) -> dict[str, Any]:
    """List all demographic question sets."""
    return await client.harvest_get("demographics/question_sets")


async def get_question_set(
    client: GreenhouseClient, *, question_set_id: int
) -> dict[str, Any]:
    """Get a single demographic question set."""
    return await client.harvest_get(f"demographics/question_sets/{question_set_id}")


async def list_questions(client: GreenhouseClient) -> dict[str, Any]:
    """List all demographic questions."""
    return await client.harvest_get("demographics/questions")


async def list_questions_for_question_set(
    client: GreenhouseClient, *, question_set_id: int
) -> dict[str, Any]:
    """List questions for a specific question set."""
    return await client.harvest_get(
        f"demographics/question_sets/{question_set_id}/questions"
    )


async def get_question(
    client: GreenhouseClient, *, question_id: int
) -> dict[str, Any]:
    """Get a single demographic question."""
    return await client.harvest_get(f"demographics/questions/{question_id}")


async def list_answer_options(client: GreenhouseClient) -> dict[str, Any]:
    """List all demographic answer options."""
    return await client.harvest_get("demographics/answer_options")


async def list_answer_options_for_question(
    client: GreenhouseClient, *, question_id: int
) -> dict[str, Any]:
    """List answer options for a specific question."""
    return await client.harvest_get(
        f"demographics/questions/{question_id}/answer_options"
    )


async def get_answer_option(
    client: GreenhouseClient, *, answer_option_id: int
) -> dict[str, Any]:
    """Get a single answer option."""
    return await client.harvest_get(f"demographics/answer_options/{answer_option_id}")


async def list_answers(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all demographic answers."""
    return await client.harvest_get(
        "demographics/answers",
        params={"per_page": per_page, "page": page},
        paginate=paginate,
    )


async def list_answers_for_application(
    client: GreenhouseClient, *, application_id: int
) -> dict[str, Any]:
    """List demographic answers for a specific application."""
    return await client.harvest_get(
        f"applications/{application_id}/demographics/answers"
    )


async def get_answer(
    client: GreenhouseClient, *, answer_id: int
) -> dict[str, Any]:
    """Get a single demographic answer."""
    return await client.harvest_get(f"demographics/answers/{answer_id}")
```

`src/greenhouse_mcp/harvest/approvals.py`:
```python
"""Harvest API — Approval tools (6 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_approvals_for_job(
    client: GreenhouseClient, *, job_id: int
) -> dict[str, Any]:
    """List approval flows for a job."""
    return await client.harvest_get(f"jobs/{job_id}/approval_flows")


async def get_approval_flow(
    client: GreenhouseClient, *, job_id: int, approval_flow_id: int
) -> dict[str, Any]:
    """Get a specific approval flow for a job."""
    return await client.harvest_get(
        f"jobs/{job_id}/approval_flows/{approval_flow_id}"
    )


async def request_approvals(
    client: GreenhouseClient, *, job_id: int, approval_flow_id: int
) -> dict[str, Any]:
    """Request approvals for a job."""
    return await client.harvest_post(
        f"jobs/{job_id}/approval_flows/{approval_flow_id}/request_approvals"
    )


async def list_pending_approvals(
    client: GreenhouseClient, *, user_id: int | None = None
) -> dict[str, Any]:
    """List all pending approvals, optionally for a specific user."""
    params: dict[str, Any] = {}
    if user_id:
        params["user_id"] = user_id
    return await client.harvest_get("approvals/pending", params=params)


async def replace_approver(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_flow_id: int,
    remove_user_id: int,
    add_user_id: int,
) -> dict[str, Any]:
    """Replace an approver in an approval group."""
    return await client.harvest_patch(
        f"jobs/{job_id}/approval_flows/{approval_flow_id}/approvers",
        json_data={"remove_user_id": remove_user_id, "add_user_id": add_user_id},
    )


async def create_or_replace_approval_flow(
    client: GreenhouseClient,
    *,
    job_id: int,
    approval_type: str,
    approver_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create or replace an approval flow for a job."""
    return await client.harvest_put(
        f"jobs/{job_id}/approval_flows",
        json_data={
            "approval_type": approval_type,
            "approver_groups": approver_groups,
        },
    )
```

`src/greenhouse_mcp/harvest/hiring_team.py`:
```python
"""Harvest API — Hiring Team tools (4 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_hiring_team(
    client: GreenhouseClient, *, job_id: int
) -> dict[str, Any]:
    """Get the hiring team for a job."""
    return await client.harvest_get(f"jobs/{job_id}/hiring_team")


async def replace_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: int,
    hiring_managers: list[dict[str, Any]] | None = None,
    sourcers: list[dict[str, Any]] | None = None,
    recruiters: list[dict[str, Any]] | None = None,
    coordinators: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Replace the entire hiring team for a job."""
    data: dict[str, Any] = {}
    if hiring_managers is not None:
        data["hiring_managers"] = hiring_managers
    if sourcers is not None:
        data["sourcers"] = sourcers
    if recruiters is not None:
        data["recruiters"] = recruiters
    if coordinators is not None:
        data["coordinators"] = coordinators
    return await client.harvest_put(f"jobs/{job_id}/hiring_team", json_data=data)


async def add_hiring_team_members(
    client: GreenhouseClient,
    *,
    job_id: int,
    hiring_managers: list[dict[str, Any]] | None = None,
    sourcers: list[dict[str, Any]] | None = None,
    recruiters: list[dict[str, Any]] | None = None,
    coordinators: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add members to the hiring team."""
    data: dict[str, Any] = {}
    if hiring_managers:
        data["hiring_managers"] = hiring_managers
    if sourcers:
        data["sourcers"] = sourcers
    if recruiters:
        data["recruiters"] = recruiters
    if coordinators:
        data["coordinators"] = coordinators
    return await client.harvest_post(f"jobs/{job_id}/hiring_team", json_data=data)


async def remove_hiring_team_member(
    client: GreenhouseClient,
    *,
    job_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Remove a member from the hiring team."""
    return await client.harvest_delete(f"jobs/{job_id}/hiring_team/members/{user_id}")
```

`src/greenhouse_mcp/harvest/prospect_pools.py`:
```python
"""Harvest API — Prospect Pool tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_prospect_pools(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all prospect pools."""
    return await client.harvest_get(
        "prospect_pools", params={"per_page": per_page, "page": page}, paginate=paginate
    )


async def get_prospect_pool(
    client: GreenhouseClient, *, prospect_pool_id: int
) -> dict[str, Any]:
    """Get a single prospect pool."""
    return await client.harvest_get(f"prospect_pools/{prospect_pool_id}")
```

`src/greenhouse_mcp/harvest/close_reasons.py`:
```python
"""Harvest API — Close Reasons (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_close_reasons(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all close reasons."""
    return await client.harvest_get_cached(
        "close_reasons",
        params={"per_page": per_page, "page": page},
        force_refresh=force_refresh,
    )
```

`src/greenhouse_mcp/harvest/tracking_links.py`:
```python
"""Harvest API — Tracking Links (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_tracking_link(
    client: GreenhouseClient, *, token: str
) -> dict[str, Any]:
    """Get tracking link data by token."""
    return await client.harvest_get(f"tracking_links/{token}")
```

- [ ] **Step 2: Write validation tests**

`tests/harvest/test_simple_modules.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"


@respx.mock
async def test_list_sources():
    from greenhouse_mcp.harvest.sources import list_sources

    respx.get(f"{HARVEST_BASE}/sources").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "LinkedIn"}])
    )
    result = await list_sources(GreenhouseClient(api_key="test"))
    assert result["items"] == [{"id": 1, "name": "LinkedIn"}]


@respx.mock
async def test_list_tags():
    from greenhouse_mcp.harvest.tags import list_tags

    respx.get(f"{HARVEST_BASE}/tags/candidate").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "VIP"}])
    )
    result = await list_tags(GreenhouseClient(api_key="test"))
    assert result["items"] == [{"id": 1, "name": "VIP"}]


@respx.mock
async def test_list_demographics_questions():
    from greenhouse_mcp.harvest.demographics import list_questions

    respx.get(f"{HARVEST_BASE}/demographics/questions").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    result = await list_questions(GreenhouseClient(api_key="test"))
    assert result["items"] == [{"id": 1}]


@respx.mock
async def test_get_hiring_team():
    from greenhouse_mcp.harvest.hiring_team import get_hiring_team

    respx.get(f"{HARVEST_BASE}/jobs/1/hiring_team").mock(
        return_value=httpx.Response(200, json={"hiring_managers": []})
    )
    result = await get_hiring_team(GreenhouseClient(api_key="test"), job_id=1)
    assert "items" in result or "hiring_managers" in result


@respx.mock
async def test_list_approvals_for_job():
    from greenhouse_mcp.harvest.approvals import list_approvals_for_job

    respx.get(f"{HARVEST_BASE}/jobs/1/approval_flows").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    result = await list_approvals_for_job(GreenhouseClient(api_key="test"), job_id=1)
    assert result["items"] == [{"id": 1}]
```

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/greenhouse_mcp/harvest/ tests/harvest/test_simple_modules.py
git commit -m "Add remaining harvest modules: tags, eeoc, demographics, approvals, etc. (41 tools)"
```

---

### Task 12: Job Board API Modules

**Files:**
- Create: all 7 job_board modules
- Create: `tests/test_job_board.py`

- [ ] **Step 1: Implement all job board modules**

`src/greenhouse_mcp/job_board/board.py`:
```python
"""Job Board API — Board metadata (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_board(client: GreenhouseClient) -> dict[str, Any]:
    """Get job board metadata (name, content, departments, offices)."""
    return await client.board_get("")
```

`src/greenhouse_mcp/job_board/jobs.py`:
```python
"""Job Board API — Published job tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_jobs(
    client: GreenhouseClient,
    *,
    content: bool = False,
) -> dict[str, Any]:
    """List all published jobs on the board."""
    params: dict[str, Any] = {}
    if content:
        params["content"] = "true"
    return await client.board_get("jobs", params=params)


async def get_board_job(
    client: GreenhouseClient, *, job_id: int, questions: bool = False
) -> dict[str, Any]:
    """Get a published job with optional application questions."""
    params: dict[str, Any] = {}
    if questions:
        params["questions"] = "true"
    return await client.board_get(f"jobs/{job_id}", params=params)
```

`src/greenhouse_mcp/job_board/departments.py`:
```python
"""Job Board API — Department tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_departments(client: GreenhouseClient) -> dict[str, Any]:
    """List departments on the job board."""
    return await client.board_get("departments")


async def get_board_department(
    client: GreenhouseClient, *, department_id: int
) -> dict[str, Any]:
    """Get a single department from the job board."""
    return await client.board_get(f"departments/{department_id}")
```

`src/greenhouse_mcp/job_board/offices.py`:
```python
"""Job Board API — Office tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_offices(client: GreenhouseClient) -> dict[str, Any]:
    """List offices on the job board."""
    return await client.board_get("offices")


async def get_board_office(
    client: GreenhouseClient, *, office_id: int
) -> dict[str, Any]:
    """Get a single office from the job board."""
    return await client.board_get(f"offices/{office_id}")
```

`src/greenhouse_mcp/job_board/prospects.py`:
```python
"""Job Board API — Prospect Post tools (2 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_prospect_post_sections(client: GreenhouseClient) -> dict[str, Any]:
    """List prospect post sections on the job board."""
    return await client.board_get("prospect_posts")


async def get_prospect_post_section(
    client: GreenhouseClient, *, section_id: int
) -> dict[str, Any]:
    """Get a single prospect post section."""
    return await client.board_get(f"prospect_posts/{section_id}")
```

`src/greenhouse_mcp/job_board/educations.py`:
```python
"""Job Board API — Education reference data (3 tools)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_board_degrees(client: GreenhouseClient) -> dict[str, Any]:
    """List degree types available on the job board."""
    return await client.board_get("education/degrees")


async def list_board_disciplines(client: GreenhouseClient) -> dict[str, Any]:
    """List academic disciplines available on the job board."""
    return await client.board_get("education/disciplines")


async def list_board_schools(client: GreenhouseClient) -> dict[str, Any]:
    """List schools available on the job board."""
    return await client.board_get("education/schools")
```

`src/greenhouse_mcp/job_board/applications.py`:
```python
"""Job Board API — Application submission (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def submit_application(
    client: GreenhouseClient,
    *,
    job_id: int,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None = None,
    resume: str | None = None,
    cover_letter: str | None = None,
    mapped_url_token: str | None = None,
) -> dict[str, Any]:
    """Submit an application through the job board. Requires API key for auth."""
    data: dict[str, Any] = {
        "job_id": job_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
    }
    if phone:
        data["phone"] = phone
    if resume:
        data["resume"] = resume
    if cover_letter:
        data["cover_letter"] = cover_letter
    if mapped_url_token:
        data["mapped_url_token"] = mapped_url_token
    return await client.board_post("applications", json_data=data)
```

- [ ] **Step 2: Write tests**

`tests/test_job_board.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards/test-board"


@respx.mock
async def test_get_board():
    from greenhouse_mcp.job_board.board import get_board

    respx.get(f"{BOARD_BASE}/").mock(
        return_value=httpx.Response(200, json={"name": "Acme Jobs"})
    )
    client = GreenhouseClient(board_token="test-board")
    result = await get_board(client)
    assert result["name"] == "Acme Jobs"


@respx.mock
async def test_list_board_jobs():
    from greenhouse_mcp.job_board.jobs import list_board_jobs

    respx.get(f"{BOARD_BASE}/jobs").mock(
        return_value=httpx.Response(200, json={"jobs": [{"id": 1}]})
    )
    client = GreenhouseClient(board_token="test-board")
    result = await list_board_jobs(client)
    assert "jobs" in result


@respx.mock
async def test_list_board_departments():
    from greenhouse_mcp.job_board.departments import list_board_departments

    respx.get(f"{BOARD_BASE}/departments").mock(
        return_value=httpx.Response(200, json={"departments": [{"id": 1}]})
    )
    client = GreenhouseClient(board_token="test-board")
    result = await list_board_departments(client)
    assert "departments" in result
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_job_board.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/greenhouse_mcp/job_board/ tests/test_job_board.py
git commit -m "Add job board API modules (13 tools)"
```

---

### Task 13: Ingestion API Modules

**Files:**
- Create: all 6 ingestion modules
- Create: `tests/test_ingestion.py`

- [ ] **Step 1: Implement all ingestion modules**

`src/greenhouse_mcp/ingestion/candidates.py`:
```python
"""Ingestion API — Post candidates (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def post_candidate(
    client: GreenhouseClient,
    *,
    first_name: str,
    last_name: str,
    email: str,
    job_id: int | None = None,
    phone: str | None = None,
    resume: str | None = None,
    source: str | None = None,
    prospect: bool = False,
) -> dict[str, Any]:
    """Submit a candidate or prospect via the Ingestion API."""
    data: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "prospect": prospect,
    }
    if job_id:
        data["job_id"] = job_id
    if phone:
        data["phone"] = phone
    if resume:
        data["resume"] = resume
    if source:
        data["source"] = source
    return await client.ingestion_post("candidates", json_data=data)
```

`src/greenhouse_mcp/ingestion/jobs.py`:
```python
"""Ingestion API — Retrieve jobs (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_jobs(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """Retrieve jobs visible to the partner via Ingestion API."""
    return await client.ingestion_get(
        "jobs", params={"per_page": per_page, "page": page}
    )
```

`src/greenhouse_mcp/ingestion/prospects.py`:
```python
"""Ingestion API — Retrieve prospect pools (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_prospect_pools(
    client: GreenhouseClient,
) -> dict[str, Any]:
    """Retrieve prospect pools via Ingestion API."""
    return await client.ingestion_get("prospect_pools")
```

`src/greenhouse_mcp/ingestion/users.py`:
```python
"""Ingestion API — Retrieve current user (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_current_user(client: GreenhouseClient) -> dict[str, Any]:
    """Retrieve the current partner user via Ingestion API."""
    return await client.ingestion_get("current_user")
```

`src/greenhouse_mcp/ingestion/tracking.py`:
```python
"""Ingestion API — Post tracking link (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def post_tracking_link(
    client: GreenhouseClient,
    *,
    job_id: int,
    source: str,
    referrer: str | None = None,
) -> dict[str, Any]:
    """Create a tracking link for a job."""
    data: dict[str, Any] = {"job_id": job_id, "source": source}
    if referrer:
        data["referrer"] = referrer
    return await client.ingestion_post("tracking_links", json_data=data)
```

`src/greenhouse_mcp/ingestion/retrieve.py`:
```python
"""Ingestion API — Retrieve candidates (1 tool)."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def retrieve_ingestion_candidates(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """Retrieve candidates submitted via the Ingestion API."""
    return await client.ingestion_get(
        "candidates", params={"per_page": per_page, "page": page}
    )
```

- [ ] **Step 2: Write tests**

`tests/test_ingestion.py`:
```python
import httpx
import respx

from greenhouse_mcp.client import GreenhouseClient

INGESTION_BASE = "https://api.greenhouse.io/v1/partner"


@respx.mock
async def test_post_candidate():
    from greenhouse_mcp.ingestion.candidates import post_candidate

    respx.post(f"{INGESTION_BASE}/candidates").mock(
        return_value=httpx.Response(200, json={"id": 1, "status": "success"})
    )
    client = GreenhouseClient(api_key="test", on_behalf_of="user@co.com")
    result = await post_candidate(
        client, first_name="Ada", last_name="Lovelace", email="ada@example.com"
    )
    assert result["status"] == "success"


@respx.mock
async def test_retrieve_jobs():
    from greenhouse_mcp.ingestion.jobs import retrieve_ingestion_jobs

    respx.get(f"{INGESTION_BASE}/jobs").mock(
        return_value=httpx.Response(200, json=[{"id": 1}])
    )
    client = GreenhouseClient(api_key="test", on_behalf_of="user@co.com")
    result = await retrieve_ingestion_jobs(client)
    assert isinstance(result, (dict, list))
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_ingestion.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/greenhouse_mcp/ingestion/ tests/test_ingestion.py
git commit -m "Add ingestion API modules (6 tools)"
```

---

### Task 14: Tool Registration in server.py

Now wire all modules into the FastMCP server. Each function becomes an `@mcp.tool`.

**Files:**
- Modify: `src/greenhouse_mcp/server.py`

- [ ] **Step 1: Update server.py to register all tools**

Replace the `create_server` function in `src/greenhouse_mcp/server.py`:

```python
def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all tools."""
    mcp = FastMCP("Greenhouse")
    mcp.description = "Comprehensive MCP server for the full Greenhouse API (~156 tools)"

    # --- Harvest tools ---
    from greenhouse_mcp.harvest import (
        activity_feed, applications, approvals, candidates, close_reasons,
        custom_fields, demographics, departments, education, eeoc,
        email_templates, hiring_team, interviews, job_openings, job_posts,
        job_stages, jobs, offers, offices, prospect_pools, rejection_reasons,
        scorecards, sources, tags, tracking_links, user_permissions, user_roles,
        users,
    )

    # Register each function as an MCP tool via a wrapper that injects the client.
    # Pattern: for each async function in a module, wrap it to auto-inject get_client().

    import functools
    import inspect

    harvest_modules = [
        candidates, applications, jobs, job_posts, job_stages, job_openings,
        offers, scorecards, interviews, users, user_permissions, departments,
        offices, custom_fields, sources, rejection_reasons, email_templates,
        tags, activity_feed, eeoc, demographics, approvals, hiring_team,
        prospect_pools, close_reasons, tracking_links, user_roles, education,
    ]

    from greenhouse_mcp.job_board import (
        applications as board_applications,
        board, departments as board_departments, educations as board_educations,
        jobs as board_jobs, offices as board_offices, prospects as board_prospects,
    )

    board_modules = [
        board, board_jobs, board_departments, board_offices,
        board_prospects, board_educations, board_applications,
    ]

    from greenhouse_mcp.ingestion import (
        candidates as ing_candidates, jobs as ing_jobs, prospects as ing_prospects,
        retrieve as ing_retrieve, tracking as ing_tracking, users as ing_users,
    )

    ingestion_modules = [
        ing_candidates, ing_jobs, ing_prospects, ing_retrieve,
        ing_tracking, ing_users,
    ]

    all_modules = harvest_modules + board_modules + ingestion_modules

    for module in all_modules:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue

            # Create a wrapper that injects the client
            @mcp.tool(name=name, description=fn.__doc__ or name)
            @functools.wraps(fn)
            async def tool_wrapper(*args, _fn=fn, **kwargs):
                client = get_client()
                return await _fn(client, *args, **kwargs)

    return mcp
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/ -v
```

- [ ] **Step 3: Commit**

```bash
git add src/greenhouse_mcp/server.py
git commit -m "Register all harvest, job board, and ingestion tools in FastMCP server"
```

---

### Task 15: Webhook Receiver — SQLite Models and HMAC Verification

**Files:**
- Create: `src/greenhouse_mcp/webhook_receiver/models.py`
- Create: `tests/test_webhook_receiver.py`

- [ ] **Step 1: Write failing tests**

`tests/test_webhook_receiver.py`:
```python
import hashlib
import hmac
import json
import sqlite3

import pytest

from greenhouse_mcp.webhook_receiver.models import WebhookDB


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test_webhooks.db"
    return WebhookDB(str(db_path))


class TestWebhookDB:
    def test_create_rule(self, db):
        rule_id = db.create_rule(
            event_type="hire_candidate",
            action_type="forward",
            action_config={"url": "https://hooks.slack.com/services/xxx"},
        )
        assert rule_id > 0

    def test_list_rules(self, db):
        db.create_rule(event_type="hire_candidate", action_type="forward", action_config={})
        db.create_rule(event_type="reject_candidate", action_type="log", action_config={})
        rules = db.list_rules()
        assert len(rules) == 2

    def test_update_rule(self, db):
        rule_id = db.create_rule(event_type="hire_candidate", action_type="log", action_config={})
        db.update_rule(rule_id, active=False)
        rules = db.list_rules()
        assert rules[0]["active"] == 0

    def test_delete_rule(self, db):
        rule_id = db.create_rule(event_type="hire_candidate", action_type="log", action_config={})
        db.delete_rule(rule_id)
        assert len(db.list_rules()) == 0

    def test_log_event(self, db):
        db.log_event(
            event_type="hire_candidate",
            payload={"action": "hire_candidate", "payload": {"id": 1}},
        )
        events = db.list_recent_events(limit=10)
        assert len(events) == 1
        assert events[0]["event_type"] == "hire_candidate"

    def test_get_matching_rules(self, db):
        db.create_rule(event_type="hire_candidate", action_type="forward", action_config={})
        db.create_rule(event_type="*", action_type="log", action_config={})
        db.create_rule(event_type="reject_candidate", action_type="forward", action_config={})
        matches = db.get_matching_rules("hire_candidate")
        assert len(matches) == 2  # specific + wildcard

    def test_store_and_get_secret(self, db):
        db.store_secret("my-secret-key")
        assert db.get_secret() == "my-secret-key"


class TestHMACVerification:
    def test_verify_signature(self):
        from greenhouse_mcp.webhook_receiver.receiver import verify_signature

        secret = "my-secret"
        body = json.dumps({"action": "hire_candidate"}).encode()
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        header = f"sha256 {expected}"
        assert verify_signature(body, header, secret) is True

    def test_reject_bad_signature(self):
        from greenhouse_mcp.webhook_receiver.receiver import verify_signature

        assert verify_signature(b"body", "sha256 wrong", "secret") is False
```

- [ ] **Step 2: Implement models.py**

`src/greenhouse_mcp/webhook_receiver/models.py`:
```python
"""SQLite database for webhook rules and event log."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any


class WebhookDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    filter_config TEXT DEFAULT '{}',
                    action_type TEXT NOT NULL,
                    action_config TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    received_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    secret_key TEXT NOT NULL
                )
            """)

    def create_rule(
        self,
        *,
        event_type: str,
        action_type: str,
        action_config: dict[str, Any],
        filter_config: dict[str, Any] | None = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO rules (event_type, filter_config, action_type, action_config, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    event_type,
                    json.dumps(filter_config or {}),
                    action_type,
                    json.dumps(action_config),
                    time.time(),
                ),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def list_rules(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM rules ORDER BY id").fetchall()
            return [dict(row) for row in rows]

    def update_rule(
        self,
        rule_id: int,
        *,
        event_type: str | None = None,
        action_type: str | None = None,
        action_config: dict[str, Any] | None = None,
        filter_config: dict[str, Any] | None = None,
        active: bool | None = None,
    ) -> None:
        updates: list[str] = []
        values: list[Any] = []
        if event_type is not None:
            updates.append("event_type = ?")
            values.append(event_type)
        if action_type is not None:
            updates.append("action_type = ?")
            values.append(action_type)
        if action_config is not None:
            updates.append("action_config = ?")
            values.append(json.dumps(action_config))
        if filter_config is not None:
            updates.append("filter_config = ?")
            values.append(json.dumps(filter_config))
        if active is not None:
            updates.append("active = ?")
            values.append(int(active))

        if updates:
            values.append(rule_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"UPDATE rules SET {', '.join(updates)} WHERE id = ?", values
                )

    def delete_rule(self, rule_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))

    def get_matching_rules(self, event_type: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM rules WHERE active = 1 AND (event_type = ? OR event_type = '*')",
                (event_type,),
            ).fetchall()
            return [dict(row) for row in rows]

    def log_event(self, *, event_type: str, payload: dict[str, Any]) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO events (event_type, payload, received_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(payload), time.time()),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def list_recent_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM events ORDER BY received_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def store_secret(self, secret_key: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO secrets (id, secret_key) VALUES (1, ?)",
                (secret_key,),
            )

    def get_secret(self) -> str | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT secret_key FROM secrets WHERE id = 1").fetchone()
            return row[0] if row else None
```

- [ ] **Step 3: Implement receiver.py (HMAC + FastAPI app)**

`src/greenhouse_mcp/webhook_receiver/receiver.py`:
```python
"""FastAPI webhook receiver with HMAC verification and event routing."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, Request, Response

from greenhouse_mcp.webhook_receiver.models import WebhookDB

app = FastAPI(title="Greenhouse Webhook Receiver")

_db: WebhookDB | None = None


def get_db() -> WebhookDB:
    global _db
    if _db is None:
        db_path = os.environ.get(
            "WEBHOOK_DB_PATH",
            str(Path.home() / ".greenhouse-mcp" / "webhooks.db"),
        )
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _db = WebhookDB(db_path)
    return _db


def verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify Greenhouse HMAC-SHA256 signature."""
    if not signature_header.startswith("sha256 "):
        return False
    expected = signature_header[7:]  # strip "sha256 "
    computed = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, expected)


async def execute_action(rule: dict[str, Any], payload: dict[str, Any]) -> None:
    """Execute the action defined in a routing rule."""
    action_type = rule["action_type"]
    action_config = json.loads(rule["action_config"]) if isinstance(rule["action_config"], str) else rule["action_config"]

    if action_type == "forward":
        url = action_config.get("url")
        if url:
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload, timeout=10.0)
    elif action_type == "log":
        pass  # Already logged in the events table


@app.post("/webhooks/greenhouse")
async def receive_webhook(
    request: Request,
    signature: str = Header(None, alias="Signature"),
) -> Response:
    """Receive and process a Greenhouse webhook."""
    db = get_db()
    body = await request.body()

    # Verify signature
    secret = db.get_secret()
    if secret and signature:
        if not verify_signature(body, signature, secret):
            return Response(status_code=401, content="Invalid signature")

    # Parse payload
    payload = json.loads(body)
    event_type = payload.get("action", "unknown")

    # Log the event
    db.log_event(event_type=event_type, payload=payload)

    # Find and execute matching rules
    rules = db.get_matching_rules(event_type)
    for rule in rules:
        await execute_action(rule, payload)

    return Response(status_code=200, content="OK")


def main() -> None:
    """CLI entry point for the webhook receiver."""
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

`src/greenhouse_mcp/webhook_receiver/actions.py`:
```python
"""Webhook action executors — kept thin, main logic in receiver.py."""
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_webhook_receiver.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/greenhouse_mcp/webhook_receiver/ tests/test_webhook_receiver.py
git commit -m "Add webhook receiver with SQLite models, HMAC verification, and event routing"
```

---

### Task 16: Webhook MCP Tools

**Files:**
- Create: `src/greenhouse_mcp/webhook_tools/rules.py`
- Create: `src/greenhouse_mcp/webhook_tools/events.py`
- Create: `src/greenhouse_mcp/webhook_tools/testing.py`
- Create: `src/greenhouse_mcp/webhook_tools/setup.py`
- Create: `tests/test_webhook_tools.py`

- [ ] **Step 1: Implement all webhook tool modules**

`src/greenhouse_mcp/webhook_tools/rules.py`:
```python
"""MCP tools for managing webhook routing rules."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_list_rules(db: WebhookDB) -> dict[str, Any]:
    """List all webhook routing rules."""
    rules = db.list_rules()
    return {"rules": rules, "total": len(rules)}


async def webhook_create_rule(
    db: WebhookDB,
    *,
    event_type: str,
    action_type: str,
    action_url: str | None = None,
    filter_field: str | None = None,
    filter_value: str | None = None,
) -> dict[str, Any]:
    """Create a webhook routing rule. event_type can be a specific event or '*' for all.
    action_type is 'forward' (requires action_url) or 'log'."""
    action_config: dict[str, Any] = {}
    if action_url:
        action_config["url"] = action_url

    filter_config: dict[str, Any] = {}
    if filter_field and filter_value:
        filter_config[filter_field] = filter_value

    rule_id = db.create_rule(
        event_type=event_type,
        action_type=action_type,
        action_config=action_config,
        filter_config=filter_config,
    )
    return {"rule_id": rule_id, "status": "created"}


async def webhook_update_rule(
    db: WebhookDB,
    *,
    rule_id: int,
    event_type: str | None = None,
    action_type: str | None = None,
    action_url: str | None = None,
    active: bool | None = None,
) -> dict[str, Any]:
    """Update an existing webhook routing rule."""
    action_config = {"url": action_url} if action_url else None
    db.update_rule(
        rule_id,
        event_type=event_type,
        action_type=action_type,
        action_config=action_config,
        active=active,
    )
    return {"rule_id": rule_id, "status": "updated"}


async def webhook_delete_rule(
    db: WebhookDB, *, rule_id: int
) -> dict[str, Any]:
    """Delete a webhook routing rule."""
    db.delete_rule(rule_id)
    return {"rule_id": rule_id, "status": "deleted"}
```

`src/greenhouse_mcp/webhook_tools/events.py`:
```python
"""MCP tools for listing webhook events."""

from __future__ import annotations

from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB

WEBHOOK_EVENT_TYPES = {
    "new_candidate_application": "A new application is created",
    "delete_application": "An application is deleted",
    "application_updated": "An application is updated",
    "offer_created": "An offer is created",
    "offer_approved": "An offer is approved",
    "offer_updated": "An offer is updated",
    "offer_deleted": "An offer is deleted",
    "new_prospect_application": "A new prospect is created",
    "delete_candidate": "A candidate is deleted",
    "hire_candidate": "A candidate is hired",
    "merge_candidate": "Two candidates are merged",
    "candidate_stage_change": "A candidate moves to a new stage",
    "unhire_candidate": "A hire is reverted",
    "reject_candidate": "A candidate is rejected",
    "unreject_candidate": "A rejection is reverted",
    "update_candidate": "A candidate profile is updated",
    "candidate_anonymized": "A candidate is anonymized (GDPR)",
    "interview_deleted": "A scheduled interview is deleted",
    "scorecard_deleted": "A scorecard is deleted",
    "job_created": "A new job is created",
    "job_deleted": "A job is deleted",
    "job_updated": "A job is updated",
    "job_approved": "A job is approved",
    "job_post_created": "A job post is created",
    "job_post_updated": "A job post is updated",
    "job_post_deleted": "A job post is deleted",
    "job_interview_stage_deleted": "A job stage is deleted",
    "department_deleted": "A department is deleted",
    "office_deleted": "An office is deleted",
}


async def webhook_list_events() -> dict[str, Any]:
    """List all 27+ Greenhouse webhook event types with descriptions."""
    return {
        "events": [
            {"event_type": k, "description": v}
            for k, v in WEBHOOK_EVENT_TYPES.items()
        ],
        "total": len(WEBHOOK_EVENT_TYPES),
    }


async def webhook_list_recent(
    db: WebhookDB, *, limit: int = 50
) -> dict[str, Any]:
    """List recent webhook events received by the receiver."""
    events = db.list_recent_events(limit=limit)
    return {"events": events, "total": len(events)}
```

`src/greenhouse_mcp/webhook_tools/testing.py`:
```python
"""MCP tool for testing webhook rules."""

from __future__ import annotations

import json
from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_test_rule(
    db: WebhookDB, *, rule_id: int
) -> dict[str, Any]:
    """Dry-run a rule against the most recent matching event. Shows what would happen."""
    rules = db.list_rules()
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if not rule:
        return {"error": f"Rule {rule_id} not found"}

    events = db.list_recent_events(limit=100)
    matching_event = None
    for event in events:
        if rule["event_type"] == "*" or event["event_type"] == rule["event_type"]:
            matching_event = event
            break

    if not matching_event:
        return {"error": f"No recent events matching event_type '{rule['event_type']}'"}

    action_config = json.loads(rule["action_config"]) if isinstance(rule["action_config"], str) else rule["action_config"]

    return {
        "rule": rule,
        "matched_event": matching_event,
        "would_execute": {
            "action_type": rule["action_type"],
            "action_config": action_config,
        },
        "dry_run": True,
    }
```

`src/greenhouse_mcp/webhook_tools/setup.py`:
```python
"""MCP tool for generating Greenhouse webhook setup instructions."""

from __future__ import annotations

import secrets
from typing import Any

from greenhouse_mcp.webhook_receiver.models import WebhookDB


async def webhook_setup_guide(
    db: WebhookDB,
    *,
    receiver_url: str,
    events: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a setup guide for configuring a Greenhouse webhook.
    Produces the exact values to enter in Greenhouse UI and stores the secret key."""
    secret_key = secrets.token_hex(32)
    db.store_secret(secret_key)

    webhook_url = f"{receiver_url.rstrip('/')}/webhooks/greenhouse"

    if events is None:
        events = ["*"]  # subscribe to all

    return {
        "setup_instructions": {
            "step_1": "Go to Greenhouse > Configure > Dev Center > Webhooks",
            "step_2": "Click 'Create New Webhook'",
            "step_3_name": "Give it a name (e.g., 'MCP Webhook Receiver')",
            "step_4_url": f"Set the Endpoint URL to: {webhook_url}",
            "step_5_secret": f"Set the Secret Key to: {secret_key}",
            "step_6_events": f"Subscribe to events: {', '.join(events) if events != ['*'] else 'All events'}",
            "step_7": "Click 'Create Webhook' — Greenhouse will ping the URL to verify",
        },
        "values_to_copy": {
            "endpoint_url": webhook_url,
            "secret_key": secret_key,
            "events": events,
        },
        "note": "The secret key has been stored in the webhook database. "
        "Make sure the receiver is running before creating the webhook in Greenhouse.",
    }
```

- [ ] **Step 2: Write tests**

`tests/test_webhook_tools.py`:
```python
import pytest

from greenhouse_mcp.webhook_receiver.models import WebhookDB


@pytest.fixture
def db(tmp_path):
    return WebhookDB(str(tmp_path / "test.db"))


async def test_webhook_create_and_list_rules(db):
    from greenhouse_mcp.webhook_tools.rules import webhook_create_rule, webhook_list_rules

    await webhook_create_rule(
        db, event_type="hire_candidate", action_type="forward",
        action_url="https://hooks.slack.com/xxx"
    )
    result = await webhook_list_rules(db)
    assert result["total"] == 1


async def test_webhook_list_events():
    from greenhouse_mcp.webhook_tools.events import webhook_list_events

    result = await webhook_list_events()
    assert result["total"] >= 27


async def test_webhook_setup_guide(db):
    from greenhouse_mcp.webhook_tools.setup import webhook_setup_guide

    result = await webhook_setup_guide(db, receiver_url="https://my-app.fly.dev")
    assert "webhooks/greenhouse" in result["values_to_copy"]["endpoint_url"]
    assert len(result["values_to_copy"]["secret_key"]) == 64  # 32 bytes hex
    assert db.get_secret() is not None


async def test_webhook_test_rule_no_events(db):
    from greenhouse_mcp.webhook_tools.rules import webhook_create_rule
    from greenhouse_mcp.webhook_tools.testing import webhook_test_rule

    result = await webhook_create_rule(
        db, event_type="hire_candidate", action_type="log"
    )
    test_result = await webhook_test_rule(db, rule_id=result["rule_id"])
    assert "error" in test_result  # no events to match against
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_webhook_tools.py -v
```

- [ ] **Step 4: Register webhook tools in server.py**

Add to the `create_server` function in `server.py`, after the API tool registration:

```python
    # --- Webhook tools ---
    from greenhouse_mcp.webhook_tools import rules, events, testing, setup
    from greenhouse_mcp.webhook_receiver.models import WebhookDB
    from pathlib import Path
    import os

    def get_webhook_db() -> WebhookDB:
        db_path = os.environ.get(
            "WEBHOOK_DB_PATH",
            str(Path.home() / ".greenhouse-mcp" / "webhooks.db"),
        )
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return WebhookDB(db_path)

    webhook_modules_with_db = [rules, events, testing, setup]
    for module in webhook_modules_with_db:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_") or not name.startswith("webhook_"):
                continue

            @mcp.tool(name=name, description=fn.__doc__ or name)
            @functools.wraps(fn)
            async def webhook_tool_wrapper(*args, _fn=fn, **kwargs):
                # Inject db for functions that need it
                import inspect as _inspect
                sig = _inspect.signature(_fn)
                if "db" in sig.parameters:
                    return await _fn(get_webhook_db(), *args, **kwargs)
                return await _fn(*args, **kwargs)
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add src/greenhouse_mcp/webhook_tools/ tests/test_webhook_tools.py src/greenhouse_mcp/server.py
git commit -m "Add webhook management MCP tools (8 tools) and register in server"
```

---

### Task 17: CI Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check src/ tests/

      - name: Type check
        run: mypy src/greenhouse_mcp/ --ignore-missing-imports

      - name: Test
        run: pytest tests/ -v --tb=short
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "Add GitHub Actions CI: lint, type check, test on Python 3.10-3.12"
```

---

### Task 18: Update README and Finalize Package

**Files:**
- Modify: `README.md`
- Modify: `LICENSE`
- Create: `.env.example`

- [ ] **Step 1: Update .env.example**

`.env.example`:
```bash
# Required: at least one of these
GREENHOUSE_API_KEY=your-harvest-api-key
# GREENHOUSE_BOARD_TOKEN=your-board-url-slug

# Optional: required for Ingestion API
# GREENHOUSE_ON_BEHALF_OF=user@company.com

# Optional: webhook receiver settings
# WEBHOOK_DB_PATH=~/.greenhouse-mcp/webhooks.db
# PORT=8080
```

- [ ] **Step 2: Update LICENSE with correct author**

Ensure the LICENSE file has Ben Monopoli as the copyright holder.

- [ ] **Step 3: Write README.md**

Write a comprehensive README with:
- What it does (comprehensive Greenhouse MCP server, ~156 tools)
- Quick start (pip install, env vars, MCP config)
- Tool list by category (Harvest, Job Board, Ingestion, Webhooks)
- Webhook receiver setup instructions
- Development setup
- License (MIT)

- [ ] **Step 4: Run full test suite one final time**

```bash
pip install -e ".[dev]" && ruff check src/ tests/ && pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add README.md LICENSE .env.example
git commit -m "Update README, LICENSE, and env example for v0.2.0 release"
```

---

### Task 19: Integration Smoke Test

Verify the full server starts and tools are registered.

- [ ] **Step 1: Test server starts with API key**

```bash
GREENHOUSE_API_KEY=test-key python -c "
from greenhouse_mcp.server import mcp
print(f'Server name: {mcp.name}')
print(f'Tools registered: {len(mcp._tool_manager._tools)}')
assert len(mcp._tool_manager._tools) > 100, 'Expected 100+ tools'
print('OK')
"
```

Expected: prints tool count > 100 and "OK".

- [ ] **Step 2: Test server starts with board token only**

```bash
GREENHOUSE_BOARD_TOKEN=test-board python -c "
from greenhouse_mcp.server import get_client
client = get_client()
assert client.board_token == 'test-board'
assert client.api_key is None
print('Board token client OK')
"
```

- [ ] **Step 3: Test webhook receiver starts**

```bash
WEBHOOK_DB_PATH=/tmp/test-webhooks.db python -c "
from greenhouse_mcp.webhook_receiver.receiver import app
print(f'Webhook receiver routes: {[r.path for r in app.routes]}')
assert '/webhooks/greenhouse' in [r.path for r in app.routes]
print('OK')
"
```

- [ ] **Step 4: Commit if any fixes were needed**

```bash
git status  # check for changes
```
