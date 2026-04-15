"""Harvest API — Rejection Reasons tools (1 tool)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_rejection_reasons(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all rejection reasons available for rejecting applications. Read-only.
    Uses cached data by default.

    Rejection reason IDs are used in reject_application (rejection_reason_id) and
    update_rejection_reason. Pass force_refresh=true after adding new reasons in
    Greenhouse.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/rejection_reasons", params=params, force_refresh=force_refresh
    )
