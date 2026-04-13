"""Harvest API — Sources tools (1 tool)."""
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
    """List all candidate sources (e.g. job boards, referrals, agencies)."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/sources", params=params, force_refresh=force_refresh)
