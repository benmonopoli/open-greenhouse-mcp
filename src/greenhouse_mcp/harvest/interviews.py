"""Harvest API — Interviews tools (6 tools).

v1 "scheduled interviews" are ``/v3/interviews``. Interviewers live in
``/v3/interviewers`` and the interview's name on ``/v3/job_interviews``; list/get tools
resolve both (plus user names) with batched lookups.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient, add_date_filter
from greenhouse_mcp.harvest.jobs import _by_id, _lookup, _user_ref, _with_warnings


async def _hydrate_interviews(
    client: GreenhouseClient, interviews: list[dict[str, Any]], warnings: list[str]
) -> None:
    """Add ``interview`` {id, name}, ``interviewers`` and ``organizer`` to each, in place."""
    if not interviews:
        return
    panel, slots = await asyncio.gather(
        _lookup(
            client, "/interviewers", {i.get("id") for i in interviews}, warnings,
            filter_name="interview_ids",
        ),
        _lookup(client, "/job_interviews", {i.get("job_interview_id") for i in interviews},
                warnings),
    )
    user_ids = {p.get("user_id") for p in panel} | {i.get("organizer_id") for i in interviews}
    users = _by_id(await _lookup(client, "/users", user_ids, warnings))
    slot_map = _by_id(slots)
    by_interview: dict[int, list[dict[str, Any]]] = {}
    for p in panel:
        ref = _user_ref(p.get("user_id"), users) or {"id": None, "name": None}
        ref["email"] = ref.get("email") or p.get("email")
        ref["response_status"] = p.get("response_status")
        ref["scorecard_id"] = p.get("scorecard_id")
        by_interview.setdefault(p.get("interview_id") or 0, []).append(ref)
    for iv in interviews:
        jid = iv.get("job_interview_id")
        iv["interview"] = {"id": jid, "name": slot_map.get(jid or 0, {}).get("name")}
        iv["interviewers"] = by_interview.get(iv.get("id") or 0, [])
        iv["organizer"] = _user_ref(iv.get("organizer_id"), users)


async def _list(
    client: GreenhouseClient, params: dict[str, Any], paginate: str, include_details: bool
) -> dict[str, Any]:
    result = await client.harvest_get("/interviews", params=params, paginate=paginate)
    if client._is_error(result) or not include_details:
        return result
    warnings: list[str] = []
    await _hydrate_interviews(client, result.get("items", []), warnings)
    return _with_warnings(result, warnings)


def _panel(
    interviewer_ids: list[int], statuses: dict[int, str] | None = None
) -> list[dict[str, Any]]:
    """v3 interviewer entries; keeps a known RSVP, otherwise ``needs_action``."""
    statuses = statuses or {}
    return [
        {"user_id": i, "response_status": statuses.get(i) or "needs_action"}
        for i in interviewer_ids
    ]


async def list_interviews(
    client: GreenhouseClient,
    *,
    per_page: Annotated[int, Field(description="Results per page (max 500)")] = 500,
    cursor: Annotated[
        str | None,
        Field(description="Pass next_cursor from the previous response to get the next page"),
    ] = None,
    created_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only interviews created at/after this")
    ] = None,
    created_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only interviews created before this")
    ] = None,
    starts_after: Annotated[
        str | None, Field(description="ISO 8601 datetime — only interviews starting at/after this")
    ] = None,
    starts_before: Annotated[
        str | None, Field(description="ISO 8601 datetime — only interviews starting before this")
    ] = None,
    job_id: Annotated[
        int | None, Field(description="Only interviews on this job — get ID from list_jobs")
    ] = None,
    status: Annotated[
        str | None,
        Field(
            description="Filter by status, e.g. 'scheduled', 'awaiting_feedback', 'complete', "
            "'to_be_scheduled'"
        ),
    ] = None,
    include_details: Annotated[
        bool,
        Field(description="Resolve interview name, interviewers and organizer (extra calls)"),
    ] = True,
    paginate: Annotated[
        str, Field(description="'single' for one page, 'all' to auto-fetch every page")
    ] = "single",
) -> dict[str, Any]:
    """List scheduled interviews across all applications. Read-only.

    Each interview has id, application_id, job_id, starts_at/ends_at (or
    all_day_start_on/all_day_end_on), status, location, video_conferencing_url,
    plus (with include_details) interview {id, name}, interviewers [{id, name,
    email, response_status, scorecard_id}] and organizer. For a specific
    candidate's interviews, use list_interviews_for_application
    (search_candidates_by_name → list_applications(candidate_id=...) → match
    the application → use its ID).
    """
    params: dict[str, Any] = {
        "per_page": per_page,
        "cursor": cursor,
        "status": status,
        "job_ids": [job_id] if job_id is not None else None,
    }
    add_date_filter(params, "created_at", gte=created_after, lt=created_before)
    add_date_filter(params, "starts_at", gte=starts_after, lt=starts_before)
    return await _list(client, params, paginate, include_details)


async def list_interviews_for_application(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Greenhouse application ID")],
) -> dict[str, Any]:
    """List scheduled interviews for a specific application. Read-only.

    To find the application_id: search_candidates_by_name →
    list_applications(candidate_id=...) → match the application to the job.
    Returns all interviews with times, interview name, interviewers (with
    their scorecard_id), and status.
    """
    params = {"application_ids": [application_id], "per_page": 500}
    return await _list(client, params, "all", True)


async def get_interview(
    client: GreenhouseClient,
    *,
    interview_id: Annotated[
        int,
        Field(
            description="Scheduled interview ID — from list_interviews_for_application"
        ),
    ],
) -> dict[str, Any]:
    """Get a scheduled interview by ID. Read-only.

    Returns details: application, interview name, interviewers, organizer,
    times, location, and status. To find interview IDs:
    list_interviews_for_application on the candidate's app.
    """
    interview = await client.harvest_get_by_id("/interviews", interview_id)
    if client._is_error(interview):
        return interview
    warnings: list[str] = []
    await _hydrate_interviews(client, [interview], warnings)
    return _with_warnings(interview, warnings)


async def create_interview(
    client: GreenhouseClient,
    *,
    application_id: Annotated[int, Field(description="Application to schedule the interview for")],
    interview_id: Annotated[
        int,
        Field(
            description="Job interview ID (the interview on the job's plan) — from "
            "list_job_stages_for_job → stage interviews[].id"
        ),
    ],
    interviewer_ids: Annotated[
        list[int], Field(description="User IDs of interviewers — get from list_users")
    ],
    start: Annotated[str, Field(description="Start time as ISO 8601, e.g. '2024-03-15T10:00:00Z'")],
    end: Annotated[str, Field(description="End time as ISO 8601, e.g. '2024-03-15T11:00:00Z'")],
    external_event_id: Annotated[
        str | None,
        Field(
            description="ID of the matching event on the organizer's calendar (Google/Outlook). "
            "A placeholder is generated if omitted"
        ),
    ] = None,
    location: Annotated[str | None, Field(description="Room, address, or meeting link")] = None,
    video_conferencing_url: Annotated[
        str | None, Field(description="Video call join URL")
    ] = None,
) -> dict[str, Any]:
    """Record a scheduled interview for an application. Write operation.

    Users say "schedule an interview for Sarah on the Backend role." To get
    application_id: search_candidates_by_name → list_applications(candidate_id=...)
    → match app. For interviewer_ids: list_users → match by name. interview_id
    is the job interview from list_job_stages_for_job (interviews[].id). This
    records the interview in Greenhouse; it does not send calendar invites.
    """
    json_data: dict[str, Any] = {
        "application_id": application_id,
        "job_interview_id": interview_id,
        "interviewers": _panel(interviewer_ids),
        "starts_at": start,
        "ends_at": end,
        "external_event_id": external_event_id or f"greenhouse-mcp-{uuid.uuid4()}",
    }
    if location is not None:
        json_data["location"] = location
    if video_conferencing_url is not None:
        json_data["video_conferencing_url"] = video_conferencing_url
    return await client.harvest_post("/interviews", json_data=json_data)


async def update_interview(
    client: GreenhouseClient,
    *,
    interview_id: Annotated[int, Field(description="Scheduled interview ID to update")],
    start: Annotated[str | None, Field(description="New start time as ISO 8601")] = None,
    end: Annotated[str | None, Field(description="New end time as ISO 8601")] = None,
    interviewer_ids: Annotated[
        list[int] | None, Field(description="Replaces all interviewers — provide the full list")
    ] = None,
    location: Annotated[str | None, Field(description="New location or meeting link")] = None,
    video_conferencing_url: Annotated[
        str | None, Field(description="New video call join URL")
    ] = None,
) -> dict[str, Any]:
    """Update a scheduled interview's time, interviewers, or location. Write operation.

    To find interview_id: list_interviews_for_application on the candidate's
    app. For new interviewer_ids: list_users → match by name. When replacing
    interviewers, existing panel members keep their RSVP; new ones start as
    needs_action.
    """
    json_data: dict[str, Any] = {}
    if start is not None:
        json_data["starts_at"] = start
    if end is not None:
        json_data["ends_at"] = end
    if interviewer_ids is not None:
        current = await client.harvest_get(
            "/interviewers", params={"interview_ids": [interview_id], "per_page": 500},
            paginate="all",
        )
        statuses: dict[int, str] = {}
        if not client._is_error(current):
            statuses = {
                p["user_id"]: p.get("response_status")
                for p in current.get("items", [])
                if p.get("user_id") is not None
            }
        json_data["interviewers"] = _panel(interviewer_ids, statuses)
    if location is not None:
        json_data["location"] = location
    if video_conferencing_url is not None:
        json_data["video_conferencing_url"] = video_conferencing_url
    return await client.harvest_patch(f"/interviews/{interview_id}", json_data=json_data)


async def delete_interview(
    client: GreenhouseClient,
    *,
    interview_id: Annotated[int, Field(description="Scheduled interview ID to cancel/delete")],
) -> dict[str, Any]:
    """Cancel a scheduled interview. Write operation — cannot be undone.

    To find interview_id: list_interviews_for_application on the candidate's
    app.
    """
    return await client.harvest_delete(f"/interviews/{interview_id}")
