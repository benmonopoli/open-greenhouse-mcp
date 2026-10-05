"""Comprehensive tests for GreenhouseClient — covers OAuth tokens, errors, rate limiting,
cursor pagination, id/date filters, caching, board client, and ingestion client."""
from __future__ import annotations

import base64
import time
from unittest.mock import patch

import httpx
import pytest

from greenhouse_mcp.client import TOKEN_URL, GreenhouseClient, add_date_filter
from tests.conftest import make_client

HARVEST_BASE = "https://harvest.greenhouse.io/v3"
BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"


def _basic_auth(key: str) -> str:
    token = base64.b64encode(f"{key}:".encode()).decode()
    return f"Basic {token}"


def _token_response(token: str = "tok", expires_in: int = 3600) -> httpx.Response:
    return httpx.Response(
        200, json={"access_token": token, "token_type": "Bearer", "expires_in": expires_in}
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_requires_credentials(self):
        with pytest.raises(ValueError):
            GreenhouseClient()

    def test_client_id_without_secret_is_not_enough(self):
        with pytest.raises(ValueError):
            GreenhouseClient(client_id="id")

    def test_harvest_credentials(self):
        c = GreenhouseClient(client_id="id", client_secret="secret")
        assert c.has_harvest
        assert c.board_token is None

    def test_board_token_only(self):
        c = GreenhouseClient(board_token="acme")
        assert not c.has_harvest
        assert c.board_token == "acme"

    def test_ingestion_key_only(self):
        c = GreenhouseClient(ingestion_api_key="ing")
        assert not c.has_harvest

    def test_set_user(self):
        c = GreenhouseClient(client_id="id", client_secret="secret")
        c.set_user("42")
        assert c.user_id == "42"


# ---------------------------------------------------------------------------
# OAuth tokens
# ---------------------------------------------------------------------------


class TestTokens:
    async def test_read_token_has_no_sub(self, mock_api):
        token_route = mock_api.post(TOKEN_URL).mock(return_value=_token_response("read-tok"))
        jobs = mock_api.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(200, json=[]))
        c = GreenhouseClient(client_id="cid", client_secret="sec", user_id="42")
        await c.harvest_get("/jobs")
        req = token_route.calls[0].request
        assert req.headers["Authorization"] == "Basic " + base64.b64encode(b"cid:sec").decode()
        body = req.content.decode()
        assert "grant_type=client_credentials" in body
        assert "sub=" not in body
        assert jobs.calls[0].request.headers["Authorization"] == "Bearer read-tok"

    async def test_write_token_uses_sub(self, mock_api):
        token_route = mock_api.post(TOKEN_URL).mock(return_value=_token_response("write-tok"))
        post = mock_api.post(f"{HARVEST_BASE}/notes").mock(
            return_value=httpx.Response(201, json={"id": 1})
        )
        c = GreenhouseClient(client_id="cid", client_secret="sec", user_id="42")
        await c.harvest_post("/notes", json_data={"body": "x"})
        assert "sub=42" in token_route.calls[0].request.content.decode()
        assert post.calls[0].request.headers["Authorization"] == "Bearer write-tok"
        assert "On-Behalf-Of" not in post.calls[0].request.headers

    async def test_write_without_user_uses_service_user(self, mock_api):
        token_route = mock_api.post(TOKEN_URL).mock(return_value=_token_response())
        mock_api.post(f"{HARVEST_BASE}/notes").mock(return_value=httpx.Response(201, json={}))
        c = GreenhouseClient(client_id="cid", client_secret="sec")
        await c.harvest_post("/notes", json_data={})
        assert "sub=" not in token_route.calls[0].request.content.decode()

    async def test_token_is_cached(self, mock_api):
        token_route = mock_api.post(TOKEN_URL).mock(return_value=_token_response())
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(200, json=[]))
        c = GreenhouseClient(client_id="cid", client_secret="sec")
        await c.harvest_get("/jobs")
        await c.harvest_get("/jobs")
        assert token_route.call_count == 1

    async def test_expired_token_is_refreshed(self, mock_api):
        token_route = mock_api.post(TOKEN_URL).mock(return_value=_token_response(expires_in=3600))
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(200, json=[]))
        c = GreenhouseClient(client_id="cid", client_secret="sec")
        await c.harvest_get("/jobs")
        with patch("greenhouse_mcp.client.time.monotonic", return_value=time.monotonic() + 7200):
            await c.harvest_get("/jobs")
        assert token_route.call_count == 2

    async def test_401_remints_token_once(self, mock_api):
        mock_api.post(TOKEN_URL).mock(
            side_effect=[_token_response("old"), _token_response("new")]
        )
        jobs = mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            side_effect=[httpx.Response(401, json={}), httpx.Response(200, json=[{"id": 1}])]
        )
        c = GreenhouseClient(client_id="cid", client_secret="sec")
        result = await c.harvest_get("/jobs")
        assert result["items"] == [{"id": 1}]
        assert jobs.calls[1].request.headers["Authorization"] == "Bearer new"

    async def test_token_failure_returns_error(self, mock_api):
        mock_api.post(TOKEN_URL).mock(return_value=httpx.Response(401, json={"error": "nope"}))
        c = GreenhouseClient(client_id="cid", client_secret="bad")
        result = await c.harvest_get("/jobs")
        assert result["status_code"] == 401
        assert "GREENHOUSE_CLIENT_ID" in result["error"]

    async def test_harvest_without_credentials_returns_error(self):
        c = GreenhouseClient(board_token="acme")
        result = await c.harvest_get("/jobs")
        assert result["status_code"] == 401
        assert "GREENHOUSE_CLIENT_ID" in result["error"]


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------


