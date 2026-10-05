"""Harvest API — Offices tools (4 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_offices(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    parent_id: Annotated[
        int | None, Field(description="Only offices directly under this parent office")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all offices. Read-only.

    Resolves office/location names to IDs. When a user mentions an office
    or location, use this to find its ID for list_jobs, create_job, or
    add_future_job_permission. Each office has a flat `location` string,
    `parent_id`, and `primary_in_house_contact_user_id`.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if parent_id is not None:
        params["parent_id"] = parent_id
    return await client.harvest_get_cached(
        "/offices", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_office(
    client: GreenhouseClient,
    *,
    office_id: Annotated[int, Field(description="Office ID — get from list_offices")],
) -> dict[str, Any]:
    """Get an office by ID. Read-only.

    Returns name, location, parent_id, and `child_ids` (direct child
    offices). To find office_id: list_offices → match by name.
    """
    office = await client.harvest_get_by_id("/offices", office_id)
    if client._is_error(office):
        return office
    children = await client.harvest_get(
        "/offices", params={"parent_id": office_id, "per_page": 500}, paginate="all"
    )
    if not client._is_error(children):
        office["child_ids"] = [c.get("id") for c in children.get("items", [])]
    return office


async def create_office(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Office name")],
    parent_id: Annotated[
        int | None, Field(description="Parent office ID for hierarchy — get from list_offices")
    ] = None,
    location: Annotated[
        str | None, Field(description="Location string, e.g. 'San Francisco, CA'")
    ] = None,
    primary_contact_user_id: Annotated[
        int | None, Field(description="User ID of the office's primary in-house contact")
    ] = None,
) -> dict[str, Any]:
    """Create a new office. Write operation — admin only.

    For parent_id (optional): list_offices → find parent by name. For the
    contact: list_users → match by name.
    """
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if location is not None:
        json_data["location"] = location
    if primary_contact_user_id is not None:
        json_data["primary_in_house_contact_user_id"] = primary_contact_user_id
    return await client.harvest_post("/offices", json_data=json_data)


async def update_office(
    client: GreenhouseClient,
    *,
    office_id: Annotated[int, Field(description="Office ID to update")],
    name: Annotated[str | None, Field(description="New office name")] = None,
    location: Annotated[str | None, Field(description="New location string")] = None,
    parent_id: Annotated[
        int | None, Field(description="New parent office ID — get from list_offices")
    ] = None,
    primary_contact_user_id: Annotated[
        int | None, Field(description="User ID of the new primary in-house contact")
    ] = None,
) -> dict[str, Any]:
    """Update an office's name, location, parent or contact. Write operation — admin only.

    To find office_id: list_offices → match by name. Greenhouse requires the
    name on every update, so the current name is kept when name is omitted.
    """
    if name is None:
        current = await client.harvest_get_by_id("/offices", office_id)
        if client._is_error(current):
            return current
        name = current.get("name")
    json_data: dict[str, Any] = {"name": name}
    if location is not None:
        json_data["location"] = location
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if primary_contact_user_id is not None:
        json_data["primary_in_house_contact_user_id"] = primary_contact_user_id
    return await client.harvest_patch(f"/offices/{office_id}", json_data=json_data)
