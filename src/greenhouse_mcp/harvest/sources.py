"""Harvest API — Sources tools (1 tool)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_sources(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all candidate sources (job boards, referrals, agencies, etc). Read-only.
    Uses cached data by default.

    Source IDs are needed for create_application (source_id) and update_application.
    For analyzing which sources produce the best hire rates, use source_effectiveness.
    Pass force_refresh=true after adding new sources.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/sources", params=params, force_refresh=force_refresh)