class TestHarvestVerbs:
    async def test_get_sends_bearer(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        await client.harvest_get("/jobs")
        assert route.calls[0].request.headers["Authorization"] == "Bearer test-token"

    async def test_post_sends_json(self, client, mock_api):
        route = mock_api.post(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(201, json={"id": 1})
        )
        result = await client.harvest_post("/candidates", json_data={"first_name": "A"})
        assert result == {"id": 1}
        assert b'"first_name"' in route.calls[0].request.content

    async def test_patch(self, client, mock_api):
        mock_api.patch(f"{HARVEST_BASE}/candidates/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "first_name": "B"})
        )
        result = await client.harvest_patch("/candidates/1", json_data={"first_name": "B"})
        assert result["first_name"] == "B"

    async def test_delete_with_body(self, client, mock_api):
        route = mock_api.delete(f"{HARVEST_BASE}/openings/bulk").mock(
            return_value=httpx.Response(204)
        )
        result = await client.harvest_delete("/openings/bulk", json_data={"ids": [1, 2]})
        assert result == {"success": True}
        assert b'"ids"' in route.calls[0].request.content

    async def test_put(self, client, mock_api):
        mock_api.put(f"{HARVEST_BASE}/approver_groups/1/replace_approver").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        result = await client.harvest_put("/approver_groups/1/replace_approver", json_data={})
        assert result == {"ok": True}

    async def test_empty_success_body(self, client, mock_api):
        mock_api.post(f"{HARVEST_BASE}/applications/1/move").mock(
            return_value=httpx.Response(204)
        )
        assert await client.harvest_post("/applications/1/move", json_data={}) == {
            "success": True
        }


# ---------------------------------------------------------------------------
# Params: id arrays, booleans, dates
# ---------------------------------------------------------------------------


class TestParams:
    async def test_lists_become_comma_separated(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/applications").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.harvest_get(
            "/applications", params={"job_ids": [3, 1, 2], "prospect": False, "x": None}
        )
        q = route.calls[0].request.url.params
        assert q["job_ids"] == "3,1,2"
        assert q["prospect"] == "false"
        assert "x" not in q

    def test_add_date_filter(self):
        params = add_date_filter({}, "created_at", gte="2026-01-01T09:30:00Z", lt="2026-02-01")
        assert params == {
            "created_at[gte]": "2026-01-01T09:30:00Z",
            "created_at[lt]": "2026-02-01T00:00:00Z",  # date-only → midnight UTC
        }

    async def test_date_filter_is_sent(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/applications").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.harvest_get(
            "/applications", params=add_date_filter({}, "created_at", gte="2026-10-01")
        )
        assert route.calls[0].request.url.params["created_at[gte]"] == "2026-10-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.parametrize("status", [403, 404, 422, 500, 503])
    async def test_error_status_returns_error_dict(self, client, mock_api, status):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(status, json={"message": "x"})
        )
        result = await client.harvest_get("/jobs")
        assert result["status_code"] == status
        assert "error" in result
        assert result["detail"] == {"message": "x"}

    async def test_403_mentions_scope(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(403, json={}))
        result = await client.harvest_get("/jobs")
        assert "scope" in result["error"]

    async def test_persistent_401_returns_error(self, client, mock_api):
        mock_api.post(TOKEN_URL).mock(return_value=_token_response())
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(return_value=httpx.Response(401, json={}))
        result = await client.harvest_get("/jobs")
        assert result["status_code"] == 401


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    async def test_429_retries_then_succeeds(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "0"}),
                httpx.Response(200, json=[{"id": 1}]),
            ]
        )
        with patch("greenhouse_mcp.client.asyncio.sleep"):
            result = await client.harvest_get("/jobs")
        assert result["items"] == [{"id": 1}]

    async def test_429_exhausts_retries(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(429, headers={"Retry-After": "0"})
        )
        with patch("greenhouse_mcp.client.asyncio.sleep"):
            result = await client.harvest_get("/jobs")
        assert result["status_code"] == 429


