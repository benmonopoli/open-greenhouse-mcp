"""Harvest API — Sources tools (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_sources(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all candidate sources (job boards, referrals, agencies). Read-only.

    Resolves source names to IDs for create_application and update_application.
    When a user mentions where a candidate came from, use this to find the
    source_id. Each source has a `type` object ({id, name}) — the sourcing
    strategy it rolls up to (e.g. "Referral", "Agencies").
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    return await client.harvest_get_cached(
        "/sources", params=params, force_refresh=force_refresh
    )
