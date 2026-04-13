"""Harvest API — Job Openings tools (5 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_job_openings(
    client: GreenhouseClient,
    *,
    job_id: int,
    status: str | None = None,
) -> dict[str, Any]:
    """List all openings for a job, optionally filtered by status (open/closed)."""
    params: dict[str, Any] = {}
    if status is not None:
        params["status"] = status
    return await client.harvest_get(f"/jobs/{job_id}/openings", params=params)


async def get_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: int,
) -> dict[str, Any]:
    """Get a specific opening on a job."""
    return await client.harvest_get_one(f"/jobs/{job_id}/openings/{opening_id}")


async def create_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: str | None = None,
    status: str | None = None,
    close_reason_id: int | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new opening on a job with optional opening ID, status, and custom fields."""
    json_data: dict[str, Any] = {}
    if opening_id is not None:
        json_data["opening_id"] = opening_id
    if status is not None:
        json_data["status"] = status
    if close_reason_id is not None:
        json_data["close_reason_id"] = close_reason_id
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_post(f"/jobs/{job_id}/openings", json_data=json_data)


async def update_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: int,
    status: str | None = None,
    close_reason_id: int | None = None,
    custom_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update a job opening's status, close reason, or custom fields."""
    json_data: dict[str, Any] = {}
    if status is not None:
        json_data["status"] = status
    if close_reason_id is not None:
        json_data["close_reason_id"] = close_reason_id
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(
        f"/jobs/{job_id}/openings/{opening_id}", json_data=json_data
    )


async def delete_job_opening(
    client: GreenhouseClient,
    *,
    job_id: int,
    opening_id: int,
) -> dict[str, Any]:
    """Delete a specific opening from a job."""
    return await client.harvest_delete(f"/jobs/{job_id}/openings/{opening_id}")
