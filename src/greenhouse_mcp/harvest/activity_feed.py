"""Harvest API — Activity Feed tools (1 tool)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def get_activity_feed(
    client: GreenhouseClient,
    *,
    candidate_id: Annotated[int, Field(description="Greenhouse candidate ID")],
) -> dict[str, Any]:
    """Get a candidate's activity timeline. Read-only.

    Users say "show me Sarah's history" or "what's happened with this candidate?"
    To find candidate_id: search_candidates_by_name. Returns notes, emails,
    stage changes, and other timeline events in chronological order.
    """
    return await client.harvest_get_one(f"/candidates/{candidate_id}/activity_feed")
