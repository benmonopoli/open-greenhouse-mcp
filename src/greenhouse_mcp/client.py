"""Shared async HTTP client for all Greenhouse API tool modules.

Harvest calls go to the v3 API with OAuth 2.0 client-credentials tokens. Reads use a
token for the credential's integration service user; writes use a token minted with
``sub=<user_id>`` when a user is configured, so actions are attributed to that person.

Never raises exceptions to the LLM — all errors are returned as structured dicts.
"""

from __future__ import annotations

import asyncio
import base64
import random
import re
import time
from typing import Any

import httpx

from greenhouse_mcp.logging import log_api_call

HARVEST_BASE = "https://harvest.greenhouse.io/v3"
TOKEN_URL = "https://auth.greenhouse.io/token"
BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"

_CACHE_TTL = 300  # 5 minutes
_MAX_RETRIES = 3
_INTER_PAGE_DELAY = 0.2  # seconds
_TOKEN_SKEW = 60  # refresh tokens this many seconds before they expire

_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
_DATE_OPS = ("gte", "lte", "gt", "lt")
_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def add_date_filter(
    params: dict[str, Any],
    field: str,
    *,
    gte: str | None = None,
    lte: str | None = None,
    gt: str | None = None,
    lt: str | None = None,
) -> dict[str, Any]:
    """Add a v3 date filter (``field[gte]=...``) to params for each operator given.

    v3 rejects date-only values, so ``YYYY-MM-DD`` is sent as midnight UTC.
    v3 doesn't allow ``created_at`` and ``updated_at`` filters in the same request.
    """
    for op, value in zip(_DATE_OPS, (gte, lte, gt, lt)):
        if value is not None:
            params[f"{field}[{op}]"] = normalize_datetime(value)
    return params


def normalize_datetime(value: str) -> str:
    """Return an ISO 8601 date-time v3 accepts: date-only values become midnight UTC."""
    value = value.strip()
    if _DATE_ONLY_RE.fullmatch(value):
        return f"{value}T00:00:00Z"
    return value


def _encode_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """Encode list values as comma-separated ids (``ids=1,2,3``) and drop Nones."""
    if params is None:
        return None
    out: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            out[key] = ",".join(str(v) for v in value)
        elif isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = value
    return out


