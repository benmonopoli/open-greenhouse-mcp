"""Harvest API — Interviews tools (6 tools)."""
from __future__ import annotations

from typing import Any

from greenhouse_mcp.client import GreenhouseClient


async def list_interviews(
    client: GreenhouseClient,
    *,
    per_page: int = 500,
    page: int = 1,
    created_after: str | None = None,
    created_before: str | None = None,
    paginate: str = "single",
) -> dict[str, Any]:
    """List all scheduled interviews, with optional created date range filters."""
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/scheduled_interviews", params=params, paginate=paginate)


async def list_interviews_for_application(
    client: GreenhouseClient,
    *,
    application_id: int,
) -> dict[str, Any]:
    """List all scheduled interviews for a specific application."""
    return await client.harvest_get(f"/applications/{application_id}/scheduled_interviews")


async def get_interview(
    client: GreenhouseClient,
    *,
    interview_id: int,
) -> dict[str, Any]:
    """Get a single scheduled interview by ID."""
    return await client.harvest_get_one(f"/scheduled_interviews/{interview_id}")


async def create_interview(
    client: GreenhouseClient,
    *,
    application_id: int,
    interview_id: int,
    interviewer_ids: list[int],
    start: str,
    end: str,
) -> dict[str, Any]:
    """Schedule an interview for an application with interviewers and a start/end time."""
    json_data: dict[str, Any] = {
        "interview_id": interview_id,
        "interviewers": [{"id": i} for i in interviewer_ids],
        "start": start,
        "end": end,
    }
    return await client.harvest_post(
        f"/applications/{application_id}/scheduled_interviews", json_data=json_data
    )


async def update_interview(
    client: GreenhouseClient,
    *,
    interview_id: int,
    start: str | None = None,
    end: str | None = None,
    interviewer_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Update a scheduled interview's start time, end time, or interviewers."""
    json_data: dict[str, Any] = {}
    if start is not None:
        json_data["start"] = start
    if end is not None:
        json_data["end"] = end
    if interviewer_ids is not None:
        json_data["interviewers"] = [{"id": i} for i in interviewer_ids]
    return await client.harvest_patch(f"/scheduled_interviews/{interview_id}", json_data=json_data)


async def delete_interview(
    client: GreenhouseClient,
    *,
    interview_id: int,
) -> dict[str, Any]:
    """Delete a scheduled interview by ID."""
    return await client.harvest_delete(f"/scheduled_interviews/{interview_id}")
