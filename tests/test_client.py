"""Comprehensive tests for GreenhouseClient — covers auth, errors, rate limiting,
pagination, caching, board client, and ingestion client."""
from __future__ import annotations

import base64
import time
from unittest.mock import patch

import httpx
import pytest

from greenhouse_mcp.client import GreenhouseClient

HARVEST_BASE = "https://harvest.greenhouse.io/v1"
BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _basic_auth(api_key: str) -> str:
    """Build the expected Basic auth header value."""
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    return f"Basic {token}"


# ---------------------------------------------------------------------------
# TestClientInit
# ---------------------------------------------------------------------------

class TestClientInit:
    def test_requires_credentials(self):
        with pytest.raises(ValueError, match="api_key.*board_token|board_token.*api_key"):
            GreenhouseClient()

    def test_api_key_only(self):
        c = GreenhouseClient(api_key="key-abc")
        assert c.api_key == "key-abc"
        assert c.board_token is None

    def test_board_token_only(self):
        c = GreenhouseClient(board_token="token-xyz")
        assert c.board_token == "token-xyz"
        assert c.api_key is None

    def test_both_credentials_allowed(self):
        c = GreenhouseClient(api_key="k", board_token="t")
        assert c.api_key == "k"
        assert c.board_token == "t"


# ---------------------------------------------------------------------------
# TestHarvestAuth
# ---------------------------------------------------------------------------

class TestHarvestAuth:
    @pytest.mark.asyncio
    async def test_get_sends_basic_auth(self, client, api_key, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        result = await client.harvest_get("/candidates")
        assert route.called
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == _basic_auth(api_key)
        assert result["items"] == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_with_params(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[{"id": 2}])
        )
        result = await client.harvest_get("/candidates", params={"per_page": "10"})
        assert route.called
        assert result["items"] == [{"id": 2}]

    @pytest.mark.asyncio
    async def test_post_sends_json(self, client, api_key, mock_api):
        route = mock_api.post(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(201, json={"id": 99})
        )
        result = await client.harvest_post("/candidates", json_data={"first_name": "Alice"})
        assert route.called
        assert result == {"id": 99}
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == _basic_auth(api_key)

    @pytest.mark.asyncio
    async def test_patch(self, client, api_key, mock_api):
        route = mock_api.patch(f"{HARVEST_BASE}/candidates/99").mock(
            return_value=httpx.Response(200, json={"id": 99, "updated": True})
        )
        result = await client.harvest_patch("/candidates/99", json_data={"last_name": "Smith"})
        assert route.called
        assert result["updated"] is True

    @pytest.mark.asyncio
    async def test_delete(self, client, api_key, mock_api):
        route = mock_api.delete(f"{HARVEST_BASE}/candidates/99").mock(
            return_value=httpx.Response(200, json={"deleted": True})
        )
        result = await client.harvest_delete("/candidates/99")
        assert route.called
        assert result == {"deleted": True}

    @pytest.mark.asyncio
    async def test_put(self, client, api_key, mock_api):
        route = mock_api.put(f"{HARVEST_BASE}/candidates/99/move").mock(
            return_value=httpx.Response(200, json={"moved": True})
        )
        result = await client.harvest_put("/candidates/99/move", json_data={"stage": "interview"})
        assert route.called
        assert result == {"moved": True}


# ---------------------------------------------------------------------------
# TestErrorHandling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_401_returns_error_dict(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(401, json={"message": "unauthorized"})
        )
        result = await client.harvest_get("/candidates")
        assert result["error"] == "Invalid API key. Check GREENHOUSE_API_KEY."
        assert result["status_code"] == 401

    @pytest.mark.asyncio
    async def test_403_returns_error_dict(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(403, json={"message": "forbidden"})
        )
        result = await client.harvest_get("/jobs")
        assert result["status_code"] == 403
        assert "error" in result

    @pytest.mark.asyncio
    async def test_404_returns_error_dict(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates/9999").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )
        result = await client.harvest_get("/candidates/9999")
        assert result["status_code"] == 404
        assert "error" in result

    @pytest.mark.asyncio
    async def test_422_returns_error_dict(self, client, mock_api):
        mock_api.post(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(422, json={"errors": [{"message": "invalid field"}]})
        )
        result = await client.harvest_post("/candidates", json_data={})
        assert result["status_code"] == 422
        assert "error" in result

    @pytest.mark.asyncio
    async def test_500_returns_error_dict(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(500, json={"message": "server error"})
        )
        result = await client.harvest_get("/candidates")
        assert result["status_code"] == 500
        assert "error" in result


# ---------------------------------------------------------------------------
# TestRateLimiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_429_retries_then_succeeds(self, client, mock_api):
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(429, headers={"Retry-After": "0"}, json={})
            return httpx.Response(200, json=[{"id": 1}])

        mock_api.get(f"{HARVEST_BASE}/candidates").mock(side_effect=side_effect)

        with patch("asyncio.sleep") as mock_sleep:
            result = await client.harvest_get("/candidates")

        assert result["items"] == [{"id": 1}]
        mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_429_exhausts_retries(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "0"}, json={})
        )

        with patch("asyncio.sleep"):
            result = await client.harvest_get("/candidates")

        assert result["status_code"] == 429
        assert "error" in result


# ---------------------------------------------------------------------------
# TestPagination
# ---------------------------------------------------------------------------