class GreenhouseClient:
    """Shared async HTTP client for Harvest v3, Job Board, and Ingestion APIs."""

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_id: str | None = None,
        board_token: str | None = None,
        board_api_key: str | None = None,
        ingestion_api_key: str | None = None,
    ) -> None:
        has_harvest = bool(client_id and client_secret)
        if not has_harvest and board_token is None and ingestion_api_key is None:
            raise ValueError(
                "Provide Harvest v3 credentials (client_id + client_secret), "
                "a board_token, or an ingestion_api_key."
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.board_token = board_token
        self.board_api_key = board_api_key
        self.ingestion_api_key = ingestion_api_key
        self._http_client: httpx.AsyncClient | None = None
        # in-memory TTL cache: cache_key -> (data, expires_at)
        self._cache: dict[str, tuple[Any, float]] = {}
        # access tokens keyed by sub ("" = integration service user)
        self._tokens: dict[str, tuple[str, float]] = {}
        self._token_lock = asyncio.Lock()

    @property
    def has_harvest(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def set_user(self, user_id: str) -> None:
        """Attribute write operations to this Greenhouse user (the token's ``sub``)."""
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy-initialise and return the shared httpx.AsyncClient."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                timeout=httpx.Timeout(30.0),
            )
        return self._http_client

    async def _access_token(self, sub: str, *, force: bool = False) -> str | dict[str, Any]:
        """Return a cached bearer token for ``sub``, or an error dict if minting fails."""
        async with self._token_lock:
            cached = self._tokens.get(sub)
            if cached and not force and time.monotonic() < cached[1]:
                return cached[0]
            data = {"grant_type": "client_credentials"}
            if sub:
                data["sub"] = sub
            start = time.monotonic()
            try:
                resp = await self._get_http_client().post(
                    TOKEN_URL,
                    data=data,
                    auth=(self.client_id or "", self.client_secret or ""),
                )
            except httpx.HTTPError as e:
                return {"error": f"Could not reach the Greenhouse token endpoint: {e}",
                        "status_code": 0}
            log_api_call(method="POST", url=TOKEN_URL, status=resp.status_code, start_time=start)
            if resp.status_code != 200:
                return {
                    "error": "Could not get a Harvest v3 access token. Check "
                    "GREENHOUSE_CLIENT_ID and GREENHOUSE_CLIENT_SECRET"
                    + (", and that GREENHOUSE_USER_ID is a valid user." if sub else "."),
                    "status_code": resp.status_code,
                    "detail": self._parse_body(resp),
                }
            body = self._parse_body(resp)
            token = str(body.get("access_token", ""))
            ttl = int(body.get("expires_in", 3600))
            self._tokens[sub] = (token, time.monotonic() + max(ttl - _TOKEN_SKEW, 30))
            return token

    async def _harvest_headers(self, *, write: bool, force: bool = False) -> dict[str, Any]:
        """Bearer header for reads (service user) or writes (configured user).

        Returns an error dict (with ``status_code``) when no token can be obtained.
        """
        if not self.has_harvest:
            return {
                "error": "Harvest v3 credentials not configured. Set GREENHOUSE_CLIENT_ID "
                "and GREENHOUSE_CLIENT_SECRET (Configure > Dev Center > API Credentials > "
                "Harvest V3 (OAuth)).",
                "status_code": 401,
            }
        sub = (self.user_id or "") if write else ""
        token = await self._access_token(sub, force=force)
        if isinstance(token, dict):
            return token
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _basic_auth(key: str) -> dict[str, str]:
        token = base64.b64encode(f"{key}:".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _ingestion_headers(self) -> dict[str, str]:
        if self.ingestion_api_key is None:
            return {}
        headers = self._basic_auth(self.ingestion_api_key)
        if self.user_id:
            headers["On-Behalf-Of"] = self.user_id
        return headers

    @staticmethod
    def _parse_next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        m = _LINK_RE.search(link_header)
        return m.group(1) if m else None

    @staticmethod
    def _cursor_from_url(url: str | None) -> str | None:
        if not url:
            return None
        cursor = httpx.URL(url).params.get("cursor")
        return str(cursor) if cursor else None

    @staticmethod
    def _error_dict(status_code: int, detail: Any = None) -> dict[str, Any]:
        messages: dict[int, str] = {
            401: "Authentication failed. Check GREENHOUSE_CLIENT_ID and "
            "GREENHOUSE_CLIENT_SECRET.",
            403: "Permission denied. Check that the Harvest v3 credential has the scope "
            "for this endpoint (Configure > Dev Center > API Credentials) and that the "
            "acting user has the permission. List endpoints need a Site Admin user.",
            404: "Resource not found.",
            422: "Validation error. Check the request data.",
            429: "Rate limit exceeded. Please try again later.",
        }
        if status_code in messages:
            msg = messages[status_code]
        elif 500 <= status_code < 600:
            msg = f"Greenhouse server error (HTTP {status_code})."
        else:
            msg = f"Unexpected HTTP error (status {status_code})."
        result: dict[str, Any] = {"error": msg, "status_code": status_code}
        if detail is not None:
            result["detail"] = detail
        return result

    @staticmethod
    def _is_error(result: Any) -> bool:
        return isinstance(result, dict) and "error" in result and "status_code" in result

    # ------------------------------------------------------------------
    # Low-level request with rate-limit retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with up to _MAX_RETRIES on 429."""
        http = self._get_http_client()
        start = time.monotonic()
        for attempt in range(_MAX_RETRIES + 1):
            resp = await http.request(
                method,
                url,
                headers=headers or {},
                params=params,
                json=json,
            )
            if resp.status_code == 429:
                if attempt < _MAX_RETRIES:
                    retry_after = float(resp.headers.get("Retry-After", "1"))
                    jitter = random.uniform(0, min(retry_after * 0.5, 2.0))
                    await asyncio.sleep(retry_after + jitter)
                    continue
            log_api_call(method=method, url=url, status=resp.status_code, start_time=start)
            return resp
        # Exhausted retries — return the last 429 response
        log_api_call(method=method, url=url, status=resp.status_code, start_time=start)
        return resp

    async def _harvest_request(
        self,
        method: str,
        url: str,
        *,
        write: bool,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response | dict[str, Any]:
        """Authenticated Harvest request; re-mints the token once on a 401."""
        headers = await self._harvest_headers(write=write)
        if self._is_error(headers):
            return headers
        resp = await self._request(method, url, headers=headers, params=params, json=json)
        if resp.status_code == 401:
            headers = await self._harvest_headers(write=write, force=True)
            if self._is_error(headers):
                return headers
            resp = await self._request(method, url, headers=headers, params=params, json=json)
        return resp

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_body(resp: httpx.Response) -> Any:
        """Return parsed JSON or empty dict on decode failure."""
        try:
            return resp.json()
        except Exception:
            return {}

    def _handle_response(self, resp: httpx.Response | dict[str, Any]) -> Any:
        """Convert an httpx.Response to either the parsed body or an error dict."""
        if isinstance(resp, dict):
            return resp  # already an error dict
        if resp.status_code in (401, 403, 404, 422, 429) or 500 <= resp.status_code < 600:
            return self._error_dict(resp.status_code, self._parse_body(resp))
        if resp.status_code >= 400:
            return self._error_dict(resp.status_code, self._parse_body(resp))
        if resp.status_code == 204 or not resp.content:
            return {"success": True}
        return self._parse_body(resp)

    # ------------------------------------------------------------------
    # Harvest API methods
    # ------------------------------------------------------------------

    async def harvest_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
    ) -> dict[str, Any]:
        """List a Harvest v3 resource.

        ``paginate="single"`` returns ``{"items", "has_next", "next_cursor"}``; pass
        ``next_cursor`` back as ``params={"cursor": ...}`` for the next page (v3 rejects
        any other params alongside a cursor, so they are dropped). ``paginate="all"``
        follows every page and returns ``{"items", "total"}``.
        """
        url = f"{HARVEST_BASE}{endpoint}"
        query = _encode_params(params) or {}
        if query.get("cursor"):
            query = {"cursor": query["cursor"]}
        resp = await self._harvest_request("GET", url, write=False, params=query)
        parsed = self._handle_response(resp)
        if self._is_error(parsed):
            return parsed  # type: ignore[no-any-return]
        assert isinstance(resp, httpx.Response)

        items: list[Any] = parsed if isinstance(parsed, list) else [parsed]
        next_url = self._parse_next_link(resp.headers.get("link"))

        if paginate == "single":
            return {
                "items": items,
                "has_next": next_url is not None,
                "next_cursor": self._cursor_from_url(next_url),
            }

        while next_url:
            await asyncio.sleep(_INTER_PAGE_DELAY)
            resp = await self._harvest_request("GET", next_url, write=False)
            parsed = self._handle_response(resp)
            if self._is_error(parsed):
                return {"items": items, "total": len(items), "partial": True, "error": parsed}
            assert isinstance(resp, httpx.Response)
            items.extend(parsed if isinstance(parsed, list) else [parsed])
            next_url = self._parse_next_link(resp.headers.get("link"))

        return {"items": items, "total": len(items)}

    async def harvest_get_by_id(
        self,
        endpoint: str,
        resource_id: int | str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch one record. v3 has no ``GET /resource/{id}``; this filters the list
        endpoint by ``ids`` and returns the object, or a 404 error dict."""
        query = dict(params or {})
        query["ids"] = resource_id
        result = await self.harvest_get(endpoint, params=query)
        if self._is_error(result):
            return result
        items = result.get("items") or []
        if not items:
            return self._error_dict(404, {"message": f"No record with id {resource_id}"})
        return items[0]  # type: ignore[no-any-return]

    async def harvest_get_ids(
        self,
        endpoint: str,
        filter_name: str,
        ids: list[int] | set[int] | tuple[int, ...],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List a resource filtered by an id array, batching to v3's 50-id limit.

        Returns ``{"items", "total"}`` (or an error dict).
        """
        unique = sorted({i for i in ids if i is not None})
        items: list[Any] = []
        for n in range(0, len(unique), 50):
            query = dict(params or {})
            query[filter_name] = unique[n:n + 50]
            result = await self.harvest_get(endpoint, params=query, paginate="all")
            if self._is_error(result):
                return result
            items.extend(result.get("items", []))
        return {"items": items, "total": len(items)}

    async def harvest_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._harvest_request("POST", url, write=True, json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def harvest_patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._harvest_request("PATCH", url, write=True, json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def harvest_delete(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._harvest_request("DELETE", url, write=True, json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def harvest_put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._harvest_request("PUT", url, write=True, json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def harvest_get_cached(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        sorted_params = sorted((_encode_params(params) or {}).items())
        cache_key = f"GET:{url}:{sorted_params}:{paginate}"
        now = time.monotonic()

        if not force_refresh and cache_key in self._cache:
            data, expires_at = self._cache[cache_key]
            if now < expires_at:
                return data  # type: ignore[no-any-return]

        result = await self.harvest_get(endpoint, params=params, paginate=paginate)

        # Only cache complete, successful responses
        if not self._is_error(result) and not result.get("partial"):
            self._cache[cache_key] = (result, now + _CACHE_TTL)

        return result

    # ------------------------------------------------------------------
    # Job Board API methods
    # ------------------------------------------------------------------

    async def board_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Job Board GET — no auth header, board token is in the URL path."""
        url = f"{BOARD_BASE}/{self.board_token}{endpoint}"
        resp = await self._request("GET", url, params=params)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def board_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Job Board POST (application submission) — Basic auth with the Job Board API key."""
        url = f"{BOARD_BASE}/{self.board_token}{endpoint}"
        headers = self._basic_auth(self.board_api_key) if self.board_api_key else {}
        resp = await self._request("POST", url, headers=headers, json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Ingestion API methods
    # ------------------------------------------------------------------

    async def ingestion_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{INGESTION_BASE}{endpoint}"
        resp = await self._request("GET", url, headers=self._ingestion_headers(), params=params)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    async def ingestion_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{INGESTION_BASE}{endpoint}"
        resp = await self._request("POST", url, headers=self._ingestion_headers(), json=json_data)
        return self._handle_response(resp)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Attachment download
    # ------------------------------------------------------------------

    async def download_url(self, url: str) -> dict[str, Any]:
        """Download content from a URL (e.g. signed S3 attachment URL)."""
        http = self._get_http_client()
        try:
            resp = await http.get(url, follow_redirects=True)
            if resp.status_code >= 400:
                return self._error_dict(resp.status_code)
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type:
                return {"content": resp.text, "content_type": content_type}
            return {
                "content_base64": base64.b64encode(resp.content).decode(),
                "content_type": content_type,
                "size_bytes": len(resp.content),
            }
        except Exception as e:
            return {"error": f"Download failed: {e}", "status_code": 0}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient and release connections."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
        self._http_client = None
        # A fresh lock, in case the client is reused from a different event loop.
        self._token_lock = asyncio.Lock()
