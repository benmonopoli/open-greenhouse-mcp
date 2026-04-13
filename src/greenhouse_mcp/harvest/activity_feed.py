"""Harvest API — Activity Feed tools (1 tool)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_activity_feed(
    client: GreenhouseClient,
    *,
    candidate_id: int,
) -> dict[str, Any]:
    """Get the activity feed (notes, emails, stage changes) for a candidate."""
    return await client.harvest_get(f"/candidates/{candidate_id}/activity_feed")
