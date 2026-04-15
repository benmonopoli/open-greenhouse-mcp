"""Harvest API — Tracking Links tools (1 tool)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def get_tracking_link(
    client: GreenhouseClient,
    *,
    token: Annotated[str, Field(description="Tracking link token string")],
) -> dict[str, Any]:
    """Get a tracking link by its token. Read-only. Returns the source and referrer
    metadata associated with this tracking link.

    Tracking links attribute candidate sources. For a list of all sources, use
    list_sources. For source performance analytics, use source_effectiveness.
    """
    return await client.harvest_get_one(f"/tracking_links/{token}")
