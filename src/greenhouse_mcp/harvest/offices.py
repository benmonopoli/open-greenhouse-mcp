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
    """List all offices in the organization. Read-only. Uses cached data by default.

    Office IDs are needed for create_job, update_job, list_jobs (office_id filter),
    and add_future_job_permission (office scope). Pass force_refresh=true after org
    structure changes. For departments, use list_departments.
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
    """Get a single office by ID. Read-only. Returns the office name, location,
    parent office (if any), and child offices.

    Use list_offices to find office IDs. Offices support hierarchies via parent_id.
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

    Optionally nest under a parent office for hierarchical structure. To modify
    an existing office, use update_office. Office IDs are used when creating or
    filtering jobs.
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

    Only updates fields you provide. To create a new office, use create_office.
    To list all offices, use list_offices.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if location is not None:
        json_data["location"] = location
    return await client.harvest_patch(f"/offices/{office_id}", json_data=json_data)
