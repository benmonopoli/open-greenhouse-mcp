"""Harvest API — Education tools (3 tools)."""
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
    """List all degree types available for candidate education records."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/degrees", params=params, force_refresh=force_refresh)


async def list_disciplines(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all academic disciplines available for candidate education records."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/disciplines", params=params, force_refresh=force_refresh
    )


async def list_schools(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all schools available for candidate education records."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/schools", params=params, force_refresh=force_refresh)
