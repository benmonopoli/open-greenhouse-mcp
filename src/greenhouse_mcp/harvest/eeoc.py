"""Harvest API — EEOC tools (2 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_eeoc(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all EEOC data collected from applications."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get("/eeoc", params=params, paginate=paginate)


async def get_eeoc_for_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """Get EEOC data submitted for a specific application."""
    return await client.harvest_get(f"/applications/{application_id}/eeoc")
