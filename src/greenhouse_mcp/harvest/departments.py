"""Harvest API — Departments tools (4 tools)."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_departments(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all departments. Read-only.

    Resolves department names to IDs. When a user mentions a department
    ("Engineering"), use this to find its ID for list_jobs, create_job,
    or add_future_job_permission.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/departments", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_department(
    client: GreenhouseClient,
    *,
    department_id: Annotated[int, Field(description="Department ID — get from list_departments")],
) -> dict[str, Any]:
    """Get a department by ID. Read-only.

    Returns name, parent department, and child departments.
    To find department_id: list_departments → match by name.
    """
    return await client.harvest_get_one(f"/departments/{department_id}")


async def create_department(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Department name")],
    parent_id: Annotated[
        int | None,
        Field(description="Parent department ID for hierarchy — get from list_departments"),
    ] = None,
) -> dict[str, Any]:
    """Create a new department. Write operation — admin only.

    For parent_id (optional): list_departments → find parent by name.
    """
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    return await client.harvest_post("/departments", json_data=json_data)


async def update_department(
    client: GreenhouseClient,
    *,
    department_id: Annotated[int, Field(description="Department ID to update")],
    name: Annotated[str | None, Field(description="New department name")] = None,
    parent_id: Annotated[
        int | None, Field(description="New parent department ID — set to null to make top-level")
    ] = None,
) -> dict[str, Any]:
    """Update a department's name or parent. Write operation — admin only.

    To find department_id: list_departments → match by name.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    return await client.harvest_patch(f"/departments/{department_id}", json_data=json_data)
