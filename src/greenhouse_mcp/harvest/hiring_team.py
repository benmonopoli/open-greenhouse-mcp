"""Harvest API — Hiring Team tools (4 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def get_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: int,
) -> dict[str, Any]:
    """Get the hiring team (managers, recruiters, sourcers, coordinators) for a job."""
    return await client.harvest_get(f"/jobs/{job_id}/hiring_team")


async def replace_hiring_team(
    client: GreenhouseClient,
    *,
    job_id: int,
    hiring_managers: list[dict[str, Any]] | None = None,
    sourcers: list[dict[str, Any]] | None = None,
    recruiters: list[dict[str, Any]] | None = None,
    coordinators: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Replace the entire hiring team for a job with new members by role."""
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
    job_id: int,
    hiring_managers: list[dict[str, Any]] | None = None,
    sourcers: list[dict[str, Any]] | None = None,
    recruiters: list[dict[str, Any]] | None = None,
    coordinators: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add new members to a job's hiring team without replacing existing members."""
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
    job_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Remove a user from a job's hiring team."""
    return await client.harvest_delete(f"/jobs/{job_id}/hiring_team/members/{user_id}")
