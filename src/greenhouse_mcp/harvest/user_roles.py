"""Harvest API — User Roles tools (1 tool)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_user_roles(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
) -> dict[str, Any]:
    """List all user roles in the organization. Read-only.

    Resolves role names to IDs for add_job_permission and
    add_future_job_permission. Only roles with role_type 'job_admin' can be
    granted on jobs.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    return await client.harvest_get_cached("/user_roles", params=params)
