"""Harvest API — Rejection Reasons tools (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_rejection_reasons(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    include_defaults: Annotated[
        bool | None, Field(description="Also include Greenhouse's built-in default reasons")
    ] = None,
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all rejection reasons. Read-only.

    Resolves rejection reason names to IDs. When a user says "reject for
    'not enough experience'," use this to find the ID, then pass it to
    reject_application or bulk_reject. Each reason's `type` is an object
    {id, key, name} — key is WE_REJECTED_THEM,
    THEY_REJECTED_US, NONE_SPECIFIED or SECURITY_CONCERN.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if include_defaults is not None:
        params["include_defaults"] = include_defaults
    return await client.harvest_get_cached(
        "/rejection_reasons", params=params, force_refresh=force_refresh
    )