# ---------------------------------------------------------------------------
# Cursor pagination
# ---------------------------------------------------------------------------


class TestPagination:
    async def test_single_page_no_link_header(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        result = await client.harvest_get("/jobs")
        assert result == {"items": [{"id": 1}], "has_next": False, "next_cursor": None}

    async def test_single_page_returns_next_cursor(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"link": f'<{HARVEST_BASE}/jobs?cursor=abc123>; rel="next"'},
            )
        )
        result = await client.harvest_get("/jobs", params={"per_page": 1})
        assert result["has_next"] is True
        assert result["next_cursor"] == "abc123"

    async def test_cursor_drops_other_params(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[])
        )
        await client.harvest_get("/jobs", params={"cursor": "abc", "status": "open", "per_page": 5})
        assert dict(route.calls[0].request.url.params) == {"cursor": "abc"}

    async def test_paginate_all_follows_links(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs", params={"cursor": "p2"}).mock(
            return_value=httpx.Response(200, json=[{"id": 2}])
        )
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"link": f'<{HARVEST_BASE}/jobs?cursor=p2>; rel="next"'},
            )
        )
        with patch("greenhouse_mcp.client.asyncio.sleep"):
            result = await client.harvest_get("/jobs", params={"status": "open"}, paginate="all")
        assert result == {"items": [{"id": 1}, {"id": 2}], "total": 2}

    async def test_paginate_all_reports_partial_failure(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/jobs", params={"cursor": "p2"}).mock(
            return_value=httpx.Response(500, json={})
        )
        mock_api.get(f"{HARVEST_BASE}/jobs").mock(
            return_value=httpx.Response(
                200,
                json=[{"id": 1}],
                headers={"link": f'<{HARVEST_BASE}/jobs?cursor=p2>; rel="next"'},
            )
        )
        with patch("greenhouse_mcp.client.asyncio.sleep"):
            result = await client.harvest_get("/jobs", paginate="all")
        assert result["partial"] is True
        assert result["items"] == [{"id": 1}]
        assert result["error"]["status_code"] == 500


# ---------------------------------------------------------------------------
# Get by id / id batches
# ---------------------------------------------------------------------------


