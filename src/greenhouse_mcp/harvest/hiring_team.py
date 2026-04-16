"""Harvest API — Hiring Team tools (4 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def get_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
) -> dict[str, Any]:
    """Get the hiring team for a job. Read-only.

    Users say "who's on the hiring team for Backend Engineer?" To find job_id:
    list_jobs → match by name. Returns members grouped by role: hiring managers,
    recruiters, sourcers, and coordinators.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}/hiring_team")


async def replace_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    hiring_managers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} — replaces all hiring managers")] = None,
    sourcers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} — replaces all sourcers")] = None,
    recruiters: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} — replaces all recruiters")] = None,
    coordinators: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} — replaces all coordinators")] = None,
) -> dict[str, Any]:
    """Replace the entire hiring team for a job. Write operation — overwrites existing members.

    To find job_id: list_jobs → match by name. For member user_ids: list_users
    → match each person by name. Pass arrays for each role (hiring_managers,
    recruiters, sourcers, coordinators).
    """
    json_data: dict[str, Any] = {}
    if hiring_managers is not None:
        json_data["hiring_managers"] = hiring_managers
    if sourcers is not None:
        json_data["sourcers"] = sourcers
    if recruiters is not None:
        json_data["recruiters"] = recruiters
    if coordinators is not None:
        json_data["coordinators"] = coordinators
    return await client.harvest_put(f"/jobs/{job_id}/hiring_team", json_data=json_data)


async def add_hiring_team_members(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    hiring_managers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} to add as hiring managers")] = None,
    sourcers: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} to add as sourcers")] = None,
    recruiters: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} to add as recruiters")] = None,
    coordinators: Annotated[list[dict[str, Any]] | None, Field(description="Array of {user_id: N} to add as coordinators")] = None,
) -> dict[str, Any]:
    """Add members to a hiring team without replacing existing ones. Write operation.

    To find job_id: list_jobs → match by name. For member user_ids: list_users
    → match by name.
    """
    json_data: dict[str, Any] = {}
    if hiring_managers is not None:
        json_data["hiring_managers"] = hiring_managers
    if sourcers is not None:
        json_data["sourcers"] = sourcers
    if recruiters is not None:
        json_data["recruiters"] = recruiters
    if coordinators is not None:
        json_data["coordinators"] = coordinators
    return await client.harvest_post(f"/jobs/{job_id}/hiring_team", json_data=json_data)


async def remove_hiring_team_member(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    user_id: Annotated[int, Field(description="User ID to remove from the hiring team — get from get_hiring_team")],
) -> dict[str, Any]:
    """Remove someone from a job's hiring team. Write operation.

    To find job_id: list_jobs → match by name. For user_id: list_users → match
    by name, or get_hiring_team to see current members and their IDs.
    """
    return await client.harvest_delete(f"/jobs/{job_id}/hiring_team/members/{user_id}")
