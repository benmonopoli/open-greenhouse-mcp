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
    """Get the activity feed for a candidate. Read-only. Returns notes, emails,
    stage changes, and other timeline events.

    Use this to review a candidate's history. To add notes, use add_note_to_candidate.
    To log an email, use add_email_note_to_candidate.
    """
    return await client.harvest_get_one(f"/candidates/{candidate_id}/activity_feed")
