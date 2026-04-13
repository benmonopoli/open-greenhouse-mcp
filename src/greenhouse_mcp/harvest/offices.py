"""Harvest API — Offices tools (4 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_offices(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all offices in the organization."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/offices", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_office(
    client: GreenhouseClient,
    *,
    office_id: int,
) -> dict[str, Any]:
    """Get a single office by ID."""
    return await client.harvest_get_one(f"/offices/{office_id}")


async def create_office(
    client: GreenhouseClient,
    *,
    name: str,
    parent_id: int | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Create a new office with a name and optional parent office and location."""
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if location is not None:
        json_data["location"] = location
    return await client.harvest_post("/offices", json_data=json_data)


async def update_office(
    client: GreenhouseClient,
    *,
    office_id: int,
    name: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Update an office's name or location."""
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if location is not None:
        json_data["location"] = location
    return await client.harvest_patch(f"/offices/{office_id}", json_data=json_data)
