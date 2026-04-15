"""Harvest API — Interviews tools (6 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_interviews(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    page: Annotated[int, Field(description="Page number (starts at 1)")] = 1,
    created_after: Annotated[str | None, Field(description="ISO 8601 datetime — only interviews created after this")] = None,
    created_before: Annotated[str | None, Field(description="ISO 8601 datetime — only interviews created before this")] = None,
    paginate: Annotated[str, Field(description="'single' for one page, 'all' to auto-fetch every page")] = "single",
) -> dict[str, Any]:
    """List all scheduled interviews across all applications. Read-only.

    Returns interviews globally — use date range filters to narrow. For interviews
    on a specific application, use list_interviews_for_application instead. For
    candidates needing interview-related action, use candidates_needing_action.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": page}
    if created_after is not None:
        params["created_after"] = created_after
    if created_before is not None:
        params["created_before"] = created_before
    return await client.harvest_get("/scheduled_interviews", params=params, paginate=paginate)


async def list_interviews_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List all scheduled interviews for a specific application. Read-only.

    Use when you need interviews for one candidate's application. For all interviews
    globally, use list_interviews. Returns interview details including interviewers
    and scheduled times.
    """
    return await client.harvest_get(f"/applications/{application_id}/scheduled_interviews")


async def get_interview(
    client: GreenhouseClient,
    *,
    interview_id: Annotated[int, Field(description="Scheduled interview ID — get from list_interviews or list_interviews_for_application")],
) -> dict[str, Any]:
    """Get a single scheduled interview by ID. Read-only. Returns interview details
    including application, interviewers, start/end times, and interview type.

    Use list_interviews_for_application to find interview IDs for a candidate. To
    view submitted scorecards for an interview, use list_scorecards_for_application.
    """
    return await client.harvest_get_one(f"/scheduled_interviews/{interview_id}")


async def create_interview(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Application to schedule the interview for")],
    interview_id: Annotated[int, Field(description="Interview stage ID (defines the interview type) — get from list_job_stages_for_job")],
    interviewer_ids: Annotated[list[int], Field(description="User IDs of interviewers — get from list_users")],
    start: Annotated[str, Field(description="Start time as ISO 8601, e.g. '2024-03-15T10:00:00Z'")],
    end: Annotated[str, Field(description="End time as ISO 8601, e.g. '2024-03-15T11:00:00Z'")],
) -> dict[str, Any]:
    """Schedule an interview for an application. Write operation.

    The interview_id is the interview stage (from the job's pipeline), not a scheduled
    interview ID. Get interview stage IDs from list_job_stages_for_job. To reschedule,
    use update_interview. To cancel, use delete_interview.
    """
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
    interview_id: Annotated[int, Field(description="Scheduled interview ID to update")],
    start: Annotated[str | None, Field(description="New start time as ISO 8601")] = None,
    end: Annotated[str | None, Field(description="New end time as ISO 8601")] = None,
    interviewer_ids: Annotated[list[int] | None, Field(description="Replaces all interviewers — provide the full list")] = None,
) -> dict[str, Any]:
    """Update a scheduled interview's time or interviewers. Write operation.

    Only updates fields you provide. Note: interviewer_ids replaces the full list (not
    a merge). To cancel an interview entirely, use delete_interview. To find scheduled
    interview IDs, use list_interviews_for_application.
    """
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
    interview_id: Annotated[int, Field(description="Scheduled interview ID to cancel/delete")],
) -> dict[str, Any]:
    """Delete (cancel) a scheduled interview. Write operation — cannot be undone.

    Removes the scheduled interview. Any submitted scorecards remain on the application.
    To reschedule instead of canceling, use update_interview.
    """
    return await client.harvest_delete(f"/scheduled_interviews/{interview_id}")
