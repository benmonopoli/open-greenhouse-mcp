"""Harvest API — Departments tools (4 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_departments(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    paginate: str = "single",
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List all departments in the organization."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    return await client.harvest_get_cached(
        "/departments", params=params, paginate=paginate, force_refresh=force_refresh
    )


async def get_department(
    client: GreenhouseClient,
    *,
    department_id: int,
) -> dict[str, Any]:
    """Get a single department by ID."""
    return await client.harvest_get_one(f"/departments/{department_id}")


async def create_department(
    client: GreenhouseClient,
    *,
    name: str,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Create a new department with a name and optional parent department."""
    json_data: dict[str, Any] = {"name": name}
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    return await client.harvest_post("/departments", json_data=json_data)


async def update_department(
    client: GreenhouseClient,
    *,
    department_id: int,
    name: str | None = None,
    parent_id: int | None = None,
) -> dict[str, Any]:
    """Update a department's name or parent department."""
    json_data: dict[str, Any] = {}
    if name is not None:
        json_data["name"] = name
    if parent_id is not None:
        json_data["parent_id"] = parent_id
    return await client.harvest_patch(f"/departments/{department_id}", json_data=json_data)
