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
    """Get the hiring team for a job. Read-only. Returns members grouped by role:
    hiring managers, recruiters, sourcers, and coordinators.

    To modify the team, use add_hiring_team_members (additive) or replace_hiring_team
    (full replacement). To remove a single member, use remove_hiring_team_member.
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
    """Replace the entire hiring team for a job. Write operation — overwrites all
    members in the specified roles.

    Only roles you provide are replaced — omitted roles are unchanged. To add
    members without replacing, use add_hiring_team_members instead. Get user IDs
    from list_users.
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
    """Add members to a job's hiring team without replacing existing members. Write operation.

    Appends to the existing team. To replace the full team, use replace_hiring_team
    instead. To remove a member, use remove_hiring_team_member. Get user IDs from
    list_users.
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
    """Remove a user from a job's hiring team. Write operation.

    Removes the user from all roles on this job. To add members, use
    add_hiring_team_members. To view the current team, use get_hiring_team.
    """
    return await client.harvest_delete(f"/jobs/{job_id}/hiring_team/members/{user_id}")
