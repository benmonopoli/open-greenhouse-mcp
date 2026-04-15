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
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
    force_refresh: Annotated[bool, Field(description="Bypass cache and fetch fresh data")] = False,
) -> dict[str, Any]:
    """List all departments in the organization. Read-only. Uses cached data by default.

    Department IDs are needed for create_job, update_job, list_jobs (department_id
    filter), and add_future_job_permission (department scope). Pass force_refresh=true
    after org structure changes. For offices, use list_offices.
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
    """Get a single department by ID. Read-only. Returns the department name,
    parent department (if any), and child departments.

    Use list_departments to find department IDs. Departments support hierarchies
    via parent_id.
    """
    return await client.harvest_get_one(f"/departments/{department_id}")


async def create_department(
    client: GreenhouseClient,
    *,
    name: Annotated[str, Field(description="Department name")],
    parent_id: Annotated[int | None, Field(description="Parent department ID for hierarchy — get from list_departments")] = None,
) -> dict[str, Any]:
    """Create a new department. Write operation — admin only.

    Optionally nest under a parent department for hierarchical org structure. To
    modify an existing department, use update_department. Department IDs are used
    when creating or filtering jobs.
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
    parent_id: Annotated[int | None, Field(description="New parent department ID — set to null to make top-level")] = None,
) -> dict[str, Any]:
    """Update a department's name or parent. Write operation — admin only.

    Only updates fields you provide. To create a new department, use create_department.
    To list all departments, use list_departments.
    """
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    return await client.harvest_patch(f"/departments/{department_id}", json_data=json_data)
