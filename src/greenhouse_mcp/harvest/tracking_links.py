"""Harvest API — Tracking Links tools (1 tool)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_tracking_link(
    client: GreenhouseClient,
    *,
    token: str,
) -> dict[str, Any]:
    """Get a tracking link by its token, returning source and referrer metadata."""
    return await client.harvest_get(f"/tracking_links/{token}")