class TestById:
    async def test_get_by_id_filters_ids(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[{"id": 7, "first_name": "A"}])
        )
        result = await client.harvest_get_by_id("/candidates", 7)
        assert result == {"id": 7, "first_name": "A"}
        assert route.calls[0].request.url.params["ids"] == "7"

    async def test_get_by_id_not_found(self, client, mock_api):
        mock_api.get(f"{HARVEST_BASE}/candidates").mock(return_value=httpx.Response(200, json=[]))
        result = await client.harvest_get_by_id("/candidates", 7)
        assert result["status_code"] == 404

    async def test_get_ids_batches_by_50(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/applications").mock(
            side_effect=[
                httpx.Response(200, json=[{"id": 1}]),
                httpx.Response(200, json=[{"id": 2}]),
            ]
        )
        result = await client.harvest_get_ids(
            "/applications", "candidate_ids", list(range(1, 61)) + [None, 5]
        )
        assert result == {"items": [{"id": 1}, {"id": 2}], "total": 2}
        first = route.calls[0].request.url.params["candidate_ids"].split(",")
        second = route.calls[1].request.url.params["candidate_ids"].split(",")
        assert len(first) == 50 and len(second) == 10


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    async def test_cache_hit_only_one_http_call(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        await client.harvest_get_cached("/departments")
        await client.harvest_get_cached("/departments")
        assert route.call_count == 1

    async def test_force_refresh_bypasses_cache(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        await client.harvest_get_cached("/departments")
        await client.harvest_get_cached("/departments", force_refresh=True)
        assert route.call_count == 2

    async def test_errors_not_cached(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            side_effect=[httpx.Response(500, json={}), httpx.Response(200, json=[{"id": 1}])]
        )
        first = await client.harvest_get_cached("/departments")
        second = await client.harvest_get_cached("/departments")
        assert first["status_code"] == 500
        assert second["items"] == [{"id": 1}]
        assert route.call_count == 2

    async def test_cache_expires_after_ttl(self, client, mock_api):
        route = mock_api.get(f"{HARVEST_BASE}/departments").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        await client.harvest_get_cached("/departments")
        with patch("greenhouse_mcp.client.time.monotonic", return_value=time.monotonic() + 301):
            await client.harvest_get_cached("/departments")
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# Job Board + Ingestion
# ---------------------------------------------------------------------------


class TestBoardClient:
    async def test_board_get_no_auth_header(self, board_client, mock_api):
        route = mock_api.get(f"{BOARD_BASE}/test-board/jobs").mock(
            return_value=httpx.Response(200, json={"jobs": []})
        )
        await board_client.board_get("/jobs")
        assert "Authorization" not in route.calls[0].request.headers

    async def test_board_post_uses_board_api_key(self, mock_api):
        route = mock_api.post(f"{BOARD_BASE}/acme/jobs/1").mock(
            return_value=httpx.Response(200, json={"success": "ok"})
        )
        c = GreenhouseClient(board_token="acme", board_api_key="board-key")
        await c.board_post("/jobs/1", json_data={"first_name": "A"})
        assert route.calls[0].request.headers["Authorization"] == _basic_auth("board-key")


class TestIngestionClient:
    async def test_ingestion_get_sends_basic_auth(self, mock_api):
        route = mock_api.get(f"{INGESTION_BASE}/jobs").mock(
            return_value=httpx.Response(200, json=[])
        )
        c = GreenhouseClient(ingestion_api_key="ing-key")
        await c.ingestion_get("/jobs")
        assert route.calls[0].request.headers["Authorization"] == _basic_auth("ing-key")

    async def test_ingestion_post_includes_on_behalf_of_user(self, mock_api):
        route = mock_api.post(f"{INGESTION_BASE}/candidates").mock(
            return_value=httpx.Response(200, json=[])
        )
        c = GreenhouseClient(ingestion_api_key="ing-key", user_id="42")
        await c.ingestion_post("/candidates", json_data={})
        assert route.calls[0].request.headers["On-Behalf-Of"] == "42"


async def test_close_closes_client():
    c = make_client()
    c._get_http_client()
    await c.close()
    assert c._http_client is None
