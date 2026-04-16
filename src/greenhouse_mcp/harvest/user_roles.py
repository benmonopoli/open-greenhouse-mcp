"""Harvest API — User Roles tools (1 tool)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_user_roles(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
) -> dict[str, Any]:
    """List all user roles in the organization. Read-only.

    Resolves role names to IDs for add_job_permission and
    add_future_job_permission.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/user_roles", params=params)
