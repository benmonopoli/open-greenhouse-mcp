"""Harvest API — Departments tools (4 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_departments(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    parent_id: Annotated[
        int | None, Field(description="Only departments directly under this parent department")
    ] = None,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all departments. Read-only.

    Resolves department names to IDs. When a user mentions a department
    ("Engineering"), use this to find its ID for list_jobs, create_job,
    or add_future_job_permission. Each department has `parent_id` (null for
    top level); rebuild the tree from parent_id.
    """
    params: dict[str, Any] = {"per_page": per_page}
    if cursor:
        params["cursor"] = cursor
    if parent_id is not None:
        params["parent_id"] = parent_id
    return await client.harvest_get_cached(
        "/departments", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_department(
    client: GreenhouseClient,
    *,
    department_id: Annotated[int, Field(description="Department ID — get from list_departments")],
) -> dict[str, Any]:
    """Get a department by ID. Read-only.

    Returns name, parent_id, external_id, and `child_ids` (direct child
    departments). To find department_id: list_departments → match by name.
    """
    dept = await client.harvest_get_by_id("/departments", department_id)
    if client._is_error(dept):
        return dept
    children = await client.harvest_get(
        "/departments", params={"parent_id": department_id, "per_page": 500}, paginate="all"
    )
    if not client._is_error(children):
        dept["child_ids"] = [c.get("id") for c in children.get("items", [])]
    return dept


async def create_department(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Department name")],
    parent_id: Annotated[
        int | None,
        Field(description="Parent department ID for hierarchy — get from list_departments"),
    ] = None,
    external_id: Annotated[
        str | None, Field(description="Your HRIS/external identifier for this department")
    ] = None,
) -> dict[str, Any]:
    """Create a new department. Write operation — admin only.

    For parent_id (optional): list_departments → find parent by name.
    """
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if external_id is not None:
        json_data["external_id"] = external_id
    return await client.harvest_post("/departments", json_data=json_data)


async def update_department(
    client: GreenhouseClient,
    *,
    department_id: Annotated[int, Field(description="Department ID to update")],
    name: Annotated[str | None, Field(description="New department name")] = None,
    parent_id: Annotated[
        int | None, Field(description="New parent department ID — get from list_departments")
    ] = None,
    external_id: Annotated[
        str | None, Field(description="New HRIS/external identifier")
    ] = None,
) -> dict[str, Any]:
    """Update a department's name, parent or external ID. Write operation — admin only.

    To find department_id: list_departments → match by name. Greenhouse
    requires the name on every update, so the current name is kept when
    name is omitted.
    """
    if name is None:
        current = await client.harvest_get_by_id("/departments", department_id)
        if client._is_error(current):
            return current
        name = current.get("name")
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    if external_id is not None:
        json_data["external_id"] = external_id
    return await client.harvest_patch(f"/departments/{department_id}", json_data=json_data)
