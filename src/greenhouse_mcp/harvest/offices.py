"""Harvest API — Offices tools (4 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_offices(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all offices. Read-only.

    Resolves office/location names to IDs. When a user mentions an office
    or location, use this to find its ID for list_jobs, create_job, or
    add_future_job_permission.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/offices", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_office(
    client: GreenhouseClient,
    *,
    office_id: Annotated[int, Field(description="Office ID — get from list_offices")],
) -> dict[str, Any]:
    """Get an office by ID. Read-only.

    Returns name, location, parent office, and child offices.
    To find office_id: list_offices → match by name.
    """
    return await client.harvest_get_one(f"/offices/{office_id}")


async def create_office(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Office name")],
    parent_id: Annotated[int | None, Field(description="Parent office ID for hierarchy — get from list_offices")] = None,
    location: Annotated[str | None, Field(description="Location string, e.g. 'San Francisco, CA'")] = None,
) -> dict[str, Any]:
    """Create a new office. Write operation — admin only.

    For parent_id (optional): list_offices → find parent by name.
    """
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if location is not None:
        json_data["location"] = location
    return await client.harvest_post("/offices", json_data=json_data)


async def update_office(
    client: GreenhouseClient,
    *,
    office_id: Annotated[int, Field(description="Office ID to update")],
    name: Annotated[str | None, Field(description="New office name")] = None,
    location: Annotated[str | None, Field(description="New location string")] = None,
) -> dict[str, Any]:
    """Update an office's name or location. Write operation — admin only.

    To find office_id: list_offices → match by name.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if location is not None:
        json_data["location"] = location
    return await client.harvest_patch(f"/offices/{office_id}", json_data=json_data)
