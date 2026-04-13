"""Harvest API — Prospect Pools tools (2 tools)."""
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
    """List all prospect pools with their stages."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/prospect_pools", params=params, paginate=paginate)


async def get_prospect_pool(
    client: GreenhouseClient,
    *,
    prospect_pool_id: int,
) -> dict[str, Any]:
    """Get a single prospect pool with its stages by ID."""
    return await client.harvest_get(f"/prospect_pools/{prospect_pool_id}")
