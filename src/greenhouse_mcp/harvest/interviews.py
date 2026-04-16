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

    For interviews on a specific candidate's application, use
    list_interviews_for_application (search_candidates_by_name → get_candidate
    → match application → use its ID).
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
    """List scheduled interviews for a specific application. Read-only.

    To find the application_id: search_candidates_by_name → get_candidate →
    match the application to the job. Returns all interviews with times,
    interviewers, and status.
    """
    return await client.harvest_get(f"/applications/{application_id}/scheduled_interviews")


async def get_interview(
    client: GreenhouseClient,
    *,
    interview_id: Annotated[int, Field(description="Scheduled interview ID — get from list_interviews or list_interviews_for_application")],
) -> dict[str, Any]:
    """Get a scheduled interview by ID. Read-only.

    Returns details: application, interviewers, times, and type. To find
    interview IDs: list_interviews_for_application on the candidate's app.
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

    Users say "schedule an interview for Sarah on the Backend role." To get
    application_id: search_candidates_by_name → get_candidate → match app.
    For interviewer_ids: list_users → match by name. The interview_id refers
    to the interview template from the job's stage configuration.
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

    To find interview_id: list_interviews_for_application on the candidate's
    app. For new interviewer_ids: list_users → match by name.
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
    """Cancel a scheduled interview. Write operation — cannot be undone.

    To find interview_id: list_interviews_for_application on the candidate's
    app.
    """
    return await client.harvest_delete(f"/scheduled_interviews/{interview_id}")
