"""Harvest API — User Roles tools (1 tool)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_user_roles(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
) -> dict[str, Any]:
    """List all user roles available in the organization."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached("/user_roles", params=params)