class TestPagination:
    @pytest.mark.asyncio
    async def test_single_page_no_link_header(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
        )
        result = await client.harvest_get("/candidates", paginate="single")
        assert result["items"] == [{"id": 1}, {"id": 2}]
        assert result["has_next"] is False
        assert result["next_page"] is None

    @pytest.mark.asyncio
    async def test_single_page_with_link_header(self, client, mock_api):
        next_url = f"{HARVEST_BASE}/candidates?page=2&per_page=100"
        link_header = f'<{next_url}>; rel="next"'
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"Link": link_header},
            )
        )
        result = await client.harvest_get("/candidates", paginate="single")
        assert result["has_next"] is True
        assert result["next_page"] == next_url

    @pytest.mark.asyncio
    async def test_paginate_all_follows_links(self, client, mock_api):
        page2_url = f"{HARVEST_BASE}/candidates?page=2"
        page1_link = f'<{page2_url}>; rel="next"'

        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json=[{"id": 1}], headers={"Link": page1_link})
            # page 2 — no more link header
            return httpx.Response(200, json=[{"id": 2}])

        mock_api.get(f"{HARVEST_BASE}/candidates").mock(side_effect=side_effect)

        with patch("asyncio.sleep"):
            result = await client.harvest_get("/candidates", paginate="all")

        assert result["items"] == [{"id": 1}, {"id": 2}]
        assert result["total"] == 2


# ---------------------------------------------------------------------------
# TestCache
# ---------------------------------------------------------------------------

class TestCache:
    @pytest.mark.asyncio
    async def test_cache_hit_only_one_http_call(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 10}])
        )
        r1 = await client.harvest_get_cached("/departments")
        r2 = await client.harvest_get_cached("/departments")
        assert r1["items"] == r2["items"]
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 10}])
        )
        await client.harvest_get_cached("/departments")
        await client.harvest_get_cached("/departments", force_refresh=True)
        assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_errors_not_cached(self, client, mock_api):
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500, json={"message": "error"})
            return httpx.Response(200, json=[{"id": 1}])

        mock_api.get(f"{HARVEST_BASE}/departments").mock(side_effect=side_effect)

        r1 = await client.harvest_get_cached("/departments")
        assert r1["status_code"] == 500
        r2 = await client.harvest_get_cached("/departments")
        # Second call should hit HTTP (not cached error) and succeed
        assert r2["items"] == [{"id": 1}]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 10}])
        )
        await client.harvest_get_cached("/departments")
        # Manually expire cache entry
        for key in client._cache:
            data, _ = client._cache[key]
            client._cache[key] = (data, time.monotonic() - 1)
        await client.harvest_get_cached("/departments")
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# TestBoardClient
# ---------------------------------------------------------------------------

class TestBoardClient:
    @pytest.mark.asyncio
    async def test_board_get_no_auth_header(self, board_client, mock_api):
        route = mock_api.get(f"{BOARD_BASE}/test-board/jobs").mock(
            return_value=httpx.Response(200, json={"jobs": []})
        )
        result = await board_client.board_get("/jobs")
        assert route.called
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header is None
        assert result == {"jobs": []}

    @pytest.mark.asyncio
    async def test_board_get_with_api_key_no_auth(self, mock_api):
        """Even when api_key is present, board_get must NOT send auth."""
        c = GreenhouseClient(api_key="key", board_token="myboard")
        route = mock_api.get(f"{BOARD_BASE}/myboard/jobs").mock(
            return_value=httpx.Response(200, json={"jobs": []})
        )
        await c.board_get("/jobs")
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header is None


# ---------------------------------------------------------------------------
# TestIngestionClient
# ---------------------------------------------------------------------------

class TestIngestionClient:
    @pytest.mark.asyncio
    async def test_ingestion_post_includes_on_behalf_of(self, mock_api):
        c = GreenhouseClient(api_key="key", on_behalf_of="user@example.com")
        route = mock_api.post(f"{INGESTION_BASE}/candidates").mock(
            return_value=httpx.Response(200, json={"id": 5})
        )
        result = await c.ingestion_post("/candidates", json_data={"name": "Bob"})
        assert route.called
        assert result == {"id": 5}
        on_behalf = route.calls[0].request.headers.get("on-behalf-of")
        assert on_behalf == "user@example.com"

    @pytest.mark.asyncio
    async def test_ingestion_get_sends_auth(self, mock_api):
        c = GreenhouseClient(api_key="mykey", on_behalf_of="agent@co.com")
        route = mock_api.get(f"{INGESTION_BASE}/prospects").mock(
            return_value=httpx.Response(200, json=[])
        )
        result = await c.ingestion_get("/prospects")
        assert route.called
        auth_header = route.calls[0].request.headers.get("authorization")
        assert auth_header == _basic_auth("mykey")
        assert result == []

    @pytest.mark.asyncio
    async def test_ingestion_post_no_on_behalf_of_when_not_set(self, mock_api):
        c = GreenhouseClient(api_key="key")
        route = mock_api.post(f"{INGESTION_BASE}/candidates").mock(
            return_value=httpx.Response(200, json={"id": 6})
        )
        await c.ingestion_post("/candidates", json_data={})
        on_behalf = route.calls[0].request.headers.get("on-behalf-of")
        assert on_behalf is None

    @pytest.mark.asyncio
    async def test_close_closes_client(self):
        c = GreenhouseClient(api_key="key")
        # Trigger lazy init
        _ = c._get_http_client()
        await c.close()
        assert c._http_client is None or c._http_client.is_closed
