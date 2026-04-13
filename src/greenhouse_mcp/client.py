"""Shared async HTTP client for all Greenhouse API tool modules.

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

HARVEST_BASE = "https://harvest.greenhouse.io/v1"
BOARD_BASE = "https://boards-api.greenhouse.io/v1/boards"
INGESTION_BASE = "https://api.greenhouse.io/v1/partner"

_CACHE_TTL = 300  # 5 minutes
_MAX_RETRIES = 3
_INTER_PAGE_DELAY = 0.2  # seconds

_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


class GreenhouseClient:
    """Shared async HTTP client for Harvest, Job Board, and Ingestion APIs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        board_token: str | None = None,
        on_behalf_of: str | None = None,
    ) -> None:
        if api_key is None and board_token is None:
            raise ValueError("Either api_key or board_token must be provided.")
        self.api_key = api_key
        self.board_token = board_token
        self.on_behalf_of = on_behalf_of
        self._http_client: httpx.AsyncClient | None = None
        # in-memory TTL cache: cache_key -> (data, expires_at)
        self._cache: dict[str, tuple[Any, float]] = {}

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

    def _harvest_auth_header(self) -> dict[str, str]:
        if self.api_key is None:
            return {}
        token = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _ingestion_headers(self) -> dict[str, str]:
        headers = self._harvest_auth_header()
        if self.on_behalf_of:
            headers["On-Behalf-Of"] = self.on_behalf_of
        return headers

    @staticmethod
    def _parse_next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        m = _LINK_RE.search(link_header)
        return m.group(1) if m else None

    @staticmethod
    def _error_dict(status_code: int, detail: Any = None) -> dict[str, Any]:
        messages: dict[int, str] = {
            401: "Invalid API key. Check GREENHOUSE_API_KEY.",
            403: "Permission denied. Check that your API key has the required permissions.",
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
    def _is_error(result: dict[str, Any]) -> bool:
        return "error" in result and "status_code" in result

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
            return resp
        # Exhausted retries — return the last 429 response
        return resp  # type: ignore[return-value]

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

    def _handle_response(self, resp: httpx.Response) -> dict[str, Any]:
        """Convert an httpx.Response to either the parsed body or an error dict."""
        if resp.status_code == 429:
            return self._error_dict(429, self._parse_body(resp))
        if resp.status_code in (401, 403, 404, 422):
            detail = self._parse_body(resp)
            return self._error_dict(resp.status_code, detail)
        if 500 <= resp.status_code < 600:
            detail = self._parse_body(resp)
            return self._error_dict(resp.status_code, detail)
        return self._parse_body(resp)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Paginated GET helper
    # ------------------------------------------------------------------

    async def _paginated_get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
    ) -> dict[str, Any]:
        resp = await self._request("GET", url, headers=headers, params=params)
        parsed = self._handle_response(resp)

        if self._is_error(parsed):
            return parsed

        if paginate == "single":
            next_url = self._parse_next_link(resp.headers.get("link"))
            items = parsed if isinstance(parsed, list) else [parsed]
            return {"items": items, "has_next": next_url is not None, "next_page": next_url}

        # paginate="all" — follow all next links
        items: list[Any] = parsed if isinstance(parsed, list) else [parsed]
        next_url = self._parse_next_link(resp.headers.get("link"))
        while next_url:
            await asyncio.sleep(_INTER_PAGE_DELAY)
            resp = await self._request("GET", next_url, headers=headers)
            parsed = self._handle_response(resp)
            if self._is_error(parsed):
                break
            page_items = parsed if isinstance(parsed, list) else [parsed]
            items.extend(page_items)
            next_url = self._parse_next_link(resp.headers.get("link"))

        return {"items": items, "total": len(items)}

    # ------------------------------------------------------------------
    # Harvest API methods
    # ------------------------------------------------------------------

    async def harvest_get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        return await self._paginated_get(
            url, headers=self._harvest_auth_header(), params=params, paginate=paginate
        )

    async def harvest_get_one(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Harvest GET for a single resource — returns the object directly."""
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._request("GET", url, headers=self._harvest_auth_header(), params=params)
        return self._handle_response(resp)

    async def harvest_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._request("POST", url, headers=self._harvest_auth_header(), json=json_data)
        return self._handle_response(resp)

    async def harvest_patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._request(
            "PATCH", url, headers=self._harvest_auth_header(), json=json_data
        )
        return self._handle_response(resp)

    async def harvest_delete(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._request("DELETE", url, headers=self._harvest_auth_header())
        return self._handle_response(resp)

    async def harvest_put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        resp = await self._request("PUT", url, headers=self._harvest_auth_header(), json=json_data)
        return self._handle_response(resp)

    async def harvest_get_cached(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        paginate: str = "single",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        url = f"{HARVEST_BASE}{endpoint}"
        sorted_params = sorted((params or {}).items())
        cache_key = f"GET:{url}:{sorted_params}:{paginate}"
        now = time.monotonic()

        if not force_refresh and cache_key in self._cache:
            data, expires_at = self._cache[cache_key]
            if now < expires_at:
                return data

        result = await self.harvest_get(endpoint, params=params, paginate=paginate)

        # Only cache successful responses
        if not self._is_error(result):
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
        return self._handle_response(resp)

    async def board_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Job Board POST — uses Harvest auth if api_key is set."""
        url = f"{BOARD_BASE}/{self.board_token}{endpoint}"
        resp = await self._request(
            "POST", url, headers=self._harvest_auth_header(), json=json_data
        )
        return self._handle_response(resp)

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
        return self._handle_response(resp)

    async def ingestion_post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{INGESTION_BASE}{endpoint}"
        resp = await self._request("POST", url, headers=self._ingestion_headers(), json=json_data)
        return self._handle_response(resp)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient and release connections."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
        self._http_client = None
