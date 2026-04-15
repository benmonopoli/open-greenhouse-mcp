"""Harvest API — Job Openings tools (5 tools)."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from greenhouse_mcp.client import GreenhouseClient


async def list_job_openings(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    status: Annotated[str | None, Field(description="Filter by status: 'open' or 'closed'")] = None,
) -> dict[str, Any]:
    """List all openings for a job. Read-only. An opening represents one headcount
    to fill — a job can have multiple openings.

    Filter by status to see only open or closed openings. Openings are filled via
    hire_application. To create a new opening, use create_job_opening.
    """
    params: dict[str, Any] = {}
    if status is not None:
        params["status"] = status
    return await client.harvest_get(f"/jobs/{job_id}/openings", params=params)


async def get_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID within the job — get from list_job_openings")],
) -> dict[str, Any]:
    """Get a specific opening on a job. Read-only. Returns the opening status,
    custom fields, and associated hired application if closed.

    Use list_job_openings to find opening IDs. Openings track individual headcount
    on a job.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}/openings/{opening_id}")


async def create_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[str | None, Field(description="Custom external opening identifier (not the Greenhouse ID)")] = None,
    status: Annotated[str | None, Field(description="Initial status: 'open' (default) or 'closed'")] = None,
    close_reason_id: Annotated[int | None, Field(description="If closing immediately — get from list_close_reasons")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...} — get field IDs from list_custom_fields")] = None,
) -> dict[str, Any]:
    """Create a new opening (headcount) on a job. Write operation.

    Each opening represents one position to fill. Openings are filled when an
    application is hired via hire_application. To update or close an opening, use
    update_job_opening. To delete, use delete_job_opening.
    """
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
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID within the job")],
    status: Annotated[str | None, Field(description="New status: 'open' or 'closed'")] = None,
    close_reason_id: Annotated[int | None, Field(description="Reason for closing — get from list_close_reasons")] = None,
    custom_fields: Annotated[list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...}")] = None,
) -> dict[str, Any]:
    """Update a job opening's status, close reason, or custom fields. Write operation.

    Use this to close an opening manually or update its custom fields. Openings are
    also closed automatically when an application is hired. To create new openings,
    use create_job_opening.
    """
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
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID to delete")],
) -> dict[str, Any]:
    """Delete a job opening. Destructive — cannot be undone.

    Removes the opening record. To close an opening without deleting, use
    update_job_opening with status='closed' instead.
    """
    return await client.harvest_delete(f"/jobs/{job_id}/openings/{opening_id}")
