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
    """List openings (headcount) for a job. Read-only.

    An opening represents one position to fill — a job can have multiple.
    To find job_id: list_jobs → match by name.
    """
    params: dict[str, Any] = {}
    if status is not None:
        params["status"] = status
    return await client.harvest_get(f"/jobs/{job_id}/openings", params=params)


async def get_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[
        int, Field(description="Opening ID within the job — get from list_job_openings")
    ],
) -> dict[str, Any]:
    """Get a specific opening on a job. Read-only.

    Returns status, custom fields, and the hired application if filled.
    To find job_id: list_jobs → match by name. To find opening_id: list_job_openings on the job.
    """
    return await client.harvest_get_one(f"/jobs/{job_id}/openings/{opening_id}")


async def create_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[
        str | None, Field(description="Custom external opening identifier (not the Greenhouse ID)")
    ] = None,
    status: Annotated[
        str | None, Field(description="Initial status: 'open' (default) or 'closed'")
    ] = None,
    close_reason_id: Annotated[
        int | None, Field(description="If closing immediately — get from list_close_reasons")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="Array of {id, value} — get field IDs from list_custom_fields"
        ),
    ] = None,
) -> dict[str, Any]:
    """Add a new headcount to a job. Write operation.

    Users say "add another opening to the Backend role." To find job_id:
    list_jobs → match by name.
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
    close_reason_id: Annotated[
        int | None, Field(description="Reason for closing — get from list_close_reasons")
    ] = None,
    custom_fields: Annotated[
        list[dict[str, Any]] | None, Field(description="Array of {id: field_id, value: ...}")
    ] = None,
) -> dict[str, Any]:
    """Update a job opening's status or custom fields. Write operation.

    To find job_id: list_jobs → match by name. To find opening_id: list_job_openings on the job.
    For close_reason_id: list_close_reasons → match by name.
    """
    json_data: dict[str, Any] = {}
    if status is not None:
        json_data["status"] = status
    if close_reason_id is not None:
        json_data["close_reason_id"] = close_reason_id
    if custom_fields is not None:
        json_data["custom_fields"] = custom_fields
    return await client.harvest_patch(f"/jobs/{job_id}/openings/{opening_id}", json_data=json_data)


async def delete_job_opening(
    client: GreenhouseClient,
    *,
    job_id: Annotated[int, Field(description="Greenhouse job ID")],
    opening_id: Annotated[int, Field(description="Opening ID to delete")],
) -> dict[str, Any]:
    """Delete a job opening. Destructive — cannot be undone.

    To find job_id: list_jobs → match by name. To find opening_id: list_job_openings on the job.
    """
    return await client.harvest_delete(f"/jobs/{job_id}/openings/{opening_id}")
